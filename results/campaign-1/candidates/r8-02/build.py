#!/usr/bin/env python3
"""build r8-02: ансамбль энкодеров с центрированием (r6-01) + лексика r1-03 поверх него; слияние выбирается групповой CV по family.

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — ids.json, config.json, mu_q.npz, emb_<модель>.npy (модели с весом > 0), fusion.json, report.json.

Обучающие данные: fit.jsonl рядом с build.py (556 записей train вне семейств train_curve; см. README). Обучаются: средние запросов
каждой модели, веса ансамбля (дискретные) и параметры слияния с лексикой. Выбор — 5-fold CV по семействам (одно семейство = один навык,
отложенное семейство = ещё не виденный навык), метрика кейса по ранжированию всех 189 навыков.
"""
import gc
import itertools
import json
import math
import os
import random
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import hyb  # noqa: E402
from enc import Encoder  # noqa: E402
from lex import Lexical  # noqa: E402

T0 = time.time()
MODEL_BUDGET_S = 330      # новая модель не начинается после этого момента
FOLDS = 5
TIE_TOL = 0.002           # ансамбль: в пределах этого от лучшей CV берётся конфигурация с меньшим числом моделей
LEX_GAIN = 0.004          # лексика включается, только если лучший метод с ней лучше ансамбля без неё не меньше чем на это
LEX_TIE = 0.003           # среди методов с лексикой в пределах этого от лучшего берётся более простой
METHODS = ("wz", "wz2", "wzk", "wzc", "wzkc", "lr", "lrm", "lrg")      # от простого к сложному
PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def pair(a, b):
    return {"better": int((a > b + 1e-9).sum()), "worse": int((a < b - 1e-9).sum())}


def by_style(per, styles):
    return {s: round(float(per[styles == s].mean()), 4) for s in sorted(set(styles.tolist()))}


def main() -> None:
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    params = json.loads((HERE / "params.json").read_text())
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    ids = [c["id"] for c in catalog]
    idx = {c: i for i, c in enumerate(ids)}
    fit = [json.loads(line) for line in (HERE / "fit.jsonl").open(encoding="utf-8") if line.strip()]
    report = {"n_docs": len(catalog), "n_fit": len(fit), "models": {}}

    import torch
    torch.set_num_threads(2)
    from sentence_transformers import SentenceTransformer

    # ---- эмбеддинги каждой моделью (sentence-transformers как эталон) + проверка numpy-энкодера, который использует solve ----
    built = []
    for spec in params["models"]:
        name = spec["name"]
        rep = report["models"].setdefault(name, {})
        if built and time.time() - T0 > MODEL_BUDGET_S:
            rep["skipped"] = "time budget"
            continue
        try:
            t1 = time.time()
            model_dir = assets / "models" / name
            docs = [spec["doc_prefix"] + spec["doc_template"].format(name=c["name"], description=c["description"]) for c in catalog]
            st = SentenceTransformer(str(model_dir), device="cpu")
            D = st.encode(docs, normalize_embeddings=True, batch_size=32).astype(np.float32)
            enc_q = [st.encode([pre + r["input"] for r in fit], normalize_embeddings=True, batch_size=32).astype(np.float32)
                     for pre in spec["query_prefixes"]]
            X = hyb.norm(sum(enc_q)).astype(np.float32)
            rep["st_seconds"] = round(time.time() - t1, 2)
            ok = False
            try:
                enc = Encoder(model_dir, spec["pooling"], spec["max_len"])
                queries = [pre + q for pre in spec["query_prefixes"] for q in PROBES]
                qn, qref = enc.encode(queries), st.encode(queries, normalize_embeddings=True, batch_size=32)
                sample = list(range(0, len(docs), 24))
                cos_q = (qn * qref).sum(1)
                cos_d = (enc.encode([docs[i] for i in sample]) * D[sample]).sum(1)
                rep["min_cos_queries"], rep["min_cos_docs_sample"] = float(cos_q.min()), float(cos_d.min())
                ok = bool(cos_q.min() > 0.999 and cos_d.min() > 0.999)
                del enc
            except Exception as exc:
                rep["numpy_error"] = repr(exc)
            rep["numpy_encoder_ok"] = ok
            rep["done_seconds"] = round(time.time() - T0, 2)
            del st
            gc.collect()
            built.append({"spec": {**spec, "numpy_encoder_ok": ok}, "D": D, "X": X, "ok": ok})
        except Exception as exc:
            rep["error"] = repr(exc)
    usable = [b for b in built if b["ok"]]
    if not usable:
        raise SystemExit("no usable encoder")
    names = [b["spec"]["name"] for b in usable]
    report["usable_models"] = names

    # ---- центрирование и z-оценки каждой модели (средний запрос по всем 556 записям: безметочная статистика) ----
    gold = [set(r["relevant"]) for r in fit]
    Rel = np.zeros((len(fit), len(ids)), bool)
    for r, g in enumerate(gold):
        for s in g:
            Rel[r, idx[s]] = True
    fams = sorted({r["family"] for r in fit})
    random.Random(0).shuffle(fams)
    fold_of = {f: i % FOLDS for i, f in enumerate(fams)}
    folds = np.array([fold_of[r["family"]] for r in fit])
    styles = np.array([r["style"] for r in fit])
    report["n_families"] = len(fams)

    Dn, mus, zs = {}, {}, {}
    for b in usable:
        n = b["spec"]["name"]
        Dn[n] = hyb.norm(b["D"] - b["D"].mean(0, keepdims=True)).astype(np.float32)
        mus[n] = b["X"].mean(0, keepdims=True).astype(np.float32)
        zs[n] = hyb.zscore(hyb.norm(b["X"] - mus[n]) @ Dn[n].T)
    report["singles"] = {n: round(float(hyb.case_metric(zs[n], Rel)[0].mean()), 4) for n in names}

    # ---- ансамбль: z-слияние, веса {0,1,2} (как r6-01), выбор по метрике на 556 записях (обучаемых параметров нет, кроме mu_q) ----
    rows, seen = [], set()
    for ws in itertools.product((0, 1, 2), repeat=len(names)):
        if sum(1 for w in ws if w) < 2:
            continue
        g = 0
        for w in ws:
            g = math.gcd(g, w)
        ws = tuple(w // g for w in ws)
        if ws in seen:
            continue
        seen.add(ws)
        sc, acc = hyb.case_metric(hyb.ensemble(zs, names, ws), Rel)
        rows.append({"w": list(ws), "cv": float(sc.mean()), "acc1": float(acc.mean())})
    best = max(rows, key=lambda r: r["cv"])
    near = [r for r in rows if r["cv"] >= best["cv"] - TIE_TOL]
    ens = min(near, key=lambda r: (sum(1 for w in r["w"] if w), sum(r["w"])))
    weights = ens["w"]
    report["ensemble_table_top"] = [{"weights": r["w"], "cv": round(r["cv"], 4), "acc1": round(r["acc1"], 4)}
                                    for r in sorted(rows, key=lambda r: -r["cv"])[:12]]
    report["ensemble_chosen"] = {"weights": weights, "cv": round(ens["cv"], 4), "acc1": round(ens["acc1"], 4)}
    sel_names = [n for n, w in zip(names, weights) if w]
    sel_w = [w for w in weights if w]
    report["cv_seconds_dense"] = round(time.time() - T0, 2)

    # ---- лексика поверх ансамбля: CV по методам ----
    fusion = {"method": "ens", "params": {}}
    try:
        t = time.time()
        queries = [r["input"] for r in fit]
        lexical = Lexical(catalog)
        feats = [lexical.features(q) for q in queries]
        bm = np.array([f[0] for f in feats], dtype=np.float64)
        tri = np.array([f[1] for f in feats], dtype=np.float64)
        length = hyb.length_feature(queries)
        report["lex_seconds"] = round(time.time() - t, 2)
        F = hyb.features({n: zs[n] for n in sel_names}, sel_names, sel_w, bm, tri, length)
        # справка: запросы без единого общего слова с каталогом (BM25 = 0)
        no_overlap = bm.max(axis=1) <= 0
        report["no_lex_overlap"] = {"n": int(no_overlap.sum()),
                                    "by_style": {s: int((no_overlap & (styles == s)).sum()) for s in sorted(set(styles.tolist()))}}

        per, accs, cv = {}, {}, {}
        for m in ("ens",) + METHODS:
            per[m], accs[m] = hyb.cross_validate(m, F, Rel, folds, sel_names, sel_w)
            cv[m] = float(per[m].mean())
        report["cv"] = {m: round(v, 4) for m, v in cv.items()}
        report["acc1_cv"] = {m: round(float(accs[m].mean()), 4) for m in per}
        report["cv_by_style"] = {m: by_style(per[m], styles) for m in per}
        report["acc1_by_style"] = {m: by_style(accs[m], styles) for m in per}
        report["paired_vs_ens"] = {m: pair(per[m], per["ens"]) for m in METHODS}
        if no_overlap.any():
            report["no_overlap_acc1"] = {m: round(float(accs[m][no_overlap].mean()), 4) for m in per}
        report["cv_seconds"] = round(time.time() - T0, 2)

        # ---- выбор: лексика только при выигрыше >= LEX_GAIN; среди методов с лексикой - простейший в пределах LEX_TIE ----
        best_lex = max(cv[m] for m in METHODS)
        if best_lex >= cv["ens"] + LEX_GAIN:
            pick = next(m for m in METHODS if cv[m] >= best_lex - LEX_TIE)
            fusion = {"method": pick, "params": hyb.fit(pick, F, Rel, sel_names, sel_w)}
            report["in_sample_selected"] = round(float(hyb.case_metric(hyb.score(pick, fusion["params"], F), Rel)[0].mean()), 4)
        report["choice"] = {"method": fusion["method"], "cv_ens": round(cv["ens"], 4), "cv_best_lex": round(best_lex, 4)}
    except Exception:
        report["lex_error"] = traceback.format_exc()[-3000:]
        fusion = {"method": "ens", "params": {}}

    # ---- выход: только выбранные модели ----
    final_specs = []
    for b, w in zip(usable, weights):
        if w:
            n = b["spec"]["name"]
            np.save(out / f"emb_{n}.npy", Dn[n])
            final_specs.append(b["spec"])
    np.savez(out / "mu_q.npz", **{n: mus[n] for n in sel_names})
    (out / "ids.json").write_text(json.dumps(ids))
    (out / "config.json").write_text(json.dumps({"models": final_specs, "weights": sel_w}))
    (out / "fusion.json").write_text(json.dumps(fusion))
    report["fusion_final"] = {"method": fusion["method"], "models": sel_names, "weights": sel_w}
    report["total_seconds"] = round(time.time() - T0, 2)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
