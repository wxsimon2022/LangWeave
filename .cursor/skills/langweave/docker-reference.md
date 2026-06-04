# LangWeave Docker 参考

## 快速命令

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f nginx
docker compose up -d --build
docker compose up -d --build nginx    # 更新 nginx.docker.conf 后
docker compose down
docker exec -it langweave-app sh
curl http://localhost:8088/app.html
```

## .env 示例

```env
DEEPSEEK_API_KEY=sk-...
LANGWEAVE_JWT_SECRET=your-secret
LANGWEAVE_MODEL=deepseek:deepseek-chat
LANGWEAVE_DATABASE_URL=mysql+pymysql://user:pass@db.example.com:3306/langweave
LANGWEAVE_REDIS_URL=redis://:password@redis.example.com:6379/0
LANGWEAVE_CORS_ORIGINS=http://localhost:8088,https://chat.mybfs.cn

# 数据库在宿主机时（macOS/Windows）
# LANGWEAVE_DATABASE_URL=mysql+pymysql://root:pass@host.docker.internal:3306/langweave
# LANGWEAVE_REDIS_URL=redis://host.docker.internal:6379/0
```

## 构建结构

| Stage | target | 产出 |
|-------|--------|------|
| frontend-builder | — | `frontends/fe/dist/` |
| backend | `backend` | Python + uvicorn |
| production | `production` | nginx + 静态文件 |

国内镜像：npm `registry.npmmirror.com` · pip/apk/apt `mirrors.aliyun.com`

## nginx.docker.conf

```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}
location /api/ {
    proxy_pass http://app_backend;   # app:8000
    proxy_buffering off;
}
```

## 架构

```
浏览器 → nginx:8088
           ├─ /、/app.html、/assets/*  →  /usr/share/nginx/html
           └─ /api/*                  →  app:8000
app → 远端 MySQL、远端 Redis
```

## 与 Bash 部署

| 项 | Bash | Docker |
|----|------|--------|
| Nginx | `nginx.chat.mybfs.cn.conf` | `nginx.docker.conf` |
| 静态文件 | rsync 到远端 | 打进 nginx 镜像 |
| MySQL/Redis | 远端 | 远端（`.env` 配置） |
| 后端 | uvicorn 进程 | `app` 容器 |

## 配置要点

| 场景 | 配置 |
|------|------|
| 静态页面 | nginx `root` + `try_files` |
| SSE 流式 | `proxy_buffering off` |
| 容器连宿主机 DB | `host.docker.internal` |
| 默认端口 | compose `8088:80` |
