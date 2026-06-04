# LangWeave 框架参考

LangWeave 是基于 LangChain 1.x + LangGraph 的 Python Agent 框架及完整聊天应用。

日常开发与部署见 [开发指南.md](开发指南.md)；项目总览见 [README.md](../../README.md)。

---

## 架构总览

```
langweave/              ← 框架核心（与业务解耦）
├── agent.py            ← Agent 包装类
├── builder.py          ← AgentBuilder 流式构建器
├── registry.py         ← AgentRegistry 名称注册表
├── config.py           ← AgentSettings 环境配置
├── memory.py           ← 多轮记忆（Checkpointer）
├── models/deepseek.py  ← DeepSeek 模型集成
├── middleware/         ← LoggingMiddleware
├── tools/              ← builtin（calculator, current_time）+ ToolRegistry
├── orchestration/      ← SupervisorBuilder（监督者模式）
└── web/                ← FastAPI 应用工厂 + SSE + Swagger2

app/                    ← 业务应用层
├── agents/             ← Agent 构建函数
├── api/                ← FastAPI 路由（unified、conversations）
├── application/        ← 业务服务层（Auth、Chat、Intent）
├── core/               ← 核心模块（MCP、RAG、LLM、监控）
├── domain/             ← 领域层（Agent 注册、工具目录）
├── infrastructure/     ← 基础设施（DB、Redis 缓存）
├── interfaces/         ← HTTP 路由适配器
├── schemas/            ← Pydantic 模型
└── helpers/            ← 工具函数
```

---

## LangWeave 核心框架

### 1. AgentBuilder — 流式构建 Agent

```python
from langweave import AgentBuilder
from langweave.tools import calculator

agent = (
    AgentBuilder()
    .with_name("my_agent")
    .with_deepseek("deepseek-chat", temperature=0.3)
    .with_tools([calculator])
    .with_system_prompt("你是助手")
    .with_response_format(MyPydanticSchema)
    .with_middleware(LoggingMiddleware())
    .with_checkpointer(get_checkpointer())
    .with_debug(True)
    .build()
)
```

**方法链：** `with_name` · `with_model` · `with_deepseek` · `with_system_prompt` · `with_tools` · `add_tool` · `with_middleware` · `with_response_format` · `with_state_schema` · `with_context_schema` · `with_checkpointer` · `with_store` · `with_debug`

### 2. Agent — 包装 LangGraph CompiledStateGraph

```python
reply = agent.chat("你好", thread_id="s1")
reply, thread_id = await agent.achat("你好")

for chunk in agent.stream("你好", stream_mode="updates"):
    print(chunk)

async for chunk in agent.astream("你好"):
    yield chunk
```

### 3. AgentRegistry

```python
from langweave import AgentRegistry

registry = AgentRegistry()
registry.register(my_agent)
agent = registry.get("my_agent")
registry.build_and_register(builder, name="agent_a", overwrite=True)
```

### 4. AgentSettings — 环境变量

| 环境变量 | 对应字段 |
|----------|----------|
| `LANGWEAVE_MODEL` | model |
| `LANGWEAVE_SYSTEM_PROMPT` | system_prompt |
| `LANGWEAVE_TEMPERATURE` | temperature |
| `LANGWEAVE_MAX_TOKENS` | max_tokens |
| `LANGWEAVE_DEBUG` | debug |
| `LANGWEAVE_MEMORY_ENABLED` | memory_enabled |
| `DEEPSEEK_API_KEY` | deepseek_api_key |

回退前缀：`LC_AGENT_*`。`load_dotenv()` 从项目根加载 `.env`。

### 5. Memory — 多轮对话记忆

```python
from langweave.memory import get_checkpointer, get_thread_messages, aclear_thread

checkpointer = get_checkpointer()  # 按 LANGWEAVE_DATABASE_URL 自动选 MySQL / 内存
msgs = await aget_thread_messages(graph, thread_id)
```

MySQL 模式需 `langgraph-checkpoint-mysql` + `aiomysql`。

### 6. Tools

- `calculator` — AST 安全算术
- `current_time` — UTC ISO 8601
- `ToolRegistry` — 按分组注册工具

---

## Agent 模式

### 意图路由（项目核心）

```
POST /api/v1/unified/stream
  → IntentService.recognize()
    → emotional_chat → emotional
    → general_chat / order_query / calculation / unknown → assistant
```

**关键文件：** `app/agents/intent_agent.py` · `app/application/services/intent.py` · `app/application/services/chat.py` · `app/api/v1/agents_unified.py`

**路由注意：** `APIRouter` prefix 必须是 `/api/v1`，不能是 `/api/v1/agents`。

**UserIntent**（`app/schemas/intent.py`）：`intent` · `confidence` · `slots` · `target_agent` · `reasoning`

首次消息做意图识别；`agent_name` 持久化后同对话不再重复分类。

### Supervisor 模式

```python
from langweave.orchestration import SupervisorBuilder

supervisor = SupervisorBuilder({"math": math_agent, "search": search_agent}).build()
```

### Fallback 模式

模型依赖缺失时注册 `UnavailableAgent`（`app/agents/fallback_agent.py`）。

---

## Web 层

### 框架端点（免鉴权）

- `GET /health`
- `GET /api/v1/agents`
- `POST /api/v1/agents/{name}/chat|invoke|stream`

### 业务端点（鉴权）

- `POST /api/v1/unified/stream` — 统一聊天入口
- `GET/POST/PATCH/DELETE /api/v1/conversations/*`
- `POST /api/v1/auth/*`

### SSE

响应头需 `X-Accel-Buffering: no`；nginx 配 `proxy_buffering off`。

### 统一响应

```json
{"code": 200, "message": "", "data": {...}}
```

### 安全中间件

- RateLimit：Redis 滑动窗口，默认 60 req/min/IP
- SecurityHeaders：CSP、X-Frame-Options 等

---

## 应用层

### 数据表

- `c_users` — 用户
- `c_conversations` — 对话（含 `agent_name`、`thread_id`）
- `c_messages` — 消息

无外键；`thread_id` 唯一索引供 LangGraph Checkpointer 使用。

### 双轨记忆

1. LangGraph Checkpointer — Agent 上下文
2. `c_messages` — 持久化与分页查询

### 鉴权

JWT（HS256）· PBKDF2 密码 · Redis 黑名单 · 单设备 session（`set_active_session_sync` 用于 sync 路由）

---

## 占位模块（待实现）

| 模块 | 文件 |
|------|------|
| MCP | `app/core/mcp/*.py` |
| RAG | `app/core/rag/*.py` |
| Langfuse | `app/core/monitoring/langfuse*.py` |
| Performance Tracker | `app/core/monitoring/performance_tracker.py` |
| Anomaly Cache | `app/infrastructure/cache/anomaly.py` |
| Celery | `app/tasks/celery_app.py` |

---

## 依赖

见根目录 `requirements.txt` 与 `pyproject.toml`。可选：`langchain-deepseek`、`fastapi-swagger2`。
