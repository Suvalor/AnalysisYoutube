# 启动&数据库迁移

```shell
# 1. 启动 mysql 和 backend 服务
docker compose up -d mysql backend

# 2. 在 backend 服务容器内执行 Alembic 迁移
docker compose exec backend alembic upgrade head

# 3. 打包及启动
docker compose up --build -d  