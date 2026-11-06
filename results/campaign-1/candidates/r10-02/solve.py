#!/usr/bin/env python3
"""solve: кодирует запрос каждым выбранным в build энкодером (numpy), центрирует, считает косинусы, сливает оценки, топ-3.

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
Читает: /assets/prepared (config.json, ids.json, emb_<модель>.npy, mu_q.npz) и модели /assets/models/<имя> (только с весом > 0).
Каталог и train не читает.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from fusion import fuse  # noqa: E402

TOP = 3


def _norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


def encode_queries(texts: list, spec: dict, model_dir: Path):
    if spec.get("numpy_encoder_ok"):
        try:
            from enc import Encoder
            return Encoder(model_dir, spec["pooling"], spec["max_len"]).encode(texts)
        except Exception as exc:
            print(f"numpy encoder failed, fallback: {exc!r}", file=sys.stderr)
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(model_dir), device="cpu").encode(texts, normalize_embeddings=True)


def solve(task: dict) -> str:
    assets = Path(task["assets_dir"])
    prepared = assets / "prepared"
    cfg = json.loads((prepared / "config.json").read_text())
    ids = json.loads((prepared / "ids.json").read_text())
    mu = np.load(prepared / "mu_q.npz")
    fusion = cfg["fusion"]
    S = []
    for spec, w in zip(cfg["models"], fusion["weights"]):
        if w == 0:
            S.append(np.zeros((1, len(ids)), np.float32))
            continue
        name = spec["name"]
        texts = [prefix + task["input"] for prefix in spec["query_prefixes"]]
        q = encode_queries(texts, spec, assets / "models" / name)
        x = _norm(q.sum(axis=0, keepdims=True))    # нормированная сумма вариантов запроса == среднее косинусов
        x = _norm(x - mu[name])                    # центрирование: вычитание среднего запросов train (обучено в build)
        S.append(x @ np.load(prepared / f"emb_{name}.npy").T)
    scores = fuse(S, fusion)[0]
    ranked = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), i))
    return json.dumps([ids[i] for i in ranked[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
