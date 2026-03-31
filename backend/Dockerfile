FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 安装依赖
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 拷贝项目代码
COPY . /app
RUN chmod +x /app/entrypoint.sh

# 暴露 FastAPI 端口
EXPOSE 8000

# 容器启动时先迁移再启动服务
CMD ["/app/entrypoint.sh"]

