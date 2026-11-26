FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG REPO_URL=https://github.com/Kukuliak-Dmytro/learnwell-burnout.git
ARG V1_BRANCH=main
ARG V2_BRANCH=lab5

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /srv

RUN git clone --depth 1 --single-branch --branch "${V1_BRANCH}" "${REPO_URL}" /srv/v1 && \
    git clone --depth 1 --single-branch --branch "${V2_BRANCH}" "${REPO_URL}" /srv/v2 && \
    rm -rf /srv/v1/.git /srv/v2/.git

RUN pip install --no-cache-dir -r /srv/v2/requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8001 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8001/health >/dev/null && \
        curl -fsS http://127.0.0.1:8002/health >/dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
