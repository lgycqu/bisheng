# src/backend/bisheng/database/models/oauth.py
"""OAuth 2.0 相关数据模型"""
from datetime import datetime
from typing import Optional, Tuple
import secrets

from sqlalchemy import Column, DateTime, text
from sqlmodel import Field

from bisheng.common.models.base import SQLModelSerializable
from bisheng.utils import generate_uuid


class OAuthApplicationBase(SQLModelSerializable):
    """OAuth 应用基础模型"""
    name: str = Field(max_length=128, description="应用名称")
    redirect_uri: str = Field(max_length=512, description="授权回调地址")
    status: int = Field(default=1, description="状态: 1启用 0禁用")


class OAuthApplication(OAuthApplicationBase, table=True):
    """OAuth 应用注册表"""
    __tablename__ = "oauth_application"

    id: Optional[str] = Field(default_factory=generate_uuid, primary_key=True, max_length=64)
    client_id: str = Field(max_length=64, unique=True, index=True)
    client_secret: str = Field(max_length=128)
    user_id: int = Field(index=True, description="创建者ID")
    create_time: Optional[datetime] = Field(default=None, sa_column=Column(
        DateTime, nullable=False, index=True, server_default=text('CURRENT_TIMESTAMP')))
    update_time: Optional[datetime] = Field(default=None, sa_column=Column(
        DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')))

    @classmethod
    def generate_client_credentials(cls) -> Tuple[str, str]:
        """生成 client_id 和 client_secret"""
        client_id = secrets.token_urlsafe(32)
        client_secret = secrets.token_urlsafe(48)
        return client_id, client_secret


class OAuthAuthorizationCode(SQLModelSerializable, table=True):
    """OAuth 授权码表（临时，用完即删）"""
    __tablename__ = "oauth_authorization_code"

    code: str = Field(primary_key=True, max_length=128)
    client_id: str = Field(max_length=64, index=True)
    user_id: int = Field(index=True)
    redirect_uri: str = Field(max_length=512)
    expires_at: datetime = Field(description="过期时间")
    create_time: Optional[datetime] = Field(default=None, sa_column=Column(
        DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP')))


class OAuthToken(SQLModelSerializable, table=True):
    """OAuth Token 表"""
    __tablename__ = "oauth_token"

    id: Optional[str] = Field(default_factory=generate_uuid, primary_key=True, max_length=64)
    access_token: str = Field(max_length=256, unique=True, index=True)
    refresh_token: str = Field(max_length=256, unique=True, index=True)
    client_id: str = Field(max_length=64, index=True)
    user_id: int = Field(index=True)
    expires_at: datetime = Field(description="过期时间")
    create_time: Optional[datetime] = Field(default=None, sa_column=Column(
        DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP')))
