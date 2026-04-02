#!/bin/sh
set -e

echo "开始执行数据库迁移..."

# 等待数据库可连接（通过重复执行迁移命令判断）
MAX_RETRIES=20
RETRY_INTERVAL=3
COUNTER=1

until alembic upgrade head; do
  if [ "$COUNTER" -ge "$MAX_RETRIES" ]; then
    echo "数据库迁移失败，已达到最大重试次数。"
    exit 1
  fi
  echo "数据库尚未就绪，第 ${COUNTER} 次重试，${RETRY_INTERVAL}s 后继续..."
  COUNTER=$((COUNTER + 1))
  sleep "$RETRY_INTERVAL"
done

echo "数据库迁移完成，启动 FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

