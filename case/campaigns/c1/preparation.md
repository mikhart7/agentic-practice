# Подготовка кампании c1 (AR-04а)

Дата записи: 2026-11-05. Подготовка выполнена агентом по `prompts/prepare.md` арены в контейнере исследователя (uid 10001, без Docker и sudo). Поиск не запускался и субагенту не передавался.

## Статус: подготовка завершена, поиск можно запускать отдельным сеансом

Сервисы healthy; `search-readiness` private, изоляция, пробный build и пробный `train submit` пройдены (2026-11-05, см. «Готовность сервисов»). Оставшиеся ограничения — в одноимённом разделе (в том числе стоимость одного примера и не проверенные вещи). Поиск запускается пользователем отдельно по `prompts/start.md`; подготовка его не запускала и субагенту не передавала.

## Условия и версии

- Условия: [campaign.md](campaign.md), зафиксированы до поиска. Источник — [черновик](../../campaign/campaign.md) в репозитории; в нём заполнены digest метрики и каталога, конфигурация train-сервиса и ограничения.
- Арена: коммит `a28eee3`, `deploy/README.md` и образец `cases/sc35` прочитаны на GitLab по ссылкам закреплённого коммита. Каталог `/opt/arena` не является git-репозиторием, совпадение с коммитом подтверждено на предыдущем этапе подготовки.
- Харнес исследователей: Claude Code 2.1.318 (`claude --version` в контейнере исследователя, 2026-11-05; 2.1.280 не знал `claude-sonnet-5-5`), модель `claude-sonnet-5-5`, effort high (для запуска `claude` внутри контейнера оператор проверяет `/status`). Решатель и метрика LLM не используют.
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

Из контейнера исследователя доступны train (build submit, train submit, status, result) и private (`search-readiness`). Public из контейнера отдельно не вызывался (оценка на public — отдельная проверка только в ходе поиска).

## Условия окружения запуска (запись 2026-11-05)

- `AR04A_CONDITIONS_ID=ar04a-metric-v1-runner-d4e3f8799ccc`, `AR04A_INPUT_ASSETS_DIGEST=4bf532e2119dc0298051f23df86fdd6a0ba53ff4ee6d7611317fa235435f2ee2` (со слов оператора; digest входных материалов в квитанции build совпал). Отпечаток окружения build: `7bd36f7f24718bdd29578a6e4bc147a7819ccf1d18a0524d3d45abb4f6b4c06a`.
- Метрика установлена оператором в `/srv/arena/metric`, digest `bc8760a07ae5…` совпал, `evaluator.prepare verify` успешно (со слов оператора; из контейнера исследователя не проверялось).
- Контейнер исследователя запущен по `compose.campaign.yaml` (профиль `research`), uid 10001.

## Готовность сервисов

- **`search-readiness` private** (2026-11-05T17:06:26Z, из контейнера исследователя, токен private-submit-token не приводится):
  ```
  python -m evaluator.client search-readiness --url "$ARENA_PRIVATE_URL" --token-file /run/secrets/arena/private-submit-token --require-campaign --max-solutions 30 --finalists 5 --output-count 2 --release-id ar04a-c1-metric-bc8760a07ae5
  {"mode": "campaign", "gate_enabled": true, "journal_ready": true, "max_solutions": 30, "finalists": 5, "output_count": 2, "evaluation_enabled": true, "release_id": "ar04a-c1-metric-bc8760a07ae5"}
  ```
  Код выхода 0; режим, защита, `evaluation_enabled`, лимит, K, N и release ID совпадают с условиями.
- **Изоляция** (`case/deploy/check_isolation.sh`, из контейнера исследователя, 2026-11-05): 26 проверок OK, 0 FAIL, код выхода 0 (uid 10001; нет `/srv/arena`, `/private`, `/state`, `/usage`, `/search-control`, ключа модели, `/etc/arena`, docker.sock, docker CLI, sudo, wsl.exe, `/mnt/c`; нет `public.jsonl` и `private.jsonl`; нет операторских `ARENA_*`; train читается, `/search` пишется; `/assets` и `/derived` только чтение, `/staging` пишется; в `/run/secrets/arena` только три submit-токена). Прежние 3 FAIL по `/assets`, `/derived`, `/staging` устранены запуском по новому compose.
- **Пробный build** (кандидат `smoke-dense`, плотный поиск `bge-base-en-v1.5` — самая тяжёлая из разрешённых bi-encoder моделей; журнал `/tmp/smoke.sqlite3`, `--max-solutions 1`; канонический журнал не тронут): `evaluator.build submit` принят, статус `FINISHED`, **26.3 с** при таймауте 600 с (запас ≈ 23×), без ошибок, публикация `21d248cc523d1ce2a7f44c86285b02032cb58671ed64d48cc4b21e50bc703754` (2 файла, 583 818 байт) видна в `/derived`. Квитанция версии 2 содержит `input_assets_digest` из условий. Это замер одной модели на 189 навыков; более тяжёлые методы (кросс-энкодер по всем парам, обучение) запас съедят — оценивать отдельно.
- **Пробный `train submit`** (повтор 2026-11-05T17:22Z после того, как оператор создал `/srv/arena/assets/prepared` и `assets/derived`):
  - Первая попытка (17:08Z) получила HTTP 422 «candidate preparation is unavailable»; оператор воспроизвёл причину в train-сервисе: `validate_candidate` падал с «invalid prepared runner asset mountpoint» (нет `assets/prepared`), квитанция build была валидна. Исправлено `stage_srv.sh` + созданием каталогов на хосте.
  - Повтор: `evaluator.train submit --candidate smoke-dense --measurement smoke-m1 --dataset ar04a-skill-select-v1 --conditions ar04a-metric-v1-runner-d4e3f8799ccc` на первых 20 примерах `train_curve` → `RUNNING`, затем `FINISHED` (evaluation_id `26676354ed8496b8df8719eeae06423e8a5dfb55a4b1e7bbafa2d19ab995153e`), `evaluator.train result` получен, измерение закрыто в `/tmp/smoke.sqlite3` (`completed_measurements: 1`).
  - Результат: 20/20 примеров решены и валидны, ошибок нет; score 0.915 на 20 примерах (технический прогон, не замер кампании и не показатель качества кандидата). В результате есть ответы и score по каждому примеру, `preparation` — квитанция build с `candidate_digest` кандидата и `input_assets_digest` из условий, расходы build учтены (26.3 с).
  - **`/assets/prepared` в runner содержит результат build:** `solve.py` кандидата читает `emb.npy` и `ids.json` только из `/assets/prepared`, и все 20 ответов — осмысленные id каталога (например, для запроса про координаты адресов — `["acuris-mcp", …]`, score 1.0), то есть публикация смонтирована. Прямого просмотра каталога внутри контейнера runner не было (он `network=none`, одноразовый).
  - **Время на пример:** время решателя на пример — среднее 9.15 с, медиана 8.90 с, мин 7.95 с, макс 12.56 с (сумма 183 с); wall всего измерения 186.4 с на 20 примеров (≈ 9.3 с на пример при двух слотах — параллелизм заметно не ускорил, т. к. `solver_seconds` 209 с > wall 186 с лишь немного). Judge (метрика) — около 0.19 с на пример. Всё далеко от 600 с на пример. Время почти целиком — загрузка `bge-base` и импорт torch в каждом одноразовом контейнере (каждый пример — отдельный запуск). Экстраполяция: `train_curve` (200 примеров) для такого кандидата ≈ 30 мин, то есть на границе ориентира ≤ 30 мин; public (380) ≈ 1 ч — на границе ≤ 60 мин. Кандидаты с более лёгким `solve` будут быстрее.
  - Побочные следы пробы остались: измерение `smoke-m1` закрыто; в `/srv/arena/builds` и `/srv/arena/derived` — квитанция и публикация `smoke-dense` (на кампанию не влияют).
- Логин Claude Code в контейнере и `/status` (модель, effort): не проверялись, это делает оператор при запуске поиска.

## Оставшиеся ограничения

- **Таймаут 600 с общий для solve и build.** Оператор 2026-11-05 принял `ARENA_RUNNER_TIMEOUT=600` вместо 60 с из ADR-0004; условия и `compose.campaign.yaml` обновлены, ADR и `docs/` — нет. Арена применяет один таймаут к одному примеру и к build, поэтому зависший пример занимает слот до 10 минут. Пробный build эмбеддингов bge-base на 189 навыках занял 26 с (запас большой); тяжёлые методы нужно оценивать отдельно. Отпечаток окружения build включает таймаут, поэтому значение нельзя менять после первого build.
- Изменения подготовки лежат в `/srv/arena/train` незакоммиченными: подготовка не коммитила. Оператору нужно закоммитить их там и забрать в свой репозиторий (`git -c safe.directory=/srv/arena/train pull /srv/arena/train main`).
- Пробные build и `train submit` выполнены на отдельном журнале `/tmp/smoke.sqlite3` (не канонический, лимит 30 не затронут).

## Следующий шаг

Оператор запускает контейнер исследователя (профиль `research`), логинится в `claude` (модель `claude-sonnet-5-5`, effort high, проверить в `/status`) и передаёт `prompts/start.md`, каталог кампании `/workspace/case/campaigns/c1` и адреса из `ARENA_*_URL` отдельным сеансом. Канонический журнал `/search/search.sqlite3` пуст (`proposed: 0`, `remaining_proposals: 30`).
