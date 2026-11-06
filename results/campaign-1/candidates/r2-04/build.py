#!/usr/bin/env python3
"""build: эмбеддинги каталога (один раз) выбранным bi-encoder.

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — emb.npy (N x D, L2-норма), ids.json, config.json (для solve), report.json (диагностика).
Документы кодирует sentence-transformers (эталон). numpy-энкодер (его использует solve, чтобы не импортировать torch)
сверяется с эталоном на тестовых запросах и нескольких документах; при расхождении solve использует sentence-transformers.
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from enc import Encoder  # noqa: E402

PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def main() -> None:
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    p = json.loads((Path(__file__).resolve().parent / "params.json").read_text())
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    docs = [p["doc_prefix"] + p["doc_template"].format(name=c["name"], description=c["description"]) for c in catalog]
    model_dir = assets / "models" / p["model"]
    report = {"model": p["model"], "n_docs": len(docs)}

    t = time.time()
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(str(model_dir), device="cpu")
    emb = st.encode(docs, normalize_embeddings=True, batch_size=32).astype(np.float32)
    report["reference_seconds"] = round(time.time() - t, 2)

    ok = False
    try:
        t = time.time()
        t1 = time.time()
        enc = Encoder(model_dir, p["pooling"], p["max_len"])
        report["numpy_load_seconds"] = round(time.time() - t1, 3)
        t1 = time.time()
        enc.encode([p["query_prefixes"][0] + PROBES[0]])
        report["numpy_one_query_seconds"] = round(time.time() - t1, 3)
        queries = [pre + q for pre in p["query_prefixes"] for q in PROBES]
        qn = enc.encode(queries)
        qref = st.encode(queries, normalize_embeddings=True, batch_size=32)
        sample = list(range(0, len(docs), 12))
        dn = enc.encode([docs[i] for i in sample])
        cos_q, cos_d = (qn * qref).sum(1), (dn * emb[sample]).sum(1)
        report["min_cos_queries"] = float(cos_q.min())
        report["min_cos_docs_sample"] = float(cos_d.min())
        report["probe_rank_equal"] = bool((np.argsort(-(qn @ emb.T), 1)[:, :5] == np.argsort(-(qref @ emb.T), 1)[:, :5]).all())
        ok = bool(cos_q.min() > 0.999 and cos_d.min() > 0.999)
        report["numpy_check_seconds"] = round(time.time() - t, 2)
    except Exception as exc:
        report["numpy_error"] = repr(exc)
    report["numpy_encoder_ok"] = ok

    np.save(out / "emb.npy", emb)
    (out / "ids.json").write_text(json.dumps([c["id"] for c in catalog]))
    (out / "config.json").write_text(json.dumps({**p, "numpy_encoder_ok": ok}))
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
