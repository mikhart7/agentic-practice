# Тесты навыка

## Без харнеса: CLI
```bash
uv run --no-project --with-requirements skill/scripts/requirements.txt --with pytest==8.4.2 python -m pytest skill/tests
```
[test_cli.py](test_cli.py) проверяет:
- на запросах обеих задач первым идёт ожидаемый навык;
- все id валидны, работает `--k`;
- каталог с дублями или пропущенными полями отклоняется.

Тесты с моделями пропускаются, если весов нет. Модели ищутся в `SELECT_SKILL_MODELS`, `skill/models` или `case/assets/models`.

## С агентом: две задачи на естественном языке
Задачи лежат в [tasks.json](tasks.json). Обе — запросы из train, ни один не называет нужный инструмент:

| Задача | Запрос пользователя | Ожидаемый навык |
|---|---|---|
| t1 | is anyone testing new treatments for my condition I could join? | `aria-mcp-server` |
| t2 | double-check that the totals in my workbook are actually computed correctly | `agent-spreadsheet` |

Агент получает `prompt` задачи и подключённый навык ([SKILL.md](../SKILL.md)), а ответ пишет в `answer-t1.txt` и `answer-t2.txt`. Каждый вызов CLI навык записывает в журнал `SELECT_SKILL_LOG`. Проверка [check.py](check.py) требует для каждой задачи трёх условий:
1. **навык вызван:** в журнале есть вызов с запросом задачи;
2. **ответ валиден:** в answer-файле один id из каталога;
3. **агент использовал результат:** ответ совпадает с top-1 навыка.

Совпадение с эталоном печатается для сведения.

```bash
export SELECT_SKILL_LOG=$PWD/skill-calls.jsonl
# запуск харнеса с подключённым skill/ и prompt задачи t1, затем t2
python skill/tests/check.py --workdir . --log skill-calls.jsonl
```

Харнес и результат прогона: TODO.
