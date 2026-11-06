#!/usr/bin/env python3
"""solve: кодирует только запрос (ансамбль plain+инструкция), применяет обученный в build адаптер, топ-3 по косинусу.

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
Читает: /assets/prepared (emb.npy, ids.json, config.json, adapter.npz) и модель /assets/models/<name>. Каталог и fit.jsonl не читает.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

TOP = 3


def encode_queries(texts: list, cfg: dict, model_dir: Path):
    if cfg.get("numpy_encoder_ok"):
        try:
            from enc import Encoder
            return Encoder(model_dir, cfg["pooling"], cfg["max_len"]).encode(texts)
        except Exception as exc:
            print(f"numpy encoder failed, fallback: {exc!r}", file=sys.stderr)
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(model_dir), device="cpu").encode(texts, normalize_embeddings=True)


def _norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


def solve(task: dict) -> str:
    assets = Path(task["assets_dir"])
    prepared = assets / "prepared"
    cfg = json.loads((prepared / "config.json").read_text())
    ids = json.loads((prepared / "ids.json").read_text())
    emb = np.load(prepared / "emb.npy")
    texts = [prefix + task["input"] for prefix in cfg["query_prefixes"]]
    q = encode_queries(texts, cfg, assets / "models" / cfg["model"])
    x = _norm(q.sum(axis=0, keepdims=True))   # косинус с нормированной суммой == среднее косинусов по вариантам запроса
    ad = cfg.get("adapter", {})
    if ad.get("enabled"):
        z = np.load(prepared / "adapter.npz")
        if ad["center"]:
            x = x - z["mu_q"]
            if ad.get("white"):
                x = x @ z["W"]
            x = _norm(x)
        if ad["mode"] in ("ridge", "query", "shared"):
            x = _norm(x + x @ z["A"])
    scores = emb @ x[0]
    ranked = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), i))
    return json.dumps([ids[i] for i in ranked[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
