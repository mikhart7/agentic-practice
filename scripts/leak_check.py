"""Проверка перед push: нет ли текста запросов public/private в новых коммитах.
Закрытые данные доступны только root, поэтому они подаются на stdin:
  sudo cat ~/arena-private/{public,private}.jsonl | python3 scripts/leak_check.py [origin/main..main]
  sudo cat ~/arena-private/{public,private}.jsonl | sudo python3 scripts/leak_check.py --paths <каталог или файл>...
Совпадением считается любая общая 6-словная n-грамма. case/dataset/train* пропускается: это train.
N-граммы held-out, которые есть и в train, не считаются утечкой: они уже опубликованы вместе с train
(иначе срабатывают копии train в пакетах кандидатов). Исключённые n-граммы печатаются.
Режим --paths проверяет файлы вне git: транскрипты агентов, выгрузки перед публикацией.
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
    # бинарные файлы (журнал search.sqlite3) читаются с пропуском невалидных байтов, как в --paths
    out = subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)
    return out.decode("utf-8", errors="ignore")


held = set()
for line in sys.stdin:
    if line.strip():
        held |= ngrams(json.loads(line)["input"])
if not held:
    sys.exit("на stdin нет запросов public/private — проверка не выполнена")

# n-граммы, которые есть и в train, уже опубликованы вместе с train и утечкой не являются:
# без этого срабатывают копии train в пакетах кандидатов (fit.jsonl и т. п.) и журнал со снимками
from pathlib import Path
TRAIN = Path(__file__).resolve().parents[1] / "case/dataset/train.jsonl"
shared = held & {g for line in TRAIN.open(encoding="utf-8") if line.strip() for g in ngrams(json.loads(line)["input"])}
held -= shared
if shared:
    print(f"исключены n-граммы, которые есть в опубликованном train ({len(shared)}): {sorted(shared)}")

if len(sys.argv) > 1 and sys.argv[1] == "--paths":
    from pathlib import Path
    files = [f for a in sys.argv[2:] for f in ([Path(a)] if Path(a).is_file() else Path(a).rglob("*")) if f.is_file()]
    leaks = 0
    for f in files:
        hits = ngrams(f.read_text(encoding="utf-8", errors="ignore")) & held
        if hits:
            leaks += 1
            print(f"{f}: {len(hits)} n-grams")
    print(f"leak check: {len(files)} files, with leaks: {leaks}")
    sys.exit(1 if leaks else 0)

revs = git("rev-list", sys.argv[1] if len(sys.argv) > 1 else "origin/main..main").split()
leaks = 0
for rev in revs:
    for path in git("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", rev).split():
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
