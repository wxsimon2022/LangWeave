# =============================================================================
# LangWeave multi-stage Docker build
#
# backend   — FastAPI (python:3.11-slim)
# production— nginx serving frontend + reverse proxy to backend
#
# node:20-alpine is NOT used because it can't be pulled through
# the NAS's docker.fnnas.com mirror. The frontend SPA is pre-built
# locally by the deploy script and copied directly into the nginx stage.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: backend — FastAPI (uvicorn main:app)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS backend

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY langweave/ langweave/
COPY app/ app/
COPY main.py pyproject.toml ./

EXPOSE 3002

ENV LANGWEAVE_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/langweave
ENV LANGWEAVE_REDIS_URL=redis://127.0.0.1:6379/0

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3002"]

# ---------------------------------------------------------------------------
# Stage 2: production — nginx + built frontend static files
# ---------------------------------------------------------------------------
FROM nginx:alpine AS production

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories 2>/dev/null || true

# Pre-built frontend SPA (built locally by deploy script)
COPY frontends/fe/dist/ /usr/share/nginx/html/

COPY script/deploy/nginx.docker.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
