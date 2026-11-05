# Замер моделей на CPU — 2026-11-02

Машина: WSL2, 4 ядра, 7 ГБ RAM, без GPU. Python 3.13, torch 2.15.0+cpu, sentence-transformers 6.2.0. Один поток (`torch.set_num_threads(1)`), каждый замер — новый процесс, как в арене. Показан второй из двух запусков (прогретый дисковый кэш).

```bash
uv sync --frozen && uv run python case/assets/fetch_models.py
for m in all-MiniLM-L6-v2:bi-encoder bge-small-en-v1.5:bi-encoder e5-small-v2:bi-encoder \
         bge-base-en-v1.5:bi-encoder ms-marco-MiniLM-L6-v2:cross-encoder bge-reranker-base:cross-encoder; do
  HF_HUB_OFFLINE=1 .venv/bin/python results/models/bench_one.py case/assets/models/${m%%:*} ${m##*:} 1
done
```

`a` — для bi-encoder кодирование 189 описаний каталога, для cross-encoder оценка 20 пар. `b` — для bi-encoder кодирование одного запроса, для cross-encoder оценка всех 189 пар.

| модель | import | load | a | b | RSS, МБ | всего |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 4.63 | 0.21 | 2.61 | 0.012 | 588 | 7.47 |
| bge-small-en-v1.5 | 4.73 | 0.30 | 4.31 | 0.026 | 636 | 9.36 |
| e5-small-v2 | 4.82 | 0.28 | 4.27 | 0.026 | 629 | 9.40 |
| bge-base-en-v1.5 | 6.24 | 0.38 | 19.92 | 0.125 | 962 | 26.67 |
| ms-marco-MiniLM-L6-v2 | 6.92 | 0.27 | 0.41 | 3.76 | 623 | 11.35 |
| bge-reranker-base | 5.03 | 2.75 | 2.18 | 23.48 | 1372 | 33.44 |

Импорт отдельно (третий запуск, `python -c`):

| импорт | время, с |
|---|---|
| `import numpy` | 0.11 |
| `import torch` | 1.67 |
| `import torch; from transformers import AutoModel, AutoTokenizer` | 2.90 |
| `from sentence_transformers import SentenceTransformer` | 6.79 |

Вывод: время запроса определяют импорт и кодирование каталога, а не модель. Отсюда решения в [ADR-0004](../../docs/adr/0004-allowed-changes-and-models.md): эмбеддинги каталога считаются один раз в `build.py` кандидата (штатный build арены), кросс-энкодер — только на коротком списке.

## В контейнере runner — 2026-11-03

Образ `ar04a-runner:local` ([runner.Dockerfile](../../case/deploy/runner.Dockerfile)), запуск как у оценщика: `--network none --cpus 2 --memory 2g --read-only`, UID 10001, `/assets` только чтение, `python -E -s`. Медиана из 5 запусков по монотонным часам: часы WSL прыгают, `date` для замеров не годится.

```bash
python results/models/time_runs.py $(realpath case/ways/baseline) $(realpath results/models/dense-probe)
```

```
container only (python -c pass)                      median   0.4s  min   0.4s  max   0.4s
import torch                                         median   2.7s  min   2.6s  max   2.7s
import torch+transformers                            median   4.0s  min   4.0s  max   4.1s
import sentence_transformers                         median   8.1s  min   7.9s  max   8.2s
baseline BM25 via runner                             median   0.7s  min   0.6s  max   0.7s
dense MiniLM via runner (catalog encoded per query)  median   9.3s  min   9.2s  max   9.4s
```

Две находки:
- **Модели грузятся из `/assets/models` без сети**, хотя `-E` игнорирует `HF_HUB_OFFLINE`: при локальном пути обращений к хабу нет.
- **Без компиляции байткода при сборке** импорт `sentence_transformers` занимал 16 с. В read-only контейнере `.pyc` не сохраняются, и каждый запуск компилировал torch и transformers заново. Исправлено флагом `--compile-bytecode` в runner.Dockerfile: стало 8.1 с.
