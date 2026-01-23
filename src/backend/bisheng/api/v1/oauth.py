# src/backend/bisheng/api/v1/oauth.py
"""OAuth 2.0 API 端点"""
import secrets
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from loguru import logger
from pydantic import BaseModel, Field

from bisheng.api.v1.schemas import resp_200
from bisheng.common.dependencies.user_deps import UserPayload
from bisheng.database.dao.oauth import (
    OAuthApplicationDao,
    OAuthAuthorizationCodeDao,
    OAuthTokenDao,
)

router = APIRouter(prefix='/oauth', tags=['OAuth'])


# ============== Request/Response Models ==============

class ApplicationCreate(BaseModel):
    """创建应用请求"""
    name: str = Field(..., max_length=128, description="应用名称")
    redirect_uri: str = Field(..., max_length=512, description="授权回调地址")


class ApplicationResponse(BaseModel):
    """应用响应"""
    id: str = Field(..., description="应用ID")
    name: str = Field(..., description="应用名称")
    client_id: str = Field(..., description="客户端ID")
    client_secret: Optional[str] = Field(default=None, description="客户端密钥（仅创建时返回）")
    redirect_uri: str = Field(..., description="授权回调地址")
    status: int = Field(..., description="状态: 1启用 0禁用")
    create_time: datetime = Field(..., description="创建时间")


class TokenRequest(BaseModel):
    """Token 请求"""
    grant_type: str = Field(..., description="授权类型: authorization_code 或 refresh_token")
    client_id: str = Field(..., description="客户端ID")
    client_secret: str = Field(..., description="客户端密钥")
    code: Optional[str] = Field(default=None, description="授权码（grant_type=authorization_code 时必填）")
    redirect_uri: Optional[str] = Field(default=None, description="回调地址（grant_type=authorization_code 时必填）")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌（grant_type=refresh_token 时必填）")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    refresh_token: str = Field(..., description="刷新令牌")


# ============== 应用管理端点（需要登录） ==============

@router.post('/applications')
async def create_application(
    request: ApplicationCreate,
    login_user: UserPayload = Depends(UserPayload.get_login_user)
):
    """创建 OAuth 应用

    创建一个新的 OAuth 应用，返回 client_id 和 client_secret。
    注意：client_secret 仅在创建时返回一次，请妥善保存。
    """
    app = OAuthApplicationDao.create(
        name=request.name,
        redirect_uri=request.redirect_uri,
        user_id=login_user.user_id
    )

    response = ApplicationResponse(
        id=app.id,
        name=app.name,
        client_id=app.client_id,
        client_secret=app.client_secret,  # 仅创建时返回
        redirect_uri=app.redirect_uri,
        status=app.status,
        create_time=app.create_time
    )

    return resp_200(data=response.model_dump())


@router.get('/applications')
async def list_applications(
    login_user: UserPayload = Depends(UserPayload.get_login_user)
):
    """获取用户的 OAuth 应用列表

    返回当前登录用户创建的所有 OAuth 应用。
    注意：列表中不包含 client_secret。
    """
    apps = OAuthApplicationDao.get_by_user_id(login_user.user_id)

    result = [
        ApplicationResponse(
            id=app.id,
            name=app.name,
            client_id=app.client_id,
            client_secret=None,  # 列表不返回 secret
            redirect_uri=app.redirect_uri,
            status=app.status,
            create_time=app.create_time
        ).model_dump()
        for app in apps
    ]

    return resp_200(data=result)


@router.delete('/applications/{app_id}')
async def delete_application(
    app_id: str,
    login_user: UserPayload = Depends(UserPayload.get_login_user)
):
    """删除 OAuth 应用

    删除指定的 OAuth 应用。只能删除自己创建的应用。
    """
    success = OAuthApplicationDao.delete(app_id, login_user.user_id)

    if not success:
        raise HTTPException(status_code=404, detail="应用不存在或无权删除")

    return resp_200(message="删除成功")


# ============== 授权流程端点 ==============

@router.get('/authorize')
async def authorize(
    client_id: str = Query(..., description="客户端ID"),
    redirect_uri: str = Query(..., description="回调地址"),
    response_type: str = Query(default="code", description="响应类型，固定为 code"),
    state: Optional[str] = Query(default=None, description="状态参数，原样返回"),
    login_user: UserPayload = Depends(UserPayload.get_login_user)
):
    """OAuth 授权端点

    用户登录后访问此端点，生成授权码并重定向到回调地址。

    流程：
    1. 验证 client_id 和 redirect_uri
    2. 生成授权码
    3. 重定向到 redirect_uri，携带 code 和 state 参数
    """
    if response_type != "code":
        raise HTTPException(status_code=400, detail="不支持的 response_type，仅支持 code")

    # 验证应用
    app = OAuthApplicationDao.get_by_client_id(client_id)
    if not app:
        raise HTTPException(status_code=400, detail="无效的 client_id")

    # 验证 redirect_uri
    if app.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri 不匹配")

    # 生成授权码
    auth_code = OAuthAuthorizationCodeDao.create(
        client_id=client_id,
        user_id=login_user.user_id,
        redirect_uri=redirect_uri
    )

    # 构建重定向 URL
    params = {"code": auth_code.code}
    if state:
        params["state"] = state

    redirect_url = f"{redirect_uri}?{urlencode(params)}"

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post('/token')
async def get_token(request: TokenRequest):
    """获取/刷新 Token

    支持两种授权类型：
    1. authorization_code: 使用授权码换取 Token
    2. refresh_token: 使用刷新令牌获取新的 Token

    此端点不需要用户登录，通过 client_id 和 client_secret 进行身份验证。
    """
    # 验证应用
    app = OAuthApplicationDao.get_by_client_id(request.client_id)
    # 使用常量时间比较防止时序攻击
    if not app or not secrets.compare_digest(app.client_secret, request.client_secret):
        logger.warning(f"OAuth token request failed: invalid client credentials for client_id={request.client_id}")
        raise HTTPException(status_code=401, detail="无效的客户端凭证")

    # 检查应用状态
    if app.status != 1:
        logger.warning(f"OAuth token request failed: application disabled for client_id={request.client_id}")
        raise HTTPException(status_code=401, detail="应用已被禁用")

    if request.grant_type == "authorization_code":
        # 授权码模式
        if not request.code:
            raise HTTPException(status_code=400, detail="缺少授权码")
        if not request.redirect_uri:
            raise HTTPException(status_code=400, detail="缺少 redirect_uri")

        # 获取并验证授权码
        auth_code = OAuthAuthorizationCodeDao.get_and_delete(request.code)
        if not auth_code:
            raise HTTPException(status_code=400, detail="无效或已过期的授权码")

        # 验证 client_id 和 redirect_uri
        if auth_code.client_id != request.client_id:
            raise HTTPException(status_code=400, detail="client_id 不匹配")
        if auth_code.redirect_uri != request.redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri 不匹配")

        # 创建 Token
        token = OAuthTokenDao.create(
            client_id=request.client_id,
            user_id=auth_code.user_id
        )
        logger.info(f"OAuth token created: client_id={request.client_id}, user_id={auth_code.user_id}")

        # 计算过期时间（秒）
        expires_in = int((token.expires_at - datetime.now()).total_seconds())

        response = TokenResponse(
            access_token=token.access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=token.refresh_token
        )

        return response.model_dump()

    elif request.grant_type == "refresh_token":
        # 刷新令牌模式
        if not request.refresh_token:
            raise HTTPException(status_code=400, detail="缺少 refresh_token")

        # 获取旧 Token
        old_token = OAuthTokenDao.get_by_refresh_token(request.refresh_token)
        if not old_token:
            raise HTTPException(status_code=400, detail="无效的 refresh_token")

        # 验证 client_id
        if old_token.client_id != request.client_id:
            raise HTTPException(status_code=400, detail="client_id 不匹配")

        # 删除旧 Token
        OAuthTokenDao.delete_by_id(old_token.id)

        # 创建新 Token
        new_token = OAuthTokenDao.create(
            client_id=request.client_id,
            user_id=old_token.user_id
        )
        logger.info(f"OAuth token refreshed: client_id={request.client_id}, user_id={old_token.user_id}")

        # 计算过期时间（秒）
        expires_in = int((new_token.expires_at - datetime.now()).total_seconds())

        response = TokenResponse(
            access_token=new_token.access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=new_token.refresh_token
        )

        return response.model_dump()

    else:
        raise HTTPException(
            status_code=400,
            detail="不支持的 grant_type，仅支持 authorization_code 和 refresh_token"
        )
