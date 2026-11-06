#!/usr/bin/env python3
"""solve r7-01: слияние лексики r1-03 и dense bge-base (r4-01) с опциональным центрированием dense и кросс-энкодером.

Параметры (метод слияния, center, ce) пишет только build в /assets/prepared/fusion.json.

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fuse import add_ce, cand_indices, make_features, score, top3  # noqa: E402
from lex import Lexical  # noqa: E402


def encode_queries(texts: list, cfg: dict, model_dir: Path):
    if cfg.get("numpy_encoder_ok"):
        try:
            from enc import Encoder
            return Encoder(model_dir, cfg["pooling"], cfg["max_len"]).encode(texts)
        except Exception as exc:
            print(f"numpy encoder failed, fallback: {exc!r}", file=sys.stderr)
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(str(model_dir), device="cpu").encode(texts, normalize_embeddings=True)


def ce_scores(query: str, docs: list, ce: dict, models: Path):
    model_dir = models / ce["model"]
    if ce.get("numpy_ok"):
        try:
            from enc import CrossEncoderNP
            return CrossEncoderNP(model_dir, ce["max_len"]).scores(query, docs)
        except Exception as exc:
            print(f"numpy cross-encoder failed, fallback: {exc!r}", file=sys.stderr)
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    torch.set_num_threads(2)
    tok, net = AutoTokenizer.from_pretrained(model_dir), AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
    batch = tok([query] * len(docs), docs, padding=True, truncation=True, max_length=ce["max_len"], return_tensors="pt")
    with torch.inference_mode():
        return [float(x) for x in net(**batch).logits[:, 0]]


def solve(task: dict) -> str:
    import numpy as np
    assets = Path(task["assets_dir"])
    prepared = assets / "prepared"
    cfg = json.loads((prepared / "config.json").read_text())
    ids = json.loads((prepared / "ids.json").read_text())
    fusion = json.loads((prepared / "fusion.json").read_text())
    emb = np.load(prepared / "emb.npy")
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    query = task["input"]
    q = encode_queries([pre + query for pre in cfg["query_prefixes"]], cfg, assets / "models" / cfg["model"])
    if fusion.get("center"):   # emb.npy уже центрирован и нормирован в build
        q = q - np.load(prepared / "mu_q.npy")
        q = q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-12)
    d1, d2 = (emb @ q[0]).tolist(), (emb @ q[1]).tolist()
    bm, tri = Lexical(catalog).features(query)
    F = make_features(d1, d2, bm, tri, query)
    ce = fusion.get("ce", {})
    if ce.get("enabled"):
        cand = cand_indices(F, ce["k"])
        docs = [f'{catalog[i]["name"]}. {catalog[i]["description"]}' for i in cand]
        add_ce(F, cand, ce_scores(query, docs, ce, assets / "models"))
    return json.dumps([ids[i] for i in top3(score(fusion["method"], fusion["params"], F))])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
