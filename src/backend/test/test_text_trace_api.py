# src/backend/test/test_text_trace_api.py
"""文本溯源 API 集成测试

测试 OAuth、文本溯源和文档预览 API 的基本行为，
包括认证、错误处理等。
"""
import pytest
from fastapi.testclient import TestClient

# 创建一个简化的 FastAPI 应用用于测试
from fastapi import FastAPI
from bisheng.api.v1.oauth import router as oauth_router
from bisheng.api.v1.open_api import router as open_api_router

# 创建测试应用
test_app = FastAPI()
test_app.include_router(oauth_router, prefix='/api/v1')
test_app.include_router(open_api_router, prefix='/api/v1')


class TestOAuthAPI:
    """OAuth API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(test_app)

    def test_create_application_unauthorized(self, client):
        """未登录时创建应用应返回 401

        测试场景：
        - 不携带任何认证信息调用创建应用接口
        - 应返回 401 未授权错误
        """
        response = client.post(
            '/api/v1/oauth/applications',
            json={
                'name': 'Test App',
                'redirect_uri': 'https://example.com/callback'
            }
        )

        # 验证返回 401 状态码
        assert response.status_code == 401

    def test_token_invalid_client(self, client):
        """无效的 client_id 应返回错误

        测试场景：
        - 使用不存在的 client_id 和 client_secret 请求 token
        - 应返回 401 错误，提示无效的客户端凭证
        """
        response = client.post(
            '/api/v1/oauth/token',
            json={
                'grant_type': 'authorization_code',
                'client_id': 'invalid_client_id',
                'client_secret': 'invalid_client_secret',
                'code': 'some_code',
                'redirect_uri': 'https://example.com/callback'
            }
        )

        # 验证返回 401 状态码
        assert response.status_code == 401


class TestTextTraceAPI:
    """文本溯源 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(test_app)

    def test_text_trace_unauthorized(self, client):
        """未认证时调用应返回 401

        测试场景：
        - 不携带 Authorization header 调用文本溯源接口
        - 应返回 401 未授权错误
        """
        response = client.post(
            '/api/v1/open/text-trace',
            json={
                'text': '测试文本内容',
                'match_mode': 'hybrid',
                'top_k': 5
            }
        )

        # 验证返回 401 状态码
        assert response.status_code == 401

    def test_text_trace_invalid_token(self, client):
        """无效 Token 应返回 401

        测试场景：
        - 携带无效的 Bearer Token 调用文本溯源接口
        - 应返回 401 错误，提示 token 无效
        """
        response = client.post(
            '/api/v1/open/text-trace',
            json={
                'text': '测试文本内容',
                'match_mode': 'hybrid',
                'top_k': 5
            },
            headers={
                'Authorization': 'Bearer invalid_token_12345'
            }
        )

        # 验证返回 401 状态码
        assert response.status_code == 401


class TestDocumentPreviewAPI:
    """文档预览 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(test_app)

    def test_preview_invalid_token(self, client):
        """无效预览 Token 应返回 401

        测试场景：
        - 使用无效的预览 token 访问文档预览接口
        - 应返回 401 错误，提示 token 无效或已过期
        """
        response = client.get(
            '/api/v1/open/document/preview/123',
            params={
                'token': 'invalid_preview_token'
            }
        )

        # 验证返回 401 状态码
        assert response.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
