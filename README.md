# Подбор навыка по запросу: навык, выращенный на арене

> Шаблон репозитория для задания B. ТЗ: [B-arena-skill.md](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/B-arena-skill.md), реестр тем: [arena-registry.md](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/arena-registry.md).
> Замени всё в `<угловых скобках>`, удали этот блок.

Тема: [AR-04. Подбор навыка по запросу (Н2-08)](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/arena-registry.md#ar-04-подбор-навыка-по-запросу-н2-08), вариант **AR-04а — улучшение алгоритма подбора навыков**: каталог и описания навыков фиксированы, эволюционирует алгоритм поиска (BM25, эмбеддинги, переранжирование, обучаемый ранжировщик). Baseline — BM25 по исходным описаниям. Общие требования: [projects/README.md](https://github.com/deeppavlov/agentic-course-itmo/blob/main/projects/README.md).

## Итог в одной таблице

| | Train | Public | Private |
|---|---|---|---|
| Baseline | | | |
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

```bash
<клонировать арену и подключить кейс>
<сгенерировать данные: python case/dataset/generate.py --split train --seed ...>
<проверить метрику: pytest case/metric/tests>
<подготовка и запуск кампании — по prompts/prepare.md и prompts/start.md арены>
<построить кривую и родословную: ...>
```

## Модели

<Модель исследователей и (если есть) решателя/судьи, версии, AA Intelligence Index, дата.>
