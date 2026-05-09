FROM python:3.12-slim

# git 是必需依赖（gitwork.py 通过 subprocess 调用），ca-certificates 与 tzdata 解决证书与时区
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 创建非 root 用户，避免 ledger / ssh 等问题
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin ling \
    && mkdir -p /etc/ling /data/workdir \
    && chown -R ling:ling /data /etc/ling

WORKDIR /app

COPY server/python/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY server/python/ling_server /app/ling_server
COPY server/python/config.example.yaml /app/config.example.yaml

# git 全局配置（容器内做提交时用）
RUN git config --system safe.directory /data/workdir \
    && git config --system pull.rebase true \
    && git config --system user.name "ling-assistant" \
    && git config --system user.email "ling-assistant@users.noreply.github.com"

USER ling

# 默认从 /etc/ling/config.yaml 读配置；可在 docker run -v 时挂载覆盖
ENV LING_CONFIG=/etc/ling/config.yaml

EXPOSE 8765

# health check：每分钟一次
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=3).status==200 else 1)" || exit 1

ENTRYPOINT ["python", "-m", "ling_server.cli"]
CMD ["-c", "/etc/ling/config.yaml", "serve"]
