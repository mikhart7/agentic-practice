# Развёртывание кейса AR-04а (для оператора)

Общий порядок, роли и права — по [deploy/README.md](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3/deploy/README.md) и [common/isolation.md](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3/common/isolation.md) арены, коммит `a28eee3`. Здесь только значения нашего кейса: арена отводит под них `cases/<case>/deploy/`. Почему так и чем отличается от арены — [ADR-0006](../../docs/adr/0006-isolation.md).

```
 оператор (WSL, mikhart)           доверенный контур                         исследователь
 ───────────────────────           ─────────────────                         ─────────────
 stage_srv.sh → /srv/arena   ──►  evaluator public  :8090 ┐                 контейнер researcher
                                  evaluator private :8080 ├─ runner ──►     (compose profile research)
                                  train-сервис      :8070 ┘  ar04a-runner   Claude Code + start.md
                                  данные /srv/arena/{public,private}        видит: /workspace (train),
                                                                            /search (журнал), токены
                                  ◄─────── кандидат по HTTP + токен ─────── 
                                  ───────► public: score, private: статус ─►
```

## Файлы

| файл | что это |
|---|---|
| [stage_srv.sh](stage_srv.sh) | раскладка `/srv/arena` по таблице «Данные и права» арены (через sudo), включая каталоги train-сервиса, квитанций build, публикаций и staging |
| [compose.campaign.yaml](compose.campaign.yaml) | доверенный контур одним проектом: train-сервис (8070), public (8090), private (8080), `network=none` для runner, без gateway и MLflow; профиль `research` — контейнер исследователя |
| [campaign.env.example](campaign.env.example) | операторский env: корень, образ оценщика, release ID, `ARENA_CONDITIONS_ID`, digest входных материалов |
| [tree_digest.py](tree_digest.py) | sha256 каталога: digest пакета метрики (release ID) и входных материалов (`ARENA_INPUT_ASSETS_DIGEST`) |
| [runner.Dockerfile](runner.Dockerfile) | runner арены + библиотеки кейса из `uv.lock` |
| [researcher.Dockerfile](researcher.Dockerfile) | контейнер исследователя арены + Claude Code (харнес добавляет оператор) |
| [check_isolation.sh](check_isolation.sh) | проверка границы изнутри контейнера исследователя |

Почему не общий `compose.yaml` арены: его сеть runner называется `ARENA_RUNNER_NETWORK`, а решатель без модели (`ARENA_USES_MODEL=false`) арена допускает только с `network=none`; сеть с именем `none` Compose создать не может. Gateway в нашей кампании не нужен: решатель и метрика обходятся без LLM.

## Шаги

`$REPO` — этот репозиторий на хосте, `ARENA` — репозиторий арены на коммите `a28eee3` (`~/arena`). Порядок — как в `deploy/README.md` арены: подготовка замораживает метрику, оператор устанавливает пакет и запускает сервисы, затем подготовка подтверждает готовность, и только после этого идёт отдельный запуск поиска.

1. **Данные и права.** Повторный запуск `stage_srv.sh` обновляет `/srv/arena/train` до текущего `main`.
   ```bash
   uv run python case/assets/fetch_models.py           # если моделей ещё нет
   sudo bash case/deploy/stage_srv.sh
   ```
2. **Образы.**
   ```bash
   cd ~/arena
   docker build --target evaluator --build-arg ARENA_TRACKING=false -t arena-evaluator:local .
   docker build -t arena-runner:local -f runner/Dockerfile .
   docker build -t ar04a-runner:local -f $REPO/case/deploy/runner.Dockerfile $REPO
   docker build -t ar04a-researcher:local -f $REPO/case/deploy/researcher.Dockerfile $REPO/case/deploy
   ```
3. **Env.** Копия примера в `/etc/arena/campaign.env`, три значения вычисляются на хосте:
   ```bash
   sudo install -d /etc/arena && sudo cp $REPO/case/deploy/campaign.env.example /etc/arena/campaign.env
   stat -c '%g' /var/run/docker.sock                                                      # -> ARENA_DOCKER_GID
   docker image inspect --format '{{.Id}}' ar04a-runner:local                              # 12 символов после sha256: -> AR04A_CONDITIONS_ID=ar04a-metric-v1-runner-<12>
   python3 $REPO/case/deploy/tree_digest.py /srv/arena/assets --exclude derived          # -> AR04A_INPUT_ASSETS_DIGEST
   ```
4. **Подготовка кампании** — отдельный запуск Claude Code с `prompts/prepare.md` арены в контейнере `researcher` (команда та же, что в шаге 8), условия — [campaign.md](../campaign/campaign.md). Не на хосте: под учёткой оператора агенту доступны транскрипты сессии, генерировавшей данные (`~/.claude`), а в них есть запросы private; агенту подготовки арена разрешает только открытые и синтетические данные (`common/isolation.md`). В контейнере арена лежит в `/opt/arena`, кейс — `/workspace/case` (на хосте это `~/arena/cases/ar04a-skill-select`), каталог кампании — `/workspace/case/campaigns/c1`. Модель — `claude-sonnet-5-5`, effort high (README, «Модели»). В образе исследователя из арены есть только `common/`, `prompts/`, `cases/template`, `README.md` и `AGENTS.md`; [`deploy/README.md`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/deploy/README.md) и образец [`cases/sc35/.../deploy/compose.yaml`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/cases/sc35/campaigns/sc35-first-20261028/deploy/compose.yaml) агент читает на GitLab на закреплённом коммите. Результат:
   - замороженный пакет метрики `<campaign_dir>/metric`, его digest → `AR04A_RELEASE_ID` (`ar04a-c1-metric-<12 символов>`);
   - `compose.campaign.yaml`, `campaign.env.example`, `campaigns/c1/campaign.md`, `campaigns/c1/preparation.md`, инициализированный журнал `/search/search.sqlite3`.

   Агент коммитит результаты подготовки в `/workspace`. Оператор забирает коммиты в свой репозиторий (у копии другой владелец, UID 10001, поэтому разрешение передаётся `upload-pack`):
   ```bash
   cd $REPO
   git fetch --upload-pack="git -c safe.directory='*' upload-pack" /srv/arena/train main && git merge --ff-only FETCH_HEAD
   ```
5. **Установка метрики** оператором: проверить код пакета, установить и сверить.
   ```bash
   sudo cp -a $REPO/case/campaigns/c1/metric/. /srv/arena/metric/
   python3 $REPO/case/deploy/tree_digest.py /srv/arena/metric --exclude __pycache__   # должен совпасть с digest из campaign.md
   docker run --rm --network none --user 10001:10001 -v /srv/arena/metric:/private/metric:ro \
     arena-evaluator:local python -m evaluator.prepare verify --metric /private/metric
   ```
6. **Оценщики и train-сервис** — один проект Compose; train запускается первым (создаёт журнал квитанций `BuildStore`), public и private ждут его готовности.
   ```bash
   docker compose -p arena-ar04a -f $REPO/case/deploy/compose.campaign.yaml --env-file /etc/arena/campaign.env up -d
   docker compose -p arena-ar04a -f $REPO/case/deploy/compose.campaign.yaml --env-file /etc/arena/campaign.env ps
   ```
   Все три должны быть `healthy`. Порты только на `127.0.0.1`.
7. **Готовность и изоляция** — подготовка записывает в `preparation.md` ответ `search-readiness` (из контейнера исследователя, тем же адресом и токеном, что получит поиск) и результат проверки изоляции:
   ```bash
   docker compose -p arena-ar04a -f $REPO/case/deploy/compose.campaign.yaml --env-file /etc/arena/campaign.env \
     --profile research run --rm researcher bash -c '
       cd /opt/arena && python -m evaluator.client search-readiness --url "$ARENA_PRIVATE_URL" \
         --token-file /run/secrets/arena/private-submit-token --require-campaign \
         --max-solutions 30 --finalists 5 --output-count 2 --release-id ar04a-c1-metric-bc8760a07ae5 &&
       bash /workspace/case/deploy/check_isolation.sh'
   ```
8. **Поиск** — отдельный от подготовки запуск. Запустить контейнер исследователя, внутри `claude` (первый раз — логин; модель `claude-sonnet-5-5`, effort high, проверить в `/status`), передать `prompts/start.md`, каталог кампании и адреса из `ARENA_*_URL`.
   ```bash
   docker compose -p arena-ar04a -f $REPO/case/deploy/compose.campaign.yaml --env-file /etc/arena/campaign.env \
     --profile research run --rm researcher
   ```

## Не проверено (проверить на шагах 4–7 и записать в preparation.md)
- Сам `docker compose config` и запуск: Docker в среде подготовки нет, YAML разобран PyYAML, а переменные окружения сервисов проверены через `Settings`, `TrainSettings` и `make_runner` арены.
- Доступ из контейнера исследователя к оценщикам через `host.docker.internal` в Docker Desktop + WSL2.
- Train-сервис с build: `evaluator.build submit` из контейнера исследователя, публикация результата и его монтирование в `/assets/prepared` и `/assets/derived/<digest>`. Проверять с отдельным пробным журналом (`evaluator.search --journal /tmp/smoke.sqlite3 init --max-solutions 1`), а не каноническим: предложение в `/search/search.sqlite3` занимает место из 30.
- Укладывается ли build эмбеддингов в 600 с (общий `ARENA_RUNNER_TIMEOUT`).
- Логин Claude Code внутри контейнера.

Уже проверено ([results/models/bench.md](../../results/models/bench.md), [results/smoke/isolation-2026-11-03.md](../../results/smoke/isolation-2026-11-03.md)): запуск контейнера runner — 0.4 с; модели грузятся из `/assets/models` при `network=none`; образ исследователя с Claude Code собирается, изоляция изнутри — 21/21.
