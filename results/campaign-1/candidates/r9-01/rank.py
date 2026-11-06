"""Новые рычаги r9: граф близких навыков каталога (псевдо-релевантная обратная связь, сглаживание по соседям, поправка на хабы)
и GBDT-ранжировщик поверх навык-независимых признаков пары (запрос, навык).

Единственная реализация для build (обучение и CV) и solve (применение). Только numpy; деревья LightGBM, обученные в build,
сериализуются в JSON и вычисляются здесь же (solve не импортирует lightgbm).

Все признаки пары вычисляются из векторов оценок запроса по каталогу (z-оценки моделей, лексика) и из графа навыков
(производная от описаний каталога). ID навыка в признаки не входит.
"""
import numpy as np

import hyb

W_LEX = 0.1          # вес лексики в базовой оценке (значение, выбранное CV в r8-01)
NBR_K = 10           # ширина списка соседей в графе навыков
CAND = 30            # число кандидатов GBDT (топ по базовой оценке)
HUB_TOP = 10         # число лучших запросов для статистики хаба


# ---------------------------------------------------------------- граф навыков
def build_graph(Dn, names, weights):
    """Dn[name] - центрированные нормированные эмбеддинги каталога. G - взвешенное среднее косинусов навык-навык (float32)."""
    G = None
    for n, w in zip(names, weights):
        if w:
            part = w * (Dn[n].astype(np.float64) @ Dn[n].astype(np.float64).T)
            G = part if G is None else G + part
    return (G / float(sum(w for w in weights if w))).astype(np.float32)


def graph_from_G(G):
    """Производные графа из сохранённой матрицы G; build и solve вызывают одну и ту же функцию."""
    G = np.asarray(G, dtype=np.float32).astype(np.float64)
    order = np.argsort(-(G - 2.0 * np.eye(len(G))), axis=1, kind="stable")[:, :NBR_K]   # без самого себя
    Gz = (G - G.mean(axis=1, keepdims=True)) / np.maximum(G.std(axis=1, keepdims=True), 1e-9)
    return {"G": G, "Gz": Gz, "nbr": order}


def hub_stat(zens_fit):
    """Хаб навыка: среднее его HUB_TOP лучших z-оценок по запросам (без меток), затем z-оценка по навыкам."""
    top = np.sort(zens_fit, axis=0)[-HUB_TOP:].mean(axis=0)
    return (top - top.mean()) / max(top.std(), 1e-9)


def base_score(F):
    """Базовая оценка r8-01: z(ансамбль) + 0.1 * z(лексика)."""
    return F["zens"] + W_LEX * F["zlex"]


# ---------------------------------------------------------------- простые методы на графе
def post(method, params, base, aux):
    """Пересчёт базовой оценки (n, N) методами графа. Возвращает (n, N)."""
    s = hyb.zscore(base)
    if method in ("prf", "prfsm"):
        k, a = params["k"], params["a"]
        top = np.argsort(-base, axis=1, kind="stable")[:, :k]
        P = aux["Gz"][top].mean(axis=1)                      # Rocchio в пространстве оценок: q' = q + a * mean(топ-k навыков)
        s = s + a * hyb.zscore(P)
    if method in ("sm", "prfsm"):
        k, b = params["sk"] if method == "prfsm" else params["k"], params["b"]
        M = base[:, aux["nbr"][:, :k]].mean(axis=2)          # среднее базовой оценки k ближайших навыков
        s = s + b * hyb.zscore(M)
    if method == "csls":
        s = s - params["g"] * aux["hub"][None, :]
    return s


GRIDS = {
    "prf": [{"k": k, "a": a} for k in (1, 2, 3, 5, 8) for a in (0.1, 0.25, 0.5, 1.0)],
    "sm": [{"k": k, "b": b} for k in (3, 5, 10) for b in (0.1, 0.25, 0.5)],
    "prfsm": [{"k": k, "a": a, "sk": sk, "b": b} for k in (2, 3, 5) for a in (0.25, 0.5) for sk in (3, 5) for b in (0.25, 0.5)],
    "csls": [{"g": g} for g in (0.1, 0.2, 0.3, 0.5, 0.75, 1.0)],
}


def fit_graph(method, base, Rel, aux):
    best, best_s = None, -1.0
    for p in GRIDS[method]:
        s = hyb.case_metric(post(method, p, base, aux), Rel)[0].mean()
        if s > best_s + 1e-12:
            best, best_s = p, s
    return best


def cv_graph(method, base, Rel, folds, aux):
    out, acc = np.zeros(len(Rel)), np.zeros(len(Rel))
    chosen = []
    for f in sorted(set(folds.tolist())):
        tr, va = np.where(folds != f)[0], np.where(folds == f)[0]
        p = fit_graph(method, base[tr], Rel[tr], aux)
        chosen.append(p)
        out[va], acc[va] = hyb.case_metric(post(method, p, base[va], aux), Rel[va])
    return out, acc, chosen


# ---------------------------------------------------------------- признаки пар для GBDT
def _gap(S):
    """S - максимум по строке и S - второй максимум (для лидера: отрицательный запас)."""
    srt = np.sort(S, axis=1)
    m1, m2 = srt[:, -1:], srt[:, -2:-1]
    return S - m1, S - m2


def pair_features(F, zs, names, aux, bm, length):
    """Признаки для всех пар (n, N, f) и их имена. F - признаки hyb.features, zs - z-оценки моделей, bm - сырой BM25 (n, N)."""
    base = base_score(F)
    n, N = base.shape
    cols, labels = [], []

    def add(name, A):
        cols.append(np.asarray(A, dtype=np.float64))
        labels.append(name)

    for m in names:
        add("z:" + m, zs[m])
        add("lrank:" + m, np.log1p(hyb.ranks(zs[m])))
    for k in ("zens", "zlex", "zb", "zt", "bn", "t"):
        add(k, F[k])
    add("lrank_ens", np.log1p(hyb.ranks(F["zens"])))
    add("lrank_lex", np.log1p(hyb.ranks(F["zlex"])))
    add("base", base)
    rk = hyb.ranks(base)
    add("lrank_base", np.log1p(rk))
    g1, g2 = _gap(base)
    add("gap_base", g1)
    add("gap2_base", g2)
    ge1, ge2 = _gap(F["zens"])
    add("gap_ens", ge1)
    add("gap2_ens", ge2)
    gl1, _ = _gap(F["zlex"])
    add("gap_lex", gl1)
    # --- граф навыков ---
    nbr = aux["nbr"]
    for k in (3, 5):
        M = base[:, nbr[:, :k]]                                  # (n, N, k) базовая оценка соседей
        add(f"nbr_mean{k}", M.mean(axis=2))
        add(f"nbr_max_gap{k}", base - M.max(axis=2))             # < 0: у навыка есть сосед сильнее
    top1 = base.argmax(axis=1)
    add("sim_top1", aux["G"][top1])                              # близость навыка к лидеру базовой оценки
    top2 = np.argsort(-base, axis=1, kind="stable")[:, 1]
    add("sim_top2", aux["G"][top2])
    top3 = np.argsort(-base, axis=1, kind="stable")[:, :3]
    in3 = np.zeros((n, N))
    np.put_along_axis(in3, top3, 1.0, axis=1)
    add("nbr_in_top3", in3[:, nbr[:, :5]].sum(axis=2))           # сколько из 5 соседей навыка в топ-3 запроса
    p = np.exp(base - base.max(axis=1, keepdims=True))
    p = p / p.sum(axis=1, keepdims=True)
    mass = p + p[:, nbr[:, :5]].sum(axis=2)
    add("cluster_mass", mass)
    add("share_in_cluster", p / np.maximum(mass, 1e-12))
    for k in (1, 3):
        topk = np.argsort(-base, axis=1, kind="stable")[:, :k]
        add(f"prf{k}", hyb.zscore(aux["Gz"][topk].mean(axis=1)))
    add("density", np.broadcast_to(np.sort(aux["G"] - 2.0 * np.eye(N), axis=1)[:, -5:].mean(axis=1), (n, N)))   # плотность окружения навыка
    # --- признаки запроса ---
    q = lambda v: np.broadcast_to(np.asarray(v, dtype=np.float64)[:, None], (n, N))
    add("q_len", q(length))
    srt = np.sort(base, axis=1)
    add("q_margin_base", q(srt[:, -1] - srt[:, -2]))
    add("q_peak_lex", q(F["zlex"].max(axis=1)))
    add("q_bm_peak", q(np.log1p(bm.max(axis=1))))
    add("q_nz_lex", q((bm > 0).sum(axis=1) / float(N)))
    return np.stack(cols, axis=-1), labels


def candidates(base, c=CAND):
    return np.argsort(-base, axis=1, kind="stable")[:, :c]


def gather(X, cand):
    """X (n, N, f), cand (n, C) -> (n, C, f)."""
    return np.take_along_axis(X, cand[:, :, None], axis=1)


# ---------------------------------------------------------------- деревья LightGBM -> numpy
def export_trees(booster):
    """Плоское представление деревьев: список словарей с массивами узлов; внутренний узел i: feature/threshold/left/right
    (child >= 0 - индекс узла, < 0 - лист ~child), листья - value."""
    trees = []
    for info in booster.dump_model()["tree_info"]:
        feat, thr, left, right, vals = [], [], [], [], []

        def walk(node):
            if "leaf_value" in node:
                vals.append(float(node["leaf_value"]))
                return ~(len(vals) - 1)
            if node.get("decision_type", "<=") != "<=":
                raise ValueError("unsupported decision_type " + str(node.get("decision_type")))
            i = len(feat)
            feat.append(int(node["split_feature"]))
            thr.append(float(node["threshold"]))
            left.append(0)
            right.append(0)
            left[i] = walk(node["left_child"])
            right[i] = walk(node["right_child"])
            return i

        root = walk(info["tree_structure"])
        trees.append({"root": root, "feat": feat, "thr": thr, "left": left, "right": right, "val": vals})
    return trees


def predict_trees(trees, X):
    """X (m, f) float64 -> (m,) сумма значений листьев (LightGBM: переход влево при x <= threshold)."""
    out = np.zeros(len(X))
    for t in trees:
        if not t["feat"]:                       # дерево из одного листа
            out += t["val"][~t["root"]]
            continue
        feat, thr = np.array(t["feat"]), np.array(t["thr"])
        left, right, val = np.array(t["left"]), np.array(t["right"]), np.array(t["val"])
        node = np.zeros(len(X), dtype=np.int64)
        active = np.ones(len(X), dtype=bool)
        res = np.zeros(len(X))
        while active.any():
            i = node[active]
            go_left = X[active, feat[i]] <= thr[i]
            nxt = np.where(go_left, left[i], right[i])
            idx = np.where(active)[0]
            leaf = nxt < 0
            res[idx[leaf]] = val[~nxt[leaf]]
            node[idx[~leaf]] = nxt[~leaf]
            active[idx[leaf]] = False
        out += res
    return out


def gbdt_scores(trees, X, cand, N):
    """Оценки GBDT для кандидатов; остальные навыки получают -inf (ниже всех кандидатов)."""
    n, C, f = X.shape
    s = predict_trees(trees, X.reshape(n * C, f).astype(np.float64)).reshape(n, C)
    out = np.full((n, N), -1e9)
    np.put_along_axis(out, cand, s, axis=1)
    return out
