# Условия кампании (черновик до подготовки)

Статус: **черновик**. Агент подготовки арены (`prompts/prepare.md`) переносит его в `<campaign_dir>/campaign.md`, заполняет пробелы, помеченные «TODO», и фиксирует до поиска.

- **Каталог кампании:** `case/campaigns/c1` этого репозитория. В контейнере исследователя, где идут подготовка и поиск, — `/workspace/case/campaigns/c1`; на хосте тот же каталог виден как `~/arena/cases/ar04a-skill-select/campaigns/c1`. Арена `a28eee3`.
- **Метрика:** `ar04a-skill-select-metric-v1` ([metric/](../metric), [ADR-0003](../../docs/adr/0003-metric.md)), `maximize`, без модели. Замораживается до поиска. TODO: digest замороженного пакета.
- **Данные** (sha256):
  - каталог `assets/catalog.jsonl` — 189 навыков, TODO: digest;
  - train `dataset/train.jsonl` — 756 запросов, `9c2e9857…`;
  - `train_curve` `dataset/train_curve.jsonl` — 200 запросов, `d4aecd33…`;
  - public — 380 запросов, `3c91b815…` (у оператора);
  - private — 376 запросов, `c2d40116…` (у оператора);
  - подробности — [dataset/generation_report.md](../dataset/generation_report.md).
- **Модель исследователей:** Claude Sonnet 5.5 (`claude-sonnet-5-5`), effort high, в Claude Code 2.1.280. AA Intelligence Index — 41, проверено 2026-11-03 (README, «Модели»). Решатель и метрика LLM не используют.
- **Разрешённые изменения:** [ADR-0004](../../docs/adr/0004-allowed-changes-and-models.md):
  - код решателя, модели из `assets/models.toml`, подготовка в `build.py` через train-сервис (эмбеддинги, индексы, обучение на train);
  - каталог, описания, сеть, LLM и таблицы запросов из train трогать нельзя.
- **Среда исполнения:** runner-образ с библиотеками из `uv.lock`; `/assets` — каталог и модели, `/assets/prepared` — результат build кандидата; контейнер 2 CPU, 2 ГБ, `network=none`.
- **Train-сервис:** с build и выбором опубликованных материалов (`supports_build: true`, `supports_asset_selection: true`) для харнеса `ar04a-runner:local`; TODO подготовки: конфигурация по [`deploy/README.md`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/deploy/README.md) арены и образцу [`cases/sc35/.../deploy/compose.yaml`](https://gitlab.deeppavlov.ai/deeppavlov/arena/-/blob/a28eee3abd72d5af3445e718b0253ff7147b8d45/cases/sc35/campaigns/sc35-first-20261028/deploy/compose.yaml).
- **MLflow:** не используется (`ARENA_TRAIN_TRACKING=false`). Train-сервис возвращает ответы и score по каждому примеру и без него. Трейсы агентов — транскрипты Claude Code в `/srv/arena/researcher-home`.
- **Таймауты:**
  - 60 с на пример;
  - оценка одного кандидата — ориентир ≤ 30 мин на `train_curve` и ≤ 60 мин на public;
  - кампания — ~1 неделя машинного времени.

## Сопоставимые замеры
- **Кривая и AUC** — `train`, подвыборка `train_curve` (50 семейств, 200 запросов), условия `ar04a-metric-v1-runner-<digest>`. Обязательна для каждого предложенного решения.
- **Public** — для перспективных кандидатов и всех K финалистов, один раз на кандидата. Ориентир — 15–20 проверок.
- **Разведочные замеры** — через тот же train-сервис на полном train или своих подвыборках; в кривую они не входят. Для групповой кросс-валидации использовать `family` из `train.meta.jsonl`.

## Лимит предложенных решений: 60
Почему столько ([ADR-0005](../../docs/adr/0005-campaign-limit.md)):
- около 8 направлений по 4–6 итераций — 35–45 решений до ожидаемого плато, ещё ~15 на доводку и разнообразие финалистов;
- машинное время около 25 ч (60 × ~15 мин на `train_curve` и ~20 × ~30 мин на public), при двух параллельных проверках укладывается в неделю;
- токены исследователей — 6–18 млн.

## Финализация
- **Финалистов на private (K):** 5.
- **Итоговых решений (N ≤ K):** 2.
- **Правило выбора финалистов:**
  - качество на `train_curve` и public;
  - разрыв train↔public как признак переобучения;
  - разнообразие подходов (не пять вариаций одного);
  - ревью без замечаний (подготовка через build с квитанцией, нет заученных запросов, описания не менялись);
  - при равном качестве — меньше времени на запрос.
