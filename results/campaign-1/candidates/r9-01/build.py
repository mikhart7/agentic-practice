#!/usr/bin/env python3
"""build r9-01: ансамбль энкодеров с центрированием + лексика (база r8-01) и два новых рычага против узкого места (indirect):
  (А) граф близких навыков каталога: псевдо-релевантная обратная связь (Rocchio), сглаживание по соседям, поправка на хабы;
  (Б) GBDT-ранжировщик (LightGBM lambdarank / бинарная классификация) поверх навык-независимых признаков пары (запрос, навык).
Метод и параметры выбираются групповой 5-fold CV по семействам на fit.jsonl (556 записей train без семейств train_curve).

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — ids.json, config.json, mu_q.npz, emb_<модель>.npy, graph.npz, fusion.json, [gbdt.json], report.json, diag.npz (диагностика).
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
import rank  # noqa: E402
from enc import Encoder  # noqa: E402
from lex import Lexical  # noqa: E402

T0 = time.time()
MODEL_BUDGET_S = 330      # новая модель не начинается после этого момента
FOLDS = 5
TIE_TOL = 0.002           # ансамбль: в пределах этого от лучшей CV берётся конфигурация с меньшим числом моделей
NEW_TIE = 0.002           # среди новых методов в пределах этого от лучшего берётся более простой
NEW_METHODS = ("csls", "prf", "sm", "prfsm", "gbdt")      # от простого к сложному
GBDT_GRID = [{"obj": obj, "leaves": lv, "rounds": nr} for obj in ("lambdarank", "binary") for lv in (4, 8) for nr in (80, 200)]
PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def pair(a, b):
    return {"better": int((a > b + 1e-9).sum()), "worse": int((a < b - 1e-9).sum())}


def by_style(per, styles):
    return {s: round(float(per[styles == s].mean()), 4) for s in sorted(set(styles.tolist()))}


# ------------------------------------------------------------------ GBDT
def gbdt_params(cfg):
    p = {"objective": cfg["obj"], "learning_rate": 0.05, "num_leaves": cfg["leaves"], "min_data_in_leaf": 20,
         "feature_fraction": 0.7, "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 5.0, "max_bin": 63,
         "num_threads": 2, "verbosity": -1, "seed": 0, "deterministic": True, "force_row_wise": True}
    if cfg["obj"] == "lambdarank":
        p.update({"metric": "ndcg", "eval_at": [3], "lambdarank_truncation_level": 10})
    return p


def gbdt_fit(lgb, Xc, Yc, cfg):
    """Xc (n, C, f), Yc (n, C) bool. Запросы без релевантного навыка среди кандидатов не обучают."""
    keep = Yc.any(axis=1)
    X, Y = Xc[keep], Yc[keep].astype(int)
    n, C, f = X.shape
    ds = lgb.Dataset(X.reshape(n * C, f), label=Y.reshape(-1), group=[C] * n, free_raw_data=False)
    return lgb.train(gbdt_params(cfg), ds, num_boost_round=cfg["rounds"])


def gbdt_cv(lgb, Xc, cand, Rel, folds, cfg, N):
    n, C, _ = Xc.shape
    Yc = np.take_along_axis(Rel, cand, axis=1)
    out, acc = np.zeros(n), np.zeros(n)
    for f in sorted(set(folds.tolist())):
        tr, va = np.where(folds != f)[0], np.where(folds == f)[0]
        booster = gbdt_fit(lgb, Xc[tr], Yc[tr], cfg)
        s = booster.predict(Xc[va].reshape(len(va) * C, -1), raw_score=True).reshape(len(va), C)
        full = np.full((len(va), N), -1e9)
        np.put_along_axis(full, cand[va], s, axis=1)
        out[va], acc[va] = hyb.case_metric(full, Rel[va])
    return out, acc


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
    Rel = np.zeros((len(fit), len(ids)), bool)
    for r, g in enumerate(set(r_["relevant"]) for r_ in fit):
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

    # ---- ансамбль: z-слияние, веса {0,1,2}, выбор по метрике на 556 записях (как r6-01/r8-01) ----
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
    report["ensemble_chosen"] = {"weights": weights, "cv": round(ens["cv"], 4), "acc1": round(ens["acc1"], 4)}
    sel_names = [n for n, w in zip(names, weights) if w]
    sel_w = [w for w in weights if w]
    report["cv_seconds_dense"] = round(time.time() - T0, 2)

    # ---- лексика, граф навыков, признаки ----
    fusion = {"method": "ens", "params": {}}
    graph_G = None
    gbdt_dump = None
    try:
        queries = [r["input"] for r in fit]
        lexical = Lexical(catalog)
        feats = [lexical.features(q) for q in queries]
        bm = np.array([f[0] for f in feats], dtype=np.float64)
        tri = np.array([f[1] for f in feats], dtype=np.float64)
        length = hyb.length_feature(queries)
        zsel = {n: zs[n] for n in sel_names}
        F = hyb.features(zsel, sel_names, sel_w, bm, tri, length)
        base = rank.base_score(F)
        N = len(ids)

        graph_G = rank.build_graph(Dn, sel_names, sel_w)
        aux = rank.graph_from_G(graph_G)
        hub = rank.hub_stat(F["zens"]).astype(np.float32).astype(np.float64)
        aux["hub"] = hub
        report["graph"] = {"mean_top5_sim": round(float(np.sort(aux["G"] - 2 * np.eye(N), axis=1)[:, -5:].mean()), 4)}

        # диагностика (не читается solve): оценки моделей/лексики на запросах fit и метки, чтобы анализировать ошибки CV вне build
        np.savez_compressed(out / "diag.npz", **{"z_" + n: zs[n].astype(np.float32) for n in names}, bm=bm.astype(np.float32),
                            tri=tri.astype(np.float32), rel=Rel, folds=folds, styles=styles, families=np.array([r["family"] for r in fit]),
                            G=aux["G"].astype(np.float32), hub=hub.astype(np.float32))

        per, accs, chosen, cv = {}, {}, {}, {}
        for m in ("ens", "wz"):
            per[m], accs[m] = hyb.cross_validate(m, F, Rel, folds, sel_names, sel_w)
        per["base01"], accs["base01"] = hyb.case_metric(base, Rel)          # w=0.1 без подбора (справка)
        for m in ("csls", "prf", "sm", "prfsm"):
            per[m], accs[m], chosen[m] = rank.cv_graph(m, base, Rel, folds, aux)
        report["cv_seconds_graph"] = round(time.time() - T0, 2)

        # ---- GBDT ----
        gbdt_ok = False
        try:
            try:
                import lightgbm as lgb
            except Exception as exc:
                report["lightgbm_import_error"] = repr(exc)
                raise
            X, labels = rank.pair_features(F, zsel, sel_names, aux, bm, length)
            cand = rank.candidates(base)
            Xc = rank.gather(X, cand)
            report["gbdt_features"] = labels
            report["cand_recall"] = round(float(np.take_along_axis(Rel, cand, axis=1).any(axis=1).mean() / max(Rel.any(axis=1).mean(), 1e-9)), 4)
            grid_cv = []
            for cfg in GBDT_GRID:
                o, a = gbdt_cv(lgb, Xc, cand, Rel, folds, cfg, N)
                grid_cv.append({**cfg, "cv": round(float(o.mean()), 4), "acc1": round(float(a.mean()), 4)})
                if "gbdt" not in per or o.mean() > per["gbdt"].mean():
                    per["gbdt"], accs["gbdt"], chosen["gbdt"] = o, a, cfg
            report["gbdt_grid"] = grid_cv
            report["cv_seconds_gbdt"] = round(time.time() - T0, 2)
            # финальная модель на всех 556 запросах и сверка numpy-оценки деревьев с LightGBM
            cfg = chosen["gbdt"]
            Yc = np.take_along_axis(Rel, cand, axis=1)
            booster = gbdt_fit(lgb, Xc, Yc, cfg)
            trees = rank.export_trees(booster)
            ref = booster.predict(Xc.reshape(len(Xc) * Xc.shape[1], -1), raw_score=True)
            mine = rank.predict_trees(trees, Xc.reshape(len(Xc) * Xc.shape[1], -1))
            report["gbdt_numpy_maxdiff"] = float(np.abs(ref - mine).max())
            gbdt_ok = bool(report["gbdt_numpy_maxdiff"] < 1e-6)
            imp = booster.feature_importance(importance_type="gain")
            report["gbdt_importance_top"] = [[labels[i], round(float(imp[i]), 1)] for i in np.argsort(-imp)[:15]]
            gbdt_dump = {"trees": trees, "cand": rank.CAND, "features": labels}
            report["in_sample_gbdt"] = round(float(hyb.case_metric(rank.gbdt_scores(trees, Xc, cand, N), Rel)[0].mean()), 4)
        except Exception:
            report["gbdt_error"] = traceback.format_exc()[-3000:]
            per.pop("gbdt", None)
            gbdt_ok = False

        for m in per:
            cv[m] = float(per[m].mean())
        report["cv"] = {m: round(v, 4) for m, v in cv.items()}
        report["acc1_cv"] = {m: round(float(accs[m].mean()), 4) for m in per}
        report["cv_by_style"] = {m: by_style(per[m], styles) for m in per}
        report["acc1_by_style"] = {m: by_style(accs[m], styles) for m in per}
        report["paired_vs_wz"] = {m: pair(per[m], per["wz"]) for m in per if m != "wz"}
        report["cv_chosen_params"] = {m: chosen[m] for m in chosen}

        # ---- выбор: лучший из НОВЫХ методов (в пределах NEW_TIE берётся более простой); сравнение с wz - в отчёте ----
        avail = [m for m in NEW_METHODS if m in cv and (m != "gbdt" or gbdt_ok)]
        best_new = max(cv[m] for m in avail)
        pick = next(m for m in avail if cv[m] >= best_new - NEW_TIE)
        if pick == "gbdt":
            fusion = {"method": "gbdt", "params": {"cfg": chosen["gbdt"]}}
        else:
            fusion = {"method": pick, "params": rank.fit_graph(pick, base, Rel, aux)}
        report["choice"] = {"picked": pick, "cv_picked": round(cv[pick], 4), "cv_wz": round(cv["wz"], 4), "cv_ens": round(cv["ens"], 4)}
    except Exception:
        report["new_stage_error"] = traceback.format_exc()[-3000:]
        fusion = {"method": "wz", "params": {"w": rank.W_LEX}}
        graph_G = None
        gbdt_dump = None

    # ---- выход: только выбранные модели ----
    final_specs = []
    for b, w in zip(usable, weights):
        if w:
            n = b["spec"]["name"]
            np.save(out / f"emb_{n}.npy", Dn[n])
            final_specs.append(b["spec"])
    np.savez(out / "mu_q.npz", **{n: mus[n] for n in sel_names})
    if graph_G is not None:
        np.savez(out / "graph.npz", G=graph_G, hub=hub.astype(np.float32))
    if gbdt_dump is not None and fusion["method"] == "gbdt":
        (out / "gbdt.json").write_text(json.dumps(gbdt_dump))
    (out / "ids.json").write_text(json.dumps(ids))
    (out / "config.json").write_text(json.dumps({"models": final_specs, "weights": sel_w}))
    (out / "fusion.json").write_text(json.dumps(fusion))
    report["fusion_final"] = {"method": fusion["method"], "params": fusion["params"], "models": sel_names, "weights": sel_w}
    report["total_seconds"] = round(time.time() - T0, 2)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
