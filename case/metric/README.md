# Метрика кейса AR-04а

Правила зафиксированы до поиска: [ADR-0003](../../docs/adr/0003-metric.md).

- **Ответ решателя** — JSON-массив не более чем из 3 уникальных id навыков из каталога, в порядке ранга.
- **Score примера** — `0.7·acc@1 + 0.3·nP@3`, где релевантны `primary` и `acceptable` из `reference`, а `nP@3 = |top3 ∩ rel| / min(3, |rel|)`.
- **Невалидный ответ** получает 0. Повреждённый `reference` — ошибка, а не 0.
- **Направление** — `maximize`. Итог по набору — среднее (агрегатор арены по умолчанию).
- **`statistics`** по примеру: `valid`, `acc1`, `np3`.

Файлы пакета:
- `metric.json` — `kind: command`, без модели;
- `score.py` — реализация;
- `catalog_ids.txt` — id каталога для проверки ответов; тест сверяет его с `case/assets/catalog.jsonl`.

Проверка:

```bash
uv run --no-project --with pytest==8.4.2 python -m pytest case/metric/tests
echo '{"example":{"id":"x","input":"merge pdfs","reference":"{\"primary\":\"pdfsamenvoegen\",\"acceptable\":[]}"},"answer":"[\"pdfsamenvoegen\"]"}' \
  | python case/metric/score.py
```

Заморозка — в арене, после завершения подготовки:

```bash
# кэш pytest иначе попадёт в пакет и сломает побайтовую воспроизводимость
find <repo>/case/metric -name __pycache__ -type d -prune -exec rm -rf {} +
uv run python -m evaluator.prepare freeze --metric <repo>/case/metric --output <campaign_dir>/metric
uv run python -m evaluator.prepare verify --metric <campaign_dir>/metric
```
