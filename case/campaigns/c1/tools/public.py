#!/usr/bin/env python3
"""Одна public-проверка кандидата (ровно один кандидат за запрос, один раз на кандидата).
restore снимка из журнала -> pack -> журнал begin(split=public) -> submit -> wait -> finish (только score).
Запускает оркестратор. Public возвращает общий score; ресурсы/детали не сохраняются.
  python public.py --candidate ID
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

CAMP = Path("/workspace/case/campaigns/c1")
JOURNAL = os.environ.get("ARENA_SEARCH_JOURNAL", "/search/search.sqlite3")
URL = os.environ.get("ARENA_PUBLIC_URL", "http://host.docker.internal:8090")
TOKEN = "/run/secrets/arena/public-submit-token"
DATASET, SUBSET = "ar04a-skill-select-v1", "public-380"
CONDITIONS = "ar04a-metric-v1-runner-d4e3f8799ccc"


def sh(*a, check=True):
    r = subprocess.run([sys.executable, "-m", *a], cwd="/opt/arena", capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"{a[:3]} failed: {(r.stderr or r.stdout)[-1500:]}")
    return r


p = argparse.ArgumentParser(); p.add_argument("--candidate", required=True); a = p.parse_args()
cid = a.candidate; out = CAMP / "runs"; mid = f"{cid}-public"
with tempfile.TemporaryDirectory(dir=str(CAMP / "runs")) as tmp:
    d = Path(tmp) / cid
    sh("evaluator.search", "--journal", JOURNAL, "restore", "--candidate", cid, "--directory", str(d))
    bundle = out / f"{cid}.public-bundle.json"
    sh("evaluator.client", "pack", "--candidate", f"{cid}={d}", "--output", str(bundle))
sh("evaluator.search", "--journal", JOURNAL, "begin", "--id", mid, "--candidate", cid, "--split", "public",
   "--dataset", DATASET, "--subset", SUBSET, "--conditions", CONDITIONS, "--job", URL)
sub = sh("evaluator.client", "submit", "--bundle", str(bundle), "--url", URL, "--token-file", TOKEN, check=False)
print("submit:", sub.returncode, (sub.stdout or sub.stderr)[-500:], flush=True)
if sub.returncode:
    sh("evaluator.search", "--journal", JOURNAL, "finish", "--id", mid, "--error", "evaluation_failed")
    raise SystemExit(1)
res_path = out / f"{mid}.json"
w = sh("evaluator.client", "wait", "--output", str(res_path), "--poll-seconds", "60", "--url", URL, "--token-file", TOKEN, check=False)
res = json.loads(res_path.read_text()) if res_path.exists() else {}
print("final:", json.dumps(res)[:600], flush=True)
score = None
if res.get("status") == "complete":
    for k in ("score", "mean_score", "aggregate_score"):
        if isinstance(res.get(k), (int, float)): score = res[k]; break
if score is not None:
    sh("evaluator.search", "--journal", JOURNAL, "finish", "--id", mid, "--score", repr(float(score)))
    print("PUBLIC", cid, score)
elif res.get("status") == "complete":
    print("complete, но score не найден в ответе — измерение оставлено running, разобрать вручную:", res_path)
    raise SystemExit(2)
else:
    sh("evaluator.search", "--journal", JOURNAL, "finish", "--id", mid, "--error", "evaluation_failed")
    raise SystemExit(1)
