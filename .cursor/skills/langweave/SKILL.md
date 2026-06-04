---
name: langweave
description: >-
  LangWeave (织语) langchain 项目：LangChain/LangGraph 框架、入口 Agent 意图路由、
  FastAPI 后端、Vue3 前端、Bash/Docker 部署。修改本项目代码、新增 Agent、
  排查 API/登录/Docker 问题或阅读架构时使用。文档均在 .cursor/skills/langweave/。
---

# LangWeave 项目技能

## 文档索引

| 文档 | 内容 |
|------|------|
| [开发指南.md](开发指南.md) | 环境、本地开发、部署 |
| [framework-reference.md](framework-reference.md) | LangWeave 框架 API、Agent 模式、Web 层 |
| [docker-reference.md](docker-reference.md) | Docker 构建、nginx、env |
| [../../README.md](../../README.md) | 项目总览、API 表、目录树 |
| [../../app/core/llm/README.md](../../app/core/llm/README.md) | LLM 工厂 |

## 项目要点

- **聊天入口**：`POST /api/v1/unified/stream`（SSE：`intent` / `chunk` / `done` / `error`）
- **路由**：`app/api/v1/agents_unified.py`，prefix `/api/v1`，路径 `/unified/stream`
- **前端**：SPA 入口 `app.html`；Token 存 `localStorage.langweave_token`；登录态恢复用 `authCheckDone`
- **部署**：Bash（`script/deploy/`）与 Docker（`docker-compose.yml`）；MySQL、Redis 为远端服务
- **Session**：`app/infrastructure/cache/session.py`，同步路由使用 `set_active_session_sync`

## 修改检查清单

- [ ] `/api/v1/unified/stream` 与前端 `client.js` 一致
- [ ] Docker：`nginx.docker.conf` 提供静态文件并反代 `/api/`
- [ ] 前端改动后执行 `npm run build` 或 `docker compose build`
