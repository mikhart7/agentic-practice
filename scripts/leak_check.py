"""Проверка перед push: нет ли текста запросов public/private в новых коммитах.
Закрытые данные доступны только root, поэтому они подаются на stdin:
  sudo cat ~/arena-private/{public,private}.jsonl | python3 scripts/leak_check.py [origin/main..main]
Совпадением считается любая общая 6-словная n-грамма. case/dataset/train* пропускается: это train.
"""
import json
import re
import subprocess
import sys

N = 6


def ngrams(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i:i + N]) for i in range(len(words) - N + 1)}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL)


held = set()
for line in sys.stdin:
    if line.strip():
        held |= ngrams(json.loads(line)["input"])
if not held:
    sys.exit("на stdin нет запросов public/private — проверка не выполнена")

revs = git("rev-list", sys.argv[1] if len(sys.argv) > 1 else "origin/main..main").split()
leaks = 0
for rev in revs:
    for path in git("diff-tree", "--no-commit-id", "--name-only", "-r", rev).split():
        if path.startswith("case/dataset/train"):
            continue
        try:
            hits = ngrams(git("show", f"{rev}:{path}")) & held
        except subprocess.CalledProcessError:
            continue  # файл удалён в этом коммите
        if hits:
            leaks += 1
            print(f"{rev[:7]} {path}: {sorted(hits)[:3]}")
print(f"leak check: {len(revs)} new commits, leaks: {leaks}")
sys.exit(1 if leaks else 0)
