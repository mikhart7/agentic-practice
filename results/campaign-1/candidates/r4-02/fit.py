"""Обучение параметров слияния (только build). Чистый Python, детерминированно.

Обучается общий механизм слияния (несколько скаляров/весов), а не соответствие «запрос -> навык»:
решение выбирается групповой кросс-валидацией по family, чтобы оценка шла по ещё не виденным семействам.
"""
import itertools
import math
import random
from collections import defaultdict

from fuse import FEATURES, feature_row, score, top3


def metric(ids, ranked, rel):
    top = [ids[i] for i in ranked]
    acc1 = 1.0 if top and top[0] in rel else 0.0
    np3 = len(set(top) & rel) / min(3, len(rel))
    return 0.7 * acc1 + 0.3 * np3


def evaluate(method, params, Fs, rels, ids):
    tot = 0.0
    for F, rel in zip(Fs, rels):
        tot += metric(ids, top3(score(method, params, F)), rel)
    return tot / len(Fs)


GRIDS = {
    "wz": [{"w": w} for w in [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0]],
    "wz2": [{"we": we, "wb": wb, "wt": wt} for we in [0, 0.5, 1.0]
            for wb in [0, 0.15, 0.3, 0.5, 0.75] for wt in [0, 0.15, 0.3, 0.5]],
    "rrf": [{"k": k, "w": w} for k in [2, 5, 10, 20, 60] for w in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]],
}


def fit_grid(method, Fs, rels, ids):
    best, best_s = None, -1.0
    for p in GRIDS[method]:
        s = evaluate(method, p, Fs, rels, ids)
        if s > best_s + 1e-12:
            best, best_s = p, s
    return best


def fit_lr(Fs, rels, ids, names=FEATURES, cand=12, iters=80, lam=0.02, lr=0.08):
    """Листовая softmax-регрессия: максимизируем суммарную вероятность релевантных навыков среди кандидатов."""
    pos = {s: i for i, s in enumerate(ids)}
    data = []  # на запрос: (строки признаков кандидатов, индексы релевантных среди кандидатов)
    allrows = []
    for F, rel in zip(Fs, rels):
        c = {i for i in range(F["n"]) if F["rens"][i] <= cand or F["rlex"][i] <= cand}
        c = sorted(c)
        rows = [feature_row(F, i, names) for i in c]
        isrel = [ids[i] in rel for i in c]
        if any(isrel):
            data.append((rows, isrel))
            allrows.extend(rows)
    m = len(names)
    mu = [sum(r[j] for r in allrows) / len(allrows) for j in range(m)]
    sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in allrows) / len(allrows)) or 1.0 for j in range(m)]
    data = [([[(x - mu[j]) / sd[j] for j, x in enumerate(r)] for r in rows], isrel) for rows, isrel in data]
    # инициализация: вес только у zdm_L-независимых признаков нулевой, Adam с нуля
    w = [0.0] * m
    m1, m2 = [0.0] * m, [0.0] * m
    for t in range(1, iters + 1):
        g = [lam * x for x in w]
        for rows, isrel in data:
            z = [sum(w[j] * r[j] for j in range(m)) for r in rows]
            zmax = max(z)
            e = [math.exp(x - zmax) for x in z]
            s = sum(e)
            p = [x / s for x in e]
            prel = sum(pi for pi, rl in zip(p, isrel) if rl)
            coef = [pi - (pi / prel if rl else 0.0) for pi, rl in zip(p, isrel)]
            for r, cf in zip(rows, coef):
                for j in range(m):
                    g[j] += cf * r[j] / len(data)
        for j in range(m):
            m1[j] = 0.9 * m1[j] + 0.1 * g[j]
            m2[j] = 0.999 * m2[j] + 0.001 * g[j] * g[j]
            w[j] -= lr * (m1[j] / (1 - 0.9 ** t)) / (math.sqrt(m2[j] / (1 - 0.999 ** t)) + 1e-8)
    return {"names": list(names), "mu": mu, "sd": sd, "w": w}


def fit(method, Fs, rels, ids):
    if method == "lr":
        return fit_lr(Fs, rels, ids)
    return fit_grid(method, Fs, rels, ids)


def folds(groups, k=5, seed=0):
    uniq = sorted(set(groups))
    random.Random(seed).shuffle(uniq)
    assign = {g: i % k for i, g in enumerate(uniq)}
    return [assign[g] for g in groups]


def cross_validate(method, Fs, rels, ids, groups, k=5):
    """Групповая CV: параметры подбираются на k-1 долях семейств, оцениваются на оставшейся. Возвращает средний score."""
    fold = folds(groups, k)
    tot, n = 0.0, 0
    for f in range(k):
        tr = [i for i in range(len(Fs)) if fold[i] != f]
        te = [i for i in range(len(Fs)) if fold[i] == f]
        params = fit(method, [Fs[i] for i in tr], [rels[i] for i in tr], ids)
        for i in te:
            tot += metric(ids, top3(score(method, params, Fs[i])), rels[i])
            n += 1
    return tot / n


def select(Fs, rels, ids, groups, methods=("wz", "wz2", "rrf", "lr")):
    """Сравнивает методы групповой CV, возвращает (метод, параметры, отчёт)."""
    report = {"n_queries": len(Fs), "n_families": len(set(groups))}
    report["dense_only"] = evaluate("dense", None, Fs, rels, ids)  # только bge-base (как r4-01)
    report["ens_only"] = evaluate("ens", None, Fs, rels, ids)  # ансамбль трёх dense без лексики
    report["lex_only"] = evaluate("lex", None, Fs, rels, ids)
    cv = {}
    for m in methods:
        cv[m] = cross_validate(m, Fs, rels, ids, groups)
    report["cv"] = cv
    best = max(methods, key=lambda m: (cv[m], -methods.index(m)))
    params = fit(best, Fs, rels, ids)
    report["method"] = best
    report["params"] = params
    report["in_sample_fused"] = evaluate(best, params, Fs, rels, ids)
    return best, params, report
