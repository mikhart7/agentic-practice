# Общая выдача исследователю (кампания c1, AR-04а)

Роль и правила: `/opt/arena/prompts/researcher.md`, `/opt/arena/common/{IMMUNE,research-protocol,search-history,long-runs}.md`. Кейс: `/workspace/case/README.md`, разрешённые изменения: `/workspace/docs/adr/0004-allowed-changes-and-models.md`, условия: `/workspace/case/campaigns/c1/campaign.md`.

## Задача
Подбор навыка по запросу: вход `{"input": "<запрос>", "assets_dir": "/assets"}`, ответ `{"answer": "<JSON-массив до 3 id>"}`. Метрика `0.7·acc@1 + 0.3·nP@3`, maximize, без модели. Каталог 189 навыков `/workspace/case/assets/catalog.jsonl` (описания менять нельзя). Baseline BM25: 0.488 на `train_curve`, 0.508 на train. Решатель без LLM и без сети (`network=none`, 2 CPU, 2 ГБ, 600 с на пример и на build).

## Пакет кандидата (`case/ways/<id>/` в твоём worktree)
- `solve.py` (stdin JSON → stdout JSON), по желанию вспомогательные текстовые файлы. Модели — только из `/assets/models/<name>` (см. `/workspace/case/assets/models.toml`).
- `build.py` для всего, что считается один раз (эмбеддинги каталога, индексы, обучение на train): получает JSON `{"assets_dir","build_dir":"/output",...}`, пишет в `/output`; результат монтируется в solve как `/assets/prepared` (только чтение). Готовые эмбеддинги/веса, посчитанные вне build, класть в пакет нельзя. В контейнере исследователя нет torch/numpy: код с моделями проверяется только через train-сервис (это реальный запуск в runner, ~9 с на пример для sentence-transformers+bge-base, в основном импорт/загрузка; прямой `transformers` ~4 с).
- Если кандидат использует train для обучения: записи train, нужные build, включи в пакет (текстовые файлы) и укажи в `README.md` кандидата происхождение, назначение и разрешающий пункт (ADR-0004). Таблицы «запрос → ответ» из train и правила под конкретные запросы запрещены.
- В `README.md` кандидата: гипотеза, механизм, изменения, происхождение train-сведений.

## Замечание оператора (2026-11-05)
Модели запускаются только в runner через train-сервис (build.py и train submit). Локально — только чистый Python (`case/eval_local.py`). Не ставь torch/transformers в контейнер исследователя и не считай локально эмбеддинги или веса для кандидатов: это неизмеряемая подготовка, переносить её в пакет нельзя. `/tmp` здесь 128 МБ noexec.

## Регистрация и замеры (обязательный порядок)
1. Запиши claim в `/workspace/case/campaigns/c1/board/claims/<ты>.md`: гипотеза, механизм, область, ожидаемый эффект, опровергающая проверка.
2. Зарегистрируй версию ДО проверки (расходует место из твоей квоты, даже если не заработает):
   `cd /opt/arena && python -m evaluator.search --journal /search/search.sqlite3 propose --id <id> --directory <абс. путь к case/ways/<id>> [--parent <id> ...] --hypothesis '...' --change '...' --tokens 0 --tokens-incomplete --seconds <секунды твоей работы над версией>`
   ID вида `<ветка>-NN` (например `r1-01`). Токены исследователя тебе неизвестны: передавай `--tokens 0 --tokens-incomplete`. После регистрации файлы под этим ID НЕ менять: исправление = новая версия с родителем.
3. Сопоставимый замер (ровно один раз на кандидата): `python /workspace/case/campaigns/c1/tools/measure.py --candidate <id> --measurement <id>-curve --subset curve` (сам делает build, если нужен: для кандидата без `build.py` добавь `--no-build`). Запускай в фоне (`run_in_background`) и жди завершения процесса без промежуточного опроса модели. Кривая 200 примеров: ориентир 2–30 мин (лексика ~3 мин). Проверь первый результат/прогресс, рассчитай остаток по `common/long-runs.md`.
4. Разведка (не в кривую, места не занимают): `--subset train` или свой jsonl (`--example-id`, `--subset /путь/своя_подвыборка.jsonl`, номер измерения `<id>-expN`), либо `python /workspace/case/eval_local.py --way <dir> --split <jsonl> --details out.jsonl` для чистого Python. Один пример — один ответ; не повторяй корректный ответ ради балла.
5. Результаты измерений: `/workspace/case/campaigns/c1/runs/<measurement>.json` и `.summary.json` (score, `solver_seconds`, `wall_seconds`). Ответы/оценки по примерам внутри `.json` — для анализа ошибок на train.
6. findings: `/workspace/case/campaigns/c1/board/findings/<ты>.md` — по каждой версии: ID, родители, гипотеза, ревизия (git commit), набор и условия, score, время, регрессии, что опровергнуто, ограничения (в том числе: настройка по `train_curve` делает его не независимой проверкой), рекомендация.
7. Public и private не используй и не вызывай. Не меняй чужие файлы, метрику, `campaign.md`, настройки сервисов.

## Git
Работай в своём worktree/ветке, коммить версии (`case/ways/<id>`, findings копируй в абсолютный путь board, он общий и вне git-ветки). Коммит ветки не меняет зарегистрированный снимок: сам снимок хранится в журнале.

## Что вернуть оркестратору (коротко)
Для каждой версии: **что проверено → что получилось (числа) → что опровергнуто → что делать дальше**, ссылки на findings и runs. Какие места из квоты потрачены. Не останавливай кампанию и не трогай финализацию.
