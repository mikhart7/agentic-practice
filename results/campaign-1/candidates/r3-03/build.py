#!/usr/bin/env python3
"""build: подбор числа кандидатов N и веса смешивания w первой стадии и кросс-энкодера по записям train.

stdin  - {"assets_dir": "/assets", "build_dir": "/output", ...}
Читает fit.jsonl рядом со скриптом (запросы train вне train_curve и множества релевантных id; происхождение - README).
Для каждого запроса: топ-NMAX лексики r1-03, оценки кросс-энкодера для пар (запрос, name+description).
Перебирает сетку (N, w), выбирает максимум метрики 0.7*acc@1 + 0.3*nP@3 (с усреднением по соседним w).
/output: params.json (для solve), report.json (сетка, время, число запросов).
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lexical  # noqa: E402
import rerank  # noqa: E402

MODEL = "ms-marco-MiniLM-L6-v2"
NMAX = 20
NS = [3, 5, 8, 10, 15, 20]
WS = [i / 20 for i in range(21)]
DEADLINE = 420   # секунд на сбор оценок; остаток таймаута 600 с - запас
MIN_QUERIES = 100


def metric(order_ids: list[str], rel: set[str]) -> float:
    top = order_ids[:3]
    acc1 = float(bool(top) and top[0] in rel)
    np3 = len(set(top) & rel) / min(3, len(rel))
    return 0.7 * acc1 + 0.3 * np3


def main() -> None:
    task = json.load(sys.stdin)
    assets, out = Path(task["assets_dir"]), Path(task["build_dir"])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    catalog = lexical.load_catalog(str(assets))
    stage = lexical.FirstStage(catalog)
    model = rerank.load_model(str(assets), MODEL)
    load_s = time.time() - t0
    rows = []
    for line in (HERE / "fit.jsonl").open(encoding="utf-8"):
        if time.time() - t0 > DEADLINE:
            break
        rec = json.loads(line)
        ranked, scores = stage.rank(rec["input"])
        cand = ranked[:NMAX]
        ce = rerank.cross_scores(model, rec["input"], [rerank.doc_text(catalog[i]) for i in cand])
        rows.append(([catalog[i]["id"] for i in cand], [scores[i] for i in cand], ce, set(rec["relevant"])))
    collect_s = time.time() - t0
    if len(rows) < MIN_QUERIES:
        raise RuntimeError(f"only {len(rows)} fit queries scored in {collect_s:.0f}s")

    grid = {}
    for n in NS:
        for w in WS:
            tot = 0.0
            for ids, lex, ce, rel in rows:
                order = rerank.mixed_order(lex[:n], ce[:n], w)
                tot += metric([ids[k] for k in order], rel)
            grid[(n, w)] = tot / len(rows)
    # сглаживание по соседним w, чтобы не выбирать острый шум
    best, best_s = None, -1.0
    for n in NS:
        for j, w in enumerate(WS):
            nb = [grid[(n, WS[k])] for k in (j - 1, j, j + 1) if 0 <= k < len(WS)]
            s = sum(nb) / len(nb)
            if s > best_s + 1e-12:
                best, best_s = (n, w), s
    n, w = best
    params = {"model": MODEL, "n": n, "w": w}
    (out / "params.json").write_text(json.dumps(params))
    report = {
        "params": params, "fit_queries": len(rows), "load_seconds": round(load_s, 1), "collect_seconds": round(collect_s, 1),
        "fit_score_selected": grid[best], "fit_score_smoothed": best_s,
        "fit_score_lexical_only": grid[(20, 1.0)], "fit_score_ce_only_n20": grid[(20, 0.0)],
        "grid": {f"n={a},w={b:.2f}": round(v, 4) for (a, b), v in grid.items()},
    }
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "grid"}))


if __name__ == "__main__":
    main()
