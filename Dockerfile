# =============================================================================
# LangWeave — single-stage backend build (multi-stage removed because
# node:20-alpine and nginx:alpine cannot be pulled through the
# NAS's broken docker.fnnas.com mirror).
#
# The frontend SPA is pre-built locally (npm run build) and copied
# into the container as FastAPI static files.
# =============================================================================
FROM python:3.11-slim

# Use China mirrors for apt and pip
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

# Install system dependencies
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
RUN mkdir -p /app/static


EXPOSE 8000

ENV LANGWEAVE_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/langweave
ENV LANGWEAVE_REDIS_URL=redis://127.0.0.1:6379/0

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
