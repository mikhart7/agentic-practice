"""Тесты CLI навыка без харнеса.

  uv run --no-project --with-requirements skill/scripts/requirements.txt --with pytest==8.4.2 python -m pytest skill/tests

Тесты с моделями пропускаются, если весов нет: SELECT_SKILL_MODELS, skill/models или case/assets/models.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "skill/scripts/select_skill.py"
CATALOG = ROOT / "case/assets/catalog.jsonl"
TASKS = json.loads((ROOT / "skill/tests/tasks.json").read_text())
MODELS = next((p for p in [Path(os.environ.get("SELECT_SKILL_MODELS", "/nonexistent")), ROOT / "skill/models",
                           ROOT / "case/assets/models"] if (p / "bge-base-en-v1.5/model.safetensors").exists()), None)
needs_models = pytest.mark.skipif(MODELS is None, reason="model weights not downloaded")


def run(*args, env=None):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, env=env)


@needs_models
def test_tasks_rank_expected_skill_first(tmp_path):
    queries = tmp_path / "q.txt"
    queries.write_text("\n".join(t["request"] for t in TASKS))
    log = tmp_path / "calls.jsonl"
    env = {**os.environ, "SELECT_SKILL_LOG": str(log)}
    out = run("--catalog", str(CATALOG), "--models-dir", str(MODELS), "--queries-file", str(queries), env=env)
    assert out.returncode == 0, out.stderr
    ids = {json.loads(line)["id"] for line in CATALOG.read_text().splitlines() if line.strip()}
    results = [json.loads(line) for line in out.stdout.splitlines()]
    for task, res in zip(TASKS, results):
        assert res["query"] == task["request"]
        assert len(res["top"]) == 3 and len({t["id"] for t in res["top"]}) == 3
        assert all(t["id"] in ids for t in res["top"])
        assert res["top"][0]["id"] == task["expected"]
    assert len(log.read_text().splitlines()) == len(TASKS)


@needs_models
def test_k_option(tmp_path):
    out = run("--catalog", str(CATALOG), "--models-dir", str(MODELS), "--query", TASKS[0]["request"], "--k", "5")
    assert out.returncode == 0, out.stderr
    assert len(json.loads(out.stdout)["top"]) == 5


def test_rejects_duplicate_ids(tmp_path):
    bad = tmp_path / "cat.jsonl"
    row = json.dumps({"id": "a", "name": "a", "description": "x"})
    bad.write_text(row + "\n" + row + "\n")
    out = run("--catalog", str(bad), "--query", "anything")
    assert out.returncode != 0 and "duplicate" in out.stderr


def test_rejects_missing_fields(tmp_path):
    bad = tmp_path / "cat.jsonl"
    bad.write_text(json.dumps({"id": "a", "name": "a"}) + "\n")
    out = run("--catalog", str(bad), "--query", "anything")
    assert out.returncode != 0 and "missing fields" in out.stderr
