# Подготовка кампании c1 (AR-04а)

Дата записи: 2026-11-05. Подготовка выполнена агентом по `prompts/prepare.md` арены в контейнере исследователя (uid 10001, без Docker и sudo). Поиск не запускался и субагенту не передавался.

## Статус: поиск запускать нельзя

Подготовка не завершена: без Docker не проверены сервисы, `search-readiness` и изоляция в целевой конфигурации. Остальное готово. Что осталось сделать оператору — в разделе «Шаги оператора»; после них нужно записать сюда ответ `search-readiness` и результат проверки изоляции. Только после этого `prompts/start.md` можно запускать отдельным сеансом.

## Условия и версии

- Условия: [campaign.md](campaign.md), зафиксированы до поиска. Источник — [черновик](../../campaign/campaign.md) в репозитории; в нём заполнены digest метрики и каталога, конфигурация train-сервиса и ограничения.
- Арена: коммит `a28eee3`, `deploy/README.md` и образец `cases/sc35` прочитаны на GitLab по ссылкам закреплённого коммита. Каталог `/opt/arena` не является git-репозиторием, совпадение с коммитом подтверждено на предыдущем этапе подготовки.
- Харнес исследователей: Claude Code 2.1.280, модель `claude-sonnet-5-5`, effort high (для запуска `claude` внутри контейнера оператор проверяет `/status`). Решатель и метрика LLM не используют.
- Окружение подготовки: Python 3.12.16 из `/opt/arena/.venv`; PyYAML и pytest ставились временно через `uv` вне репозитория.

## Метрика

- Пакет: [metric](metric), версия `ar04a-skill-select-metric-v1`, `maximize`, `kind: command`, `uses_model: false`, таймаут 30 с.
- Заморожен командой `python -m evaluator.prepare freeze --metric case/metric --output case/campaigns/c1/metric`, затем `verify` — успешно (5 файлов + `metric.lock.json`, `semantic_tests_run: false`).
- Digest пакета: `bc8760a07ae545189d94ce789f73882cb00f3702c7b516603ae75044f2f244a2` (`python case/deploy/tree_digest.py case/campaigns/c1/metric`). Release ID: `ar04a-c1-metric-bc8760a07ae5`.
- Копия побайтно совпадает с исходным `case/metric` (кроме `metric.lock.json`).
- Тесты: 27 passed из `case/metric` (в том числе «жульнические» ответы: повторы, чужие id, длиннее 3, не JSON, регистр, повреждённый reference). В замороженной копии три теста, читающие данные кейса, не находят файлы — путь строится как `Path(__file__).parents[3]`, а там копия на уровень глубже; остальные 24 проходят. Это ограничение тестов, не метрики, пакет не менялся, чтобы не нарушать заморозку.
- Прогон через код арены ([checks/metric_pipeline.py](checks/metric_pipeline.py), `load_metric`, `evaluate_answer`, `aggregate_results`, ожидания записаны до запуска): 12 синтетических случаев, 3 повреждённых reference (ошибка оценщика, не нулевой score), эталонный ответ на `train_curve` (200 запросов) даёт 1.0, пустой ответ 0.0 — расхождений нет.
- Техническая проверка связки: baseline `case/ways/baseline` на `train_curve` локально с замороженной метрикой — score 0.488 (acc@1 0.460, nP@3 0.553, valid 1.000), как ожидалось. Это не замер кампании и не входит в кривую.

## Данные (sha256)

- Каталог `assets/catalog.jsonl` (189 навыков): `412b5a50aa99ab679551307d244976b36eccbf4527c573c16311ab45e81b714a`.
- `dataset/train.jsonl` (756): `9c2e9857f611e37398d7e4dcb3d7066753850798f9356fa3148acb702b6e767a`; `dataset/train_curve.jsonl` (200): `d4aecd33871ce77bd42d5d1131c3d3a311c9a1083d4d844215e2827f3d076bc7` — совпадают с черновиком.
- Public (380, `3c91b815…`) и private (376, `c2d40116…`) этой подготовке недоступны, как и положено; их digest из условий не перепроверялись.
- Digest входных материалов (`ARENA_INPUT_ASSETS_DIGEST`) не вычислен: моделей `assets/models` в контейнере нет. Его считает оператор: `python case/deploy/tree_digest.py /srv/arena/assets --exclude derived`.

## Журнал

- `/search/search.sqlite3` (на хосте `/srv/arena/search/search.sqlite3`) создан `python -m evaluator.search --journal /search/search.sqlite3 init --max-solutions 30`.
- `status`: `max_solutions: 30`, `proposed: 0`, `remaining_proposals: 30`, не остановлен, нет финализации. Создание журнала не занимает места в лимите.

## Конфигурация развёртывания

- [deploy/compose.campaign.yaml](../../deploy/compose.campaign.yaml): train-сервис (8070), public (8090), private (8080), контейнер исследователя (профиль `research`). Общий compose арены не использован: решатель без модели требует `network=none`, а его сеть runner носит имя `ARENA_RUNNER_NETWORK`.
- [deploy/campaign.env.example](../../deploy/campaign.env.example), [deploy/tree_digest.py](../../deploy/tree_digest.py); [stage_srv.sh](../../deploy/stage_srv.sh) дополнен каталогами train-сервиса, квитанций build, публикаций, staging и слотов; [check_isolation.sh](../../deploy/check_isolation.sh) проверяет и новые монтирования. Прежние `public.env.example`, `private.env.example` и `compose.override.yaml` удалены (в индексе git, не закоммичено): в env стояло `ARENA_RUNNER_NETWORK=arena-runners`, с `ARENA_USES_MODEL=false` такая конфигурация не стартует («model-free runner requires network none»).
- Проверка без Docker: YAML разобран PyYAML, env каждого сервиса (с подстановкой переменных) загружен через `Settings.from_env` и `TrainSettings.from_env`, создан `make_runner`. Результат: train, public и private принимаются; `runner_network=none`, таймаут 600 с, `supports_build` и `supports_asset_selection` включены, режим `campaign` только у private; отпечатки окружения build у трёх сервисов совпадают; пути монтирования runner совпадают на хосте и в контейнере. `docker compose config` и сам запуск не проверялись.
- Параметры из условий: runner 2 CPU, 2 ГБ, `network=none`, таймаут 600 с (решение оператора, см. ниже), K=5, N=2, лимит 30, `ARENA_TRAIN_TRACKING=false`, слоты исполнения 2.
- Допущения, которые условия не задают: `ARENA_DATASET_ID=ar04a-skill-select-v1`, `ARENA_CAMPAIGN_ID=ar04a-c1`, формат `ARENA_CONDITIONS_ID=ar04a-metric-v1-runner-<12 символов digest образа runner>`, ресурсы контейнера исследователя — по умолчанию арены (2 ГБ, 2 CPU, 128 процессов, `/tmp` 128 МБ без exec). Хватит ли их Claude Code, не проверено.

## Адреса

Адреса, которые получит поиск (токены в `/run/secrets/arena/{train,public,private}-submit-token`, значения здесь не приводятся):

- train: `http://host.docker.internal:8070`
- public: `http://host.docker.internal:8090`
- private: `http://host.docker.internal:8080`

Доступность из контейнера исследователя не проверена.

## Готовность сервисов

Не проверена: сервисы не запущены, Docker в среде подготовки нет.

- `GET /v1/search-readiness` private: не выполнялся.
- Изоляция: `check_isolation.sh` запущен в контейнере подготовки (до перехода на новый compose): 23 проверки OK (не root; нет `/srv/arena`, `/private`, `/state`, `/usage`, `/search-control`, ключа модели, `/etc/arena`, docker.sock, docker CLI, sudo, wsl.exe, `/mnt/c`; нет `public.jsonl` и `private.jsonl`; нет операторских `ARENA_*`; train читается, `/search` пишется, в `/run/secrets/arena` только три submit-токена) и 3 FAIL: `/assets`, `/derived`, `/staging` не смонтированы — контейнер запущен по старой конфигурации. После запуска по `compose.campaign.yaml` проверку нужно повторить и записать результат.
- Build и `evaluator.build submit` из контейнера исследователя, публикация и монтирование в `/assets/prepared`: не проверялись.
- Логин Claude Code в контейнере и доступ через `host.docker.internal` в Docker Desktop + WSL2: не проверялись.

## Оставшиеся ограничения

- **Таймаут 600 с общий для solve и build.** Оператор 2026-11-05 принял `ARENA_RUNNER_TIMEOUT=600` вместо 60 с из ADR-0004; условия и `compose.campaign.yaml` обновлены, ADR и `docs/` — нет. Арена применяет один таймаут к одному примеру и к build, поэтому зависший пример занимает слот до 10 минут. Достаточность 600 с для build эмбеддингов и индексов не проверена; замер на пробном кандидате (см. ниже) покажет запас. Отпечаток окружения build включает таймаут, поэтому значение нельзя менять после первого build.
- Изменения подготовки лежат в `/srv/arena/train` незакоммиченными: подготовка не коммитила. Оператору нужно закоммитить их там и забрать в свой репозиторий (`git -c safe.directory=/srv/arena/train pull /srv/arena/train main`).
- Пробный build и `train submit` требуют кандидата, зарегистрированного в журнале; делать это в каноническом журнале нельзя (предложение занимает место из 30). Используйте отдельный журнал: `python -m evaluator.search --journal /tmp/smoke.sqlite3 init --max-solutions 1`.

## Шаги оператора

Подробные команды — [deploy/README.md](../../deploy/README.md), шаги 1–7. Кратко:

1. Закоммитить файлы подготовки в `/srv/arena/train` и забрать в репозиторий; `sudo bash case/deploy/stage_srv.sh`.
2. Собрать образы: `arena-evaluator:local` (target `evaluator`), `arena-runner:local`, `ar04a-runner:local`, `ar04a-researcher:local`.
3. Заполнить `/etc/arena/campaign.env` из `campaign.env.example`: `ARENA_DOCKER_GID`, `AR04A_CONDITIONS_ID`, `AR04A_INPUT_ASSETS_DIGEST`.
4. Установить метрику в `/srv/arena/metric`, сверить digest с `bc8760a07ae5…` и выполнить `evaluator.prepare verify`.
5. `docker compose -p arena-ar04a -f case/deploy/compose.campaign.yaml --env-file /etc/arena/campaign.env up -d`; убедиться, что train, public и private `healthy`.
6. Из контейнера исследователя (профиль `research`): `search-readiness --require-campaign --max-solutions 30 --finalists 5 --output-count 2 --release-id ar04a-c1-metric-bc8760a07ae5` и `check_isolation.sh`; проверить пробный build с отдельным журналом и его длительность относительно 600 с.
7. Передать результаты сюда и повторить подготовку для проверки; затем отдельный запуск поиска по `prompts/start.md`.
