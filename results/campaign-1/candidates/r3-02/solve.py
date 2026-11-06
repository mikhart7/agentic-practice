"""R3 (переранжирование): лексика r1-03 -> топ-N -> кросс-энкодер -> топ-3.

Контракт runner арены: stdin {"input", "assets_dir"} -> stdout {"answer": "<JSON-массив до 3 id>"}.
Первая стадия (lexical.py) - чистый Python по каталогу. Вторая стадия - кросс-энкодер из
<assets_dir>/models/<MODEL> (transformers + torch образа runner), пары (запрос, "name. description")
для первых N кандидатов; порядок топ-N заменяется порядком оценок кросс-энкодера, ничьи - по рангу первой стадии.
Сбой модели не маскируется запасным ответом: исключение завершает процесс с ошибкой.
"""
import json
import os
import sys
import time
from pathlib import Path

import lexical

MODEL = "ms-marco-MiniLM-L6-v2"
N = 20          # сколько кандидатов первой стадии получают оценку кросс-энкодера
MAX_LEN = 256   # токенов на пару (запрос + документ)
TOP = 3


def cross_scores(assets_dir: str, query: str, docs: list[str]) -> list[float]:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(2)
    path = Path(assets_dir) / "models" / MODEL
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).eval()
    batch = tok([query] * len(docs), docs, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
    with torch.inference_mode():
        logits = model(**batch).logits
    return [float(x) for x in logits[:, 0]]


def solve(task: dict) -> str:
    t0 = time.time()
    catalog = lexical.load_catalog(task["assets_dir"])
    ranked, _ = lexical.first_stage(task["input"], catalog)
    cand = ranked[:N]
    t1 = time.time()
    docs = [f'{catalog[i]["name"]}. {catalog[i]["description"]}' for i in cand]
    ce = cross_scores(task["assets_dir"], task["input"], docs)
    order = sorted(range(len(cand)), key=lambda k: (-ce[k], k))
    print(f"first_stage={t1 - t0:.2f}s cross={time.time() - t1:.2f}s model={MODEL} n={len(cand)}", file=sys.stderr)
    return json.dumps([catalog[cand[k]]["id"] for k in order[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
