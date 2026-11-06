#!/usr/bin/env python3
"""build r7-01: гибрид лексики и dense (как r4-01) + опциональные центрирование dense и признак кросс-энкодера; выбор по CV.

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — emb.npy (навыки: сырые или центрированные), mu_q.npy (средние запросов по двум видам, если центрирование),
          ids.json, config.json, fusion.json (метод, параметры, center, ce), report.json.

Обучение: записи `train_fit.jsonl` (train без семейств train_curve; происхождение и ADR-0004 — в README.md).
Четыре варианта сравниваются групповой CV по family на одних и тех же фолдах:
  raw      — слияние r4-01 (сырые косинусы bge-base);
  cen      — те же признаки, но dense-косинусы центрированы (вычитание среднего запросов и среднего каталога, приём r5-02);
  raw+ce / cen+ce — плюс логиты кросс-энкодера ms-marco-MiniLM-L6-v2 на кандидатах (топ-K dense + топ-K лексики).
Правило выбора (fit.choose): центрирование — если CV лучше не меньше чем на 0.003; кросс-энкодер — если CV лучше не меньше чем на 0.01.
Средние запросов/каталога и все веса считаются только по train_fit.jsonl и каталогу; ответов и таблиц запрос->навык в выход нет.
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

from enc import CrossEncoderNP, Encoder  # noqa: E402
import fit as fitmod  # noqa: E402
from fuse import CE_K, add_ce, cand_indices, make_features  # noqa: E402
from lex import Lexical  # noqa: E402

T0 = time.time()
CE_MODEL = "ms-marco-MiniLM-L6-v2"
CE_MAX_LEN = 256
CE_START_S, CE_STOP_S = 250, 400   # кросс-энкодер на обучающих запросах не начинается после CE_START_S и прекращается после CE_STOP_S (с от старта build)
CV_BUDGET_S = 450         # CV вариантов с кросс-энкодером не начинается позже
METHODS = ("wz", "lr")
PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


def ce_text(entry):
    return f'{entry["name"]}. {entry["description"]}'


def main() -> None:
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    p = json.loads((HERE / "params.json").read_text())
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    ids = [c["id"] for c in catalog]
    docs = [p["doc_prefix"] + p["doc_template"].format(name=c["name"], description=c["description"]) for c in catalog]
    model_dir = assets / "models" / p["model"]
    report = {"model": p["model"], "n_docs": len(docs)}

    t = time.time()
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(str(model_dir), device="cpu")
    D0 = st.encode(docs, normalize_embeddings=True, batch_size=32).astype(np.float32)
    report["reference_seconds"] = round(time.time() - t, 2)

    ok = False
    try:
        t = time.time()
        enc = Encoder(model_dir, p["pooling"], p["max_len"])
        queries = [pre + q for pre in p["query_prefixes"] for q in PROBES]
        qn = enc.encode(queries)
        qref = st.encode(queries, normalize_embeddings=True, batch_size=32)
        sample = list(range(0, len(docs), 12))
        dn = enc.encode([docs[i] for i in sample])
        cos_q, cos_d = (qn * qref).sum(1), (dn * D0[sample]).sum(1)
        report["min_cos_queries"] = float(cos_q.min())
        report["min_cos_docs_sample"] = float(cos_d.min())
        ok = bool(cos_q.min() > 0.999 and cos_d.min() > 0.999)
        report["numpy_check_seconds"] = round(time.time() - t, 2)
    except Exception as exc:
        report["numpy_error"] = repr(exc)
    report["numpy_encoder_ok"] = ok
    (out / "ids.json").write_text(json.dumps(ids))
    (out / "config.json").write_text(json.dumps({**p, "numpy_encoder_ok": ok}))

    # запасной вариант на случай сбоя обучения: сырой dense + лексика с равным весом (как r4-01)
    fusion = {"method": "wz", "params": {"w": 0.5}, "center": False, "ce": {"enabled": False}}
    emb_out, mu_out = D0, None
    try:
        t = time.time()
        recs = [json.loads(line) for line in (HERE / "train_fit.jsonl").open(encoding="utf-8") if line.strip()]
        texts = [r["input"] for r in recs]
        rels = [set(r["gold"]) for r in recs]
        groups = [r["family"] for r in recs]
        styles = [r["style"] for r in recs]
        V = [st.encode([pre + q for q in texts], normalize_embeddings=True, batch_size=64).astype(np.float32)
             for pre in p["query_prefixes"]]
        report["train_encode_seconds"] = round(time.time() - t, 2)

        # dense-признаки: сырые и центрированные (средние запросов по виду запроса, среднее каталога)
        mu_q = np.stack([v.mean(0) for v in V]).astype(np.float32)             # (2, d)
        mu_d = D0.mean(0, keepdims=True)
        Dc = norm(D0 - mu_d).astype(np.float32)
        dense = {"raw": [(v @ D0.T).tolist() for v in V],
                 "cen": [(norm(v - mu_q[k]) @ Dc.T).tolist() for k, v in enumerate(V)]}
        lexical = Lexical(catalog)
        lexf = [lexical.features(q) for q in texts]
        Fs = {key: [make_features(d[0][k], d[1][k], lexf[k][0], lexf[k][1], texts[k]) for k in range(len(recs))]
              for key, d in dense.items()}
        report["features_seconds"] = round(time.time() - t, 2)
        report["n_queries"], report["n_families"] = len(recs), len(set(groups))

        # ---- кросс-энкодер: оценки для кандидатов обоих вариантов ----
        cv_ce, ce_ok, ce_np_ok = {}, False, False
        ce_cache = {}
        try:
            if time.time() - T0 < CE_START_S:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                torch.set_num_threads(2)
                cdir = assets / "models" / CE_MODEL
                tok, net = AutoTokenizer.from_pretrained(cdir), AutoModelForSequenceClassification.from_pretrained(cdir).eval()

                def ce_torch(query, ds):
                    batch = tok([query] * len(ds), ds, padding=True, truncation=True, max_length=CE_MAX_LEN, return_tensors="pt")
                    with torch.inference_mode():
                        return [float(x) for x in net(**batch).logits[:, 0]]

                dtexts = [ce_text(c) for c in catalog]
                # эквивалентность numpy-реализации (её использует solve)
                try:
                    cenp = CrossEncoderNP(assets / "models" / CE_MODEL, CE_MAX_LEN)
                    diffs = []
                    for q in PROBES:
                        sub = list(range(0, len(dtexts), 31))
                        a = ce_torch(q, [dtexts[i] for i in sub])
                        b = cenp.scores(q, [dtexts[i] for i in sub])
                        diffs.append(max(abs(x - y) for x, y in zip(a, b)))
                    report["ce_numpy_max_abs_diff"] = float(max(diffs))
                    ce_np_ok = bool(max(diffs) < 2e-3)
                except Exception as exc:
                    report["ce_numpy_error"] = repr(exc)
                report["ce_numpy_ok"] = ce_np_ok

                t = time.time()
                complete = True
                for k in range(len(recs)):
                    need = sorted(set(cand_indices(Fs["raw"][k])) | set(cand_indices(Fs["cen"][k])))
                    for s in range(0, len(need), 32):
                        part = need[s: s + 32]
                        for j, v in zip(part, ce_torch(texts[k], [dtexts[j] for j in part])):
                            ce_cache[(k, j)] = v
                    if time.time() - T0 > CE_STOP_S:
                        complete = False
                        report["ce_aborted_at_query"] = k
                        break
                report["ce_pairs"], report["ce_seconds"] = len(ce_cache), round(time.time() - t, 2)
                ce_ok = complete
        except Exception:
            report["ce_error"] = traceback.format_exc()[-1500:]

        # ---- CV без кросс-энкодера ----
        reps, pers = {}, {}
        for key in ("raw", "cen"):
            reps[key], pers[key] = fitmod.run_variant(Fs[key], rels, ids, groups, styles, METHODS)
        report["variants"] = {k: reps[k] for k in reps}
        report["cv_seconds_no_ce"] = round(time.time() - T0, 2)

        Fce = {}
        if ce_ok:
            for key in ("raw", "cen"):
                if time.time() - T0 > CV_BUDGET_S:
                    report["ce_cv_skipped"] = key
                    continue
                rows = []
                for k, F in enumerate(Fs[key]):
                    cand = cand_indices(F)
                    rows.append(add_ce(dict(F), cand, [ce_cache[(k, j)] for j in cand]))
                Fce[key] = rows
                reps[key + "+ce"], pers[key + "+ce"] = fitmod.run_variant(rows, rels, ids, groups, styles, ("lrce",))
                cv_ce[key] = reps[key + "+ce"]["cv"]
            report["variants"] = {k: reps[k] for k in reps}
        report["cv_seconds"] = round(time.time() - T0, 2)

        # ---- парные сравнения вариантов по запросам (CV вне фолда) ----
        def pair(xa, xb):
            return {"better": sum(x > y + 1e-9 for x, y in zip(xa, xb)), "worse": sum(x < y - 1e-9 for x, y in zip(xa, xb))}
        report["paired"] = {"cen_lr_vs_raw_lr": pair(pers["cen"]["lr"], pers["raw"]["lr"])}
        for key in ("raw", "cen"):
            if key + "+ce" in pers:
                report["paired"][key + "+ce_vs_" + key + "_lr"] = pair(pers[key + "+ce"]["lrce"], pers[key]["lr"])

        # ---- выбор и финальная подгонка на всех записях ----
        choice = fitmod.choose(reps["raw"]["cv"], reps["cen"]["cv"], cv_ce)
        report["choice"] = choice
        key = "cen" if choice["center"] else "raw"
        Fsel = Fce[key] if choice["ce"] else Fs[key]
        params = fitmod.fit(choice["method"], Fsel, rels, ids)
        report["in_sample_selected"] = fitmod.evaluate(choice["method"], params, Fsel, rels, ids)
        fusion = {"method": choice["method"], "params": params, "center": choice["center"],
                  "ce": {"enabled": choice["ce"], "k": CE_K, "model": CE_MODEL, "max_len": CE_MAX_LEN, "numpy_ok": ce_np_ok}}
        if choice["center"]:
            emb_out, mu_out = Dc, mu_q
        report["fit_seconds"] = round(time.time() - T0, 2)
    except Exception:
        report["fit_error"] = traceback.format_exc()[-3000:]
    np.save(out / "emb.npy", np.asarray(emb_out, dtype=np.float32))
    if mu_out is not None:
        np.save(out / "mu_q.npy", mu_out.astype(np.float32))
    (out / "fusion.json").write_text(json.dumps(fusion))
    report["fusion_final"] = {k: v for k, v in fusion.items() if k != "params"}
    report["total_seconds"] = round(time.time() - T0, 2)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
