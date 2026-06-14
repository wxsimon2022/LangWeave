#!/usr/bin/env bash
set -euo pipefail

# ============================================
#  admin.meet.mybfs.cn — HTTPS 一键配置脚本
#  基于 acme.sh (Let's Encrypt) + nginx
# ============================================
# 用法:
#   bash script/deploy/setup_admin_https.sh
#
# 前置条件:
#   - 域名 admin.meet.mybfs.cn DNS 已指向本机
#   - nginx 已安装，管理后台前端文件就绪
# ============================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SSL_DIR="/home/biu/chat/current/ssl"
NGINX_CONF="$ROOT_DIR/script/deploy/nginx.admin.meet.mybfs.cn.conf"
NGINX_SBIN="/usr/local/nginx/sbin/nginx"
DOMAIN="admin.meet.mybfs.cn"
EMAIL="admin@mybfs.cn"

# 前端静态文件路径（acme.sh webroot 模式验证用）
WEBROOT="/home/biu/chat/current/admin"

echo "============================================"
echo "  $DOMAIN HTTPS 一键配置"
echo "============================================"
echo ""

# ---- 1. 安装 acme.sh ----
echo "[1/6] 检查/安装 acme.sh..."
if [ ! -f "$HOME/.acme.sh/acme.sh" ]; then
  curl https://get.acme.sh | sh -s email="$EMAIL"
  echo "  ✅ acme.sh 已安装"
else
  echo "  ✅ acme.sh 已存在，跳过安装"
fi

# 加载 acme.sh 到 PATH
source "$HOME/.acme.sh/acme.sh.env" 2>/dev/null || true
export PATH="$HOME/.acme.sh:$PATH"

# ---- 2. 设置默认 CA 为 Let's Encrypt ----
# ZeroSSL 国内 CDN 不稳定，改用 Let's Encrypt
echo ""
echo "[2/7] 设置默认 CA 为 Let's Encrypt..."
~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
echo "  ✅ 默认 CA: Let's Encrypt"

# ---- 3. 确保 SSL 目录 ----
echo ""
echo "[3/7] 创建 SSL 证书目录..."
mkdir -p "$SSL_DIR"
echo "  ✅ $SSL_DIR"

# ---- 4. 申请证书 ----
echo ""
echo "[4/7] 申请 Let's Encrypt 证书..."
echo "  域名: $DOMAIN"
echo "  验证方式: webroot ($WEBROOT)"
echo ""

# 检查是否已有证书
if [ -f "$SSL_DIR/${DOMAIN}_bundle.pem" ] && [ -f "$SSL_DIR/${DOMAIN}.key" ]; then
  echo "  ⚠️  证书文件已存在，尝试续期..."
  ~/.acme.sh/acme.sh --renew -d "$DOMAIN" --force --server letsencrypt || true
else
  ~/.acme.sh/acme.sh --issue -d "$DOMAIN" -w "$WEBROOT" --server letsencrypt
fi

# ---- 5. 安装证书 ----
echo ""
echo "[5/7] 安装证书到 nginx 目录..."
~/.acme.sh/acme.sh --install-cert -d "$DOMAIN" \
  --key-file "$SSL_DIR/${DOMAIN}.key" \
  --fullchain-file "$SSL_DIR/${DOMAIN}_bundle.pem" \
  --reloadcmd "$NGINX_SBIN -s reload"
echo "  ✅ 证书已安装"

# ---- 6. 备份原有配置 / 写入新配置 ----
echo ""
echo "[6/7] 写入 nginx 配置..."
if [ -f "$NGINX_CONF" ]; then
  cp -a "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%Y%m%d%H%M%S)"
  echo "  ✅ 原配置已备份"
fi

cat > "$NGINX_CONF" << 'NGINX'
server {
    listen 80;
    server_name admin.meet.mybfs.cn;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name admin.meet.mybfs.cn;

    ssl_certificate     /home/biu/chat/current/ssl/admin.meet.mybfs.cn_bundle.pem;
    ssl_certificate_key /home/biu/chat/current/ssl/admin.meet.mybfs.cn.key;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    client_max_body_size 20m;

    location / {
        root /home/biu/chat/current/admin;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 10s;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 10s;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 10s;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

echo "  ✅ nginx 配置已写入: $NGINX_CONF"

# ---- 7. 最终提示 ----
echo ""
echo "[7/7] 完成"
echo ""
echo "============================================"
echo "  ✅ 配置完成"
echo "============================================"
echo ""
echo "  证书路径:"
echo "    PEM:  $SSL_DIR/${DOMAIN}_bundle.pem"
echo "    KEY:  $SSL_DIR/${DOMAIN}.key"
echo ""
echo "  ⚠️  如果线上 nginx 加载的配置路径与仓库不同，还需手动复制："
echo "     cp $NGINX_CONF <nginx配置目录>/"
echo "     $NGINX_SBIN -t && $NGINX_SBIN -s reload"
echo ""
echo "  验证方法:"
echo "    curl -sI -o /dev/null -w 'HTTPS: %{http_code}\\n' https://$DOMAIN/"
echo "    curl -sI -o /dev/null -w 'HTTP -> %{http_code}\\n' http://$DOMAIN/"
echo "    # 预期: HTTPS 200, HTTP 301"
echo ""
echo "  证书自动续期: acme.sh 已安装 cron，无需额外配置"
echo "  检查续期任务: crontab -l | grep acme"
echo ""
