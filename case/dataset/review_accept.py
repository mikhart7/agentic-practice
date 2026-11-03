"""Лист ручной проверки разметки train (primary и acceptable) до заморозки условий кампании.

Берутся все семейства с непустым acceptable и случайные семейства без него: там ошибка вероятнее
всего в пропущенной альтернативе. Для каждого семейства показаны все навыки его кластера,
чтобы было видно, какие ещё навыки могли бы подойти.
  python case/dataset/review_accept.py   # -> results/data-review/accept-review.md
"""
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parents[1] / "results" / "data-review" / "accept-review.md"
N_WITHOUT, SEED = 15, 3


def load(path: Path) -> dict[str, dict]:
    return {(row := json.loads(line))["id"]: row for line in path.open(encoding="utf-8")}


def main() -> None:
    catalog = load(HERE.parent / "assets" / "catalog.jsonl")
    cluster_of = {i: m["cluster"] for i, m in load(HERE / "catalog_meta.jsonl").items()}
    meta = load(HERE / "train.meta.jsonl")
    families = defaultdict(list)
    for row in load(HERE / "train.jsonl").values():
        families[meta[row["id"]]["family"]].append(row)

    with_acc = sorted(f for f, rows in families.items() if json.loads(rows[0]["reference"])["acceptable"])
    without = sorted(set(families) - set(with_acc))
    chosen = with_acc + sorted(random.Random(SEED).sample(without, N_WITHOUT))

    lines = [
        "# Ручная проверка разметки train",
        "",
        f"Сгенерировано `python case/dataset/review_accept.py`: {len(with_acc)} семейств с acceptable "
        f"(все) и {N_WITHOUT} без него (случайно, seed {SEED}).",
        "",
        "В каждом семействе отметьте вердикт и, если не согласны, напишите, что исправить:",
        "- `[x] верно` — primary правильный, список acceptable полный и без лишних;",
        "- `[x] исправить` — укажите, какой навык добавить или убрать в acceptable, либо заменить primary.",
        "",
    ]
    for family in chosen:
        rows = families[family]
        ref = json.loads(rows[0]["reference"])
        cluster = cluster_of[ref["primary"]]
        lines += [f"## {family}", "", f"Намерение: *{meta[rows[0]['id']]['intent']}*. Кластер `{cluster}`.", ""]
        lines += [f"- `{meta[r['id']]['style']}`: {r['input']}" for r in rows]
        lines += ["", "| навык | описание | разметка |", "|---|---|---|"]
        for skill_id, c in cluster_of.items():
            if c == cluster:
                mark = "**primary**" if skill_id == ref["primary"] else "acceptable" if skill_id in ref["acceptable"] else ""
                lines.append(f"| `{skill_id}` | {catalog[skill_id]['description']} | {mark} |")
        lines += ["", "- [ ] верно", "- [ ] исправить: ", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{OUT}: {len(chosen)} семейств")


if __name__ == "__main__":
    main()
