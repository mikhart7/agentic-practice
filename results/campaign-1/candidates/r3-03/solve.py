"""R3 (переранжирование, смешивание): лексика r1-03 -> топ-N -> кросс-энкодер -> смесь z-оценок -> топ-3.

Контракт runner арены: stdin {"input", "assets_dir"} -> stdout {"answer": "<JSON-массив до 3 id>"}.
N и вес смешивания w читаются из <assets_dir>/prepared/params.json (результат build: подбор по записям train).
Сбой модели или отсутствие params.json не маскируются запасным ответом.
"""
import json
import sys
from pathlib import Path

import lexical
import rerank

TOP = 3


def solve(task: dict) -> str:
    assets = Path(task["assets_dir"])
    params = json.loads((assets / "prepared" / "params.json").read_text())
    n, w = int(params["n"]), float(params["w"])
    catalog = lexical.load_catalog(task["assets_dir"])
    ranked, scores = lexical.first_stage(task["input"], catalog)
    cand = ranked[:n]
    model = rerank.load_model(task["assets_dir"], params["model"])
    ce = rerank.cross_scores(model, task["input"], [rerank.doc_text(catalog[i]) for i in cand])
    order = rerank.mixed_order([scores[i] for i in cand], ce, w)
    return json.dumps([catalog[cand[k]]["id"] for k in order[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
