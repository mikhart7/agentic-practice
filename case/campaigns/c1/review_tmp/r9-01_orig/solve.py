#!/usr/bin/env python3
"""solve r9-01: ансамбль энкодеров (numpy, центрирование) + лексика r1-03 + рычаги r9 (граф навыков / GBDT); метод выбрал build.

stdin  — {"input": "<запрос>", "assets_dir": "/assets"}
stdout — {"answer": "<JSON-массив до 3 id>"}
Читает: /assets/prepared (config.json, ids.json, fusion.json, emb_<модель>.npy, mu_q.npz, graph.npz, gbdt.json), модели /assets/models/<имя>,
каталог /assets/catalog.jsonl (лексика). fit.jsonl не читает; lightgbm не импортирует (деревья вычисляются в rank.py).
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import hyb  # noqa: E402
import rank  # noqa: E402


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
    method = fusion["method"]
    if method == "ens":
        scores = hyb.ensemble(zs, names, cfg["weights"])[0]
    else:
        from lex import Lexical
        catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
        bm, tri = Lexical(catalog).features(query)
        bm, tri = np.array([bm]), np.array([tri])
        length = hyb.length_feature([query])
        F = hyb.features(zs, names, cfg["weights"], bm, tri, length)
        if method in ("wz", "wz2", "lr", "lrm"):
            scores = hyb.score(method, fusion["params"], F)[0]
        else:
            g = np.load(prepared / "graph.npz")
            aux = rank.graph_from_G(g["G"])
            aux["hub"] = g["hub"].astype(np.float64)
            base = rank.base_score(F)
            if method == "gbdt":
                model = json.loads((prepared / "gbdt.json").read_text())
                X, _ = rank.pair_features(F, zs, names, aux, bm, length)
                cand = rank.candidates(base, model["cand"])
                scores = rank.gbdt_scores(model["trees"], rank.gather(X, cand), cand, len(ids))[0]
            else:
                scores = rank.post(method, fusion["params"], base, aux)[0]
    return json.dumps([ids[i] for i in hyb.top3(scores)])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
