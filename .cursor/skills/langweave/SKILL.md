---
name: langweave
description: >-
  LangWeave (织语) langchain 项目开发与部署指南：入口 Agent 意图路由、FastAPI 后端、Vue3 前端、
  Bash 脚本部署与 Docker 部署。在用户修改 LangWeave 代码、排查聊天/API/登录问题、
  新增 Agent、配置 nginx、docker compose、Electron 桌面端或阅读本项目结构时使用。
---

# LangWeave 项目技能

## 项目概览

- **仓库**：LangChain Agents 框架 + 完整聊天应用（情感陪伴 + 通用助手）
- **后端入口**：`main.py` → `app.core.app.create_app()`
- **前端**：`frontends/fe`（Vue 3 + Vite），SPA 入口 **`app.html`**（不是 `index.html`）
- **宣传页**：`frontends/fe/public/index.html`，生产由 nginx 单独提供
- **桌面端**：`frontends/desktop`（Electron + electron-updater）
- **框架包**：`langweave/`（AgentBuilder、Registry、FastAPI 集成）

## 核心架构：入口 Agent 意图路由

```
POST /api/v1/unified/stream  (SSE)
  → IntentService.recognize()  (intent Agent)
  → 路由到 emotional / assistant 等 specialist Agent
```

**设计要点**（修改聊天链路前先读）：

| 要点 | 说明 |
|------|------|
| 唯一聊天入口 | 前端只调 `/api/v1/unified/stream`，旧 `emotional-chat` / `chat` / `intent` API 已移除 |
| 路由前缀 | `agents_unified.py` 的 router prefix 必须是 `API_V1_PREFIX`（`/api/v1`），**不能**用 `/api/v1/agents`，否则会与框架 `/{agent_name}/stream` 冲突 → `Unknown agent: unified` |
| 首次识别 | 每条新对话首次消息做意图分类；`agent_name` 持久化后同对话不再重复分类 |
| SSE 事件 | `intent` / `chunk` / `done` / `error` |

**关键文件**：

- `app/api/v1/agents_unified.py` — 统一流式入口 + 对话 CRUD
- `app/application/services/chat.py` — 入口路由业务逻辑
- `app/application/services/intent.py` — 意图识别
- `app/domain/agents/` — `intent_agent.py`、`research_agent_v2.py`（emotional）、`general_agent_v2.py`（assistant）
- `app/interfaces/http/router.py` — 业务路由聚合（无旧版 chat 路由）
- `frontends/fe/src/api/client.js` — 前端 API 客户端

## API 速查

| 用途 | 方法 | 路径 |
|------|------|------|
| 健康检查 | GET | `/health` |
| 登录/注册 | POST | `/api/v1/auth/login` `/register` |
| 当前用户 | GET | `/api/v1/auth/me` |
| 流式聊天 | POST | `/api/v1/unified/stream` |
| 对话列表 | GET | `/api/v1/conversations` |
| 对话历史 | GET | `/api/v1/conversations/{id}/history` |
| 心跳 | POST | `/api/v1/heartbeat/ping` |

Token 存 `localStorage.langweave_token`；`VITE_API_BASE_URL` 为空时走同源（Docker/nginx 推荐）。

## 两种部署方式（并存，互不影响）

### 1. Bash 脚本部署（生产默认）

```bash
./script/deploy/deploy_all.sh      # 全量：前端构建 + rsync + 重启 + nginx reload
./script/deploy/deploy_backend.sh  # 仅后端
./script/deploy/build_desktop.sh   # Electron 打包
```

- Nginx 配置：`script/deploy/nginx.chat.mybfs.cn.conf`
- **不要**为 Docker 改这些脚本

### 2. Docker 部署

```bash
cp .env.example .env   # 填 DEEPSEEK_API_KEY、LANGWEAVE_JWT_SECRET、LANGWEAVE_DATABASE_URL、LANGWEAVE_REDIS_URL
docker compose up -d --build
# 默认访问 http://localhost:8088（compose 中 ports: "8088:80"）
```

**容器组成**：仅 `app` + `nginx`。**MySQL / Redis 用远端服务**，不在 compose 里起镜像。

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 三阶段：`frontend-builder` → `backend` → `production`(nginx+静态) |
| `docker-compose.yml` | app(target: backend) + nginx(target: production) |
| `script/deploy/nginx.docker.conf` | Docker 专用 nginx（与生产 bash nginx **分开**） |
| `.dockerignore` | 排除 node_modules、.env、dist 等 |

**Docker 架构**：

```
浏览器 → nginx:80 (映射宿主机 8088)
           ├─ /、/app.html、/assets/* → /usr/share/nginx/html（Vite 构建产物）
           └─ /api/* → proxy_pass app:8000（SSE 需 proxy_buffering off）
app → 外部 MySQL（LANGWEAVE_DATABASE_URL）、外部 Redis（LANGWEAVE_REDIS_URL）
```

**Docker 常见坑**（详见 [docker-reference.md](docker-reference.md)）：

1. **根路径 404**：nginx 不能把 `/` 全 proxy 到 FastAPI（后端不提供静态文件）；必须由 nginx `root` + `try_files` 提供前端
2. **SPA 入口**：Vite `rollupOptions.input` 是 `app.html`；访问聊天页用 `/app.html`
3. **容器连宿主机 DB**：macOS/Windows 用 `host.docker.internal` 替代 `127.0.0.1`
4. **国内构建慢**：Dockerfile 已配阿里云 apt/pip/npm 镜像，勿删
5. **改 nginx 配置后**：`docker compose up -d --build nginx`

## 前端要点

### 刷新闪登录页

`App.vue` 使用 `authCheckDone`：在 `restoreSession()`（`/api/v1/auth/me`）完成前显示 loading，避免 `authenticated=false` 时短暂渲染登录表单。

```vue
<main v-if="!authCheckDone && !authenticated">…loading…</main>
<main v-if="authCheckDone && !authenticated">…登录…</main>
<main v-if="authenticated">…聊天…</main>
```

### 本地开发

```bash
cd frontends/fe && npm install && npm run dev   # :5173，/api 代理到 :8000
uvicorn main:app --reload                        # 后端
```

## 后端要点

### 鉴权与 Redis

- JWT + Redis 单设备登录：`app/infrastructure/cache/session.py`
- 同步路由（login/register/refresh）必须用 **`set_active_session_sync`**，勿在已有 event loop 里复用同一 coroutine（会 `cannot reuse already awaited coroutine`）
- Redis 用途：心跳、DAU(HyperLogLog)、token 黑名单、活跃 session

### 环境变量（生产必填）

`DEEPSEEK_API_KEY`、`LANGWEAVE_JWT_SECRET`、`LANGWEAVE_DATABASE_URL`、`LANGWEAVE_REDIS_URL`

MySQL 连接示例：`mysql+pymysql://user:pass@host:3306/langweave`

### 新增 Agent 流程

1. 在 `app/domain/agents/` 实现并注册到 AgentRegistry（`app/bootstrap.py`）
2. 在 `IntentService` / 路由映射里加入 `target_agent`
3. 若需新 HTTP 端点，挂到 `app/interfaces/http/router.py` 或 `app/api/v1/`
4. **不要**恢复 `/api/v1/agents/{name}/stream` 作为业务入口（与 unified 冲突）

## 修改检查清单

- [ ] unified 路由 prefix 仍为 `/api/v1`，路径 `/unified/stream`
- [ ] 前端 `client.js` 与后端路径一致
- [ ] Docker nginx 静态文件 + API 代理分离；bash nginx 配置未误改
- [ ] 登录/session 改动是否需 sync Redis  helper
- [ ] 前端改完需 `npm run build` 或 `docker compose build`
- [ ] README 架构图/API 表是否需要同步

## 延伸阅读

- Docker 排障与 env 示例：[docker-reference.md](docker-reference.md)
- 完整目录树与 API 文档：`README.md`
