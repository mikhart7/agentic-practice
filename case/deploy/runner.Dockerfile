# Runner кейса AR-04а: комплектный runner арены + закреплённые библиотеки кейса (ADR-0004).
# Сборка из корня репозитория проекта, после сборки arena-runner:local в ~/arena:
#   docker build -t arena-runner:local -f runner/Dockerfile ~/arena
#   docker build -t ar04a-runner:local -f case/deploy/runner.Dockerfile .
FROM ghcr.io/astral-sh/uv:0.8.13 AS uv

FROM arena-runner:local
USER root
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock /opt/ar04a/
# те же версии, что в uv.lock проекта; torch — CPU-сборка
RUN cd /opt/ar04a \
    && uv export --frozen --no-dev --no-emit-project -o requirements.txt \
    && uv pip install --system --no-cache --require-hashes \
       --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match \
       -r requirements.txt \
    && rm -rf /root/.cache
# модели читаются из /assets/models без сети
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
USER 10001:10001
