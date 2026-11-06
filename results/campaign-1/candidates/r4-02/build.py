#!/usr/bin/env python3
"""build r4-02: эмбеддинги каталога тремя bi-encoder (bge-base, e5-small, MiniLM) + обучение слияния с лексикой на train.

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — emb_<tag>.npy, ids.json, config.json, fusion.json (метод и параметры слияния), report.json.

Обучение: записи `train_fit.jsonl` (train без семейств train_curve; происхождение и ADR-0004 — в README.md).
Dense-признаки обучающих запросов считает этот же build теми же моделями (sentence-transformers), лексические —
код lex.py (r1-03). Подбирается общий механизм слияния групповой кросс-валидацией по family.
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from enc import Encoder  # noqa: E402
import fit as fitmod  # noqa: E402
from fuse import make_features  # noqa: E402
from lex import Lexical  # noqa: E402

PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def main() -> None:
    t0 = time.time()
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    models = json.loads((HERE / "params.json").read_text())["models"]
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    ids = [c["id"] for c in catalog]
    (out / "ids.json").write_text(json.dumps(ids))
    recs = [json.loads(line) for line in (HERE / "train_fit.jsonl").open(encoding="utf-8") if line.strip()]
    texts = [r["input"] for r in recs]
    report = {"n_docs": len(catalog), "models": {}}
    cfg_models = []
    train_dense = {}  # tag -> список матриц косинусов (по видам запроса) для обучающих запросов, списки Python

    from sentence_transformers import SentenceTransformer
    for m in models:
        rep = report["models"][m["tag"]] = {"model": m["model"]}
        model_dir = assets / "models" / m["model"]
        docs = [m["doc_prefix"] + m["doc_template"].format(name=c["name"], description=c["description"]) for c in catalog]
        t = time.time()
        st = SentenceTransformer(str(model_dir), device="cpu")
        emb = st.encode(docs, normalize_embeddings=True, batch_size=32).astype(np.float32)
        rep["doc_seconds"] = round(time.time() - t, 2)
        ok = False
        try:
            t = time.time()
            enc = Encoder(model_dir, m["pooling"], m["max_len"])
            queries = [pre + q for pre in m["query_prefixes"] for q in PROBES]
            qn = enc.encode(queries)
            qref = st.encode(queries, normalize_embeddings=True, batch_size=32)
            sample = list(range(0, len(docs), 12))
            dn = enc.encode([docs[i] for i in sample])
            cos_q, cos_d = (qn * qref).sum(1), (dn * emb[sample]).sum(1)
            rep["min_cos_queries"] = float(cos_q.min())
            rep["min_cos_docs_sample"] = float(cos_d.min())
            ok = bool(cos_q.min() > 0.999 and cos_d.min() > 0.999)
            rep["numpy_check_seconds"] = round(time.time() - t, 2)
        except Exception as exc:
            rep["numpy_error"] = repr(exc)
        rep["numpy_encoder_ok"] = ok
        np.save(out / f"emb_{m['tag']}.npy", emb)
        cfg_models.append({**m, "numpy_encoder_ok": ok})
        t = time.time()
        train_dense[m["tag"]] = [
            (st.encode([pre + q for q in texts], normalize_embeddings=True, batch_size=64).astype(np.float32) @ emb.T).tolist()
            for pre in m["query_prefixes"]]
        rep["train_encode_seconds"] = round(time.time() - t, 2)
        del st
    (out / "config.json").write_text(json.dumps({"models": cfg_models}))

    # --- обучение слияния на train (вне семейств train_curve) ---
    fusion = {"method": "wz", "params": {"w": 0.5}}  # запасной вариант, если обучение упадёт
    try:
        t = time.time()
        lexical = Lexical(catalog)
        Fs = []
        for k, r in enumerate(recs):
            bm, tri = lexical.features(r["input"])
            dense = {tag: [mat[k] for mat in mats] for tag, mats in train_dense.items()}
            Fs.append(make_features(dense, bm, tri, r["input"]))
        report["features_seconds"] = round(time.time() - t, 2)
        rels = [set(r["gold"]) for r in recs]
        groups = [r["family"] for r in recs]
        method, params, fr = fitmod.select(Fs, rels, ids, groups)
        fusion = {"method": method, "params": params}
        report["fusion"] = fr
        report["fit_seconds"] = round(time.time() - t, 2)
    except Exception:
        report["fit_error"] = traceback.format_exc()[-3000:]
    (out / "fusion.json").write_text(json.dumps(fusion))
    report["total_seconds"] = round(time.time() - t0, 2)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
