# LangWeave Docker 参考

## 快速命令

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f nginx
docker compose up -d --build          # 全量重建
docker compose up -d --build nginx    # 仅重建 nginx（改 nginx.docker.conf 后）
docker compose down
docker exec -it langweave-app sh
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8088/app.html
curl -s http://localhost:8088/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
```

## .env 示例（Docker + 远端 MySQL/Redis）

```env
DEEPSEEK_API_KEY=sk-...
LANGWEAVE_JWT_SECRET=your-secret
LANGWEAVE_MODEL=deepseek:deepseek-chat

# 远端 MySQL
LANGWEAVE_DATABASE_URL=mysql+pymysql://user:pass@db.example.com:3306/langweave

# 远端 Redis
LANGWEAVE_REDIS_URL=redis://:password@redis.example.com:6379/0

# MySQL/Redis 在 Docker 宿主机上时（macOS/Windows）
# LANGWEAVE_DATABASE_URL=mysql+pymysql://root:pass@host.docker.internal:3306/langweave
# LANGWEAVE_REDIS_URL=redis://host.docker.internal:6379/0

LANGWEAVE_CORS_ORIGINS=http://localhost:8088,https://chat.mybfs.cn
```

## Dockerfile 三阶段

| Stage | target | 产出 |
|-------|--------|------|
| frontend-builder | — | `frontends/fe/dist/` |
| backend | `backend` | Python + uvicorn，无前端文件 |
| production | `production` | nginx:alpine + dist + nginx.docker.conf |

国内镜像（勿随意删除）：

- npm: `registry.npmmirror.com`
- pip: `mirrors.aliyun.com/pypi/simple/`
- apt/apk: `mirrors.aliyun.com`

## nginx.docker.conf 要点

```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;   # SPA fallback
}
location /api/ {
    proxy_pass http://app_backend;      # app:8000
    proxy_buffering off;                # SSE 必须
}
```

**错误模式**：`location / { proxy_pass http://app_backend; }` → FastAPI 无静态挂载 → 404。

Auth 路径实际为 `/api/v1/auth/*`，走 `/api/` 即可；`/auth/` location 为冗余兼容。

## 端口

- compose 默认 `"8088:80"`（避免 macOS 80 占用）
- 改端口：编辑 `docker-compose.yml` → `nginx.ports`

## 与 Bash 部署的差异

| 项 | Bash (`deploy_all.sh`) | Docker |
|----|------------------------|--------|
| Nginx 配置 | `nginx.chat.mybfs.cn.conf` | `nginx.docker.conf` |
| 静态文件 | rsync 到远端目录 | 打进 nginx 镜像 |
| MySQL/Redis | 远端已有 | 同样用远端（不进 compose） |
| 后端进程 | systemd/supervisor | uvicorn 容器 |

两套部署**独立维护**；新增 Docker 功能时不要改 `script/deploy/deploy_all.sh` 行为。

## 故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `/` 或 `/app.html` 404 | nginx 反代到 app 而非静态 | 检查 nginx.docker.conf 的 `root`/`try_files` |
| API 502 | app 未启动或 DB 连不上 | `docker compose logs app` |
| 登录后无法聊天 | CORS 或 API 路径 | 确认 `LANGWEAVE_CORS_ORIGINS` 含访问 origin |
| 容器内连不上 127.0.0.1 DB | 127.0.0.1 指容器自身 | 改用 `host.docker.internal` 或远端 IP |
| 构建极慢 | 未走国内镜像 | 确认 Dockerfile 镜像源配置 |
| SSE 无流式 | nginx 缓冲 | `proxy_buffering off` |
