# LangWeave · 织语

**LangWeave**（织语）是基于 **LangChain 1.x** 与 **LangGraph** 的 Python Agents 框架与完整聊天应用。在官方 `create_agent` 之上提供统一构建、注册、多 Agent 编排与 FastAPI Web 服务，并附带**情感陪伴 + AI 助手**双 Agent 的聊天应用（Vue 3 SPA 前端 + Electron 桌面端 + 管理后台）。

> **命名**：Weave = 编织 —— 将模型、工具、中间件与多个 Agent 编织成可运行的图。

---

## 架构

```mermaid
flowchart TB
    subgraph app [应用层]
        AB[AgentBuilder]
        AR[AgentRegistry]
        SB[SupervisorBuilder]
    end
    subgraph lc [LangChain]
        CA[create_agent]
        MW[AgentMiddleware]
    end
    subgraph lg [LangGraph]
        G[CompiledStateGraph]
    end
    AB --> CA
    CA --> G
    MW --> CA
    AR --> Agent
    SB --> AB
    Agent --> G
```

| 模块 | 职责 |
|------|------|
| `AgentBuilder` | 流式配置 model / tools / middleware / checkpointer |
| `Agent` | 封装 `invoke` / `stream` / `chat`，支持 `thread_id` |
| `AgentRegistry` | 按名称注册与获取 Agent |
| `ToolRegistry` | 按分组管理工具 |
| `LoggingMiddleware` | 记录 model 与 tool 调用 |
| `SupervisorBuilder` | 监督者模式，将子 Agent 包装为 handoff 工具 |

---

## 业务 Agent 架构：入口 Agent 意图路由

```
用户消息
   │
   ▼
┌─────────────────────────────┐
│  POST /api/v1/chat/stream   │  ← 统一入口（SSE 流式）
│    │                         │
│    ▼                         │
│  IntentService.recognize()   │  ← intent Agent 分类意图
│    │                         │
│    ├─ emotional_chat ───────→ emotional Agent （情感陪伴）
│    ├─ general_chat ─────────→ assistant Agent （通用助手）
│    ├─ order_query ──────────→ assistant Agent （订单查询）
│    ├─ calculation ──────────→ assistant Agent （数学计算）
│    └─ unknown ──────────────→ assistant Agent （默认兜底）
└─────────────────────────────┘
```

**关键设计**：

- **入口 Agent** 是唯一的前端聊天入口。每条消息先经过 `intent` Agent 做结构化意图分类，再路由到对应的 specialist Agent
- **首次消息才做意图识别**。路由后的 `agent_name` 持久化到对话记录中，后续同一对话的消息直接走对应 Agent，不再重复分类
- SSE 流中新增 `intent` 事件，前端可展示路由状态

---

## 快速开始（DeepSeek）

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（启动时会自动加载，无需手动 export）
```

`.env` 示例：

```env
DEEPSEEK_API_KEY=sk-your-key
LANGWEAVE_MODEL=deepseek:deepseek-chat
```

```python
from langweave import AgentBuilder
from langweave.tools import calculator

agent = (
    AgentBuilder()
    .with_name("math")
    .with_deepseek("deepseek-chat", temperature=0.3)
    .with_tools([calculator])
    .with_system_prompt("Use tools for arithmetic.")
    .build()
)

print(agent.chat("99 * 101 等于多少？"))
```

也可直接写模型字符串或使用工厂函数：

```python
from langweave import AgentBuilder, chat_model

agent = AgentBuilder().with_model(chat_model("deepseek-chat")).build()
# 或: .with_model("deepseek:deepseek-reasoner")
```

### OpenAI（可选）

```bash
pip install langchain-openai
export OPENAI_API_KEY=sk-...
export LANGWEAVE_MODEL=openai:gpt-4o-mini
```

---

## 启动项目

### 后端

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 数据库

项目使用 MySQL（开发环境可回退 SQLite）：

```env
LANGWEAVE_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/langweave
LANGWEAVE_JWT_SECRET=change-this-in-production
LANGWEAVE_JWT_EXPIRE_MINUTES=10080
```

启动时自动建表。

### Redis

用于心跳检测、单设备登录、日活统计：

```env
LANGWEAVE_REDIS_URL=redis://127.0.0.1:6379/0
```

---

## API 接口

### 入口 Agent（统一聊天入口）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/stream` | **入口 Agent** — SSE 流式，先识别意图后路由到对应 Agent |
| GET | `/api/v1/chat/conversations` | 列出所有对话（跨 Agent 类型） |
| GET | `/api/v1/chat/history` | 分页查看对话历史 |
| DELETE | `/api/v1/chat/history` | 清空对话历史 |
| DELETE | `/api/v1/chat/conversations/{id}` | 删除整个对话 |
| PATCH | `/api/v1/chat/conversations/{id}` | 修改对话名称 |

SSE 事件：

| 事件 | 触发时机 | Payload |
|------|----------|---------|
| `intent` | 意图识别完成 | `{intent, confidence, reasoning, target_agent}` |
| `chunk` | 逐 token 流式输出 | `{content: "..."}` |
| `done` | 回复结束 | `{conversation_id, thread_id, agent, assistant_message}` |
| `error` | 流式异常 | `{message: "..."}` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "我最近好焦虑，心情很差..."}'
# 返回 SSE：intent → chunk → chunk → ... → done
```

### 情感聊天（旧版，向后兼容）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/emotional-chat/stream` | SSE 流式（直接走 emotional Agent，无意图路由） |
| GET | `/api/v1/emotional-chat/conversations` | 仅列出 emotional Agent 的对话 |
| GET | `/api/v1/emotional-chat/history` | 查看历史 |
| POST | `/api/v1/emotional-chat/messages` | 同步发送消息 |
| DELETE | `/api/v1/emotional-chat/history` | 清空历史 |
| PATCH | `/api/v1/emotional-chat/conversations/{id}` | 重命名 |

### 意图识别（内部接口）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/intent/recognize` | 仅识别意图（结构化输出） |
| POST | `/api/v1/intent/chat` | 识别 + 路由到 target_agent 并回复 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/intent/recognize \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我查订单10001到哪了"}'
```

响应：

```json
{
  "intent": {
    "intent": "order_query",
    "confidence": 0.91,
    "slots": {"order_id": "10001"},
    "target_agent": "assistant",
    "reasoning": "用户询问订单物流"
  }
}
```

代码中调用：

```python
from app.application.services.intent import IntentService

service = IntentService(registry)
intent = await service.recognize("查订单10001")
result = await service.recognize_and_chat("查订单10001")  # 含 reply
```

### 鉴权

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册并返回 JWT |
| POST | `/api/v1/auth/login` | 登录并返回 JWT（含单设备登录检查） |
| POST | `/api/v1/auth/logout` | 登出（撤销 token） |
| POST | `/api/v1/auth/refresh` | 刷新 token |
| GET | `/api/v1/auth/me` | 获取当前用户 |
| GET | `/api/v1/auth/me/with-admin` | 获取用户信息（含 is_admin 判断） |

### Agent 框架接口（免鉴权）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/agents` | 列出已注册 Agent |
| POST | `/api/v1/agents/{name}/chat` | 对话，返回文本 |
| POST | `/api/v1/agents/{name}/invoke` | 完整状态（含 messages） |
| POST | `/api/v1/agents/{name}/stream` | SSE 流式输出 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agents/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "12 * 8 = ?"}'
```

### 会话记忆

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sessions/{agent}/{thread_id}` | 查看会话历史 |
| DELETE | `/api/v1/sessions/{agent}/{thread_id}` | 清空该会话记忆 |

### 心跳 / 在线状态

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/heartbeat/ping` | 客户端心跳上报（Redis） |

### 管理后台接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/users` | 用户列表 |
| POST | `/api/v1/admin/users` | 新增用户 |
| GET | `/api/v1/admin/users/online` | 在线用户 |
| GET | `/api/v1/admin/stats/dau` | 日活统计 |

---

## 前端

### 主聊天 SPA（Vue 3 + Vite）

```bash
cd frontends/fe
npm install
npm run dev
```

- 默认地址：`http://127.0.0.1:5173`
- 与后端交互的聊天入口为 `/api/v1/chat/stream`（入口 Agent）

### 管理后台（Vue 3 + Vite）

```bash
cd frontends/admin
npm install
npm run dev
```

- 默认地址：`http://127.0.0.1:5174`
- 功能：用户管理、在线状态、日活统计

### 桌面客户端（Electron）

```bash
cd frontends/desktop
npm install
npm run build
```

打包脚本：

```bash
./script/deploy/build_desktop.sh
```

---

## 部署

### 全量部署

```bash
./script/deploy/deploy_all.sh
```

包含：前端构建 → 打包发布 → rsync 到远端 → 安装依赖 → 重启服务 → nginx reload

### 仅后端部署

```bash
./script/deploy/deploy_backend.sh
```

只更新后端代码和依赖，不构建前端。

### 桌面端打包

```bash
./script/deploy/build_desktop.sh
```

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 推荐 |
| `LANGWEAVE_MODEL` | 默认模型（默认 `deepseek:deepseek-chat`） | |
| `LANGWEAVE_DATABASE_URL` | 数据库连接（默认 SQLite） | |
| `LANGWEAVE_JWT_SECRET` | JWT 签名密钥 | 生产必填 |
| `LANGWEAVE_JWT_EXPIRE_MINUTES` | JWT 过期分钟数（默认 120） | |
| `LANGWEAVE_REDIS_URL` | Redis 连接（心跳、单设备登录、DAU） | 推荐 |
| `LANGWEAVE_TEMPERATURE` | 采样温度 | |
| `LANGWEAVE_MAX_TOKENS` | 最大生成 token | |
| `LANGWEAVE_SYSTEM_PROMPT` | 默认 system prompt | |
| `LANGWEAVE_MEMORY_ENABLED` | 多轮记忆开关（默认 true） | |
| `LANGWEAVE_DEBUG` | 设为 `true` 开启 LangGraph debug | |

---

## 业务功能

### Agent 列表

| Agent | 名称 | 说明 |
|-------|------|------|
| `intent` | 意图识别 Agent | 结构化输出，分类用户意图，路由到 specialist |
| `emotional` | 情感陪伴 Agent | 共情式对话，支持多轮记忆（checkpointer） |
| `assistant` | 通用助手 Agent | 含计算器、时钟工具，支持工具调用 |
| `fallback` | 兜底 Agent | 当目标 Agent 不存在时使用 |

### 单设备登录

基于 Redis 的 session 追踪。每个 JWT 签发时记录 `jti` 到 Redis，每次请求校验当前 token 是否为最新活跃 session。同一账号新登录会踢掉旧设备。

### 日活统计（DAU）

基于 Redis HyperLogLog 实现每日 UV 统计，支持历史趋势查询。

### 对话管理

- 编辑对话名称（双击或点击修改按钮）
- 删除整个对话
- 自动从首条消息生成对话标题

---

## 项目结构

```
langweave/                        # 框架层（通用 Agent 能力）
  agent.py                        # Agent 包装器
  builder.py                      # AgentBuilder 流式构建器
  config.py                       # 配置加载
  registry.py                     # AgentRegistry
  models/                         # 自定义模型封装（DeepSeek 等）
  middleware/                     # 中间件（Logging 等）
  tools/                          # 框架内置工具（calculator）
  orchestration/                  # 编排模式（Supervisor）
  memory.py                       # 多轮记忆管理
  web/                            # 通用 HTTP API
    app.py                        # create_app 工厂
    deps.py                       # FastAPI 依赖注入
    routes.py                     # 框架路由
    response.py                   # 统一响应体
    serialize.py                  # JSON 序列化
    openapi.py                    # OpenAPI / Swagger 配置
    tree_docs.py                  # 目录树文档 UI

app/                              # 业务层
  constants.py                    # 共享常量
  exceptions.py                   # 自定义异常
  utils.py                        # 工具函数
  logging.py                      # 日志配置
  types.py                        # 类型别名

  domain/
    agents/
      registry.py                 # 业务 Agent 注册
      intent.py                   # 意图分类 Agent
      emotional.py                # 情感陪伴 Agent
      assistant.py                # 通用助手 Agent
      fallback.py                 # 兜底 Agent
      memory.py                   # 记忆模式 Agent
    tools/
      catalog.py                  # 业务工具：catalog 查询
      order.py                    # 业务工具：订单查询

  application/
    security.py                   # JWT 生成/验证、密码哈希
    services/
      auth.py                     # 鉴权服务
      chat.py                     # 聊天服务（入口 Agent 路由）
      emotional_chat.py           # 情感聊天服务
      intent.py                   # 意图识别服务
      session.py                  # 会话管理服务

  infrastructure/
    cache/
      session.py                  # 单设备登录 session（Redis）
      token_blacklist.py          # 令牌黑名单（Redis）
      heartbeat.py                # 用户心跳（Redis Sorted Set）
      dau.py                      # 日活统计（HyperLogLog）
      anomaly.py                  # 异常检测（Redis）
    persistence/
      database.py                 # 数据库连接
      models.py                   # ORM 模型（User, Conversation, ChatMessage）

  interfaces/
    http/
      router.py                   # 路由聚合
      deps.py                     # 依赖注入（鉴权、服务）
      auth_routes.py              # 鉴权路由
      chat_routes.py              # 入口 Agent 聊天路由
      emotional_chat_routes.py    # 情感聊天路由（旧版）
      intent_routes.py            # 意图识别路由
      heartbeat_routes.py         # 心跳路由
      admin_routes.py             # 管理后台路由
      session_routes.py           # 会话记忆路由

  schemas/
    auth.py                       # 鉴权数据结构
    emotional_chat.py             # 聊天数据结构
    intent.py                     # 意图识别数据结构
    admin.py                      # 管理后台数据结构
    session.py                    # 会话数据结构

main.py                           # 入口，仅组装框架 + 业务
app/bootstrap.py                  # 业务启动：DB 初始化、Agent 注册
script/deploy/                    # 部署脚本
frontends/
  fe/                             # 主聊天 SPA（Vue 3 + Vite）
  admin/                          # 管理后台 SPA（Vue 3 + Vite）
  desktop/                        # Electron 桌面端
tests/                            # 测试
```

---

## 多 Agent（Supervisor 模式）

框架内置 Supervisor 编排模式（目前项目未启用），供自定义场景使用：

```python
from langweave import AgentBuilder
from langweave.orchestration import SupervisorBuilder

researcher = AgentBuilder().with_name("researcher").with_model(model).build()
coder = AgentBuilder().with_name("coder").with_model(model).build()

supervisor = SupervisorBuilder(
    {"researcher": researcher, "coder": coder},
    model=model,
).build()

print(supervisor.chat("Explain async/await and give a tiny example."))
```

---

## 多轮对话记忆

`assistant`、`emotional` 已启用 LangGraph checkpointer（内存会话，重启服务后清空）。

1. 首次对话可不传 `thread_id`，响应会返回 `thread_id`
2. 后续请求带上同一 `thread_id`，Agent 会记住此前消息

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agents/emotional/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "最近很焦虑"}'
# 记下返回的 data.thread_id 用于后续对话
```

关闭记忆：`LANGWEAVE_MEMORY_ENABLED=false`

---

## 测试

```bash
pip install pytest
pytest tests/ -q
```

测试使用 `FakeMessagesListChatModel`，无需 API Key。

---

## 与 LangChain 的关系

本框架**不替代** LangChain Agent API，而是：

1. 用 `create_agent` 编译 LangGraph 图
2. 复用官方 `AgentMiddleware` 生态（如 `ModelRetryMiddleware`、`SummarizationMiddleware`）
3. 在应用层补充注册表、监督者编排与内置工具

可直接在 `AgentBuilder.with_middleware()` 中接入 [LangChain 内置中间件](https://docs.langchain.com/oss/python/langchain/middleware)。

---

## 开源协议

本项目采用 [MIT License](LICENSE) 发布。

- 可自由使用、修改、分发与商用
- 需保留版权声明与许可全文
- 软件按「原样」提供，不提供任何担保
