# 文本溯源 API 设计文档

## 概述

提供对外开放的 API，允许第三方应用通过 OAuth 2.0 授权后，传入一段文本，从用户有权限访问的知识库（个人 + 组织）中查找文本出处，返回匹配的文档列表，并支持通过预览链接查看文档内容和高亮定位。

## 核心功能

- 支持三种匹配方式：精确匹配、语义匹配、混合匹配
- 支持设置返回数量限制和相似度阈值
- 返回文档预览链接，点击可查看文档并高亮匹配位置
- 支持 PDF、Word、Excel、PPT 格式的文档预览
- 基于用户权限过滤知识库范围

## API 设计

### 文本溯源 API

**端点**: `POST /api/v1/open/text-trace`

**请求头**:
```
Authorization: Bearer {access_token}
```

**请求参数**:
```json
{
  "text": "需要溯源的文本内容",
  "match_mode": "exact | semantic | hybrid",
  "top_k": 10,
  "threshold": 0.7
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 需要溯源的文本内容 |
| match_mode | string | 否 | 匹配方式：exact(精确)/semantic(语义)/hybrid(混合)，默认 hybrid |
| top_k | int | 否 | 返回最多 N 个结果，默认 10 |
| threshold | float | 否 | 相似度阈值 0-1，默认 0.7 |

**响应**:
```json
{
  "matches": [
    {
      "document_id": "xxx",
      "document_name": "文档名称.pdf",
      "knowledge_base": "知识库名称",
      "score": 0.95,
      "preview_url": "https://xxx/api/v1/open/document/preview/xxx?token=xxx&highlight=xxx",
      "matched_text": "匹配的文本片段预览..."
    }
  ],
  "total": 5
}
```

### 文档预览

**端点**: `GET /api/v1/open/document/preview/{document_id}`

**参数**:
- `token`: 临时访问令牌（有效期 30 分钟，一次性使用）
- `highlight`: 高亮位置信息的 Base64 编码

**功能**:
- 支持 PDF、Word、Excel、PPT 格式的在线预览
- 自动滚动到第一个匹配位置
- 高亮显示匹配的文本片段（黄色背景）
- 多个匹配位置时，提供"上一个/下一个"导航按钮

## OAuth 2.0 授权

### 应用注册

第三方应用需要在 BISHENG 管理后台注册，获取：
- `client_id`: 应用唯一标识
- `client_secret`: 应用密钥
- `redirect_uri`: 授权回调地址

### 授权流程

```
1. 引导用户访问授权页面
   GET /api/v1/oauth/authorize?client_id=xxx&redirect_uri=xxx&state=xxx

2. 用户登录并同意授权后，重定向回第三方应用
   GET {redirect_uri}?code=授权码&state=xxx

3. 用授权码换取 Access Token
   POST /api/v1/oauth/token
   {
     "grant_type": "authorization_code",
     "client_id": "xxx",
     "client_secret": "xxx",
     "code": "授权码",
     "redirect_uri": "xxx"
   }

4. 返回 Token
   {
     "access_token": "xxx",
     "token_type": "Bearer",
     "expires_in": 7200,
     "refresh_token": "xxx"
   }
```

### 刷新 Token

```
POST /api/v1/oauth/token
{
  "grant_type": "refresh_token",
  "client_id": "xxx",
  "client_secret": "xxx",
  "refresh_token": "xxx"
}
```

## 文本匹配逻辑

### 精确匹配（exact）
- 使用 Elasticsearch 的全文检索能力
- 对输入文本进行分词后精确匹配
- 返回包含该文本片段的文档及位置信息

### 语义匹配（semantic）
- 将输入文本通过 Embedding 模型转为向量
- 在 Milvus 中检索相似向量
- 返回语义相近的文档片段

### 混合匹配（hybrid）
- 先执行精确匹配
- 若精确匹配结果数量不足 top_k，再补充语义匹配结果
- 去重后按相似度排序返回

### 相似度计算
- 精确匹配：基于 BM25 算法计算相关性分数，归一化到 0-1
- 语义匹配：使用向量余弦相似度，范围 0-1
- 混合模式：精确匹配结果优先，分数加权（精确匹配 +0.1 权重提升）

### 权限过滤
- 根据 Token 解析出用户 ID
- 查询用户的个人知识库 ID 列表
- 查询用户所属组织的知识库 ID 列表
- 仅在这些知识库范围内执行检索

## 数据库设计

### 新增数据表

```sql
-- OAuth 应用注册表
CREATE TABLE oauth_application (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    client_id VARCHAR(64) UNIQUE NOT NULL,
    client_secret VARCHAR(128) NOT NULL,
    redirect_uri VARCHAR(512) NOT NULL,
    user_id INT NOT NULL,  -- 创建者
    status TINYINT DEFAULT 1,  -- 1:启用 0:禁用
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- OAuth 授权码表（临时，用完即删）
CREATE TABLE oauth_authorization_code (
    code VARCHAR(128) PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    redirect_uri VARCHAR(512) NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- OAuth Token 表
CREATE TABLE oauth_token (
    id VARCHAR(64) PRIMARY KEY,
    access_token VARCHAR(256) UNIQUE NOT NULL,
    refresh_token VARCHAR(256) UNIQUE NOT NULL,
    client_id VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## API 端点汇总

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/oauth/authorize` | GET | 授权页面 |
| `/api/v1/oauth/token` | POST | 获取/刷新 Token |
| `/api/v1/open/text-trace` | POST | 文本溯源 API |
| `/api/v1/open/document/preview/{id}` | GET | 文档预览页面 |

## 错误处理

### 错误响应格式

```json
{
  "error": "error_code",
  "message": "错误描述",
  "detail": "详细信息（可选）"
}
```

### 错误码定义

| HTTP 状态码 | error_code | 说明 |
|-------------|------------|------|
| 401 | invalid_token | Token 无效或已过期 |
| 401 | unauthorized | 未提供认证信息 |
| 403 | access_denied | 用户拒绝授权或无权限 |
| 400 | invalid_request | 请求参数错误 |
| 400 | invalid_client | client_id 或 client_secret 错误 |
| 404 | document_not_found | 文档不存在 |
| 429 | rate_limit_exceeded | 请求频率超限 |
| 500 | internal_error | 服务器内部错误 |

## 安全措施

- Access Token 有效期 2 小时，Refresh Token 有效期 7 天
- 预览临时 Token 有效期 30 分钟，一次性使用
- API 请求频率限制：每用户每分钟 60 次
- 授权码有效期 5 分钟，使用后立即删除
- client_secret 加密存储
- 所有 API 强制 HTTPS

## 技术实现要点

### 后端模块结构

```
src/backend/bisheng/
├── api/v1/
│   ├── oauth.py          # OAuth 授权相关接口
│   └── open_api.py       # 开放 API（文本溯源、文档预览）
├── services/
│   ├── oauth_service.py  # OAuth 业务逻辑
│   └── text_trace_service.py  # 文本溯源业务逻辑
└── database/models/
    └── oauth.py          # OAuth 相关数据模型
```

### 依赖现有模块

- 知识库检索：复用 `bisheng/knowledge/` 模块的检索能力
- 文档预览：复用现有的文档预览组件，新增高亮参数支持
- 用户权限：复用 `bisheng/user/` 模块的权限查询
- Elasticsearch：复用现有的 ES 连接和查询封装
- Milvus：复用现有的向量检索封装
