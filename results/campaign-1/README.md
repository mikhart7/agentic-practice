# Кампания c1: выгрузка

Кампания AR-04а на арене DeepPavlov `a28eee3`, 2026-11-05 — 2026-11-06. Условия и ход описаны в [case/campaigns/c1/campaign.md](../../case/campaigns/c1/campaign.md), отбор финалистов — в [selection.md](../../case/campaigns/c1/selection.md).

## Итог
- **Предложено:** 27 решений из 30. Поиск остановлен командой оператора на плато; свидетельство остановки сверено оценщиком private.
- **Финалисты (K = 5):** r10-01, r9-02, r6-01, r4-01, r5-02.
- **Выбрано оценщиком (N = 2):** r9-02 (private 0.856) и r10-01 (0.853). BM25 на private — 0.608.
- **Кривая на `train_curve`:** от 0.488 (BM25) до 0.813. AUC до горизонта 30 — 22.39, `mean_quality` 0.746.

## Что где
| Путь | Что это |
|---|---|
| `search.sqlite3` | журнал поиска как есть, со снимками кандидатов |
| `journal.json` | `evaluator.search export`: кандидаты, родители, гипотезы, все замеры |
| `curve.json` | `evaluator.search curve` на `train_curve`, baseline 0.488, горизонт 30 |
| `candidates/<id>/` | снимки всех 27 кандидатов (`evaluator.search restore`); `__pycache__` из снимков не коммитится, поэтому для сверки digest восстанавливайте из `search.sqlite3` |
| `private/summary.json` | итог оценщика private: score и время каждого финалиста, победители, условия, допуск по остановке |
| `private/slices.md` | private по стилям запросов и срезу `hard`, вместе с BM25 |
| `traces/setup/` | пробный запуск Claude Code в контейнере исследователя, 2026-11-03 |
| `traces/preparation/` | две сессии подготовки по `prompts/prepare.md` |
| `traces/search/` | сессия поиска по `prompts/start.md`: оркестратор и `subagents/` (исследователи и ревьюеры) |

## Как получено
```bash
# журнал скопирован из /srv/arena/search; команды арены (~/arena, uv run --frozen python -m evaluator.search --journal search.sqlite3 ...)
export > journal.json
curve --split train --dataset ar04a-skill-select-v1 \
  --subset 37f62d06aad1d4255526dfeecdc7ad60a56d13b2449c10f48d9dee1193af61ab \
  --conditions ar04a-metric-v1-runner-d4e3f8799ccc --direction maximize --baseline 0.488 --horizon 30 > curve.json
restore --candidate <id> --directory candidates/<id>
```

Транскрипты взяты из HOME исследователя (`/srv/arena/researcher-home/.claude/projects/-workspace`). Подготовка и поиск не имели доступа к public и private. Перед публикацией в транскриптах заменён email аккаунта Claude: Claude Code сам добавляет его в контекст сессии. Также проверено, что в них нет submit-токенов и учётных данных. Транскрипты оператора, видевшего private, здесь не публикуются.
