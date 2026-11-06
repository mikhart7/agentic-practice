#!/usr/bin/env python3
"""solve r4-02: слияние лексики r1-03 и трёх dense (bge-base, e5-small, MiniLM) параметрами из /assets/prepared/fusion.json.

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fuse import make_features, score, top3  # noqa: E402
from lex import Lexical  # noqa: E402


def encode_queries(texts: list, m: dict, model_dir: Path):
    if m.get("numpy_encoder_ok"):
        try:
            from enc import Encoder
            return Encoder(model_dir, m["pooling"], m["max_len"]).encode(texts)
        except Exception as exc:
            print(f"numpy encoder failed, fallback: {exc!r}", file=sys.stderr)
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(model_dir), device="cpu").encode(texts, normalize_embeddings=True)


def solve(task: dict) -> str:
    import numpy as np
    assets = Path(task["assets_dir"])
    prepared = assets / "prepared"
    cfg = json.loads((prepared / "config.json").read_text())
    ids = json.loads((prepared / "ids.json").read_text())
    fusion = json.loads((prepared / "fusion.json").read_text())
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    query = task["input"]
    dense = {}
    for m in cfg["models"]:
        emb = np.load(prepared / f"emb_{m['tag']}.npy")
        q = encode_queries([pre + query for pre in m["query_prefixes"]], m, assets / "models" / m["model"])
        dense[m["tag"]] = [(emb @ v).tolist() for v in q]
    bm, tri = Lexical(catalog).features(query)
    F = make_features(dense, bm, tri, query)
    return json.dumps([ids[i] for i in top3(score(fusion["method"], fusion["params"], F))])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
