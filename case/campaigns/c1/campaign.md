# Условия кампании c1 (подготовленные)

Статус: **подготовлено, зафиксировано до поиска**. Перенесено из [черновика](../../campaign/campaign.md) агентом подготовки (`prompts/prepare.md`, арена `a28eee3`); оставшиеся ограничения и результаты проверок — в [preparation.md](preparation.md).

- **Каталог кампании:** `case/campaigns/c1` этого репозитория. В контейнере исследователя, где идут подготовка и поиск, — `/workspace/case/campaigns/c1`; на хосте тот же каталог виден как `~/arena/cases/ar04a-skill-select/campaigns/c1`. Арена `a28eee3`.
- **Метрика:** `ar04a-skill-select-metric-v1` ([metric/](metric), исходный пакет [../../metric](../../metric), [ADR-0003](../../../docs/adr/0003-metric.md)), `maximize`, без модели. Заморожена до поиска: `evaluator.prepare freeze`, `verify` — успешно. Digest замороженного пакета `bc8760a07ae545189d94ce789f73882cb00f3702c7b516603ae75044f2f244a2` (`python case/deploy/tree_digest.py case/campaigns/c1/metric`: sha256 по отсортированным парам «путь, sha256 файла», включая `metric.lock.json` и `tests/`). Release ID: `ar04a-c1-metric-bc8760a07ae5`.
- **Данные** (sha256):
  - каталог `assets/catalog.jsonl` — 189 навыков, `412b5a50aa99ab679551307d244976b36eccbf4527c573c16311ab45e81b714a`;
  - train `dataset/train.jsonl` — 756 запросов, `9c2e9857…`;
  - `train_curve` `dataset/train_curve.jsonl` — 200 запросов, `d4aecd33…`;
  - public — 380 запросов, `3c91b815…` (у оператора);
  - private — 376 запросов, `c2d40116…` (у оператора);
  - подробности — [dataset/generation_report.md](../../dataset/generation_report.md).
- **Модель исследователей:** Claude Sonnet 5.5 (`claude-sonnet-5-5`), effort high, в Claude Code 2.1.280. AA Intelligence Index — 41, проверено 2026-11-03 (README, «Модели»). Решатель и метрика LLM не используют.
- **Разрешённые изменения:** [ADR-0004](../../../docs/adr/0004-allowed-changes-and-models.md):
  - код решателя, модели из `assets/models.toml`, подготовка в `build.py` через train-сервис (эмбеддинги, индексы, обучение на train);
  - каталог, описания, сеть, LLM и таблицы запросов из train трогать нельзя.
- **Среда исполнения:** runner-образ с библиотеками из `uv.lock`; `/assets` — каталог и модели, `/assets/prepared` — результат build кандидата; контейнер 2 CPU, 2 ГБ, `network=none`.
- **Train-сервис:** с build и выбором опубликованных материалов (`supports_build: true`, `supports_asset_selection: true`) для харнеса `ar04a-runner:local` (`ARENA_HARNESSES={}`, одно значение по умолчанию для train, public и private); конфигурация — [`case/deploy/compose.campaign.yaml`](../../deploy/compose.campaign.yaml) и [`campaign.env.example`](../../deploy/campaign.env.example), сделана по [`deploy/README.md`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/deploy/README.md) арены и образцу [`cases/sc35/.../deploy/compose.yaml`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/cases/sc35/campaigns/sc35-first-20261028/deploy/compose.yaml); отличие от образца — нет gateway, сетей runner и MLflow, `ARENA_RUNNER_NETWORK=none`.
  - Общие для train, public и private: runner-образ, метрика, `ARENA_BUILD_DIR` (`/srv/arena/builds`), `ARENA_PUBLISHED_ASSETS_DIR` (`/srv/arena/derived`), `ARENA_INPUT_ASSETS_DIGEST` и отпечаток окружения; в `Settings`/`TrainSettings` арены отпечатки трёх сервисов совпадают.
  - Порты на `127.0.0.1` хоста: train 8070, public 8090, private 8080.
  - `ARENA_DATASET_ID=ar04a-skill-select-v1`, `ARENA_CAMPAIGN_ID=ar04a-c1`, `ARENA_CONDITIONS_ID=ar04a-metric-v1-runner-<12 символов digest образа ar04a-runner:local>` (значение задаёт оператор после сборки образа).
  - Слоты исполнения: `ARENA_EXECUTION_SLOTS=2` на все три сервиса (две параллельные проверки).
- **MLflow:** не используется (`ARENA_TRAIN_TRACKING=false`). Train-сервис возвращает ответы и score по каждому примеру и без него. Трейсы агентов — транскрипты Claude Code в `/srv/arena/researcher-home`.
- **Таймауты:**
  - 600 с на пример и на build кандидата (`ARENA_RUNNER_TIMEOUT=600`; арена задаёт один таймаут для solve и build). Решение оператора от 2026-11-05 вместо 60 с из ADR-0004; ориентир по времени оценки кандидата ниже остаётся целевым, а не лимитом;
  - оценка одного кандидата — ориентир ≤ 30 мин на `train_curve` и ≤ 60 мин на public;
  - кампания — ~1 неделя машинного времени.

## Сопоставимые замеры
- **Кривая и AUC** — `train`, подвыборка `train_curve` (50 семейств, 200 запросов), условия `ar04a-metric-v1-runner-<digest>`. Обязательна для каждого предложенного решения.
- **Public** — для перспективных кандидатов и всех K финалистов, один раз на кандидата. Ориентир — 8–10 проверок.
- **Разведочные замеры** — через тот же train-сервис на полном train или своих подвыборках; в кривую они не входят. Для групповой кросс-валидации использовать `family` из `train.meta.jsonl`.

## Лимит предложенных решений: 30
Почему столько ([ADR-0005](../../../docs/adr/0005-campaign-limit.md)):
- около 6 направлений по 4–5 итераций — ~25 решений, ещё ~5 на доводку и разнообразие финалистов;
- машинное время около 14 ч (30 × ~18 мин на `train_curve` и ~10 × ~32 мин на public), при двух параллельных проверках ≈ 7–8 ч;
- токены исследователей — 3–9 млн; при исчерпании окна лимита подписки агенты ждут сброса, модель не меняется.

## Финализация
- **Финалистов на private (K):** 5.
- **Итоговых решений (N ≤ K):** 2.
- **Правило выбора финалистов:**
  - качество на `train_curve` и public;
  - разрыв train↔public как признак переобучения;
  - разнообразие подходов (не пять вариаций одного);
  - ревью без замечаний (подготовка через build с квитанцией, нет заученных запросов, описания не менялись);
  - при равном качестве — меньше времени на запрос.

## Ограничения, известные на момент подготовки
- **Таймаут 600 с общий для solve и build.** Арена задаёт один `ARENA_RUNNER_TIMEOUT`, отдельного таймаута build нет. Оператор 2026-11-05 принял 600 с вместо 60 с из ADR-0004 (ADR и `docs/` не обновлялись). Следствия: зависший пример занимает слот до 10 минут, а при 200 примерах `train_curve` худший случай значительно превышает ориентир ≤ 30 мин; на практике важно, чтобы типичный solve оставался быстрым (около секунд). Укладывается ли build эмбеддингов и индексов 189 навыков в 600 с при 2 CPU и 2 ГБ, не проверено.
- **Digest входных материалов** (`ARENA_INPUT_ASSETS_DIGEST`) считает оператор на хосте: `python case/deploy/tree_digest.py /srv/arena/assets --exclude derived`. Моделей в контейнере подготовки нет.
- **Оценка кандидата через сервисы** (train, public, private), `search-readiness`, проверка изоляции, build из контейнера исследователя и логин Claude Code на момент записи этих условий не выполнены: Docker в среде подготовки нет. Статус — в [preparation.md](preparation.md).
