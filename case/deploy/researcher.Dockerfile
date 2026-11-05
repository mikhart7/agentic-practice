# Исследовательский контейнер арены + харнес (Claude Code).
# Арена: «Необходимый CLI-харнес оператор добавляет в свой image» (deploy/README.md).
#   docker compose --env-file /etc/arena/operator.env --profile train build researcher   # в ~/arena
#   docker build -t ar04a-researcher:local -f case/deploy/researcher.Dockerfile case/deploy
FROM arena-researcher:local
USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl bash && rm -rf /var/lib/apt/lists/*
# версия закреплена: та же, что у оператора при подготовке (claude --version)
ARG CLAUDE_CODE_VERSION=2.1.318
RUN curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_CODE_VERSION}" \
    && install -m 0755 /root/.local/bin/claude /usr/local/bin/claude
USER 10001:10001
WORKDIR /workspace
