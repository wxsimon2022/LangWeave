部署脚本说明：

1. 本地构建前端并整理后端发布包
2. 上传到 `root@124.223.72.223:/home/biu/chat`
3. 上传 nginx 配置到 `root@124.223.72.223:/usr/local/nginx/conf/vhost/`
4. 证书文件同步到远端发布目录下的 `ssl/`

默认域名配置来自 `script/chat.mybfs.cn_nginx/`。

脚本：

- `script/deploy/deploy_all.sh`：唯一部署入口，单脚本完成构建、`rsync` 直传覆盖、远端部署、启动和 nginx reload

服务端环境变量可参考：

- `script/deploy/.env.server.example`

远端部署行为：

1. `rsync` 直传覆盖到 `/home/biu/chat/current/`
2. 首次部署时自动创建 `/home/biu/chat/shared/.env`
3. 自动创建或复用 `.venv`
4. 若服务器缺少 `python3.11`，会自动通过 `dnf` 安装
5. 自动安装依赖
6. 自动重启 `uvicorn main:app`
7. 自动执行 nginx 校验与 reload

推荐直接执行：

```bash
./script/deploy/deploy_all.sh
```
