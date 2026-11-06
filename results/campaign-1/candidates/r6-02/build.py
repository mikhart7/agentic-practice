#!/usr/bin/env python3
"""build: эмбеддинги каталога и обучающих запросов четырьмя энкодерами, центрирование, выбор слияния групповой CV по family.

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — ids.json, config.json, mu_q.npz, emb_<модель>.npy (только модели с весом > 0), report.json.

Обучающие данные: fit.jsonl рядом с build.py (556 записей train вне семейств train_curve; см. README). Обучаются: средний вектор запросов
каждой модели (центрирование) и выбор режима/весов слияния. Выбор — 5-fold CV по семействам (у каждого навыка в train одно семейство =>
отложенное семейство = отложенный навык), метрика кейса 0.7*acc@1 + 0.3*nP@3 по ранжированию всех 189 навыков.
"""
import gc
import itertools
import json
import math
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from enc import Encoder  # noqa: E402
from fusion import fuse  # noqa: E402

T0 = time.time()
MODEL_BUDGET_S = 330      # новая модель не начинается после этого момента (остальные помечаются в report как пропущенные)
FOLDS = 5
TIE_TOL = 0.002           # в пределах этого от лучшей CV выбирается конфигурация с меньшим числом моделей
RRF_K = (10, 60)
TAUS = (0.4, 0.7, 1.0, 1.5)   # температура log-softmax над z-оценками (режим zlsm)
SELECT_MODE = "zlsm"          # выбор среди этого режима; z и rrf считаются для справки (report)
PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)


def case_scores(S, gold_sets, ids):
    """S: (n, 189). Метрика кейса по запросам: 0.7*acc@1 + 0.3*nP@3 (nP@3 = |top3 ∩ rel| / min(3, |rel|))."""
    top = np.argsort(-S, axis=1, kind="stable")[:, :3]
    acc = np.zeros(len(S))
    np3 = np.zeros(len(S))
    for r, rel in enumerate(gold_sets):
        t = [ids[j] for j in top[r]]
        acc[r] = float(t[0] in rel)
        np3[r] = len(set(t) & rel) / min(3, len(rel))
    return 0.7 * acc + 0.3 * np3, acc


def gcd_all(ws):
    g = 0
    for w in ws:
        g = math.gcd(g, w)
    return g


def enumerate_configs(n):
    """Только слияния >= 2 моделей (одиночные модели идут в report как справка)."""
    out, seen = [], set()
    for ws in itertools.product((0, 1, 2), repeat=n):
        if sum(1 for w in ws if w) < 2:
            continue
        g = gcd_all(ws)
        ws = tuple(w // g for w in ws)
        if ws in seen:
            continue
        seen.add(ws)
        out.append({"mode": "z", "k": 0, "weights": list(ws)})
        for tau in TAUS:
            out.append({"mode": "zlsm", "k": 0, "tau": tau, "weights": list(ws)})
    for ws in itertools.product((0, 1), repeat=n):
        if sum(ws) < 2:
            continue
        for k in RRF_K:
            out.append({"mode": "rrf", "k": k, "weights": list(ws)})
    return out


def complexity(cfg):
    return (sum(1 for w in cfg["weights"] if w), sum(cfg["weights"]), cfg.get("tau", 0), cfg["k"])


def label(cfg, names):
    w = "+".join(f"{w}*{n}" for n, w in zip(names, cfg["weights"]) if w)
    par = {"z": "", "zlsm": f"{cfg.get('tau')}", "rrf": f"{cfg['k']}"}[cfg["mode"]]
    return f"{cfg['mode']}{par}:{w}"


def main() -> None:
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    params = json.loads((here / "params.json").read_text())
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    ids = [c["id"] for c in catalog]
    idx = {c: i for i, c in enumerate(ids)}
    fit = [json.loads(line) for line in (here / "fit.jsonl").open(encoding="utf-8") if line.strip()]
    report = {"n_docs": len(catalog), "n_fit": len(fit), "models": {}}

    import torch
    torch.set_num_threads(2)
    from sentence_transformers import SentenceTransformer

    # ---- эмбеддинги каждой моделью (sentence-transformers как эталон) + проверка numpy-энкодера, который использует solve ----
    built = []     # {"spec", "D" (n_docs, d), "X" (n_fit, d)}
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
            X = norm(sum(enc_q)).astype(np.float32)
            rep["st_seconds"] = round(time.time() - t1, 2)
            ok = False
            try:
                t2 = time.time()
                enc = Encoder(model_dir, spec["pooling"], spec["max_len"])
                rep["numpy_load_seconds"] = round(time.time() - t2, 3)
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
        except Exception as exc:       # модель не обязана собраться: ансамбль строится из тех, что собрались
            rep["error"] = repr(exc)
    usable = [b for b in built if b["ok"]]
    names = [b["spec"]["name"] for b in usable]
    report["usable_models"] = names

    # ---- групповая CV: оценки каждой модели для каждого запроса вне его фолда ----
    gold = [set(r["relevant"]) for r in fit]
    y = np.array([idx[r["primary"]] for r in fit])
    fams = sorted({r["family"] for r in fit})
    random.Random(0).shuffle(fams)
    fold_of = {f: i % FOLDS for i, f in enumerate(fams)}
    folds = np.array([fold_of[r["family"]] for r in fit])
    styles = np.array([r["style"] for r in fit])
    report["n_families"] = len(fams)

    S_cv, S_raw = [], []
    for b in usable:
        D, X = b["D"], b["X"]
        Dn = norm(D - D.mean(0, keepdims=True))        # центрирование каталога: статистика каталога, без train
        S = np.zeros((len(fit), len(ids)), np.float32)
        for f in range(FOLDS):
            tr, va = np.where(folds != f)[0], np.where(folds == f)[0]
            mu_q = X[tr].mean(0, keepdims=True)
            S[va] = norm(X[va] - mu_q) @ Dn.T
        S_cv.append(S)
        S_raw.append(X @ D.T)
    singles = {}
    for n, Sc, Sr in zip(names, S_cv, S_raw):
        singles[n] = {"cv_centered": round(float(case_scores(Sc, gold, ids)[0].mean()), 4),
                      "cv_raw": round(float(case_scores(Sr, gold, ids)[0].mean()), 4),
                      "acc1_centered": round(float(case_scores(Sc, gold, ids)[1].mean()), 4)}
    report["singles"] = singles
    top1 = [np.argmax(S, axis=1) for S in S_cv]
    report["top1_agreement"] = {f"{names[i]}|{names[j]}": round(float((top1[i] == top1[j]).mean()), 3)
                                for i in range(len(names)) for j in range(i + 1, len(names))}
    # оракул: хотя бы одна модель угадала top-1 (верхняя граница выгоды от разнообразия)
    report["oracle_acc1_any_model"] = round(float(np.mean([any(ids[t[r]] in gold[r] for t in top1) for r in range(len(fit))])), 4)
    report["cv_seconds_encoders"] = round(time.time() - T0, 2)

    rows = []
    if len(usable) >= 2:
        for cfg in enumerate_configs(len(usable)):
            sc, acc = case_scores(fuse(S_cv, cfg), gold, ids)
            rows.append({"cfg": cfg, "label": label(cfg, names), "cv": float(sc.mean()), "acc1": float(acc.mean()), "_sc": sc})
    if rows:
        best_any = max(rows, key=lambda r: r["cv"])
        report["cv_best_any_mode"] = {"label": best_any["label"], "cv": round(best_any["cv"], 4)}
        sel = [r for r in rows if r["cfg"]["mode"] == SELECT_MODE]
        best = max(sel, key=lambda r: r["cv"])
        near = [r for r in sel if r["cv"] >= best["cv"] - TIE_TOL]
        chosen = min(near, key=lambda r: complexity(r["cfg"]))
        final_cfg = chosen["cfg"]
        report["fusion_table_top"] = [{"label": r["label"], "cv": round(r["cv"], 4), "acc1": round(r["acc1"], 4)}
                                      for r in sorted(rows, key=lambda r: -r["cv"])[:25]]
        report["fusion_n_configs"] = len(rows)
        report["cv_best_raw"] = {"label": best["label"], "cv": round(best["cv"], 4)}
        report["cv_chosen"] = {"label": chosen["label"], "cv": round(chosen["cv"], 4), "acc1": round(chosen["acc1"], 4)}
        report["fusion_mode_best"] = {m: round(max(r["cv"] for r in rows if r["cfg"]["mode"] == m), 4) for m in ("z", "rrf", "zlsm")}
        # по стилям и парное сравнение с bge-base (центрирование) — справка
        base_sc = case_scores(S_cv[0], gold, ids)[0] if names[0] == "bge-base-en-v1.5" else None
        by_style = {}
        for s in sorted(set(styles)):
            m = styles == s
            by_style[s] = {"n": int(m.sum()), "chosen": round(float(chosen["_sc"][m].mean()), 4)}
            if base_sc is not None:
                by_style[s]["bge_base_centered"] = round(float(base_sc[m].mean()), 4)
        report["cv_by_style"] = by_style
        if base_sc is not None:
            d = chosen["_sc"] - base_sc
            report["chosen_vs_bge_base_pairs"] = {"better": int((d > 1e-9).sum()), "worse": int((d < -1e-9).sum())}
    else:   # меньше двух рабочих моделей: единственная модель (центрирование), результат совпадёт с одиночным центрированием
        final_cfg = {"mode": "z", "k": 0, "weights": [1] * len(usable)}
        report["fallback_single"] = True
    if not usable:
        raise SystemExit("no usable encoder")

    # ---- финальная подгонка на всех записях: средний вектор запросов каждой модели ----
    final_models = [(b, w) for b, w in zip(usable, final_cfg["weights"]) if w]
    mus = {}
    for b, w in final_models:
        name = b["spec"]["name"]
        mus[name] = b["X"].mean(0, keepdims=True).astype(np.float32)
        np.save(out / f"emb_{name}.npy", norm(b["D"] - b["D"].mean(0, keepdims=True)).astype(np.float32))
    np.savez(out / "mu_q.npz", **mus)
    (out / "ids.json").write_text(json.dumps(ids))
    config = {"models": [b["spec"] for b, _ in final_models],
              "fusion": {"mode": final_cfg["mode"], "k": final_cfg["k"], "tau": final_cfg.get("tau", 1.0),
                         "weights": [w for _, w in final_models]}}
    (out / "config.json").write_text(json.dumps(config))
    report["config_final"] = config["fusion"] | {"models": [b["spec"]["name"] for b, _ in final_models]}
    report["total_seconds"] = round(time.time() - T0, 2)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
