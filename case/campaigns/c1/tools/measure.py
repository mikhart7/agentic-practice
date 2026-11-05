#!/usr/bin/env python3
"""Обёртка над штатным train-клиентом арены: build (если есть build.py) -> submit -> ожидание -> result.

Ожидание выполняет процесс, а не модель: запускай командой в фоне (run_in_background) и жди её завершения.
Все пути состояния — абсолютные и общие для всех исследователей.

  python measure.py --candidate ID --measurement ID [--subset curve|train|FILE.jsonl] [--example-id X ...] [--no-build]

Результат: runs/<measurement>.json (полный ответ train-сервиса) и runs/<measurement>.summary.json.
Код выхода 0 — измерение FINISHED и записано в журнал, 1 — FAILED/ошибка (статус сохранён в журнале).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CAMPAIGN = Path("/workspace/case/campaigns/c1")
DATASET = "ar04a-skill-select-v1"
CONDITIONS = "ar04a-metric-v1-runner-d4e3f8799ccc"
SUBSETS = {"curve": Path("/workspace/case/dataset/train_curve.jsonl"),
           "train": Path("/workspace/case/dataset/train.jsonl")}
TOKEN = "/run/secrets/arena/train-submit-token"


def run(module: str, *args: str) -> dict:
    out = subprocess.run([sys.executable, "-m", module, *args], cwd="/opt/arena", capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(f"{module} {args[0]} failed: {out.stderr.strip()[-2000:] or out.stdout.strip()[-2000:]}")
    return json.loads(out.stdout)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", required=True)
    p.add_argument("--measurement", required=True)
    p.add_argument("--subset", default="curve", help="curve | train | путь к своему jsonl (формат train.jsonl)")
    p.add_argument("--example-id", action="append")
    p.add_argument("--no-build", action="store_true", help="не запускать build (у кандидата нет build.py или квитанция уже есть)")
    p.add_argument("--journal", default=os.environ.get("ARENA_SEARCH_JOURNAL", "/search/search.sqlite3"))
    p.add_argument("--url", default=os.environ.get("ARENA_TRAIN_URL", "http://host.docker.internal:8070"))
    p.add_argument("--poll", type=int, default=30, help="период опроса статуса, с (опрашивает процесс, не модель)")
    a = p.parse_args()
    data = SUBSETS.get(a.subset, Path(a.subset))
    runs = CAMPAIGN / "runs"
    runs.mkdir(exist_ok=True)
    t0 = time.time()
    if not a.no_build:
        build = run("evaluator.build", "submit", "--journal", a.journal, "--candidate", a.candidate,
                    "--url", a.url, "--token-file", TOKEN, "--output", str(runs / f"{a.measurement}.build.json"))
        print("build submitted:", build.get("status"), flush=True)
        while build.get("status") == "RUNNING":  # build идёт асинхронно: ждём процессом, не моделью
            time.sleep(a.poll)
            build = run("evaluator.build", "status", "--digest", build["candidate_digest"], "--url", a.url,
                        "--token-file", TOKEN, "--output", str(runs / f"{a.measurement}.build.json"))
        print("build:", build.get("status"), json.dumps(build.get("error")), flush=True)
        if build.get("status") != "FINISHED":
            return 1
    args = ["submit", "--candidate", a.candidate, "--measurement", a.measurement, "--dataset", DATASET,
            "--conditions", CONDITIONS, "--train-data", str(data), "--url", a.url, "--token-file", TOKEN,
            "--journal", a.journal]
    for e in a.example_id or []:
        args += ["--example-id", e]
    sub = run("evaluator.train", *args)
    eid = sub.get("evaluation_id") or sub.get("id")
    print("submitted", eid, "total_wait_start", time.strftime("%H:%M:%S"), flush=True)
    while True:
        st = run("evaluator.train", "status", "--evaluation-id", eid, "--url", a.url, "--token-file", TOKEN)
        if st.get("status") in {"FINISHED", "FAILED"}:
            break
        time.sleep(a.poll)
    out = runs / f"{a.measurement}.json"
    res = run("evaluator.train", "result", "--evaluation-id", eid, "--measurement", a.measurement,
              "--url", a.url, "--token-file", TOKEN, "--output", str(out), "--journal", a.journal)
    m = res.get("metrics", {})
    summary = {"candidate": a.candidate, "measurement": a.measurement, "subset": a.subset, "evaluation_id": eid,
               "status": res.get("status"), "wall_seconds": round(time.time() - t0, 1), "metrics": m}
    (runs / f"{a.measurement}.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if res.get("status") == "FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
