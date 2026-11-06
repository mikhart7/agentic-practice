"""Обучение параметров слияния (только build). Чистый Python, детерминированно.

Обучается общий механизм слияния (несколько скаляров/весов), а не соответствие «запрос -> навык»:
решение выбирается групповой кросс-валидацией по family, чтобы оценка шла по ещё не виденным семействам.
"""
import itertools
import math
import random
from collections import defaultdict

from fuse import FEATURES, FEATURES_CE, feature_row, score, top3


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
    "wz2": [{"wb": wb, "wt": wt} for wb in [0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0] for wt in [0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]],
    "rrf": [{"k": k, "w": w} for k in [2, 5, 10, 20, 60] for w in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]],
}


def fit_grid(method, Fs, rels, ids):
    best, best_s = None, -1.0
    for p in GRIDS[method]:
        s = evaluate(method, p, Fs, rels, ids)
        if s > best_s + 1e-12:
            best, best_s = p, s
    return best


def fit_lr(Fs, rels, ids, names=FEATURES, cand=15, iters=100, lam=0.02, lr=0.08, ce=False):
    """Листовая softmax-регрессия: максимизируем суммарную вероятность релевантных навыков среди кандидатов."""
    pos = {s: i for i, s in enumerate(ids)}
    data = []  # на запрос: (строки признаков кандидатов, индексы релевантных среди кандидатов)
    allrows = []
    for F, rel in zip(Fs, rels):
        if ce:   # кандидаты кросс-энкодера (признаки CE определены только на них)
            c = [i for i in range(F["n"]) if F["cand"][i]]
        else:
            c = sorted({i for i in range(F["n"]) if F["rdm"][i] <= cand or F["rlex"][i] <= cand})
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
    if method == "lrce":
        return fit_lr(Fs, rels, ids, names=FEATURES_CE, ce=True)
    return fit_grid(method, Fs, rels, ids)


def folds(groups, k=5, seed=0):
    uniq = sorted(set(groups))
    random.Random(seed).shuffle(uniq)
    assign = {g: i % k for i, g in enumerate(uniq)}
    return [assign[g] for g in groups]


def cross_validate(method, Fs, rels, ids, groups, k=5):
    """Групповая CV: параметры подбираются на k-1 долях семейств, оцениваются на оставшейся.

    Возвращает список оценок метрики по запросам (в исходном порядке): среднее — CV-score, список — для разбивки по стилям
    и парных сравнений вариантов.
    """
    fold = folds(groups, k)
    out = [0.0] * len(Fs)
    for f in range(k):
        tr = [i for i in range(len(Fs)) if fold[i] != f]
        te = [i for i in range(len(Fs)) if fold[i] == f]
        params = fit(method, [Fs[i] for i in tr], [rels[i] for i in tr], ids)
        for i in te:
            out[i] = metric(ids, top3(score(method, params, Fs[i])), rels[i])
    return out


def mean(xs):
    return sum(xs) / len(xs)


def by_style(scores, styles):
    groups = {}
    for s, st in zip(scores, styles):
        groups.setdefault(st, []).append(s)
    return {st: {"n": len(v), "cv": round(mean(v), 4)} for st, v in sorted(groups.items())}


def run_variant(Fs, rels, ids, groups, styles, methods):
    """CV по методам для одного набора признаков. Возвращает (отчёт, {метод: оценки по запросам})."""
    rep = {"dense_only": evaluate("dense", None, Fs, rels, ids), "lex_only": evaluate("lex", None, Fs, rels, ids), "cv": {}, "cv_by_style": {}}
    per = {}
    for m in methods:
        per[m] = cross_validate(m, Fs, rels, ids, groups)
        rep["cv"][m] = round(mean(per[m]), 4)
        rep["cv_by_style"][m] = by_style(per[m], styles)
    return rep, per


def choose(cv_raw, cv_cen, cv_ce, tol_center=0.003, gain_ce=0.01):
    """Правило выбора конфигурации по CV (значения — средние CV лучших методов каждого варианта).

    cv_raw/cv_cen — {метод: CV} без кросс-энкодера для сырых/центрированных dense-косинусов; cv_ce — {"raw": {...}, "cen": {...}}
    для методов с кросс-энкодером (может быть пустым). Простое побеждает при разнице в пределах шума:
      центрирование включается, если лучший метод с ним лучше лучшего без него не меньше чем на tol_center;
      кросс-энкодер — если лучше лучшего варианта без него не меньше чем на gain_ce (он стоит времени и CPU в solve).
    Возвращает {"center": bool, "ce": bool, "method": str}.
    """
    best = lambda d: max(d.items(), key=lambda kv: (kv[1], kv[0] == "lr"))
    mr, sr = best(cv_raw)
    mc, sc = best(cv_cen)
    center = sc >= sr + tol_center
    method, base = (mc, sc) if center else (mr, sr)
    if cv_ce:
        cands = []
        for key, d in cv_ce.items():
            if d:
                m, s = best(d)
                cands.append((s, key, m))
        if cands:
            s, key, m = max(cands)
            if s >= base + gain_ce:
                return {"center": key == "cen", "ce": True, "method": m}  # центрирование задаёт вариант с CE
    return {"center": center, "ce": False, "method": method}
