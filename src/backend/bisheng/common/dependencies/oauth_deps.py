# src/backend/bisheng/common/dependencies/oauth_deps.py
"""OAuth Token 认证依赖"""
from datetime import datetime
from typing import Optional, List

from fastapi import Header, HTTPException
from pydantic import BaseModel

from bisheng.database.dao.oauth import OAuthTokenDao
from bisheng.user.domain.models.user import UserDao
from bisheng.user.domain.models.user_role import UserRoleDao


class OAuthUser(BaseModel):
    """OAuth 认证的用户"""
    user_id: int
    user_name: str
    user_role: List[int]
    client_id: str

    @classmethod
    async def get_oauth_user(
        cls,
        authorization: Optional[str] = Header(None)
    ) -> "OAuthUser":
        """从 Bearer Token 获取用户信息

        Args:
            authorization: Authorization header, 格式为 "Bearer <token>"

        Returns:
            OAuthUser 实例

        Raises:
            HTTPException: 认证失败时抛出 401 错误
        """
        # 1. 验证 authorization header 存在
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized"}
            )

        # 2. 验证格式正确 (Bearer xxx)
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized"}
            )

        access_token = parts[1]

        # 3. 从 OAuthTokenDao 获取 token
        token = OAuthTokenDao.get_by_access_token(access_token)
        if not token:
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_token"}
            )

        # 4. 验证 token 未过期
        if token.expires_at < datetime.now():
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_token"}
            )

        # 5. 获取用户信息
        user = UserDao.get_user(token.user_id)
        if not user:
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_token"}
            )

        # 6. 获取用户角色
        user_roles = UserRoleDao.get_user_roles(token.user_id)
        role_ids = [user_role.role_id for user_role in user_roles]

        # 7. 返回 OAuthUser 实例
        return cls(
            user_id=user.user_id,
            user_name=user.user_name,
            user_role=role_ids,
            client_id=token.client_id
        )
