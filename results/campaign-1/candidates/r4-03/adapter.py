"""Линейный адаптер запросов dense: ridge-регрессия сдвига эмбеддинга запроса к эмбеддингу его релевантного навыка.

Обучается в build на train (вне семейств train_curve); сдвиг один на вид запроса (D x D), общий для всех навыков.
Применение: q' = normalize(q + alpha * q @ Delta). Параметры (lambda, alpha) выбираются групповой CV по family
по качеству dense-ранжирования на отложенных семействах; alpha = 0 (адаптера нет) входит в выбор.
"""
import numpy as np


def fit(Q, T, lam):
    """Delta (D x D): Q @ Delta ~ T - Q, ridge. Q, T — (n, D) float64."""
    d = Q.shape[1]
    return np.linalg.solve(Q.T @ Q + lam * np.eye(d), Q.T @ (T - Q))


def apply(Q, Delta, alpha):
    X = Q + alpha * (Q @ Delta)
    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12)


def metric(sims, rel_rows):
    """Метрика кейса (0.7 acc@1 + 0.3 nP@3) по матрице сходств (n, N); rel_rows — списки индексов релевантных."""
    top = np.argsort(-sims, axis=1, kind="stable")[:, :3]
    tot = 0.0
    for t, rel in zip(top, rel_rows):
        rs = set(rel)
        acc1 = 1.0 if int(t[0]) in rs else 0.0
        np3 = len(rs & {int(x) for x in t}) / min(3, len(rs))
        tot += 0.7 * acc1 + 0.3 * np3
    return tot / len(rel_rows)


def select(views, emb, rel_rows, fold, lams=(0.5, 2.0, 8.0, 32.0), alphas=(0.5, 1.0, 2.0), k=5, min_gain=0.005):
    """Подбор (lam, alpha) групповой CV. views — список (n, D) матриц нормированных эмбеддингов запросов (по видам).

    Возвращает (best, table, oof): best = (lam, alpha) или None; oof[v] — матрица (n, D) кросс-подогнанных
    эмбеддингов запросов для выбранных параметров (для обучения слияния без утечки).
    """
    n = views[0].shape[0]
    emb64 = emb.astype(np.float64)
    V = [v.astype(np.float64) for v in views]
    T = np.zeros((n, emb.shape[1]))
    for i, rel in enumerate(rel_rows):
        t = emb64[rel].mean(0)
        T[i] = t / max(np.linalg.norm(t), 1e-12)
    fold = np.asarray(fold)
    base = metric(sum(v @ emb64.T for v in V) / len(V), rel_rows)
    table = [{"lam": 0.0, "alpha": 0.0, "cv": base}]
    resid = {}  # (lam, view) -> OOF сдвиг Q @ Delta (n, D)
    for lam in lams:
        for vi, Q in enumerate(V):
            R = np.zeros_like(Q)
            for f in range(k):
                tr, te = fold != f, fold == f
                R[te] = Q[te] @ fit(Q[tr], T[tr], lam)
            resid[(lam, vi)] = R
    best, best_s = None, base + min_gain
    for lam in lams:
        for a in alphas:
            sims = 0.0
            for vi, Q in enumerate(V):
                X = Q + a * resid[(lam, vi)]
                X /= np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12)
                sims = sims + X @ emb64.T
            s = metric(sims / len(V), rel_rows)
            table.append({"lam": lam, "alpha": a, "cv": s})
            if s > best_s:
                best, best_s = (lam, a), s
    oof = None
    if best is not None:
        lam, a = best
        oof = []
        for vi, Q in enumerate(V):
            X = Q + a * resid[(lam, vi)]
            oof.append(X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12))
    return best, table, oof, T


def final(views, T, lam):
    """Delta для каждого вида запроса по всем обучающим записям."""
    return [fit(v.astype(np.float64), T, lam).astype(np.float32) for v in views]
