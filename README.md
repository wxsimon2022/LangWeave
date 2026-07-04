# LangWeave · 织语

[![GitHub Repo stars](https://img.shields.io/github/stars/wxsimon2022/LangWeave?style=social)](https://github.com/wxsimon2022/LangWeave)
[![GitHub](https://img.shields.io/github/license/wxsimon2022/LangWeave)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/langchain-1.x-green.svg)](https://github.com/langchain-ai/langchain)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688.svg)](https://fastapi.tiangolo.com/)

**LangWeave**（织语）是基于 **LangChain 1.x** 与 **LangGraph** 的 Python Agents 框架与完整聊天应用。在官方 `create_agent` 之上提供统一构建、注册、多 Agent 编排与 FastAPI Web 服务，并附带**情感陪伴 + AI 助手**双 Agent 的聊天应用（Vue 3 SPA 前端 + Electron 桌面端 + 管理后台）。

> **命名**：Weave = 编织 —— 将模型、工具、中间件与多个 Agent 编织成可运行的图。

📖 **开发指南**：[.cursor/skills/langweave/开发指南.md](.cursor/skills/langweave/开发指南.md) · [docs/README.md](docs/README.md)

---

## 目录

- [架构](#架构)
- [快速开始](#快速开始deepseek)
- [运行方式](#运行方式)
- [API 接口](#api-接口)
- [前端](#前端)
- [部署](#部署)
- [环境变量](#环境变量)
- [项目结构](#项目结构)
- [多轮对话记忆](#多轮对话记忆)
- [多 Agent 编排](#多-agentsupervisor-模式)
- [与 LangChain 的关系](#与-langchain-的关系)

---

## 架构

### 框架组件

| 模块 | 层 | 职责 |
|------|-----|------|
| `AgentBuilder` | langweave | 流式配置 model / tools / middleware / checkpointer |
| `Agent` | langweave | 封装 invoke / stream / chat，支持 thread_id |
| `AgentRegistry` | langweave | 按名称注册与获取 Agent |
| `ChatService` | application | 入口 Agent 路由，负责意图识别→specialist 分发 |
| `RateLimitMiddleware` | app | IP 限流（Redis 降级内存令牌桶） |
| `SupervisorBuilder` | langweave | 监督者模式，子 Agent 包装为 handoff 工具 |

### 意图路由流程

```
用户消息
   │
   ▼
POST /api/v1/unified/stream          ← 统一入口（SSE 流式）
   │
   ▼
IntentService.recognize()             ← intent Agent 分类意图
   │
   ├─ emotional_chat ──→ emotional    （情感陪伴 · 小暖）
   ├─ general_chat  ──→ assistant     （通用助手 · 计算器/时钟）
   ├─ order_query   ──→ assistant     （订单查询）
   ├─ calculation   ──→ assistant     （数学计算）
   └─ unknown       ──→ assistant     （默认兜底）
```

**设计要点：**

- **统一入口**：前端所有聊天请求走 `/api/v1/unified/stream`（SSE 流式）
- **意图识别**：首次消息经 `intent` Agent 结构化分类后路由到 specialist Agent
- **持久化路由**：路由结果写入 `c_conversations.agent_name`，同对话后续消息直走 specialist，不重复分类
- **SSE 事件**：流中包含 `intent`（路由状态）、`chunk`（逐 token）、`done`（回复完成）

---

## 快速开始（DeepSeek）

```bash
pip install -r requirements.txt    # langchain, langgraph, MySQL checkpointer, etc.
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（启动时会自动加载，无需手动 export）
```

`.env` 示例：

```env
DEEPSEEK_API_KEY=sk-your-key
LANGWEAVE_MODEL=deepseek:deepseek-chat
LANGWEAVE_DATABASE_URL=mysql+pymysql://user:password@host:3306/dbname
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

## 运行方式

### 开发模式

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

启动前需配置 `.env`，完整示例见 `.env.example`：

```env
# 必填
LANGWEAVE_DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
DEEPSEEK_API_KEY=sk-your-key
LANGWEAVE_JWT_SECRET=your-secret-key

# 推荐
LANGWEAVE_REDIS_URL=redis://127.0.0.1:6379/0
```

启动时自动建表（c_users、c_conversations 等）及初始化 admin 账号（admin / admin123）。

### Docker 一键启动

```bash
cp .env.example .env          # 填入 API Key、MySQL/Redis 连接
docker compose up -d --build  # app + nginx
```

访问 `http://localhost:8088`。详细配置见 [docker-reference](.cursor/skills/langweave/docker-reference.md)。

> **注意**：应用**强依赖 MySQL**，SQLite 不可用。多轮记忆使用 `langgraph-checkpoint-mysql` 持久化到同一库。

---

## API 接口

### 入口 Agent（统一聊天入口）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/unified/stream` | **统一入口** — SSE 流式，先识别意图后路由 |
| GET | `/api/v1/conversations` | 列出所有对话 |
| GET | `/api/v1/conversations/{id}/history` | 分页查看对话历史 |
| DELETE | `/api/v1/conversations/{id}/history` | 清空对话历史 |
| DELETE | `/api/v1/conversations/{id}` | 删除整个对话 |
| PATCH | `/api/v1/conversations/{id}` | 修改对话名称 |

SSE 事件：

| 事件 | 触发时机 | Payload |
|------|----------|---------|
| `intent` | 意图识别完成 | `{intent, confidence, reasoning, target_agent}` |
| `chunk` | 逐 token 流式输出 | `{content: "..."}` |
| `done` | 回复结束 | `{conversation_id, thread_id, agent, assistant_message}` |
| `error` | 流式异常 | `{message: "..."}` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/unified/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "我最近好焦虑，心情很差..."}'
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
- **聊天入口**：`/app.html`（Vite 构建 input）；宣传页为 `/`（`public/index.html`）
- 本地 dev 将 `/api` 代理到 `http://localhost:8000`；`VITE_API_BASE_URL` 留空即可
- 登录态：刷新时先 `restoreSession()`，用 `authCheckDone` 避免短暂闪现登录页

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

### Bash 脚本部署（生产）

```bash
./script/deploy/deploy_all.sh      # 全量：前端构建 → rsync → 依赖 → 重启 → nginx reload
./script/deploy/deploy_backend.sh  # 仅后端
./script/deploy/build_desktop.sh   # Electron 桌面端（含 electron-updater 在线更新）
```

- Nginx 配置：`script/deploy/nginx.chat.mybfs.cn.conf`
- 环境变量与远端目录：见 [script/deploy/README.md](script/deploy/README.md)

### Docker 部署

```bash
cp .env.example .env   # 填入 API Key、JWT、远端 MySQL/Redis 地址
docker compose up -d --build
```

- 服务：`app` + `nginx`
- 访问：`http://localhost:8088`
- MySQL、Redis：远端，通过 `.env` 配置
- 配置：`Dockerfile`、`docker-compose.yml`、`script/deploy/nginx.docker.conf`
- 文档：[开发指南](.cursor/skills/langweave/开发指南.md) · [docker-reference](.cursor/skills/langweave/docker-reference.md)

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 推荐 |
| `LANGWEAVE_MODEL` | 默认模型（默认 `deepseek:deepseek-chat`） | |
| `LANGWEAVE_DATABASE_URL` | MySQL 连接（必填，应用强依赖 MySQL，不支持 SQLite） | **是** |
| `LANGWEAVE_JWT_SECRET` | JWT 签名密钥 | 生产必填 |
| `LANGWEAVE_JWT_EXPIRE_MINUTES` | JWT 过期分钟数（默认 120） | |
| `LANGWEAVE_REDIS_URL` | Redis 连接（心跳、单设备登录、DAU） | 推荐 |
| `LANGWEAVE_TEMPERATURE` | 采样温度 | |
| `LANGWEAVE_MAX_TOKENS` | 最大生成 token | |
| `LANGWEAVE_SYSTEM_PROMPT` | 默认 system prompt | |
| `LANGWEAVE_MEMORY_ENABLED` | 多轮记忆开关（默认 true） | |
| `LANGWEAVE_DEBUG` | 设为 `true` 开启 LangGraph debug | |

---



---

## 项目结构

```
langweave/                         # 框架层
├── agent.py / builder.py          Agent 包装器与流式构建器
├── config.py / registry.py        配置加载与 Agent 注册表
├── memory.py                      多轮记忆（MySQL checkpointer）
├── web/                           FastAPI 工厂 + 路由 + Swagger
└── tools/                         内置工具（calculator）

app/                                # 业务层
├── core/                           LLM、MCP、RAG、监控等基础能力
├── domain/                         领域层
│   ├── agents/                     Agent 实现（intent / emotional / assistant / fallback）
│   ├── tools/                      领域工具（订单查询等）
│   └── registry.py                 注册入口
├── application/                    应用服务层
│   ├── services/                   ChatService（入口路由）、Auth、Session、Intent
│   └── security.py                 JWT / HMAC
├── infrastructure/                 基础设施层
│   ├── cache/                      Redis（心跳、DAU、单设备登录、令牌黑名单）
│   └── persistence/                MySQL ORM + 连接管理
├── interfaces/http/                FastAPI 路由（auth / chat / admin / heartbeat）
├── middleware/                      限流中间件（RateLimitMiddleware）
├── schemas/                        Pydantic 请求/响应模型
├── prompts/                        提示词模板
└── bootstrap.py                    应用组合根（DB 初始化 → Agent 注册 → 启动）

frontends/                          前端项目（Vue 3 SPA + Electron）
sql/                             数据库迁移 SQL
scripts/                            部署脚本
config/                             配置文件（MCP、Prompts）
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

`assistant`、`emotional` 已启用 LangGraph checkpointer（**MySQL 持久化**，跨重启保留）。

多轮记忆依赖 `LANGWEAVE_DATABASE_URL` 指向 MySQL 数据库。首次使用时，`langweave/memory.py` 会自动创建 `checkpoints`、`checkpoint_blobs`、`checkpoint_writes` 三张表；如果表结构来自 `langgraph-checkpoint-mysql` 旧版本，迁移逻辑会自动补充缺失的 `checkpoint_ns` 列并修复排序规则。

1. 首次对话可不传 `thread_id`，响应会返回 `thread_id`
2. 后续请求带上同一 `thread_id`，Agent 会记住此前消息

```bash
curl -X POST http://127.0.0.1:8000/api/v1/unified/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "最近很焦虑"}'
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
