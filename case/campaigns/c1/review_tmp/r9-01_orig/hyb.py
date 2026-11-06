"""Гибрид: ансамбль dense-энкодеров (z-слияние центрированных косинусов) + лексика r1-03 (BM25 и триграммы).

Единственная реализация признаков и оценок: её используют и build (обучение/CV по train), и solve (применение).
Методы слияния:
  ens  - только ансамбль (то же, что r6-01);
  wz   - z(ансамбль) + w * z(лексика);
  wz2  - z(ансамбль) + wb * z(BM25) + wt * z(триграммы);
  lr   - softmax-регрессия по признакам (как r4-01, dense-признак = z ансамбля);
  lrm  - то же, но вместо z ансамбля отдельные z каждой модели ансамбля.
"""
import re

import numpy as np

NGRAM = 0.6          # вес триграмм в лексике r1-03
CAND_K = 15          # кандидаты регрессии: ранг ансамбля <= K или ранг лексики <= K
LR_BASE = ["zlex", "zb", "zt", "bn", "t", "gap", "zens_L", "zlex_L"]
GRIDS = {
    "wz": [{"w": w} for w in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0)],
    "wz2": [{"wb": wb, "wt": wt} for wb in (0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0) for wt in (0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)],
}


def zscore(S):
    return (S - S.mean(axis=1, keepdims=True)) / np.maximum(S.std(axis=1, keepdims=True), 1e-9)


def norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


def length_feature(queries):
    nw = np.array([len(re.findall(r"[a-z0-9]+", q.lower())) for q in queries], dtype=np.float64)
    return np.clip((nw - 5) / 5, -1.0, 1.0)


def ranks(S):
    """Ранг 1.. по убыванию, ничьи - по индексу."""
    order = np.argsort(-S, axis=1, kind="stable")
    R = np.empty_like(order)
    R[np.arange(S.shape[0])[:, None], order] = np.arange(1, S.shape[1] + 1)[None, :]
    return R


def ensemble(zs, names, weights):
    """Взвешенная сумма z-оценок моделей (в порядке names); weights - список весов."""
    total = None
    for n, w in zip(names, weights):
        if w:
            part = w * zs[n]
            total = part if total is None else total + part
    return total


def features(zs, names, weights, bm, tri, length):
    """Признаки (n, N) для каждой пары запрос-навык. zs[name] - z-оценки модели; bm/tri - лексика (n, N); length - (n,)."""
    zens = zscore(ensemble(zs, names, weights))
    top = bm.max(axis=1, keepdims=True)
    top = np.where(top > 0, top, 1.0)
    bn = bm / top
    lex = bn + NGRAM * tri
    zlex = zscore(lex)
    F = {"zens": zens, "zlex": zlex, "zb": zscore(bm), "zt": zscore(tri), "bn": bn, "t": tri,
         "gap": zens - zens.max(axis=1, keepdims=True),
         "zens_L": zens * length[:, None], "zlex_L": zlex * length[:, None]}
    for n in names:
        F["z:" + n] = zs[n]
    F["cand"] = (ranks(zens) <= CAND_K) | (ranks(lex) <= CAND_K)
    return F


def lr_names(method, names, weights):
    if method == "lr":
        return ["zens"] + LR_BASE
    return ["z:" + n for n, w in zip(names, weights) if w] + LR_BASE


def score(method, params, F):
    if method == "ens":
        return F["zens"]
    if method == "wz":
        return F["zens"] + params["w"] * F["zlex"]
    if method == "wz2":
        return F["zens"] + params["wb"] * F["zb"] + params["wt"] * F["zt"]
    if method in ("lr", "lrm"):
        mu, sd, w = np.array(params["mu"]), np.array(params["sd"]), np.array(params["w"])
        X = np.stack([F[n] for n in params["names"]], axis=-1)
        return ((X - mu) / sd) @ w
    raise ValueError(method)


def take(F, idx):
    return {k: v[idx] for k, v in F.items()}


def case_metric(S, Rel):
    """Метрика кейса по запросам: 0.7*acc@1 + 0.3*nP@3 (nP@3 = |top3 & rel| / min(3, |rel|)); Rel - булева матрица (n, N)."""
    top = np.argsort(-S, axis=1, kind="stable")[:, :3]
    rows = np.arange(len(S))[:, None]
    hit = Rel[rows, top]
    acc = hit[:, 0].astype(np.float64)
    np3 = hit.sum(1) / np.minimum(3, Rel.sum(1))
    return 0.7 * acc + 0.3 * np3, acc


def fit_grid(method, F, Rel):
    best, best_s = None, -1.0
    for p in GRIDS[method]:
        s = case_metric(score(method, p, F), Rel)[0].mean()
        if s > best_s + 1e-12:
            best, best_s = p, s
    return best


def fit_lr(F, Rel, names, iters=100, lam=0.02, lr=0.08):
    """Softmax по кандидатам: максимизируется суммарная вероятность релевантных навыков (как r4-01)."""
    cand = F["cand"]
    valid = (cand & Rel).any(axis=1)
    X = np.stack([F[n] for n in names], axis=-1)[valid]
    cand, rel = cand[valid], Rel[valid]
    rows = X[cand]
    mu, sd = rows.mean(0), rows.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Xs = (X - mu) / sd
    m = len(names)
    w, m1, m2 = np.zeros(m), np.zeros(m), np.zeros(m)
    for t in range(1, iters + 1):
        z = np.where(cand, Xs @ w, -1e9)
        z -= z.max(axis=1, keepdims=True)
        e = np.exp(z) * cand
        p = e / e.sum(axis=1, keepdims=True)
        prel = (p * rel).sum(axis=1, keepdims=True)
        coef = p - np.where(rel, p, 0.0) / np.maximum(prel, 1e-12)
        g = lam * w + (coef[..., None] * Xs).sum(axis=(0, 1)) / len(Xs)
        m1 = 0.9 * m1 + 0.1 * g
        m2 = 0.999 * m2 + 0.001 * g * g
        w = w - lr * (m1 / (1 - 0.9 ** t)) / (np.sqrt(m2 / (1 - 0.999 ** t)) + 1e-8)
    return {"names": list(names), "mu": mu.tolist(), "sd": sd.tolist(), "w": w.tolist()}


def fit(method, F, Rel, names, weights):
    if method == "ens":
        return {}
    if method in ("lr", "lrm"):
        return fit_lr(F, Rel, lr_names(method, names, weights))
    return fit_grid(method, F, Rel)


def cross_validate(method, F, Rel, folds, names, weights):
    """Групповая CV: параметры подбираются на k-1 долях семейств, оцениваются на оставшейся; возвращает метрику по запросам."""
    out = np.zeros(len(Rel))
    acc = np.zeros(len(Rel))
    for f in sorted(set(folds.tolist())):
        tr, va = np.where(folds != f)[0], np.where(folds == f)[0]
        params = fit(method, take(F, tr), Rel[tr], names, weights)
        out[va], acc[va] = case_metric(score(method, params, take(F, va)), Rel[va])
    return out, acc


def top3(scores_row):
    return sorted(range(len(scores_row)), key=lambda i: (-float(scores_row[i]), i))[:3]
