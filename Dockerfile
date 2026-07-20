FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 ffmpeg curl && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash weaver
USER weaver
WORKDIR /home/weaver/app
COPY --from=builder /root/.local /home/weaver/.local
ENV PATH="/home/weaver/.local/bin:$PATH"
COPY --chown=weaver:weaver src/ ./src/
COPY --chown=weaver:weaver skills/ ./skills/
COPY --chown=weaver:weaver data/schema.sql ./data/schema.sql
RUN mkdir -p /home/weaver/app/data /home/weaver/app/exports
EXPOSE 8765
ENV DEPLOY_MODE=docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8765/api/health || exit 1
CMD ["python", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8765"]
