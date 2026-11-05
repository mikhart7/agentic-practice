# Развёртывание кейса AR-04а (для оператора)

Общий порядок, роли и права — по [deploy/README.md](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3/deploy/README.md) и [common/isolation.md](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3/common/isolation.md) арены, коммит `a28eee3`. Здесь только значения нашего кейса: арена отводит под них `cases/<case>/deploy/`. Почему так и чем отличается от арены — [ADR-0006](../../docs/adr/0006-isolation.md).

```
 оператор (WSL, mikhart)           доверенный контур                         исследователь
 ───────────────────────           ─────────────────                         ─────────────
 stage_srv.sh → /srv/arena   ──►  evaluator public  :8090 ┐                 контейнер researcher
                                  evaluator private :8080 ├─ runner ──►     (compose profile train)
                                  train-сервис      :8070 ┘  ar04a-runner   Claude Code + start.md
                                  данные /srv/arena/{public,private}        видит: /workspace (train),
                                                                            /search (журнал), токены
                                  ◄─────── кандидат по HTTP + токен ─────── 
                                  ───────► public: score, private: статус ─►
```

## Файлы

| файл | что это |
|---|---|
| [stage_srv.sh](stage_srv.sh) | раскладка `/srv/arena` по таблице «Данные и права» арены (через sudo) |
| [public.env.example](public.env.example), [private.env.example](private.env.example) | операторские env двух оценщиков (ключи как в `deploy/operator.env.example`) |
| [runner.Dockerfile](runner.Dockerfile) | runner арены + библиотеки кейса из `uv.lock` |
| [researcher.Dockerfile](researcher.Dockerfile) | контейнер исследователя арены + Claude Code (харнес добавляет оператор) |
| [compose.override.yaml](compose.override.yaml) | образ исследователя, постоянный HOME (логин и транскрипты), адреса оценщиков, submit-токены |
| [check_isolation.sh](check_isolation.sh) | проверка границы изнутри контейнера исследователя |

## Шаги

Все команды `docker compose` выполняются в `~/arena`, `$REPO` — этот репозиторий. Порядок — как в `deploy/README.md` арены: подготовка замораживает метрику, оператор устанавливает пакет и запускает сервисы, затем подготовка подтверждает готовность, и только после этого идёт отдельный запуск поиска.

1. **Данные и права.** Повторный запуск `stage_srv.sh` обновляет `/srv/arena/train` до текущего `main`.
   ```bash
   uv run python case/assets/fetch_models.py           # если моделей ещё нет
   sudo bash case/deploy/stage_srv.sh
   ```
2. **Env.** Скопировать `public.env.example` и `private.env.example` в `/etc/arena/`, заполнить `TODO`.
3. **Образы.**
   ```bash
   docker compose --env-file /etc/arena/private.env --profile private build
   docker compose --env-file /etc/arena/private.env --profile train build researcher
   docker build -t arena-runner:local -f runner/Dockerfile .
   docker build -t ar04a-runner:local -f $REPO/case/deploy/runner.Dockerfile $REPO
   docker build -t ar04a-researcher:local -f $REPO/case/deploy/researcher.Dockerfile $REPO/case/deploy
   ```
4. **Подготовка кампании** — отдельный запуск Claude Code с `prompts/prepare.md` арены в контейнере `researcher` (команда та же, что в шаге 8), условия — [campaign.md](../campaign/campaign.md). Не на хосте: под учёткой оператора агенту доступны транскрипты сессии, генерировавшей данные (`~/.claude`), а в них есть запросы private; агенту подготовки арена разрешает только открытые и синтетические данные (`common/isolation.md`). В контейнере арена лежит в `/opt/arena`, кейс — `/workspace/case` (на хосте это `~/arena/cases/ar04a-skill-select`), каталог кампании — `/workspace/case/campaigns/c1`. Модель — `claude-sonnet-5-5`, effort high (README, «Модели»). В образе исследователя из арены есть только `common/`, `prompts/`, `cases/template`, `README.md` и `AGENTS.md`; [`deploy/README.md`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/deploy/README.md) и образец [`cases/sc35/.../deploy/compose.yaml`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/cases/sc35/campaigns/sc35-first-20261028/deploy/compose.yaml) агент читает на GitLab на закреплённом коммите. Результат:
   - замороженный пакет метрики `<campaign_dir>/metric`, его digest → `ARENA_RELEASE_ID`;
   - конфигурация train-сервиса с build (шаг 6);
   - `campaign.md` и черновик `preparation.md`.

   Коммиты подготовки забираются в репозиторий оператора: `git -c safe.directory=/srv/arena/train pull /srv/arena/train main`.
5. **Установка метрики** оператором: проверить код пакета, установить и сверить.
   ```bash
   sudo cp -a $REPO/case/campaigns/c1/metric/. /srv/arena/metric/
   docker compose --env-file /etc/arena/private.env --profile private run --rm --no-deps \
     evaluator python -m evaluator.prepare verify --metric /private/metric
   ```
6. **Оценщики и train-сервис** — public и private как два проекта Compose, каждый со своим состоянием и портом; train-сервис — по конфигурации из шага 4.
   ```bash
   docker compose -p arena-public  --env-file /etc/arena/public.env  --profile private up -d
   docker compose -p arena-private --env-file /etc/arena/private.env --profile private up -d
   ```
   Train-сервис (`python -m evaluator.train serve`, порт 8070) нужен для замеров `train_curve` и для build. В общем Compose его нет, он поднимается отдельным сервисом по разделу «Необязательный train-сервис и подготовка материалов» `deploy/README.md` арены, образец — [`cases/sc35/.../deploy/compose.yaml`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/cases/sc35/campaigns/sc35-first-20261028/deploy/compose.yaml). Нужно: харнес `ar04a-runner:local` с `supports_build: true` и `supports_asset_selection: true` (переиспользование результата build родителя), `ARENA_BUILD_DIR`, `ARENA_PUBLISHED_ASSETS_DIR`, `ARENA_INPUT_ASSETS_DIGEST`; тот же харнес и каталог квитанций у public и private ([ADR-0004](../../docs/adr/0004-allowed-changes-and-models.md)).
7. **Готовность и изоляция** — подготовка записывает в `preparation.md` ответ `search-readiness` (из контейнера исследователя, тем же адресом и токеном, что получит поиск) и результат проверки изоляции:
   ```bash
   python -m evaluator.client search-readiness --url "$ARENA_PRIVATE_URL" \
     --token-file /run/secrets/arena/private-submit-token --require-campaign \
     --max-solutions 30 --finalists 5 --output-count 2 --release-id <ARENA_RELEASE_ID>
   docker compose -f compose.yaml -f $REPO/case/deploy/compose.override.yaml \
     --env-file /etc/arena/private.env --profile train run --rm researcher \
     bash /workspace/case/deploy/check_isolation.sh
   ```
8. **Поиск** — отдельный от подготовки запуск. Запустить контейнер исследователя, внутри `claude` (первый раз — логин; модель `claude-sonnet-5-5`, effort high, проверить в `/status`), передать `prompts/start.md`, каталог кампании и адреса из `ARENA_*_URL`.
   ```bash
   docker compose -f compose.yaml -f $REPO/case/deploy/compose.override.yaml \
     --env-file /etc/arena/private.env --profile train run --rm researcher
   ```

## Не проверено (проверить на шагах 4–7 и записать в preparation.md)
- Доступ из контейнера исследователя к оценщикам через `host.docker.internal` в Docker Desktop + WSL2.
- Train-сервис с build: `evaluator.build submit` из контейнера исследователя, публикация результата и его монтирование в `/assets/prepared` и `/assets/derived/<digest>`.
- Логин Claude Code внутри контейнера.

Уже проверено ([results/models/bench.md](../../results/models/bench.md), [results/smoke/isolation-2026-11-03.md](../../results/smoke/isolation-2026-11-03.md)): запуск контейнера runner — 0.4 с; модели грузятся из `/assets/models` при `network=none`; образ исследователя с Claude Code собирается, изоляция изнутри — 21/21.
