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

Все команды `docker compose` выполняются в `~/arena`, `$REPO` — этот репозиторий.

1. **Данные и права.**
   ```bash
   uv run python case/assets/fetch_models.py           # если моделей ещё нет
   sudo bash case/deploy/stage_srv.sh
   ```
2. **Подготовка кампании** — отдельный запуск Claude Code с `prompts/prepare.md` арены, кейс `cases/ar04a-skill-select`, условия — [campaign.md](../campaign/campaign.md). Запускается в том же контейнере `researcher`, что и поиск (команда — шаг 7), а не на хосте: под учёткой оператора агенту доступны транскрипты сессии, генерировавшей данные (`~/.claude`), а в них есть запросы private. В контейнере арена лежит в `/opt/arena`, кейс — `/workspace/case`, каталог кампании — `/workspace/case/campaigns/c1`. Перед запуском `sudo bash case/deploy/stage_srv.sh` обновляет `/srv/arena/train` до текущего `main`; после — коммиты подготовки забираются в репозиторий оператора: `git -c safe.directory=/srv/arena/train pull /srv/arena/train main`. Результат:
   - замороженный пакет метрики → `sudo cp -a <campaign_dir>/metric/. /srv/arena/metric/`;
   - его digest → `ARENA_RELEASE_ID`;
   - запись `preparation.md`.
3. **Env.** Скопировать `public.env.example` и `private.env.example` в `/etc/arena/`, заполнить `TODO`.
4. **Образы.**
   ```bash
   docker compose --env-file /etc/arena/private.env --profile private build
   docker compose --env-file /etc/arena/private.env --profile train build researcher
   docker build -t arena-runner:local -f runner/Dockerfile .
   docker build -t ar04a-runner:local -f $REPO/case/deploy/runner.Dockerfile $REPO
   docker build -t ar04a-researcher:local -f $REPO/case/deploy/researcher.Dockerfile $REPO/case/deploy
   docker compose --env-file /etc/arena/private.env --profile private run --rm --no-deps \
     evaluator python -m evaluator.prepare verify --metric /private/metric
   ```
5. **Оценщики** — два проекта Compose, каждый со своим состоянием и портом.
   ```bash
   docker compose -p arena-public  --env-file /etc/arena/public.env  --profile private up -d
   docker compose -p arena-private --env-file /etc/arena/private.env --profile private up -d
   uv run python -m evaluator.client search-readiness --url http://127.0.0.1:8080 \
     --token-file /srv/arena/secrets/private-submit-token --require-campaign \
     --max-solutions 60 --finalists 5 --output-count 2 --release-id <ARENA_RELEASE_ID>
   ```
   Train-сервис (`python -m evaluator.train serve`, порт 8070) нужен для замеров `train_curve` и для build. В общем Compose его нет, он поднимается отдельным сервисом. Его конфигурацию готовит агент подготовки по разделу «Необязательный train-сервис и подготовка материалов» `deploy/README.md` арены, образец — `cases/sc35/campaigns/sc35-first-20261028/deploy/compose.yaml`. Нужно: харнес `ar04a-runner:local` с `supports_build: true`, `ARENA_BUILD_DIR`, `ARENA_PUBLISHED_ASSETS_DIR`, `ARENA_INPUT_ASSETS_DIGEST`; тот же харнес и каталог квитанций у public и private ([ADR-0004](../../docs/adr/0004-allowed-changes-and-models.md)).
6. **Проверка изоляции** — результат записать в `preparation.md`:
   ```bash
   docker compose -f compose.yaml -f $REPO/case/deploy/compose.override.yaml \
     --env-file /etc/arena/private.env --profile train run --rm researcher \
     bash /workspace/case/deploy/check_isolation.sh
   ```
7. **Поиск.** Запустить контейнер исследователя, внутри `claude` (первый раз — логин), передать `prompts/start.md`, каталог кампании и адреса из `ARENA_*_URL`.
   ```bash
   docker compose -f compose.yaml -f $REPO/case/deploy/compose.override.yaml \
     --env-file /etc/arena/private.env --profile train run --rm researcher
   ```

## Не проверено (проверить на шаге 4–6 и записать в preparation.md)
- Доступ из контейнера исследователя к оценщикам через `host.docker.internal` в Docker Desktop + WSL2.
- Время запуска контейнера runner (в ADR-0005 заложено ~1 с) — от него зависит лимит.
- Загрузка моделей из `/assets/models` при `network=none` в `ar04a-runner:local`.
- Установка Claude Code в образе и логин внутри контейнера.
