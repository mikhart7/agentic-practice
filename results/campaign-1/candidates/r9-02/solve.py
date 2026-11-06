#!/usr/bin/env python3
"""solve r9-02: ансамбль энкодеров (numpy, центрирование) + лексика r1-03 (вес зависит от уверенности лексики, метод gate) ; метод слияния выбрал build (fusion.json).

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
Читает: /assets/prepared (config.json, ids.json, fusion.json, emb_<модель>.npy, mu_q.npz), модели /assets/models/<имя>;
каталог /assets/catalog.jsonl только при методе с лексикой. fit.jsonl не читает.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import hyb  # noqa: E402

TOP = 3


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
    fusion = json.loads((prepared / "fusion.json").read_text())
    mu = np.load(prepared / "mu_q.npz")
    query = task["input"]
    names = [s["name"] for s in cfg["models"]]
    zs = {}
    for spec in cfg["models"]:
        name = spec["name"]
        q = encode_queries([prefix + query for prefix in spec["query_prefixes"]], spec, assets / "models" / name)
        x = hyb.norm(q.sum(axis=0, keepdims=True))        # нормированная сумма вариантов запроса == среднее косинусов
        x = hyb.norm(x - mu[name])                         # центрирование: вычитание среднего запросов train (обучено в build)
        zs[name] = hyb.zscore(x @ np.load(prepared / f"emb_{name}.npy").T)
    if fusion["method"] == "ens":
        scores = hyb.ensemble(zs, names, cfg["weights"])[0]
    else:
        from lex import Lexical
        catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
        bm, tri = Lexical(catalog).features(query)
        F = hyb.features(zs, names, cfg["weights"], np.array([bm]), np.array([tri]), hyb.length_feature([query]))
        scores = hyb.score(fusion["method"], fusion["params"], F)[0]
    return json.dumps([ids[i] for i in hyb.top3(scores)])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
