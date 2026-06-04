---
name: langweave
description: >-
  LangWeave (织语) langchain 项目：LangChain/LangGraph 框架、入口 Agent 意图路由、
  FastAPI 后端、Vue3 前端、Bash/Docker 部署。修改本项目代码、新增 Agent、
  排查 API/登录/Docker 问题或阅读架构时使用。文档均在 .cursor/skills/langweave/。
---

# LangWeave 项目技能

## 文档索引（单一来源）

| 文档 | 内容 |
|------|------|
| [开发指南.md](开发指南.md) | 环境、本地开发、部署、排障 |
| [framework-reference.md](framework-reference.md) | LangWeave 框架 API、Agent 模式、Web 层 |
| [docker-reference.md](docker-reference.md) | Docker 构建、nginx、env、排障 |
| [../../README.md](../../README.md) | 项目总览、API 表、目录树 |
| [../../app/core/llm/README.md](../../app/core/llm/README.md) | LLM 工厂 |

## 快速要点

- **聊天唯一入口**：`POST /api/v1/unified/stream`（SSE：`intent` / `chunk` / `done` / `error`）
- **路由 prefix**：`agents_unified.py` 必须是 `/api/v1`，不能是 `/api/v1/agents`（会与框架 `/{name}/stream` 冲突）
- **前端 SPA 入口**：`app.html`；Token 在 `localStorage.langweave_token`
- **部署**：Bash（`script/deploy/`）与 Docker（`docker-compose.yml`）并存；MySQL/Redis 均用远端
- **Redis session**：同步路由用 `set_active_session_sync`

## 修改检查清单

- [ ] unified 路径 `/api/v1/unified/stream` 与前端 `client.js` 一致
- [ ] 未恢复已删除的旧 API（emotional-chat / chat / intent）
- [ ] Docker nginx 静态 + API 分离；bash nginx 未误改
- [ ] 前端改动后 rebuild 或 `docker compose build`
