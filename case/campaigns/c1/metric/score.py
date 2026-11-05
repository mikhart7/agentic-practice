"""Метрика кейса AR-04а: подбор навыка по запросу.

stdin  — {"example": {"id", "input", "reference"}, "answer": "<строка решателя>"}
stdout — {"score": float, "statistics": {...}}

reference — JSON-строка {"primary": id, "acceptable": [id, ...]}; релевантны primary и acceptable.
answer    — JSON-массив до 3 уникальных id навыков из каталога в порядке убывания уверенности.

score = 0.7 * acc@1 + 0.3 * nP@3
  acc@1 = 1, если первый id релевантен;
  nP@3  = |top3 ∩ rel| / min(3, |rel|) — precision@3, нормированная на число релевантных,
          чтобы при одном релевантном навыке максимум был 1, а не 1/3.

Невалидный ответ (не JSON-массив строк, больше 3 id, повторы, id не из каталога) получает 0:
это ошибка решателя. Повреждённый reference — ошибка оценщика, она не превращается в 0.
Правила зафиксированы до поиска (docs/adr/0003-metric.md).
"""
import json
import sys
from pathlib import Path

K = 3
W_ACC1, W_NP3 = 0.7, 0.3
CATALOG_IDS = frozenset(Path(__file__).with_name("catalog_ids.txt").read_text(encoding="utf-8").split())


def parse_reference(reference: str) -> set[str]:
    ref = json.loads(reference)
    rel = {ref["primary"], *ref["acceptable"]}
    if not rel <= CATALOG_IDS:
        raise ValueError(f"reference ids not in catalog: {sorted(rel - CATALOG_IDS)}")
    return rel


def parse_answer(answer: str) -> list[str] | None:
    """Ранжированный список id или None, если ответ невалиден."""
    try:
        ranked = json.loads(answer)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(ranked, list) or len(ranked) > K:
        return None
    if not all(isinstance(x, str) for x in ranked) or len(set(ranked)) != len(ranked):
        return None
    if not set(ranked) <= CATALOG_IDS:
        return None
    return ranked


def evaluate(reference: str, answer: str) -> dict:
    rel = parse_reference(reference)
    ranked = parse_answer(answer)
    if ranked is None:
        return {"score": 0.0, "statistics": {"valid": 0, "acc1": 0.0, "np3": 0.0}}
    acc1 = float(bool(ranked) and ranked[0] in rel)
    np3 = len(set(ranked) & rel) / min(K, len(rel))
    return {"score": W_ACC1 * acc1 + W_NP3 * np3, "statistics": {"valid": 1, "acc1": acc1, "np3": np3}}


def main() -> None:
    payload = json.load(sys.stdin)
    reference = payload["example"].get("reference")
    if not isinstance(reference, str):
        raise ValueError("metric requires a JSON-string reference")
    print(json.dumps(evaluate(reference, payload["answer"])))


if __name__ == "__main__":
    main()
