"""Стартовый кандидат: BM25 по name + description навыков.

Контракт runner арены (немодельный режим):
stdin  — {"input": "<запрос>", "assets_dir": "/assets", ...}
stdout — {"answer": "<JSON-массив до 3 id навыков>"}
Каталог — <assets_dir>/catalog.jsonl.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

K1, B, TOP = 1.5, 0.75, 3


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, docs: list[list[str]]):
        self.tfs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = sum(self.lens) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for tf, length in zip(self.tfs, self.lens):
            s = 0.0
            for t in query:
                if t in tf:
                    s += self.idf[t] * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * length / self.avg))
            out.append(s)
        return out


def solve(task: dict) -> str:
    catalog = [json.loads(line) for line in (Path(task["assets_dir"]) / "catalog.jsonl").open(encoding="utf-8")]
    index = BM25([tokenize(c["name"] + " " + c["description"]) for c in catalog])
    scores = index.scores(tokenize(task["input"]))
    # при равенстве — порядок каталога, чтобы ответ был детерминированным
    ranked = sorted(range(len(catalog)), key=lambda i: (-scores[i], i))
    return json.dumps([catalog[i]["id"] for i in ranked[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
