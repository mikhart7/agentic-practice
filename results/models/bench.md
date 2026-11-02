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

Вывод: время запроса определяют импорт и кодирование каталога, а не модель. Отсюда решения в [ADR-0004](../../docs/adr/0004-allowed-changes-and-models.md): предвычисленные эмбеддинги каталога в пакете кандидата, кросс-энкодер — только на коротком списке.
