"""Тесты метрики. Обязательно — «жульнические» ответы, которые метрика должна ловить.

Метрику запускаем как арена: отдельным процессом, JSON через stdin/stdout, рабочий каталог /.
"""
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

METRIC = Path(__file__).parents[1]
SCORE = METRIC / "score.py"
ROOT = Path(__file__).parents[3]


def ref(primary: str, *acceptable: str) -> str:
    return json.dumps({"primary": primary, "acceptable": list(acceptable)})


def run(reference: str | None, answer: str, check: bool = True) -> subprocess.CompletedProcess:
    payload = {"example": {"id": "t", "input": "query", "reference": reference}, "answer": answer}
    return subprocess.run([sys.executable, str(SCORE)], input=json.dumps(payload), cwd="/",
                          capture_output=True, text=True, check=check)


def score(reference: str, answer) -> dict:
    answer = answer if isinstance(answer, str) else json.dumps(answer)
    return json.loads(run(reference, answer).stdout)


# --- корректные ответы ---

def test_perfect_answer_scores_one():
    assert score(ref("pdf-to-md"), ["pdf-to-md"])["score"] == pytest.approx(1.0)


def test_correct_top1_with_padding_still_one():
    # при одном релевантном nP@3 = 1/1, лишние кандидаты не штрафуются
    assert score(ref("pdf-to-md"), ["pdf-to-md", "marqpdf", "ocrspace"])["score"] == pytest.approx(1.0)


def test_acceptable_alternative_counts_as_hit():
    out = score(ref("pdfsamenvoegen", "marqpdf"), ["marqpdf", "pdfsamenvoegen"])
    assert out["statistics"]["acc1"] == 1.0
    assert out["score"] == pytest.approx(1.0)


def test_hit_at_rank_two_gets_partial_credit():
    out = score(ref("pdf-to-md"), ["marqpdf", "pdf-to-md"])
    assert out["statistics"] == {"valid": 1, "acc1": 0.0, "np3": 1.0}
    assert out["score"] == pytest.approx(0.3)


def test_partial_coverage_of_several_relevant():
    out = score(ref("google-cal-mcp", "mcp-icloud-caldav", "calendarmcp"), ["calendarmcp", "meet-bot", "sync-day"])
    assert out["statistics"]["np3"] == pytest.approx(1 / 3)
    assert out["score"] == pytest.approx(0.7 + 0.3 / 3)


def test_miss_scores_zero_but_valid():
    out = score(ref("pdf-to-md"), ["serpapi-mcp", "miapi", "gannet-mcp"])
    assert out == {"score": 0.0, "statistics": {"valid": 1, "acc1": 0.0, "np3": 0.0}}


def test_empty_list_is_valid_zero():
    assert score(ref("pdf-to-md"), [])["statistics"]["valid"] == 1


def test_better_ranking_scores_higher():
    r = ref("pdf-to-md")
    assert score(r, ["pdf-to-md", "marqpdf"])["score"] > score(r, ["marqpdf", "pdf-to-md"])["score"] \
        > score(r, ["marqpdf", "ocrspace"])["score"]


# --- жульнические и сломанные ответы: 0 ---

@pytest.mark.parametrize("answer", [
    "pdf-to-md",                                   # голая строка вместо JSON-массива
    "not json at all",
    '{"answer": ["pdf-to-md"]}',                   # объект вместо массива
    '"pdf-to-md"',                                 # JSON-строка
    "",
    json.dumps([["pdf-to-md"]]),                   # вложенный массив
    json.dumps([1, 2, 3]),                         # не строки
    json.dumps(["pdf-to-md", "marqpdf", "ocrspace", "isomor"]),  # больше 3: перебор вариантов
    json.dumps(["pdf-to-md", "pdf-to-md", "pdf-to-md"]),         # повторы раздувают nP@3
    json.dumps(["pdf-to-md", "not-a-skill"]),      # id не из каталога
    json.dumps(["PDF-TO-MD"]),                     # регистр не нормализуется
])
def test_invalid_answers_get_zero(answer):
    out = score(ref("pdf-to-md"), answer)
    assert out == {"score": 0.0, "statistics": {"valid": 0, "acc1": 0.0, "np3": 0.0}}


def test_whole_catalog_cannot_be_returned():
    ids = (METRIC / "catalog_ids.txt").read_text().split()
    assert score(ref("pdf-to-md"), ids)["score"] == 0.0


# --- ошибки оценщика не превращаются в выдуманный 0 ---

@pytest.mark.parametrize("reference", [None, "not json", json.dumps({"primary": "no-such-skill", "acceptable": []})])
def test_broken_reference_is_an_error(reference):
    assert run(reference, json.dumps(["pdf-to-md"]), check=False).returncode != 0


# --- согласованность с данными ---

def test_catalog_ids_match_catalog():
    catalog = {json.loads(l)["id"] for l in (ROOT / "case/assets/catalog.jsonl").open()}
    assert set((METRIC / "catalog_ids.txt").read_text().split()) == catalog


def test_all_train_references_are_valid():
    # идеальный ответ — основной навык и все допустимые в топ-3
    for line in (ROOT / "case/dataset/train.jsonl").open():
        row = json.loads(line)
        r = json.loads(row["reference"])
        assert score(row["reference"], [r["primary"], *r["acceptable"]][:3])["score"] == pytest.approx(1.0)


def test_primary_alone_misses_np3_when_alternatives_exist():
    # nP@3 вознаграждает полноту топ-3: без допустимой альтернативы — 0.7 + 0.3 * 1/2
    assert score(ref("pdfsamenvoegen", "marqpdf"), ["pdfsamenvoegen"])["score"] == pytest.approx(0.85)


def test_memorized_train_answers_do_not_transfer_across_families():
    """Подгонка под известные экземпляры: таблица «запрос → ответ», выученная на одних
    семействах, ничего не даёт на других — перефразы одного намерения не пересекают split."""
    rows = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "case/dataset/train.jsonl").open()}
    families = defaultdict(list)
    for line in (ROOT / "case/dataset/train.meta.jsonl").open():
        m = json.loads(line)
        families[m["family"]].append(rows[m["id"]])
    names = sorted(families)
    random.Random(0).shuffle(names)
    seen, held = names[: len(names) // 2], names[len(names) // 2:]
    lookup = {r["input"]: json.loads(r["reference"])["primary"] for f in seen for r in families[f]}
    held_rows = [r for f in held for r in families[f]]
    hits = [score(r["reference"], [lookup[r["input"]]] if r["input"] in lookup else [])["score"]
            for r in held_rows[:40]]
    assert sum(hits) == 0.0
