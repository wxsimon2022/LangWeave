# =============================================================================
# Stage 1: Build frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

# Use China npm mirror for faster downloads
RUN npm config set registry https://registry.npmmirror.com

WORKDIR /app/frontends/fe

COPY frontends/fe/package.json frontends/fe/package-lock.json* ./
RUN npm ci

COPY frontends/fe/ .
RUN npm run build

# =============================================================================
# Stage 2: Python backend
# =============================================================================
FROM python:3.11-slim AS backend

# Use China apt mirror for faster apt-get
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# Use China pip mirror
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

# Install system dependencies (mysqlclient, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source code
COPY langweave/ langweave/
COPY app/ app/
COPY main.py pyproject.toml ./

EXPOSE 8000

# Database and Redis URLs must be provided at runtime via .env or docker-compose.
# These defaults are for local development only.
ENV LANGWEAVE_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/langweave
ENV LANGWEAVE_REDIS_URL=redis://127.0.0.1:6379/0

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 3: Nginx with built frontend
# =============================================================================
FROM nginx:alpine AS production

# Use China apt mirror for faster apk add (if needed)
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories 2>/dev/null || true

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontends/fe/dist/ /usr/share/nginx/html/

# Copy custom nginx config
COPY script/deploy/nginx.docker.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
