#!/usr/bin/env python3
"""Программная проверка задач навыка после прогона агента в харнесе.

Для каждой задачи из tasks.json:
  1) агент вызвал навык: в журнале вызовов (SELECT_SKILL_LOG) есть вызов с этим запросом;
  2) результат валиден: в answer-файле ровно один id, и он есть в каталоге;
  3) агент использовал результат навыка: ответ совпадает с top-1 последнего вызова по этому запросу.
Совпадение с эталоном печатается для сведения: задача проверяет вызов навыка, а не качество ранжирования.

  python skill/tests/check.py --workdir <каталог прогона> --log <calls.jsonl> [--catalog case/assets/catalog.jsonl]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", type=Path, required=True, help="где агент писал answer-*.txt")
    p.add_argument("--log", type=Path, required=True, help="журнал вызовов навыка (SELECT_SKILL_LOG)")
    p.add_argument("--catalog", type=Path, default=HERE.parents[1] / "case/assets/catalog.jsonl")
    p.add_argument("--tasks", type=Path, default=HERE / "tasks.json")
    a = p.parse_args()
    ids = {json.loads(line)["id"] for line in a.catalog.read_text(encoding="utf-8").splitlines() if line.strip()}
    calls = [json.loads(line) for line in a.log.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if a.log.exists() else []
    failed = 0
    for t in json.loads(a.tasks.read_text(encoding="utf-8")):
        mine = [c for c in calls if c["query"].strip().strip("\"'").lower() == t["request"].lower()]
        answer_path = a.workdir / t["answer_file"]
        answer = answer_path.read_text(encoding="utf-8").strip().strip("`\"'") if answer_path.exists() else None
        checks = {
            "skill called": bool(mine),
            "valid id": answer in ids,
            "answer = skill top-1": bool(mine) and answer == mine[-1]["top"][0]["id"],
        }
        ok = all(checks.values())
        failed += not ok
        detail = ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in checks.items())
        print(f"{t['id']} {'PASS' if ok else 'FAIL'} | {detail} | answer {answer!r}, expected {t['expected']!r}"
              f" ({'match' if answer == t['expected'] else 'differs'})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
