"""Слияние оценок нескольких энкодеров. Единственная реализация: её используют и build (CV), и solve.

S — список матриц оценок (n_запросов, n_навыков) в порядке cfg["models"]; cfg = {"mode": "z"|"rrf", "k": int, "weights": [..]}.
  z   : оценки каждой модели стандартизуются по навыкам внутри запроса (среднее 0, std 1), взвешенная сумма
  rrf : взвешенная сумма 1 / (k + ранг), ранг с 1 по убыванию оценки
  zlsm: произведение экспертов: оценки стандартизуются (как в z), делятся на температуру tau, берётся log-softmax по навыкам,
        взвешенная сумма логарифмов вероятностей (чувствительна к верхушке ранжирования, а не к хвосту распределения)
"""
import numpy as np


def zscore(S):
    return (S - S.mean(axis=1, keepdims=True)) / np.maximum(S.std(axis=1, keepdims=True), 1e-9)


def ranks(S):
    """Ранг навыка внутри запроса (1 = лучший); ничьи — по индексу (стабильная сортировка)."""
    order = np.argsort(-S, axis=1, kind="stable")
    R = np.empty_like(order)
    rows = np.arange(S.shape[0])[:, None]
    R[rows, order] = np.arange(1, S.shape[1] + 1)[None, :]
    return R


def log_softmax(X):
    m = X.max(axis=1, keepdims=True)
    return X - m - np.log(np.exp(X - m).sum(axis=1, keepdims=True))


def fuse(S, cfg):
    total = None
    for s, w in zip(S, cfg["weights"]):
        if w == 0:
            continue
        if cfg["mode"] == "z":
            part = w * zscore(s)
        elif cfg["mode"] == "zlsm":
            part = w * log_softmax(zscore(s) / cfg["tau"])
        else:
            part = w / (cfg["k"] + ranks(s))
        total = part if total is None else total + part
    return total
