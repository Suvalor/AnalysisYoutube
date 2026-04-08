# 默认经 DaoCloud 同步的 Docker Hub 镜像，避免直连 registry-1.docker.io 超时
# 若本机已配置镜像加速或 VPN，可构建时覆盖：docker compose build --build-arg BASE_IMAGE=python:3.11-slim
ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim
FROM ${BASE_IMAGE}

# apt：官方 deb.debian.org 经 CDN 常出现 502/超时（与代码无关）。默认换清华 Debian 源，可用构建参数关闭或改镜像。
# 海外环境可：docker compose build --build-arg APT_USE_MIRROR=0
ARG APT_USE_MIRROR=1
ARG APT_DEBIAN_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian
ARG APT_SECURITY_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian-security

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 安装 OpenCV/FFmpeg 运行时依赖（修复 libGL.so.1 缺失）
RUN set -eux; \
    if [ "$APT_USE_MIRROR" = "1" ]; then \
      if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org/debian|${APT_DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|https://deb.debian.org/debian|${APT_DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|http://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|https://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
      elif [ -f /etc/apt/sources.list ]; then \
        sed -i "s|http://deb.debian.org/debian|${APT_DEBIAN_MIRROR}|g" /etc/apt/sources.list; \
        sed -i "s|https://deb.debian.org/debian|${APT_DEBIAN_MIRROR}|g" /etc/apt/sources.list; \
        sed -i "s|http://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" /etc/apt/sources.list; \
        sed -i "s|https://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" /etc/apt/sources.list; \
      fi; \
    fi; \
    UPD_OK=0; \
    for n in 1 2 3 4 5; do \
      if apt-get update; then UPD_OK=1; break; fi; \
      echo "apt-get update 失败，第 ${n} 次重试（15s 后）…"; \
      sleep 15; \
    done; \
    [ "$UPD_OK" = 1 ] || exit 1; \
    apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
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

