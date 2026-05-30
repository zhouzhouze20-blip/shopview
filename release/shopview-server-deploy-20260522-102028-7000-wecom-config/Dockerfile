# 百货柜位管理系统 - 极简部署 Dockerfile

# 阶段1: 构建前端
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /app

RUN npm config set registry https://registry.npmjs.org/ && \
    npm config set strict-ssl false && \
    npm config set fetch-retries 5

COPY client/package*.json ./

RUN npm ci --include=optional --legacy-peer-deps

COPY client/ ./

RUN npm run build:no-check

# 阶段2: Python 运行时
FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_EXTRA_INDEX_URL=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=20 \
    PIP_PROGRESS_BAR=off \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL} \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app:/app/python_app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY python_requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r python_requirements.txt

COPY python_app/ ./python_app/
COPY --from=frontend-builder /app/dist ./static
COPY static/WW_verify*.txt ./static/
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN mkdir -p /app/uploads /app/logs
RUN chmod +x /app/docker-entrypoint.sh /app/python_app/alembic_upgrade.sh

RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 7000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:7000/api/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn python_app.main:app --host 0.0.0.0 --port ${PORT:-7000} --workers ${UVICORN_WORKERS:-4}"]
