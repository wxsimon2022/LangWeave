"""OpenAPI / Swagger metadata for LangWeave API docs."""

from __future__ import annotations

from typing import Any

API_DESCRIPTION = """
LangWeave（织语）HTTP API — 基于 LangChain / LangGraph 的 Agent 服务。

## 功能模块

- **agents**：Agent 对话、完整 invoke、SSE 流式
- **intent**：意图识别与自动路由
- **meta**：健康检查

## 统一响应格式

```json
{"code": 200, "message": "", "data": {}}
```

- `code`: 业务状态码，`200` 为成功
- `message`: 提示信息
- `data`: 业务数据；失败时多为 `null`

## 认证

当前版本未启用鉴权；生产环境请在网关或中间件层补充。

## 文档（Swagger 2.0）

- Swagger UI：`/docs`
- Swagger 2 JSON：`/swagger.json`

（若使用 `doc_mode=openapi3`，则为 `/docs` + `/openapi.json`）
"""

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "meta",
        "description": "服务状态与元信息",
    },
    {
        "name": "agents",
        "description": "Agent 对话与 LangGraph 调用。`agent_name` 如 `assistant`、`intent`。",
    },
    {
        "name": "intent",
        "description": "意图识别：结构化分类用户输入，并可路由到目标 Agent。",
    },
    {
        "name": "sessions",
        "description": "多轮会话记忆：查询历史、清空上下文（需 thread_id）。",
    },
]

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "docExpansion": "list",
    "defaultModelsExpandDepth": 2,
    "displayRequestDuration": True,
    "filter": True,
    "persistAuthorization": True,
}
