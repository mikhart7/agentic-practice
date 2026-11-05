"""Проверка замороженного пакета метрики через штатный путь арены (load_metric -> evaluate_answer -> aggregate_results).

Входы — только синтетические примеры и открытый train_curve. Ожидания записаны до запуска.
Запуск (окружение арены): python case/campaigns/c1/checks/metric_pipeline.py
"""
import json
import sys
from pathlib import Path

from evaluator.contracts import Example
from evaluator.metric_package import load_metric, metric_package_provenance
from evaluator.metrics import aggregate_results, evaluate_answer
from evaluator.reliability import empty_usage

CASE = Path(__file__).resolve().parents[3]
PACKAGE = CASE / "campaigns/c1/metric"
CATALOG = [json.loads(line)["id"] for line in (CASE / "assets/catalog.jsonl").open(encoding="utf-8")]


def Ex(id, reference):
    return Example(id=id, input="synthetic", reference=reference)


def ref(primary, acceptable=()):
    return json.dumps({"primary": primary, "acceptable": list(acceptable)})


metric = load_metric(PACKAGE)
a, b, c, d = CATALOG[:4]
CASES = [
    # (reference, answer, ожидаемый score, acc1, np3)
    (ref(a), json.dumps([a]), 1.0, 1.0, 1.0),
    (ref(a), json.dumps([b, a]), 0.3, 0.0, 1.0),
    (ref(a), json.dumps([b, c, d]), 0.0, 0.0, 0.0),
    (ref(a, [b]), json.dumps([a]), 0.7 + 0.3 * 0.5, 1.0, 0.5),
    (ref(a, [b]), json.dumps([a, b]), 1.0, 1.0, 1.0),
    (ref(a, [b]), json.dumps([c, b]), 0.3 * 0.5, 0.0, 0.5),
    (ref(a), json.dumps([]), 0.0, 0.0, 0.0),
    (ref(a), json.dumps([a, a]), 0.0, 0.0, 0.0),
    (ref(a), json.dumps([a, b, c, d]), 0.0, 0.0, 0.0),
    (ref(a), json.dumps(["no-such-skill"]), 0.0, 0.0, 0.0),
    (ref(a), "not json", 0.0, 0.0, 0.0),
    (ref(a), json.dumps([a.upper()]), 0.0, 0.0, 0.0),
]
failures = []
results = []
for i, (reference, answer, score, acc1, np3) in enumerate(CASES):
    usage = empty_usage()
    result = evaluate_answer(metric, Ex(f"s{i}", reference), answer, usage=usage)
    results.append({"example_id": f"s{i}", "answer": answer, **result,
                    "resources": {"solver": {"wall_seconds": 0.0, "usage": empty_usage()},
                                  "judge": {"wall_seconds": 0.0, "usage": usage}}})
    got = (result["score"], result["statistics"]["acc1"], result["statistics"]["np3"])
    if any(abs(x - y) > 1e-12 for x, y in zip(got, (score, acc1, np3))):
        failures.append((i, got, (score, acc1, np3)))
expected_mean = sum(case[2] for case in CASES) / len(CASES)
aggregate = aggregate_results(metric, results, usage=empty_usage())
if abs(aggregate - expected_mean) > 1e-12:
    failures.append(("aggregate", aggregate, expected_mean))

# повреждённый reference — ошибка оценщика, а не нулевой score
for bad in ("not json", json.dumps({"primary": "no-such-skill", "acceptable": []}), None):
    try:
        evaluate_answer(metric, Ex("bad", bad), json.dumps([a]), usage=empty_usage())
        failures.append(("corrupt reference accepted", bad))
    except Exception:
        pass

# открытый train_curve: эталонный ответ даёт ровно 1.0, пустой ответ — ровно 0.0
rows = [json.loads(line) for line in (CASE / "dataset/train_curve.jsonl").open(encoding="utf-8")]
oracle, empty = [], []
for row in rows:
    r = json.loads(row["reference"])
    best = [r["primary"], *r["acceptable"]][:3]
    for answer, bucket in ((json.dumps(best), oracle), (json.dumps([]), empty)):
        res = evaluate_answer(metric, Ex(row["id"], row["reference"]), answer, usage=empty_usage())
        bucket.append({"example_id": row["id"], "answer": answer, **res,
                       "resources": {"solver": {"wall_seconds": 0.0, "usage": empty_usage()},
                                     "judge": {"wall_seconds": 0.0, "usage": empty_usage()}}})
oracle_score = aggregate_results(metric, oracle, usage=empty_usage())
empty_score = aggregate_results(metric, empty, usage=empty_usage())
if oracle_score != 1.0 or empty_score != 0.0:
    failures.append(("train_curve", oracle_score, empty_score))

print(json.dumps({
    "metric_package": metric_package_provenance(PACKAGE), "direction": metric.direction,
    "synthetic_cases": len(CASES), "train_curve_examples": len(rows),
    "oracle_score": oracle_score, "empty_score": empty_score, "failures": failures,
}, ensure_ascii=False))
sys.exit(1 if failures else 0)
