#!/usr/bin/env python3
"""build: эмбеддинги каталога (один раз) выбранным bi-encoder + самопроверка numpy-энкодера против sentence-transformers.

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — emb.npy (N x D, L2-норма), ids.json, config.json (для solve), report.json (диагностика).
Если numpy-энкодер расходится с эталоном (sentence-transformers), в emb.npy пишутся эталонные векторы,
а solve получает numpy_encoder_ok=false и кодирует запрос через sentence-transformers (медленнее, но верно).
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
    enc = Encoder(model_dir, p["pooling"], p["max_len"])
    emb = enc.encode(docs)
    report["numpy_encode_seconds"] = round(time.time() - t, 2)
    queries = [p["query_prefix"] + q for q in PROBES]
    qemb = enc.encode(queries)

    ok = None
    try:
        t = time.time()
        from sentence_transformers import SentenceTransformer
        st = SentenceTransformer(str(model_dir), device="cpu")
        ref = st.encode(docs, normalize_embeddings=True, batch_size=32)
        qref = st.encode(queries, normalize_embeddings=True, batch_size=32)
        report["reference_seconds"] = round(time.time() - t, 2)
        cos_d, cos_q = (emb * ref).sum(1), (qemb * qref).sum(1)
        report["min_cos_docs"] = float(cos_d.min())
        report["min_cos_queries"] = float(cos_q.min())
        # ранжирование тестовых запросов должно совпасть
        report["probe_rank_equal"] = bool((np.argsort(-(qemb @ emb.T), 1)[:, :5] == np.argsort(-(qref @ ref.T), 1)[:, :5]).all())
        ok = bool(cos_d.min() > 0.999 and cos_q.min() > 0.999)
        if not ok:
            emb = ref
    except Exception as exc:  # без эталона оставляем numpy-энкодер, но фиксируем это
        report["reference_error"] = repr(exc)
    report["numpy_encoder_ok"] = ok if ok is not None else True

    np.save(out / "emb.npy", emb.astype(np.float32))
    (out / "ids.json").write_text(json.dumps([c["id"] for c in catalog]))
    (out / "config.json").write_text(json.dumps({**p, "numpy_encoder_ok": report["numpy_encoder_ok"]}))
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
