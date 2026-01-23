# src/backend/bisheng/database/dao/oauth.py
"""OAuth 2.0 数据访问层"""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import select, delete

from bisheng.core.database import get_sync_db_session
from bisheng.database.models.oauth import (
    OAuthApplication,
    OAuthAuthorizationCode,
    OAuthToken,
)


class OAuthApplicationDao:
    """OAuth 应用数据访问对象"""

    @classmethod
    def create(cls, name: str, redirect_uri: str, user_id: int) -> OAuthApplication:
        """创建 OAuth 应用

        Args:
            name: 应用名称
            redirect_uri: 授权回调地址
            user_id: 创建者用户ID

        Returns:
            创建的 OAuthApplication 实例
        """
        client_id, client_secret = OAuthApplication.generate_client_credentials()
        app = OAuthApplication(
            name=name,
            redirect_uri=redirect_uri,
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        with get_sync_db_session() as session:
            session.add(app)
            session.commit()
            session.refresh(app)
            return app

    @classmethod
    def get_by_client_id(cls, client_id: str) -> Optional[OAuthApplication]:
        """根据 client_id 获取应用

        Args:
            client_id: OAuth 客户端ID

        Returns:
            OAuthApplication 实例或 None
        """
        with get_sync_db_session() as session:
            statement = select(OAuthApplication).where(
                OAuthApplication.client_id == client_id,
                OAuthApplication.status == 1
            )
            return session.exec(statement).first()

    @classmethod
    def get_by_user_id(cls, user_id: int) -> List[OAuthApplication]:
        """获取用户的所有应用

        Args:
            user_id: 用户ID

        Returns:
            用户创建的所有 OAuthApplication 列表
        """
        with get_sync_db_session() as session:
            statement = select(OAuthApplication).where(
                OAuthApplication.user_id == user_id
            ).order_by(OAuthApplication.create_time.desc())
            return session.exec(statement).all()

    @classmethod
    def delete(cls, app_id: str, user_id: int) -> bool:
        """删除应用

        Args:
            app_id: 应用ID
            user_id: 用户ID（用于权限验证）

        Returns:
            是否删除成功
        """
        with get_sync_db_session() as session:
            statement = select(OAuthApplication).where(
                OAuthApplication.id == app_id,
                OAuthApplication.user_id == user_id
            )
            app = session.exec(statement).first()
            if app:
                session.delete(app)
                session.commit()
                return True
            return False


class OAuthAuthorizationCodeDao:
    """OAuth 授权码数据访问对象"""

    @classmethod
    def create(
        cls,
        client_id: str,
        user_id: int,
        redirect_uri: str,
        expires_minutes: int = 5
    ) -> OAuthAuthorizationCode:
        """创建授权码

        Args:
            client_id: OAuth 客户端ID
            user_id: 用户ID
            redirect_uri: 回调地址
            expires_minutes: 过期时间（分钟），默认5分钟

        Returns:
            创建的 OAuthAuthorizationCode 实例
        """
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=expires_minutes)
        auth_code = OAuthAuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            expires_at=expires_at,
        )
        with get_sync_db_session() as session:
            session.add(auth_code)
            session.commit()
            session.refresh(auth_code)
            return auth_code

    @classmethod
    def get_and_delete(cls, code: str) -> Optional[OAuthAuthorizationCode]:
        """获取并删除授权码（一次性使用）

        Args:
            code: 授权码

        Returns:
            OAuthAuthorizationCode 实例或 None（如果不存在或已过期）
        """
        with get_sync_db_session() as session:
            statement = select(OAuthAuthorizationCode).where(
                OAuthAuthorizationCode.code == code
            )
            auth_code = session.exec(statement).first()
            if auth_code:
                # 检查是否过期
                if auth_code.expires_at < datetime.now():
                    session.delete(auth_code)
                    session.commit()
                    return None
                # 删除授权码（一次性使用）
                session.delete(auth_code)
                session.commit()
                return auth_code
            return None

    @classmethod
    def cleanup_expired(cls) -> int:
        """清理过期授权码

        Returns:
            删除的授权码数量
        """
        with get_sync_db_session() as session:
            statement = delete(OAuthAuthorizationCode).where(
                OAuthAuthorizationCode.expires_at < datetime.now()
            )
            result = session.exec(statement)
            session.commit()
            return result.rowcount


class OAuthTokenDao:
    """OAuth Token 数据访问对象"""

    @classmethod
    def create(
        cls,
        client_id: str,
        user_id: int,
        expires_hours: int = 2
    ) -> OAuthToken:
        """创建 Token

        Args:
            client_id: OAuth 客户端ID
            user_id: 用户ID
            expires_hours: 过期时间（小时），默认2小时

        Returns:
            创建的 OAuthToken 实例
        """
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        token = OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            user_id=user_id,
            expires_at=expires_at,
        )
        with get_sync_db_session() as session:
            session.add(token)
            session.commit()
            session.refresh(token)
            return token

    @classmethod
    def get_by_access_token(cls, access_token: str) -> Optional[OAuthToken]:
        """根据 access_token 获取 Token

        Args:
            access_token: 访问令牌

        Returns:
            OAuthToken 实例或 None
        """
        with get_sync_db_session() as session:
            statement = select(OAuthToken).where(
                OAuthToken.access_token == access_token
            )
            return session.exec(statement).first()

    @classmethod
    def get_by_refresh_token(cls, refresh_token: str) -> Optional[OAuthToken]:
        """根据 refresh_token 获取 Token

        Args:
            refresh_token: 刷新令牌

        Returns:
            OAuthToken 实例或 None
        """
        with get_sync_db_session() as session:
            statement = select(OAuthToken).where(
                OAuthToken.refresh_token == refresh_token
            )
            return session.exec(statement).first()

    @classmethod
    def delete_by_id(cls, token_id: str) -> bool:
        """删除 Token

        Args:
            token_id: Token ID

        Returns:
            是否删除成功
        """
        with get_sync_db_session() as session:
            statement = select(OAuthToken).where(OAuthToken.id == token_id)
            token = session.exec(statement).first()
            if token:
                session.delete(token)
                session.commit()
                return True
            return False

    @classmethod
    def delete_by_user_and_client(cls, user_id: int, client_id: str) -> int:
        """删除用户在某应用的所有 Token

        Args:
            user_id: 用户ID
            client_id: OAuth 客户端ID

        Returns:
            删除的 Token 数量
        """
        with get_sync_db_session() as session:
            statement = delete(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.client_id == client_id
            )
            result = session.exec(statement)
            session.commit()
            return result.rowcount
