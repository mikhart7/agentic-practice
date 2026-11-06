"""Слияние лексики (r1-03) и трёх dense-моделей (bge-base, e5-small, MiniLM): признаки и оценка. Чистый Python.

Используется и build (обучение параметров слияния на train), и solve (применение). Параметры лежат в
`<prepared>/fusion.json`: {"method": "wz" | "wz2" | "rrf" | "lr", "params": {...}}.
"""
import math
import re

FEATURES = ["zd1", "zd2", "ze", "zm", "zens", "zb", "zt", "bn", "t", "gap", "gap_e", "zens_L", "zlex_L"]
ENS_W = (1.0, 0.5, 0.5)  # веса bge / e5 / MiniLM в ансамбле dense (фиксированы заранее)


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


def make_features(dense, bm, tri, query):
    """Признаки одного запроса по всем N навыкам.

    dense — {"bge": [cos_plain, cos_instr], "e5": [cos], "mini": [cos]} (косинусы к навыкам),
    bm — сырой BM25, tri — косинус триграмм слов.
    """
    n = len(bm)
    d1, d2 = dense["bge"]
    de, dmi = dense["e5"][0], dense["mini"][0]
    dm = [(a + b) / 2 for a, b in zip(d1, d2)]
    top = max(bm) or 1.0
    lex = [s / top + 0.6 * c for s, c in zip(bm, tri)]  # = лексика r1-03
    nw = len(re.findall(r"[a-z0-9]+", query.lower()))
    length = max(-1.0, min(1.0, (nw - 5) / 5))
    zdm, zlex, ze, zm = zs(dm), zs(lex), zs(de), zs(dmi)
    ens = [ENS_W[0] * a + ENS_W[1] * b + ENS_W[2] * c for a, b, c in zip(zdm, ze, zm)]
    zens = zs(ens)
    return {
        "n": n, "L": length,
        "dm": dm, "lex": lex, "zdm": zdm, "zlex": zlex, "ze": ze, "zm": zm, "zens": zens,
        "zd1": zs(d1), "zd2": zs(d2), "zb": zs(bm), "zt": zs(tri),
        "bn": [s / top for s in bm], "t": list(tri),
        "gap": [x - max(dm) for x in dm], "gap_e": [x - max(de) for x in de],
        "rens": ranks(zens), "rlex": ranks(lex),
        "zens_L": [x * length for x in zens], "zlex_L": [x * length for x in zlex],
    }


def feature_row(F, i, names=FEATURES):
    return [F[name][i] for name in names]


def score(method, params, F):
    n = F["n"]
    if method == "dense":
        return F["zdm"]
    if method == "ens":
        return F["zens"]
    if method == "lex":
        return F["lex"]
    if method == "wz":
        w = params["w"]
        return [a + w * b for a, b in zip(F["zens"], F["zlex"])]
    if method == "wz2":
        we, wb, wt = params["we"], params["wb"], params["wt"]
        return [a + we * (e + m) + wb * b + wt * c
                for a, e, m, b, c in zip(F["zdm"], F["ze"], F["zm"], F["zb"], F["zt"])]
    if method == "rrf":
        k, w = params["k"], params["w"]
        return [1.0 / (k + F["rens"][i]) + w / (k + F["rlex"][i]) for i in range(n)]
    if method == "lr":
        names, mu, sd, wts = params["names"], params["mu"], params["sd"], params["w"]
        cols = [F[nm] for nm in names]
        return [sum(wts[j] * (cols[j][i] - mu[j]) / sd[j] for j in range(len(names))) for i in range(n)]
    raise ValueError(method)


def top3(scores):
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:3]
