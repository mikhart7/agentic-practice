# Кейс: подбор навыка по запросу (AR-04а)

Оформлен по `cases/template` арены (коммит `a28eee3`). Для кампании каталог копируется в `cases/ar04a-skill-select` репозитория арены.

## Задача
Дан запрос пользователя к агенту на английском. Нужно выбрать из фиксированного каталога 189 навыков (MCP-серверов) тот, который его выполнит.

- **Вход** (stdin решателя, контракт runner арены): `{"input": "<запрос>", "assets_dir": "/assets"}`.
- **Ответ** (stdout): `{"answer": "<JSON-массив до 3 id навыков в порядке убывания уверенности>"}`, например `{"answer": "[\"pdf-to-md\", \"marqpdf\"]"}`.
- **Разрешённые материалы** (`/assets`, только чтение):
  - `catalog.jsonl` — `id`, `name`, `description`;
  - `models/<name>` — закреплённые модели из [`assets/models.toml`](assets/models.toml).

  Кластеры навыков (`dataset/catalog_meta.jsonl`) решателю **не** передаются.
- **Train** для исследования: [`dataset/train.jsonl`](dataset/train.jsonl) и [`dataset/train.meta.jsonl`](dataset/train.meta.jsonl) (семейства, стили, кластеры).

## Разрешённые изменения
Подробно и с обоснованием — [ADR-0004](../docs/adr/0004-allowed-changes-and-models.md).

**Можно менять:** код решателя и вспомогательные модули:
- токенизацию;
- BM25 и его параметры;
- гибриды;
- переранжирование;
- правила и порядок топ-3;
- выбор моделей из закреплённого списка;
- подготовку в `build.py` (штатный build арены): эмбеддинги каталога, индексы, обучение на train. Её выполняет train-сервис в runner, результат виден `solve.py` в `/assets/prepared`. Потомок может взять результат build родителя по digest (`parameters.asset_digests` → `/assets/derived/<digest>`).

**Нельзя:**
- менять или дополнять описания каталога (это вариант AR-04б);
- обращаться к сети, LLM и моделям вне списка;
- хранить таблицы «запрос → ответ» из train;
- класть в пакет готовые эмбеддинги, индексы или веса, посчитанные вне build;
- использовать public и private.

**Зафиксировано:**
- каталог и данные всех split;
- метрика;
- список моделей и их ревизии;
- библиотеки runner-образа (`uv.lock`);
- ресурсы контейнера: 2 CPU, 2 ГБ;
- таймаут: 600 с на пример и на build (один `ARENA_RUNNER_TIMEOUT` арены); типичный запрос — секунды.

## Данные
См. [dataset/README.md](dataset/README.md):
- train — 756 запросов в репозитории;
- public — 380 запросов, у оператора;
- private — 376 запросов, у оператора.

Деление по семействам-намерениям.

## Метрика
См. [metric/](metric) и [ADR-0003](../docs/adr/0003-metric.md). `score = 0.7·acc@1 + 0.3·nP@3`, направление `maximize`, невалидный ответ получает 0.

## Кампания
См. [campaign/campaign.md](campaign/campaign.md).

## Стартовый кандидат
[ways/baseline](ways/baseline) — BM25 по `name + description`, train score 0.508.

## Локальная проверка
```bash
uv sync --frozen && uv run python case/assets/fetch_models.py          # зависимости и модели
uv run --no-project --with pytest==8.4.2 python -m pytest case/metric/tests
python case/eval_local.py --way case/ways/baseline --split case/dataset/train.jsonl
```
