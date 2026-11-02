"""Проверка пула запросов и детерминированное деление на train / public / private.

Пул сгенерирован LLM по промпту из generation_prompt.md и хранится у оператора вне репозитория:
каждый блок — одно семейство (намерение) и 4 перефразы разных стилей.

  uv run case/dataset/generate.py check --pool ~/arena-private/pool
  uv run case/dataset/generate.py split --pool ~/arena-private/pool --seed 1 \
      --train-dir case/dataset --private-dir ~/arena-private

Деление: у каждого навыка ровно 2 семейства, одно идёт в train, другое — в public или private.
Внутри кластера public/private чередуются, чтобы оба раздела покрывали все кластеры.
Формат записей — как требует оценщик арены: {"id", "input", "reference"}, где reference —
JSON-строка {"primary", "acceptable"}. Метаданные (family, style, cluster, tags) — в *.meta.jsonl.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "case/assets/catalog.jsonl"
META = ROOT / "case/dataset/catalog_meta.jsonl"
STYLES = {"cmd", "verbose", "indirect", "casual", "typo", "question"}
FAMILIES_PER_SKILL = 2
QUERIES_PER_FAMILY = 4
HEADER = re.compile(r"^@ (\S+) \| accept: ?(.*?) \| intent: (.+)$")
STOP = set("a an the and or for to of in on with by from as at is it be via your our my any no not "
           "up into out over that this what which who mcp server ai agents agent tools free key".split())


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def pool_files(pool: Path) -> list[Path]:
    return sorted(pool.glob("*.txt"))


def pool_digest(pool: Path) -> str:
    h = hashlib.sha256()
    for f in pool_files(pool):
        h.update(f.name.encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def parse(pool: Path) -> list[dict]:
    families, cur = [], None
    for f in pool_files(pool):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            where = f"{f.name}:{n}"
            if not line.strip():
                continue
            if m := HEADER.match(line):
                accept = [a.strip() for a in m[2].split(",") if a.strip()]
                cur = {"skill": m[1], "accept": accept, "intent": m[3].strip(), "queries": [], "where": where}
                families.append(cur)
            elif cur and (m := re.match(r"^(\w+): (.+)$", line)):
                cur["queries"].append({"style": m[1], "text": m[2].strip()})
            else:
                raise SystemExit(f"{where}: unparsable line: {line!r}")
    return families


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 2}


def check(families: list[dict], partial: bool) -> list[str]:
    catalog = {r["id"]: r for r in load_jsonl(CATALOG)}
    errors, seen = [], {}
    per_skill = Counter(f["skill"] for f in families)
    for f in families:
        w, s = f["where"], f["skill"]
        if s not in catalog:
            errors.append(f"{w}: unknown skill {s!r}")
        for a in f["accept"]:
            if a not in catalog or a == s:
                errors.append(f"{w}: bad accept id {a!r}")
        styles = [q["style"] for q in f["queries"]]
        if len(styles) != QUERIES_PER_FAMILY:
            errors.append(f"{w}: {len(styles)} queries, need {QUERIES_PER_FAMILY}")
        if set(styles) - STYLES or len(set(styles)) != len(styles) or "indirect" not in styles:
            errors.append(f"{w}: styles {styles} must be distinct, known and include indirect")
        for q in f["queries"]:
            key = q["text"].lower()
            if key in seen:
                errors.append(f"{w}: duplicate query, first at {seen[key]}")
            seen[key] = w
    for s in catalog:
        if per_skill[s] != FAMILIES_PER_SKILL and not (partial and per_skill[s] == 0):
            errors.append(f"skill {s!r}: {per_skill[s]} families, need {FAMILIES_PER_SKILL}")
    return errors


def indirect_overlap(families: list[dict]) -> tuple[float, list[tuple[float, str, str]]]:
    """Доля содержательных слов indirect-запроса, совпадающих с name+description своего навыка."""
    catalog = {r["id"]: r for r in load_jsonl(CATALOG)}
    rows = []
    for f in families:
        skill = catalog.get(f["skill"])
        if not skill:
            continue
        skill_tokens = tokens(skill["name"] + " " + skill["description"])
        for q in f["queries"]:
            if q["style"] == "indirect" and (qt := tokens(q["text"])):
                rows.append((len(qt & skill_tokens) / len(qt), f["skill"], q["text"]))
    mean = sum(r[0] for r in rows) / len(rows) if rows else 0.0
    return mean, sorted(rows, reverse=True)


def split(families: list[dict], seed: int) -> dict[str, list[dict]]:
    cluster = {r["id"]: r["cluster"] for r in load_jsonl(META)}
    rng = random.Random(seed)
    by_skill = defaultdict(list)
    for f in families:
        by_skill[f["skill"]].append(f)
        f["family"] = f"{f['skill']}#{len(by_skill[f['skill']])}"
    by_cluster = defaultdict(list)
    for skill in sorted(by_skill):
        by_cluster[cluster[skill]].append(skill)
    out = {"train": [], "public": [], "private": []}
    for c in sorted(by_cluster):
        skills = by_cluster[c][:]
        rng.shuffle(skills)
        heldout = ["public", "private"] if rng.random() < 0.5 else ["private", "public"]
        for k, skill in enumerate(skills):
            fams = by_skill[skill][:]
            rng.shuffle(fams)
            out["train"].append(fams[0])
            out[heldout[k % 2]].append(fams[1])
    return out


def records(families: list[dict], split_name: str) -> tuple[list[dict], list[dict]]:
    cluster = {r["id"]: r["cluster"] for r in load_jsonl(META)}
    rows, meta = [], []
    for f in sorted(families, key=lambda f: f["family"]):
        for q in f["queries"]:
            qid = f"{split_name}-" + hashlib.sha256(q["text"].encode()).hexdigest()[:12]
            ref = {"primary": f["skill"], "acceptable": f["accept"]}
            rows.append({"id": qid, "input": q["text"], "reference": json.dumps(ref)})
            tags = ["hard"] if cluster[f["skill"]] != "misc" else []
            meta.append({"id": qid, "family": f["family"], "style": q["style"],
                         "cluster": cluster[f["skill"]], "intent": f["intent"], "tags": tags})
    return rows, meta


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["check", "split"])
    p.add_argument("--pool", type=Path, default=Path.home() / "arena-private/pool")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--partial", action="store_true", help="check: не требовать покрытия всех навыков")
    p.add_argument("--train-dir", type=Path, default=ROOT / "case/dataset")
    p.add_argument("--private-dir", type=Path, default=Path.home() / "arena-private")
    a = p.parse_args()
    families = parse(a.pool)
    errors = check(families, a.partial and a.cmd == "check")
    for e in errors:
        print(e, file=sys.stderr)
    n_queries = sum(len(f["queries"]) for f in families)
    mean, worst = indirect_overlap(families)
    print(f"pool sha256 {pool_digest(a.pool)}: {len(families)} families, {n_queries} queries, "
          f"{len(errors)} errors; indirect overlap with own description {mean:.3f}")
    for score, skill, text in worst[:5]:
        print(f"  overlap {score:.2f} {skill}: {text}")
    if errors:
        raise SystemExit(1)
    if a.cmd == "split":
        parts = split(families, a.seed)
        for name, fams in parts.items():
            rows, meta = records(fams, name)
            base = a.train_dir if name == "train" else a.private_dir
            write_jsonl(base / f"{name}.jsonl", rows)
            write_jsonl(base / f"{name}.meta.jsonl", meta)
            print(f"{name}: {len(fams)} families, {len(rows)} queries -> {base / (name + '.jsonl')}")


if __name__ == "__main__":
    main()
