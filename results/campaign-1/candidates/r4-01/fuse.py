"""Слияние лексики (r1-03) и dense (bge-base, r2-04): признаки и функции оценки. Чистый Python.

Используется и build (обучение параметров слияния на train), и solve (применение). Параметры лежат в
`<prepared>/fusion.json`: {"method": "wz" | "wz2" | "rrf" | "lr", "params": {...}}.
"""
import math
import re

FEATURES = ["zd1", "zd2", "zb", "zt", "bn", "t", "gap", "zdm_L", "zlex_L"]


def zs(v):
    n = len(v)
    mu = sum(v) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in v) / n)
    sd = sd if sd > 1e-9 else 1.0
    return [(x - mu) / sd for x in v]


def ranks(v):
    """Ранг 1..n по убыванию score, при равенстве — меньший индекс выше."""
    order = sorted(range(len(v)), key=lambda i: (-v[i], i))
    r = [0] * len(v)
    for pos, i in enumerate(order, 1):
        r[i] = pos
    return r


def make_features(d1, d2, bm, tri, query):
    """Признаки одного запроса по всем N навыкам.

    d1/d2 — косинусы dense (запрос без инструкции / с инструкцией BGE), bm — сырой BM25, tri — косинус триграмм.
    """
    n = len(bm)
    dm = [(a + b) / 2 for a, b in zip(d1, d2)]
    top = max(bm) or 1.0
    lex = [s / top + 0.6 * c for s, c in zip(bm, tri)]  # = лексика r1-03
    nw = len(re.findall(r"[a-z0-9]+", query.lower()))
    length = max(-1.0, min(1.0, (nw - 5) / 5))
    zdm, zlex = zs(dm), zs(lex)
    mx = max(dm)
    return {
        "n": n, "L": length,
        "dm": dm, "lex": lex, "zdm": zdm, "zlex": zlex,
        "zd1": zs(d1), "zd2": zs(d2), "zb": zs(bm), "zt": zs(tri),
        "bn": [s / top for s in bm], "t": list(tri), "gap": [x - mx for x in dm],
        "rdm": ranks(dm), "rlex": ranks(lex),
        "zdm_L": [x * length for x in zdm], "zlex_L": [x * length for x in zlex],
    }


def feature_row(F, i, names=FEATURES):
    return [F[name][i] for name in names]


def score(method, params, F):
    n = F["n"]
    if method == "dense":
        return F["zdm"]
    if method == "lex":
        return F["lex"]
    if method == "wz":
        w = params["w"]
        return [a + w * b for a, b in zip(F["zdm"], F["zlex"])]
    if method == "wz2":
        wb, wt = params["wb"], params["wt"]
        return [a + wb * b + wt * c for a, b, c in zip(F["zdm"], F["zb"], F["zt"])]
    if method == "rrf":
        k, w = params["k"], params["w"]
        return [1.0 / (k + F["rdm"][i]) + w / (k + F["rlex"][i]) for i in range(n)]
    if method == "lr":
        names, mu, sd, wts = params["names"], params["mu"], params["sd"], params["w"]
        cols = [F[nm] for nm in names]
        return [sum(wts[j] * (cols[j][i] - mu[j]) / sd[j] for j in range(len(names))) for i in range(n)]
    raise ValueError(method)


def top3(scores):
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:3]
