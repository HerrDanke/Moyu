# syntax=docker/dockerfile:1

# ---------- 阶段 1：构建前端 ----------
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：运行时 ----------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    NOVEL_DIR=/novels \
    STATIC_DIR=/app/static \
    PORT=8000

WORKDIR /app

# 非 root 用户（评审建议）
RUN useradd --create-home --uid 10001 moyu

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./static

RUN mkdir -p /data /novels && chown -R moyu:moyu /app /data /novels

USER moyu
WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]