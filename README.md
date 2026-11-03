# Подбор навыка по запросу: навык, выращенный на арене

> Шаблон репозитория для задания B. ТЗ: [B-arena-skill.md](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/B-arena-skill.md), реестр тем: [arena-registry.md](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/arena-registry.md).
> Замени всё в `<угловых скобках>`, удали этот блок.

Тема (согласована при регистрации): [AR-04. Подбор навыка по запросу (Н2-08)](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/arena-registry.md#ar-04-подбор-навыка-по-запросу-н2-08), вариант **AR-04а — улучшение алгоритма подбора навыков**: каталог и описания навыков фиксированы, эволюционирует алгоритм поиска (BM25, эмбеддинги, переранжирование, обучаемый ранжировщик). Baseline — BM25 по исходным описаниям. Общие требования: [projects/README.md](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/README.md).

## Итог в одной таблице

| | Train | Public | Private |
|---|---|---|---|
| Baseline (BM25) | 0.508 | | |
| Выращенное решение | | | |
| <классический подход, если реализован> | | | |

Лимит предложенных решений: <N>. Кандидатов в журнале: <M>. AUC кривой: <...>.

## Структура

```
docs/domain.md      обзор домена и классических подходов
docs/arena.md       как устроена арена (или своя методология и сравнение с ареной)
docs/evolution.md   разбор эволюции: кривая, родословная, ключевые мутации, переобучение
docs/solution.md    итоговое решение своими словами
docs/talk.md        план рассказа
docs/adr/           решения: методология, split, метрика, лимит
case/               кейс арены (по cases/template): задача, данные, метрика, кампания, стартовый способ
skill/              итоговый навык: SKILL.md + scripts/ + tests/
results/            выгрузки журнала, замеры, графики
```

## Как воспроизвести

Арена используется из GitLab без изменений, закреплена на коммите `a28eee3`. Код арены в этот репозиторий не копируется: кейс подключается к ней ссылкой `cases/ar04a-skill-select → case/`.

```bash
# зависимости, модели, арена
uv sync --frozen && uv run python case/assets/fetch_models.py
bash scripts/setup_arena.sh                                    # ~/arena @ a28eee3 + ссылка на кейс

# каталог и данные (каталог закоммичен; public/private — только у оператора)
python case/dataset/build_catalog.py build                      # тот же каталог побайтово
python case/dataset/generate.py split --seed 1                  # нужен пул у оператора
python case/dataset/curve_subset.py                             # train_curve

# метрика и baseline
uv run --no-project --with pytest==8.4.2 python -m pytest case/metric/tests
python case/eval_local.py --way case/ways/baseline --split case/dataset/train.jsonl

# развёртывание, подготовка и поиск — case/deploy/README.md (prompts/prepare.md и prompts/start.md арены)
# <построить кривую и родословную: после кампании>
```

## Модели

<Модель исследователей и (если есть) решателя/судьи, версии, AA Intelligence Index, дата.>
