"""Фиксированная подвыборка train для сопоставимых замеров кривой эволюции (ADR-0005).

50 семейств (200 запросов), пропорционально кластерам, целыми семействами.
  python case/dataset/curve_subset.py   # -> case/dataset/train_curve.jsonl и train_curve.meta.jsonl
"""
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
N_FAMILIES, SEED = 50, 7


def main() -> None:
    meta = [json.loads(line) for line in (HERE / "train.meta.jsonl").open()]
    by_cluster = defaultdict(set)
    for m in meta:
        by_cluster[m["cluster"]].add(m["family"])
    total = sum(len(f) for f in by_cluster.values())
    rng = random.Random(SEED)
    chosen = []
    for cluster in sorted(by_cluster):
        fams = sorted(by_cluster[cluster])
        rng.shuffle(fams)
        chosen += fams[: max(1, round(len(fams) * N_FAMILIES / total))]
    rng.shuffle(chosen)
    chosen = set(chosen[:N_FAMILIES])
    ids = {m["id"] for m in meta if m["family"] in chosen}
    rows = [line for line in (HERE / "train.jsonl").open() if json.loads(line)["id"] in ids]
    (HERE / "train_curve.jsonl").write_text("".join(rows))
    (HERE / "train_curve.meta.jsonl").write_text("".join(json.dumps(m) + "\n" for m in meta if m["id"] in ids))
    print(f"{len(chosen)} families, {len(rows)} queries -> {HERE / 'train_curve.jsonl'}")


if __name__ == "__main__":
    main()
