#!/usr/bin/env python3
"""build: эмбеддинги каталога bge-base + обучение общего линейного адаптера запроса на train (групповая CV по family).

stdin  — {"assets_dir": "/assets", "build_dir": "/output", ...}
/output — emb.npy (навыки, уже преобразованы), ids.json, config.json, adapter.npz (A, mu_q; если адаптер включён), report.json.

Обучающие данные: fit.jsonl рядом с build.py (556 записей train вне семейств train_curve; см. README).
Как выбирается конфигурация: 5-fold CV по семействам (у каждого навыка в train одно семейство => отложенное семейство = отложенный
навык); оценка по метрике кейса (0.7 acc@1 + 0.3 nP@3) при ранжировании по ВСЕМ 189 навыкам. Базой служит исходное dense (r2-04).
"""
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

T0 = time.time()
GRID_BUDGET_S = 330          # перебор конфигураций прекращается по времени (остаток помечается в report)
FOLDS = 5
STEP_CKPTS = (40, 80, 160)
LR = 3e-4
LAMBDAS = (0.03, 0.1, 0.3)
WHITENS = ((0.25, 0.1), (0.5, 0.1), (0.5, 1.0), (1.0, 1.0), (0.5, 0.01))   # (степень, eps относительно среднего собственного значения)
TIE_TOL = 0.003             # в пределах шума CV (SE ~1.7 п.п.) выбирается более простая конфигурация
MIN_GAIN = 0.005             # адаптер/центрирование включаются, только если CV лучше базы не меньше чем на это
PROBES = ["convert a pdf file to markdown", "i need something that reads my calendar and books meetings",
          "geocode a list of addresses", "pls summarise this long github issue thread for me"]


def norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)


def case_score(S, gold_sets, ids):
    """S: (n, 189) оценки. Метрика кейса: 0.7*acc@1 + 0.3*nP@3 (nP@3 = |top3 ∩ rel| / min(3, |rel|))."""
    top = np.argsort(-S, axis=1)[:, :3]
    acc = np.zeros(len(S))
    np3 = np.zeros(len(S))
    for r, rel in enumerate(gold_sets):
        t = [ids[j] for j in top[r]]
        acc[r] = float(t[0] in rel)
        np3[r] = len(set(t) & rel) / min(3, len(rel))
    return 0.7 * acc + 0.3 * np3, acc


def whiten_matrix(Xq, D, mu_q, mu_d, power, eps_rel):
    """Частичное отбеливание: W = U diag((w + eps)^-power) U^T по ковариации центрированных запросов и навыков."""
    Z = np.concatenate([Xq - mu_q, D - mu_d]).astype(np.float64)
    C = Z.T @ Z / len(Z)
    w, U = np.linalg.eigh(C)
    w = np.maximum(w, 0.0)
    eps = eps_rel * w.mean()
    return ((U * (w + eps) ** (-power)) @ U.T).astype(np.float32)


def apply(X, D, cfg, A=None, mu_q=None, mu_d=None, W=None):
    """Преобразование запросов X и навыков D по конфигурации. Возвращает (Q, Dn)."""
    Q, Dn = X, D
    if cfg["center"]:
        Q, Dn = Q - mu_q, Dn - mu_d
        if W is not None:
            Q, Dn = Q @ W, Dn @ W
        Q, Dn = norm(Q), norm(Dn)
    if A is not None and cfg["mode"] in ("query", "shared", "ridge"):
        Q = norm(Q + Q @ A)
        if cfg["mode"] == "shared":
            Dn = norm(Dn + Dn @ A)
    return Q, Dn


def fit_ce(torch, Xc, Dc, y_idx, train_classes, lam, mode, max_steps, ckpts, seed=0):
    """CE по классам-навыкам обучающей части (классы без обучающих запросов в softmax не входят); A инициализируется нулём."""
    torch.manual_seed(seed)
    X = torch.from_numpy(Xc)
    D = torch.from_numpy(Dc)
    d = X.shape[1]
    A = torch.zeros(d, d, requires_grad=True)
    logtau = torch.tensor(math.log(0.05), requires_grad=True)
    opt = torch.optim.Adam([A, logtau], lr=LR)
    cls = torch.tensor(train_classes, dtype=torch.long)
    remap = {c: i for i, c in enumerate(train_classes)}
    y = torch.tensor([remap[c] for c in y_idx], dtype=torch.long)
    F = torch.nn.functional
    out = {}
    for step in range(1, max_steps + 1):
        Q = F.normalize(X + X @ A, dim=1)
        Dd = F.normalize(D + D @ A, dim=1) if mode == "shared" else D
        logits = (Q @ Dd[cls].T) / torch.exp(logtau)
        loss = F.cross_entropy(logits, y) + lam * (A ** 2).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step in ckpts:
            out[step] = A.detach().numpy().copy()
    return out


def fit_ridge(Xc, Dc, y_idx, lam):
    """A = argmin ||X A - (D_y - X)||^2 + lam ||A||^2 (замкнутая форма)."""
    T = Dc[y_idx] - Xc
    G = Xc.T @ Xc + lam * np.eye(Xc.shape[1], dtype=np.float32)
    return np.linalg.solve(G, Xc.T @ T).astype(np.float32)


def probe_finetune(st, texts, report):
    """Разведка (в): время шага дообучения энкодера в runner на батче из 32 запросов. На качество кандидата не влияет."""
    try:
        import torch
        am, tok = st[0].auto_model, st.tokenizer
        batch = tok(texts[:32], padding=True, truncation=True, max_length=64, return_tensors="pt")
        am.train()
        for p in am.parameters():
            p.requires_grad_(True)
        am(**batch)  # прогрев
        t = time.time()
        with torch.no_grad():
            am(**batch)
        report["probe_forward_nograd_s"] = round(time.time() - t, 3)
        t = time.time()
        am(**batch).last_hidden_state[:, 0].pow(2).sum().backward()
        report["probe_full_step_s"] = round(time.time() - t, 3)
        am.zero_grad()
        n_layers = len(am.encoder.layer)
        for p in am.embeddings.parameters():
            p.requires_grad_(False)
        for i, layer in enumerate(am.encoder.layer):
            for p in layer.parameters():
                p.requires_grad_(i >= n_layers - 4)
        t = time.time()
        am(**batch).last_hidden_state[:, 0].pow(2).sum().backward()
        report["probe_top4_step_s"] = round(time.time() - t, 3)
        report["probe_batch_tokens"] = int(batch["input_ids"].numel())
        am.eval()
    except Exception as exc:
        report["probe_error"] = repr(exc)


def main() -> None:
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    p = json.loads((here / "params.json").read_text())
    catalog = [json.loads(line) for line in (assets / "catalog.jsonl").open(encoding="utf-8") if line.strip()]
    ids = [c["id"] for c in catalog]
    idx = {c: i for i, c in enumerate(ids)}
    docs = [p["doc_prefix"] + p["doc_template"].format(name=c["name"], description=c["description"]) for c in catalog]
    fit = [json.loads(line) for line in (here / "fit.jsonl").open(encoding="utf-8") if line.strip()]
    model_dir = assets / "models" / p["model"]
    report = {"model": p["model"], "n_docs": len(docs), "n_fit": len(fit)}

    import torch
    torch.set_num_threads(2)
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(str(model_dir), device="cpu")
    D0 = st.encode(docs, normalize_embeddings=True, batch_size=32).astype(np.float32)
    report["docs_seconds"] = round(time.time() - T0, 2)

    # ансамбль запроса как в r2-04: среднее косинусов по двум префиксам == косинус с нормированной суммой
    enc_q = [st.encode([pre + r["input"] for r in fit], normalize_embeddings=True, batch_size=32).astype(np.float32)
             for pre in p["query_prefixes"]]
    X = norm(sum(enc_q)).astype(np.float32)
    report["queries_seconds"] = round(time.time() - T0, 2)

    # проверка numpy-энкодера (его использует solve)
    ok = False
    try:
        t1 = time.time()
        enc = Encoder(model_dir, p["pooling"], p["max_len"])
        report["numpy_load_seconds"] = round(time.time() - t1, 3)
        queries = [pre + q for pre in p["query_prefixes"] for q in PROBES]
        qn, qref = enc.encode(queries), st.encode(queries, normalize_embeddings=True, batch_size=32)
        sample = list(range(0, len(docs), 24))
        cos_q, cos_d = (qn * qref).sum(1), (enc.encode([docs[i] for i in sample]) * D0[sample]).sum(1)
        report["min_cos_queries"], report["min_cos_docs_sample"] = float(cos_q.min()), float(cos_d.min())
        ok = bool(cos_q.min() > 0.999 and cos_d.min() > 0.999)
    except Exception as exc:
        report["numpy_error"] = repr(exc)
    report["numpy_encoder_ok"] = ok
    report["numpy_check_done_seconds"] = round(time.time() - T0, 2)

    # ---- групповая CV ----
    gold = [set(r["relevant"]) for r in fit]
    y = [idx[r["primary"]] for r in fit]
    fams = sorted({r["family"] for r in fit})
    random.Random(0).shuffle(fams)
    fold_of = {f: i % FOLDS for i, f in enumerate(fams)}
    folds = np.array([fold_of[r["family"]] for r in fit])
    styles = np.array([r["style"] for r in fit])
    report["n_families"] = len(fams)

    configs = []   # порядок: от простого к сложному (при равенстве выигрывает более простой)
    for center in (False, True):
        configs.append({"center": center, "mode": "none", "lam": 0.0})
    for power, eps_rel in WHITENS:
        configs.append({"center": True, "mode": "none", "lam": 0.0, "white": [power, eps_rel]})
    configs.append({"center": True, "mode": "shared", "lam": 0.1})

    rows = []          # {cfg, step, cv, acc1}
    fold_vecs = {}
    truncated = False
    for ci, cfg in enumerate(configs):
        if time.time() - T0 > GRID_BUDGET_S and cfg["mode"] in ("query", "shared"):
            truncated = True
            report["grid_truncated_at_config"] = ci
            break
        per_step = {}          # step -> оценки по запросам (индексы в fit)
        for f in range(FOLDS):
            tr, va = np.where(folds != f)[0], np.where(folds == f)[0]
            mu_q = X[tr].mean(0, keepdims=True) if cfg["center"] else None
            mu_d = D0.mean(0, keepdims=True) if cfg["center"] else None
            Wm = whiten_matrix(X[tr], D0, mu_q, mu_d, *cfg["white"]) if cfg.get("white") else None
            Xt = norm(X[tr] - mu_q) if cfg["center"] else X[tr]
            Dc = norm(D0 - mu_d) if cfg["center"] else D0
            train_classes = sorted({y[i] for i in tr})
            if cfg["mode"] == "none":
                variants = {0: None}
            elif cfg["mode"] == "ridge":
                variants = {0: fit_ridge(Xt, Dc, [y[i] for i in tr], cfg["lam"])}
            else:
                variants = fit_ce(torch, Xt, Dc, [y[i] for i in tr], train_classes, cfg["lam"], cfg["mode"], max(STEP_CKPTS), STEP_CKPTS)
            for step, A in variants.items():
                Q, Dn = apply(X[va], D0, cfg, A, mu_q, mu_d, Wm)
                sc, acc = case_score(Q @ Dn.T, [gold[i] for i in va], ids)
                per_step.setdefault(step, {})[f] = (va, sc, acc)
        for step, byf in sorted(per_step.items()):
            va_all = np.concatenate([v[0] for v in byf.values()])
            sc_all = np.concatenate([v[1] for v in byf.values()])
            acc_all = np.concatenate([v[2] for v in byf.values()])
            rows.append({"center": cfg["center"], "mode": cfg["mode"], "lam": cfg["lam"], "white": cfg.get("white"), "step": step,
                         "cv_score": round(float(sc_all.mean()), 4), "cv_acc1": round(float(acc_all.mean()), 4),
                         "fold_scores": [round(float(v[1].mean()), 4) for v in byf.values()],
                         "_va": va_all, "_sc": sc_all})
    report["grid_seconds"] = round(time.time() - T0, 2)
    report["grid_truncated"] = truncated

    base = next(r for r in rows if not r["center"] and r["mode"] == "none")
    best = max(rows, key=lambda r: r["cv_score"])
    # самая простая конфигурация (порядок rows: от простого к сложному) в пределах TIE_TOL от лучшей по CV
    simplest = next(r for r in rows if r["cv_score"] >= best["cv_score"] - TIE_TOL)
    chosen = simplest if simplest["cv_score"] >= base["cv_score"] + MIN_GAIN else base
    sc_by_style = {}
    for s in sorted(set(styles)):
        m_b = np.isin(base["_va"], np.where(styles == s)[0])
        m_c = np.isin(chosen["_va"], np.where(styles == s)[0])
        sc_by_style[s] = {"n": int(m_c.sum()), "base": round(float(base["_sc"][m_b].mean()), 4),
                          "chosen": round(float(chosen["_sc"][m_c].mean()), 4)}
    report["cv_table"] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    report["cv_base"] = {k: v for k, v in base.items() if not k.startswith("_")}
    report["cv_best_raw"] = {k: v for k, v in best.items() if not k.startswith("_")}
    report["cv_chosen"] = {k: v for k, v in chosen.items() if not k.startswith("_")}
    report["cv_by_style"] = sc_by_style
    report["min_gain"] = MIN_GAIN

    # ---- финальная подгонка на всех записях fit.jsonl ----
    cfg = {"center": chosen["center"], "mode": chosen["mode"], "lam": chosen["lam"], "white": chosen.get("white")}
    mu_q = X.mean(0, keepdims=True) if cfg["center"] else None
    mu_d = D0.mean(0, keepdims=True) if cfg["center"] else None
    Wm = whiten_matrix(X, D0, mu_q, mu_d, *cfg["white"]) if cfg.get("white") else None
    A = None
    if cfg["mode"] in ("ridge", "query", "shared"):
        Xt = norm(X - mu_q) if cfg["center"] else X
        Dc = norm(D0 - mu_d) if cfg["center"] else D0
        if cfg["mode"] == "ridge":
            A = fit_ridge(Xt, Dc, y, cfg["lam"])
        else:
            A = fit_ce(torch, Xt, Dc, y, sorted(set(y)), cfg["lam"], cfg["mode"], chosen["step"], (chosen["step"],))[chosen["step"]]
        report["A_fro_norm"] = round(float(np.linalg.norm(A)), 4)
        # train-fit (не качество!): точность на обучающих запросах, для контроля переобучения относительно CV
        Q, Dn = apply(X, D0, cfg, A, mu_q, mu_d)
        report["train_fit_score_not_quality"] = round(float(case_score(Q @ Dn.T, gold, ids)[0].mean()), 4)
    _, Dfinal = apply(X[:1], D0, cfg, A, mu_q, mu_d, Wm)


    np.save(out / "emb.npy", Dfinal.astype(np.float32))
    (out / "ids.json").write_text(json.dumps(ids))
    use_adapter = cfg["center"] or A is not None
    if use_adapter:
        np.savez(out / "adapter.npz", A=(A if A is not None else np.zeros((0, 0), np.float32)),
                 mu_q=(mu_q if mu_q is not None else np.zeros((1, 0), np.float32)),
                 W=(Wm if Wm is not None else np.zeros((0, 0), np.float32)))
    (out / "config.json").write_text(json.dumps({**p, "numpy_encoder_ok": ok, "adapter": {**cfg, "enabled": use_adapter}}))
    report["config_final"] = cfg
    report["total_seconds"] = round(time.time() - T0, 2)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "cv_table"}))


if __name__ == "__main__":
    main()
