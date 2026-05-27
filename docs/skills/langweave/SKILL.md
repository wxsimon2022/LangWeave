---
name: langweave
description: >-
  LangWeave (织语) is a LangChain 1.x / LangGraph agent framework with a
  complete chat application. Use when working in the langchain project or
  building LangChain agents with FastAPI: multi-agent orchestration, intent
  routing, conversation memory (in-memory or MySQL), structured-agent output,
  SSE streaming, supervisor pattern, tool groups, MCP server connections, RAG,
  Langfuse monitoring, JWT auth, rate limiting, and an admin/desktop/web
  frontend. Includes an "emotional companion + AI assistant" dual-agent chat
  application.
---

# LangWeave (织语) — Skill Guide

LangWeave 是基于 LangChain 1.x + LangGraph 的 Python Agent 框架及完整聊天应用。项目位于 `/Users/simon/Documents/my_python/langchain`。

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
├── tools/             ← builtin（calculator, current_time）+ ToolRegistry
├── orchestration/     ← SupervisorBuilder（监督者模式）
└── web/               ← FastAPI 应用工厂 + SSE + Swagger2

app/                    ← 业务应用层
├── agents/            ← Agent 构建函数
├── api/               ← FastAPI 路由
├── application/       ← 业务服务层（AuthService, ChatService, IntentService）
├── core/              ← 核心模块（MCP, RAG, LLM, 监控, 缓存）
├── domain/            ← 领域层（Agent 注册、工具目录）
├── infrastructure/    ← 基础设施（DB 模型、Redis 缓存）
├── interfaces/        ← HTTP 接口适配器
├── schemas/           ← Pydantic 请求/响应模型
└── helpers/           ← 工具函数
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
    .with_response_format(MyPydanticSchema)  # 结构化输出
    .with_middleware(LoggingMiddleware())
    .with_checkpointer(get_checkpointer())    # 多轮记忆
    .with_debug(True)
    .build()
)
```

**方法链：**
- `with_name()` — Agent 名称
- `with_model()` — 直接传模型实例或字符串
- `with_deepseek()` — 快捷配置 DeepSeek（`deepseek-chat` / `deepseek-reasoner`）
- `with_system_prompt()` — 系统提示词
- `with_tools()` — 工具列表
- `add_tool()` — 追加工具
- `with_middleware()` — 中间件（AgentMiddleware）
- `with_response_format()` — 结构化输出 Schema（Pydantic）
- `with_state_schema()` — 自定义 State Schema
- `with_context_schema()` — 上下文 Schema
- `with_checkpointer()` — 持久化 Checkpointer
- `with_store()` — LangGraph Store
- `with_debug()` — 调试模式

### 2. Agent — 包装 LangGraph CompiledStateGraph

```python
# 同步调用
result = agent.invoke("你好")
result = agent.invoke({"messages": [HumanMessage("你好")]}, thread_id="s1")
reply = agent.chat("你好", thread_id="s1")

# 异步调用
reply, thread_id = await agent.achat("你好")
state = await agent.ainvoke("你好", thread_id="s1")

# 流式
for chunk in agent.stream("你好", stream_mode="updates"):
    print(chunk)

async for chunk in agent.astream("你好"):
    yield chunk

# 历史
history = agent.get_history(thread_id)
history = await agent.aget_history(thread_id)
```

**关键设计：**
- `_normalize_input()` 统一处理 str / dict / list 三种输入
- `_resolve_thread()` 自动生成 thread_id 或使用已有 ID
- `_merge_config()` 合并用户 config 与 thread config
- 返回结果中带 `_thread_id` 字段（多轮记忆用）
- `_last_ai_content()` 提取最后的 AI 回复文本（处理 content 为 str 或 list 两种情况）

### 3. AgentRegistry — 名称注册表

```python
from langweave import AgentRegistry

registry = AgentRegistry()
registry.register(my_agent)
agent = registry.get("my_agent")
names = registry.list_names()
registry.build_and_register(builder, name="agent_a", overwrite=True)
registry.unregister("my_agent")
```

### 4. AgentSettings — 环境驱动配置

通过 `LANGWEAVE_*` 环境变量配置：

| 环境变量 | 对应字段 |
|----------|----------|
| `LANGWEAVE_MODEL` | model（如 `deepseek:deepseek-chat`） |
| `LANGWEAVE_SYSTEM_PROMPT` | system_prompt |
| `LANGWEAVE_TEMPERATURE` | temperature |
| `LANGWEAVE_MAX_TOKENS` | max_tokens |
| `LANGWEAVE_DEBUG` | debug |
| `LANGWEAVE_MEMORY_ENABLED` | memory_enabled |
| `DEEPSEEK_API_KEY` | deepseek_api_key |

回退前缀：`LC_AGENT_*`

```python
settings = AgentSettings.from_env()
settings = AgentSettings.from_env(model="gpt-4", temperature=0.5)
```

`load_dotenv()` 自动从项目根目录加载 `.env`，幂等调用。

### 5. Memory — 多轮对话记忆

```python
from langweave.memory import get_checkpointer

# 内存模式
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# MySQL 模式（自动检测数据库 URL）
from langweave.memory import get_checkpointer
checkpointer = get_checkpointer()  # 根据 LANGWEAVE_DATABASE_URL 自动选
```

**MySQL 模式**（LazyConnection）：
- 通过 `_LazyAsyncCheckpointer` 延迟创建 AIOMySQLSaver 连接
- 支持 `aget_tuple` / `aput` / `aput_writes` / `alist` / `adelete_thread`
- 自动处理 `utf8mb4_general_ci` 排序规则
- 需要 `langgraph-checkpoint-mysql` + `aiomysql`

```python
# 历史查询
from langweave.memory import get_thread_messages, aget_thread_messages, aclear_thread

msgs = get_thread_messages(graph, thread_id)
msgs = await aget_thread_messages(graph, thread_id)
await aclear_thread(graph, thread_id)
```

### 6. Tools — 内置工具和分组注册

**内置工具（`langweave/tools/builtin.py`）：**
- `calculator(expression: str) -> str` — AST 安全算术求值（+ - * / **）
- `current_time() -> str` — 返回 UTC ISO 8601 时间

**ToolRegistry（`langweave/tools/registry.py`）：**
```python
from langweave.tools import ToolRegistry

registry = ToolRegistry()
registry.register("math", calculator)
registry.register("business", query_order_status)

tools = registry.get("math")             # 单组
tools = registry.all()                   # 全部
tools = registry.tools_for(["math"])     # 多组
groups = registry.groups()               # 所有组名
```

**业务工具示例（`app/domain/tools/order.py`）：**
```python
from langchain_core.tools import tool

@tool
def query_order_status(order_id: str) -> str:
    """Query order status by order id (demo business logic)."""
    demo_orders = {"10001": "shipped", "10002": "processing"}
    return demo_orders.get(order_id.strip(), "not found")
```

**工具收集（`app/domain/tools/catalog.py`）：**
```python
def get_default_tools():
    return [calculator, current_time, query_order_status]
```

---

## Agent 模式

### 1. 意图路由模式（Entry Agent + Intent Routing）

这是项目的核心模式：一个统一入口 Agent 接收消息 -> intent 识别 -> 路由到 specialist Agent。

```
用户 → POST /api/v1/unified/stream
  → IntentService.recognize()  (intent agent 结构化分类)
    → emotional_chat → emotional agent
    → general_chat / order_query / calculation → assistant agent
    → unknown → assistant (默认兜底)
```

**关键文件：**
- `app/agents/intent_agent.py` — Intent Agent 构建
- `app/application/services/intent.py` — IntentService 实现
- `app/application/services/chat.py` — ChatService 编排

**结构化输出 Schema（`app/schemas/intent.py`）：**
```python
class UserIntent(BaseModel):
    intent: IntentType  # emotional_chat | general_chat | order_query | calculation | unknown
    confidence: float   # 0~1
    slots: dict         # 提取的实体
    target_agent: str   # 路由目标 agent 名称
    reasoning: str | None
```

**意图解析逻辑：**
1. 优先取 `structured_response`（Agent 结构化输出）
2. 其次尝试从消息文本中 JSON 解析
3. 最后返回兜底 `unknown`

**首次消息才做意图识别**：路由后的 `agent_name` 持久化到数据库中，后续同一对话的消息直接走对应 Agent，不再重复分类。

### 2. 监督者模式（Supervisor）

```python
from langweave.orchestration import SupervisorBuilder

workers = {"math": math_agent, "search": search_agent}
supervisor = SupervisorBuilder(workers).build()
reply = supervisor.chat("计算 99*101 并搜索最新新闻")
```

每个 worker Agent 通过 `create_handoff_tool()` 包装成 `StructuredTool`，supervisor 调用工具来委派任务。

### 3. 降级模式（Fallback）

当模型依赖（如 `langchain-deepseek`）未安装时，注册 `UnavailableAgent`，在 `achat` / `ainvoke` / `aget_history` 中返回错误信息。

```python
# app/agents/fallback_agent.py
class UnavailableAgent:
    def __init__(self, name, description, error_message):
        ...
    async def achat(self, message, *, thread_id=None, **kwargs):
        return self._error_message, thread_id
```

---

## Web 层

### FastAPI 应用工厂

```python
from langweave.web import create_app

app = create_app(
    registry=registry,
    title="LangWeave API",
    on_startup=register_agents,   # 启动时注册 Agent
    doc_mode="swagger2",          # 或 "openapi3"
    cors_origins=["http://localhost:5173"],
)
```

**生命周期（lifespan）：** 启动时调用 `on_startup(registry)` 注册所有 Agent。

**端点：**
- `GET /health` — 健康检查
- `GET /api/v1/agents` — 列出所有 Agent
- `POST /api/v1/agents/{name}/chat` — 对话
- `POST /api/v1/agents/{name}/invoke` — 完整调用
- `POST /api/v1/agents/{name}/stream` — SSE 流式输出

### SSE 流式响应

```python
async def _sse_stream(agent, body):
    async for chunk in agent.astream(body.message, stream_mode=body.stream_mode):
        envelope = ApiResponse.ok({"event": "chunk", "payload": chunk})
        yield f"data: {json_dumps(envelope.model_dump())}\n\n"
    yield f"data: {json_dumps(ApiResponse.ok({"event": "done"}).model_dump())}\n\n"
```

**响应头：**
```
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no   # 禁用 Nginx 缓冲
```

### 统一响应格式

```python
class ApiResponse(BaseModel, Generic[T]):
    code: int = 200      # 业务状态码
    message: str = ""    # 提示信息
    data: T | None       # 业务数据

# 响应示例：{"code":200, "message":"", "data":{...}}
```

### 异常处理

全局异常处理器统一返回 `ApiResponse` 格式：
- `HTTPException` — 返回对应 status_code
- `RequestValidationError` — 返回 422
- `Exception` — 返回 500

### 安全中间件

**RateLimitMiddleware（`langweave/web/middleware.py`）：**
- Redis 模式（推荐）：使用 `INCR` + `EXPIRE` 滑动窗口计数
- 内存模式（fallback）：`_MemoryTokenBucket` 令牌桶算法
- 默认：60 req/min/IP
- 严格限制：login 10/min, register 5/min
- 排除路径：`/health`, `/api/v1/auth/login`, `/api/v1/auth/register`

**SecurityHeadersMiddleware：**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- CSP + Permissions-Policy

### API 文档

两种模式：
- **Swagger 2.0**（默认）：`fastapi-swagger2 + 目录树 UI`，端点 `/docs`
- **OpenAPI 3**：标准 FastAPI Swagger UI，端点 `/docs`

---

## 应用层业务逻辑

### 数据库模型（MySQL + SQLAlchemy）

**`c_users`** — 用户
```
id, username, password_hash, is_admin, created_at
```

**`c_conversations`** — 对话
```
id, user_id, agent_name, thread_id, title, created_at, updated_at
```

**`c_messages`** — 消息
```
id, conversation_id, role, content, created_at
```

设计原则：
- 无外键约束（逻辑关联通过索引列实现）
- `(user_id, agent_name)` 无唯一约束 — 一个用户可以有多段对话
- `thread_id` 唯一索引 — LangGraph Checkpointer 需要的标识

### 数据库连接

```python
# .env 配置
LANGWEAVE_DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname

# 连接池配置
pool_size=5, max_overflow=10, pool_recycle=3600, pool_pre_ping=True
```

### 身份认证

- JWT 令牌（HS256 算法）
- PBKDF2 密码哈希（390000 轮迭代）
- Token 过期：默认 2 小时
- Redis 黑名单支持登出

### 对话记忆

对话服务（`app/application/services/chat.py`）使用**双轨记忆**：
1. **LangGraph Checkpointer** — Agent 内部多轮上下文
2. **c_messages 表** — 用户消息持久化，支持历史查询

`stream_message()` 流程：
1. 解析 / 创建对话
2. 处理首次意图识别
3. 加载历史消息注入 Agent
4. SSE 流式输出
5. 完成后持久化 user + assistant 消息

---

## 项目管理

### 部署脚本

- `script/deploy/deploy_all.sh` — 全量部署
- `script/deploy/deploy_backend.sh` — 后端部署
- `script/deploy/build_desktop.sh` — 桌面端构建
- `script/deploy/publish_release.sh` — 发布 Release
- `Dockerfile` — 容器化构建
- `docker-compose.yml` — 本地开发编排

### 数据库迁移

- `migrations/` — SQL 迁移脚本
- `migrations/README.md` — 迁移指南

### 环境配置

```bash
cp .env.example .env
# 或 .env.prod（生产环境）
```

关键环境变量：
```
DEEPSEEK_API_KEY=sk-xxx
LANGWEAVE_MODEL=deepseek:deepseek-chat
LANGWEAVE_DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
LANGWEAVE_REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret
```

---

## 前端

- **Web SPA**（`frontends/fe/`）— Vue 3 + Vite
- **管理后台**（`frontends/admin/`）— 独立管理界面
- **桌面端**（`frontends/desktop/`）— Electron 应用

---

## 占位模块（待实现）

项目中以下模块为占位状态，需要进一步开发：

| 模块 | 文件 | 状态 |
|------|------|------|
| MCP Manager | `app/core/mcp/mcp_manager.py` | 占位 |
| MCP Client | `app/core/mcp/mcp_client.py` | 占位 |
| MCP Tool Wrapper | `app/core/mcp/mcp_tool_wrapper.py` | 占位 |
| RAG Retriever | `app/core/rag/retriever.py` | 占位 |
| Embedding Service | `app/core/rag/embeddings.py` | 占位 |
| Langfuse Integration | `app/core/monitoring/langfuse_integration.py` | 占位 |
| Langfuse Multitenancy | `app/core/monitoring/langfuse_multitenancy.py` | 占位 |
| Performance Tracker | `app/core/monitoring/performance_tracker.py` | 占位 |
| Anomaly Cache | `app/infrastructure/cache/anomaly.py` | 占位 |
| DAU Cache | `app/infrastructure/cache/dau.py` | 占位 |
| Heartbeat Cache | `app/infrastructure/cache/heartbeat.py` | 占位 |
| Session Cache | `app/infrastructure/cache/session.py` | 占位 |
| Token Blacklist | `app/infrastructure/cache/token_blacklist.py` | 占位 |
| Celery Tasks | `app/tasks/celery_app.py` | 占位 |

---

## 依赖

```
langchain>=1.3
langchain-core>=1.4
langgraph>=1.2
pydantic>=2.0
python-dotenv>=1.0
sqlalchemy>=2.0
pymysql>=1.1
python-jose>=3.3
langgraph-checkpoint-mysql>=3.0
aiomysql>=0.3
fastapi>=0.115
uvicorn[standard]>=0.32
```

可选依赖：`langchain-deepseek`, `fastapi-swagger2`
