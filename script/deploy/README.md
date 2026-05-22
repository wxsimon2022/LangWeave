部署脚本说明：

1. 本地构建前端并整理后端发布包
2. 上传到 `root@124.223.72.223:/home/biu/chat`
3. 上传 nginx 配置到 `root@124.223.72.223:/usr/local/nginx/conf/vhost/`
4. 证书文件同步到远端发布目录下的 `ssl/`

默认域名配置来自 `script/chat.mybfs.cn_nginx/`。

脚本：

- `script/deploy/deploy_all.sh`：唯一部署入口，单脚本完成构建、`rsync` 直传覆盖、远端部署、启动和 nginx reload

## 环境变量

项目环境变量来源：

| 文件 | 用途 | 是否包含在发布包中 |
|---|---|---|
| `.env` | 本地开发配置 | ❌ 被 rsync 排除 |
| `.env.prod` | **生产配置**（项目根目录） | ✅ 发布到 `config/.env.prod` |
| `.env.example` | 空模板，供参考 | ✅ 发布包中保留 |

### 首次部署

服务器上 `/home/biu/chat/shared/.env` 不存在时，脚本会自动从发布包中的 `config/.env.prod` 复制作为远端环境变量。后续部署不会覆盖 shared/.env，因此可以安全地在服务器上手动修改。

### 修改生产配置

修改项目根目录下的 `.env.prod`，然后重新部署。已有的 `shared/.env` 不会被覆盖，如需同步需手动替换。

### 推荐部署命令

```bash
./script/deploy/deploy_all.sh
```

远端部署行为：

1. `rsync` 直传覆盖到 `/home/biu/chat/current/`
2. 首次部署时自动从 `config/.env.prod` 创建 `/home/biu/chat/shared/.env`（已存在则不覆盖）
3. 自动创建或复用 `.venv`
4. 若服务器缺少 `python3.11`，会自动通过 `dnf` 安装
5. 自动安装依赖
6. 自动重启 `uvicorn main:app`
7. 自动执行 nginx 校验与 reload
