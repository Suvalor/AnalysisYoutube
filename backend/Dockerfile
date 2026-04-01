# 默认经 DaoCloud 同步的 Docker Hub 镜像，避免直连 registry-1.docker.io 超时
# 若本机已配置镜像加速或 VPN，可构建时覆盖：docker compose build --build-arg BASE_IMAGE=python:3.11-slim
ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 安装 OpenCV/FFmpeg 运行时依赖（修复 libGL.so.1 缺失）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安装依赖（使用清华 PyPI 镜像，降低 pip 下载超时概率）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝项目代码
COPY . /app
RUN chmod +x /app/entrypoint.sh

# 暴露 FastAPI 端口
EXPOSE 8000

# 容器启动时先迁移再启动服务
CMD ["/app/entrypoint.sh"]

