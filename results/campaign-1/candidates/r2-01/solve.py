#!/usr/bin/env python3
"""solve: кодирует только запрос, топ-3 по косинусу к эмбеддингам каталога из <assets_dir>/prepared.

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
Читает: /assets/prepared (emb.npy, ids.json, config.json) и модель /assets/models/<name>. Каталог не нужен.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

TOP = 3


def encode_query(text: str, cfg: dict, model_dir: Path):
    if cfg.get("numpy_encoder_ok"):
        try:
            from enc import Encoder
            return Encoder(model_dir, cfg["pooling"], cfg["max_len"]).encode([text])[0]
        except Exception as exc:
            print(f"numpy encoder failed, fallback: {exc!r}", file=sys.stderr)
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(model_dir), device="cpu").encode([text], normalize_embeddings=True)[0]


def solve(task: dict) -> str:
    assets = Path(task["assets_dir"])
    prepared = assets / "prepared"
    cfg = json.loads((prepared / "config.json").read_text())
    ids = json.loads((prepared / "ids.json").read_text())
    emb = np.load(prepared / "emb.npy")
    q = encode_query(cfg["query_prefix"] + task["input"], cfg, assets / "models" / cfg["model"])
    scores = emb @ q
    ranked = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), i))
    return json.dumps([ids[i] for i in ranked[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
