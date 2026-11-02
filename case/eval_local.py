"""Локальный прогон кандидата по контракту арены: каждый пример — отдельный процесс solve.py
и отдельный процесс score.py, как у оценщика (без контейнера и без изоляции).
Только для train и отладки; public/private оценивает сервис арены.

  python case/eval_local.py --way case/ways/baseline --split case/dataset/train.jsonl
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_json(argv: list[str], payload: dict) -> dict:
    out = subprocess.run(argv, input=json.dumps(payload), capture_output=True, text=True, check=True, cwd="/")
    return json.loads(out.stdout)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--way", type=Path, required=True)
    p.add_argument("--split", type=Path, required=True)
    p.add_argument("--assets", type=Path, default=ROOT / "case/assets")
    p.add_argument("--metric", type=Path, default=ROOT / "case/metric")
    p.add_argument("--details", type=Path, help="куда записать ответы и оценки по примерам (JSONL)")
    a = p.parse_args()
    meta_path = a.split.with_name(a.split.stem + ".meta.jsonl")
    meta = {m["id"]: m for m in map(json.loads, meta_path.open())} if meta_path.exists() else {}
    solve = [sys.executable, str((a.way / "solve.py").resolve())]
    score = [sys.executable, str((a.metric / "score.py").resolve())]
    groups, rows = defaultdict(list), []
    for line in a.split.open(encoding="utf-8"):
        ex = json.loads(line)
        answer = run_json(solve, {"input": ex["input"], "assets_dir": str(a.assets.resolve())})["answer"]
        result = run_json(score, {"example": ex, "answer": answer})
        m = meta.get(ex["id"], {})
        rows.append({"id": ex["id"], "answer": answer, **result})
        for key in ["all", f"style={m.get('style')}", "hard" if m.get("tags") else "misc"]:
            groups[key].append(result)
    if a.details:
        a.details.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{'slice':16s} {'n':>4s} {'score':>6s} {'acc@1':>6s} {'nP@3':>6s} {'valid':>6s}")
    for key in ["all", "hard", "misc"] + sorted(k for k in groups if k.startswith("style=")):
        g = groups.get(key)
        if not g:
            continue
        mean = lambda f: sum(f(r) for r in g) / len(g)
        print(f"{key:16s} {len(g):4d} {mean(lambda r: r['score']):6.3f} "
              f"{mean(lambda r: r['statistics']['acc1']):6.3f} {mean(lambda r: r['statistics']['np3']):6.3f} "
              f"{mean(lambda r: r['statistics']['valid']):6.3f}")


if __name__ == "__main__":
    main()
