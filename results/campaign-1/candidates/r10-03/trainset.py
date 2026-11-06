"""Обучающие записи для build: train.jsonl + train.meta.jsonl (копии файлов case/dataset без изменений), склеенные по id.

Запись: id, input, primary, relevant (primary + acceptable), family, style. Используется только build.py; solve этот модуль не импортирует.
Несоответствие файлов (разные id, повторы, пустой список, нет primary) - ошибка, а не молчаливая подмена.
"""
import hashlib
import json
from pathlib import Path


def _lines(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load(here):
    here = Path(here)
    train, meta = _lines(here / "train.jsonl"), _lines(here / "train.meta.jsonl")
    if len(train) != len(meta) or [r["id"] for r in train] != [m["id"] for m in meta]:
        raise ValueError("train.jsonl и train.meta.jsonl не совпадают по id или порядку")
    if len({r["id"] for r in train}) != len(train):
        raise ValueError("повторяющиеся id в train")
    records = []
    for r, m in zip(train, meta):
        ref = json.loads(r["reference"])
        relevant = [ref["primary"]] + list(ref.get("acceptable", []))
        records.append({"id": r["id"], "input": r["input"], "primary": ref["primary"], "relevant": relevant,
                        "family": m["family"], "style": m["style"]})
    if not records:
        raise ValueError("пустой train")
    return records


def digests(here):
    here = Path(here)
    return {n: hashlib.sha256((here / n).read_bytes()).hexdigest() for n in ("train.jsonl", "train.meta.jsonl")}
