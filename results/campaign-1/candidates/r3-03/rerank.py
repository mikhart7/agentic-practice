"""Общая часть build и solve: кросс-энкодер и смешивание с оценкой первой стадии."""
import math
import os
from pathlib import Path

MAX_LEN = 256  # токенов на пару (запрос + документ)


def load_model(assets_dir: str, name: str):
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(2)
    path = Path(assets_dir) / "models" / name
    return AutoTokenizer.from_pretrained(path), AutoModelForSequenceClassification.from_pretrained(path).eval()


def doc_text(entry: dict) -> str:
    return f'{entry["name"]}. {entry["description"]}'


def cross_scores(model, query: str, docs: list[str]) -> list[float]:
    import torch

    tok, net = model
    batch = tok([query] * len(docs), docs, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
    with torch.inference_mode():
        logits = net(**batch).logits
    return [float(x) for x in logits[:, 0]]


def zscore(xs: list[float]) -> list[float]:
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))
    return [(x - m) / sd if sd > 1e-9 else 0.0 for x in xs]


def mixed_order(lex: list[float], ce: list[float], w: float) -> list[int]:
    """Порядок позиций топ-N: w * z(первая стадия) + (1 - w) * z(кросс-энкодер); ничья - по рангу первой стадии."""
    zl, zc = zscore(lex), zscore(ce)
    s = [w * a + (1 - w) * b for a, b in zip(zl, zc)]
    return sorted(range(len(s)), key=lambda k: (-s[k], k))
