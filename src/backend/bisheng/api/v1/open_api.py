# src/backend/bisheng/api/v1/open_api.py
"""开放 API 端点 - 文本溯源和文档预览"""
import html
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from loguru import logger

from bisheng.api.services.text_trace_service import (
    TextTraceService,
    TextTraceRequest,
    TextTraceResponse,
    MatchResult,
)
from bisheng.api.v1.schemas import resp_200
from bisheng.common.dependencies.oauth_deps import OAuthUser
from bisheng.knowledge.domain.models.knowledge_file import KnowledgeFileDao

router = APIRouter(prefix='/open', tags=['Open API'])


# ============== 文本溯源 API ==============

@router.post('/text-trace')
async def text_trace(
    request: TextTraceRequest,
    oauth_user: OAuthUser = Depends(OAuthUser.get_oauth_user)
):
    """文本溯源 API

    根据输入文本在用户有权限的知识库中搜索匹配的文档。
    支持精确匹配、语义匹配和混合匹配三种模式。

    Args:
        request: 文本溯源请求，包含待溯源文本、匹配模式、返回数量和阈值
        oauth_user: OAuth 认证用户

    Returns:
        匹配结果列表，每个结果包含文档信息、匹配分数和预览URL
    """
    logger.info(f"Text trace request from user {oauth_user.user_id}: text={request.text[:50]}...")

    # 调用服务执行搜索
    response: TextTraceResponse = await TextTraceService.search(
        request=request,
        user_id=oauth_user.user_id,
        user_role=oauth_user.user_role
    )

    # 为每个结果生成预览 URL
    results_with_preview: List[dict] = []
    for match in response.matches:
        # 创建预览 Token
        try:
            file_id = int(match.document_id) if match.document_id else 0
            if file_id > 0:
                token = await TextTraceService.create_preview_token(
                    file_id=file_id,
                    user_id=oauth_user.user_id,
                    highlight_text=match.matched_text[:500]  # 限制高亮文本长度
                )
                preview_url = f"/api/v1/open/document/preview/{match.document_id}?token={token}"
            else:
                preview_url = ""
        except (ValueError, TypeError):
            preview_url = ""

        result_dict = match.model_dump()
        result_dict['preview_url'] = preview_url
        results_with_preview.append(result_dict)

    return resp_200(data={
        'matches': results_with_preview,
        'total': response.total
    })


# ============== 文档预览 API ==============

@router.get('/document/preview/{document_id}', response_class=HTMLResponse)
async def document_preview(
    document_id: str,
    token: str = Query(..., description="预览临时 Token")
):
    """文档预览 API

    验证预览 Token 并返回带高亮的 HTML 预览页面。
    Token 为一次性使用，验证后即失效。

    Args:
        document_id: 文档ID
        token: 预览临时 Token

    Returns:
        HTML 预览页面，包含文档内容和高亮匹配文本
    """
    # 验证 Token
    token_data = await TextTraceService.validate_preview_token(token)
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="无效或已过期的预览 Token"
        )

    # 验证 document_id 匹配
    try:
        doc_id = int(document_id)
        if doc_id != token_data.file_id:
            raise HTTPException(
                status_code=403,
                detail="文档ID与Token不匹配"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的文档ID"
        )

    # 获取文件信息
    file_info = await KnowledgeFileDao.query_by_id(token_data.file_id)
    if not file_info:
        raise HTTPException(
            status_code=404,
            detail="文档不存在"
        )

    # 获取文件内容（这里简化处理，实际可能需要从 MinIO 获取）
    # 由于文件可能是各种格式，这里使用 matched_text 作为预览内容
    document_name = file_info.file_name or "未知文档"
    highlight_text = token_data.highlight_text or ""

    # 生成 HTML 预览页面
    html_content = generate_preview_html(
        document_name=document_name,
        content=highlight_text,
        highlight_text=highlight_text
    )

    return HTMLResponse(content=html_content)


def generate_preview_html(
    document_name: str,
    content: str,
    highlight_text: str
) -> str:
    """生成预览 HTML 页面

    Args:
        document_name: 文档名称
        content: 文档内容
        highlight_text: 需要高亮的文本

    Returns:
        HTML 页面字符串
    """
    # 转义 HTML 特殊字符
    safe_document_name = html.escape(document_name)
    safe_content = html.escape(content)
    safe_highlight = html.escape(highlight_text)

    # 在内容中高亮匹配文本
    if safe_highlight and safe_highlight in safe_content:
        highlighted_content = safe_content.replace(
            safe_highlight,
            f'<mark id="highlight-match" class="highlight">{safe_highlight}</mark>'
        )
    else:
        # 如果完全匹配不到，整个内容作为高亮显示
        highlighted_content = f'<mark id="highlight-match" class="highlight">{safe_content}</mark>'

    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_document_name} - 文档预览</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .header h1 {{
            font-size: 1.5rem;
            color: #1a1a1a;
            margin-bottom: 10px;
            word-break: break-all;
        }}

        .header .actions {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            transition: background-color 0.2s;
        }}

        .btn-primary {{
            background-color: #1890ff;
            color: #fff;
        }}

        .btn-primary:hover {{
            background-color: #40a9ff;
        }}

        .content {{
            background-color: #fff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .content-body {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 15px;
            line-height: 1.8;
        }}

        .highlight {{
            background-color: #ffeb3b;
            padding: 2px 4px;
            border-radius: 2px;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{safe_document_name}</h1>
            <div class="actions">
                <button class="btn btn-primary" onclick="scrollToHighlight()">
                    定位到匹配位置
                </button>
            </div>
        </div>

        <div class="content">
            <div class="content-body">
{highlighted_content}
            </div>
        </div>

        <div class="footer">
            BISHENG 文档预览
        </div>
    </div>

    <script>
        function scrollToHighlight() {{
            const highlight = document.getElementById('highlight-match');
            if (highlight) {{
                highlight.scrollIntoView({{
                    behavior: 'smooth',
                    block: 'center'
                }});
            }}
        }}

        // 页面加载后自动滚动到高亮位置
        window.addEventListener('load', function() {{
            setTimeout(scrollToHighlight, 300);
        }});
    </script>
</body>
</html>'''

    return html_template
