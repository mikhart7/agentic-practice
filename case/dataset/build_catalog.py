"""Сборка фиксированного каталога навыков из официального реестра MCP.

Три шага, только stdlib:

  # 1. Снимок последних активных версий реестра (не коммитится, нужен только для отбора)
  uv run case/dataset/build_catalog.py snapshot --out /tmp/registry.jsonl

  # 2. Кандидаты по кластерам из catalog_selection.toml — для ручного отбора
  uv run case/dataset/build_catalog.py candidates --snapshot /tmp/registry.jsonl --cluster pdf

  # 3. Каталог из отобранных серверов с закреплёнными версиями
  #    case/assets/catalog.jsonl — то, что видит решатель (id, name, description);
  #    case/dataset/catalog_meta.jsonl — кластер и источник, решателю не передаются
  uv run case/dataset/build_catalog.py build

Шаг 3 воспроизводим: он читает только пары name@version из catalog_selection.toml.
"""
import argparse
import json
import random
import re
import sys
import time
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.modelcontextprotocol.io/v0"
SELECTION = Path(__file__).with_name("catalog_selection.toml")
OFFICIAL = "io.modelcontextprotocol.registry/official"


def get(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def snapshot(out: Path) -> None:
    cursor, n = None, 0
    with out.open("w", encoding="utf-8") as f:
        while True:
            q = {"limit": 100, "version": "latest"}
            if cursor:
                q["cursor"] = cursor
            page = get(f"{REGISTRY}/servers?{urllib.parse.urlencode(q)}")
            for item in page["servers"]:
                if item["_meta"][OFFICIAL].get("status") == "active":
                    f.write(json.dumps(item["server"], ensure_ascii=False) + "\n")
                    n += 1
            cursor = page["metadata"].get("nextCursor")
            if not cursor:
                break
    print(f"{n} active servers -> {out}", file=sys.stderr)


def load_selection() -> list[dict]:
    return tomllib.loads(SELECTION.read_text(encoding="utf-8"))["cluster"]


def usable(description: str) -> bool:
    # отбрасываем пустые, слишком короткие и неанглийские описания
    if len(description) < 40:
        return False
    letters = [c for c in description if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) > 0.95


def candidates(snapshot_path: Path, cluster_id: str | None, limit: int, seed: int) -> None:
    servers = [json.loads(line) for line in snapshot_path.open(encoding="utf-8")]
    for cluster in load_selection():
        if cluster_id and cluster["id"] != cluster_id or not cluster["keywords"]:
            continue
        pattern = re.compile("|".join(cluster["keywords"]), re.IGNORECASE)
        chosen = {s["name"] for s in cluster.get("servers", [])}
        seen, hits = set(), []
        for s in servers:
            desc = s.get("description", "")
            # пространство имён (io.github.<user>/...) не учитываем, иначе совпадает почти всё
            text = f"{s['name'].rsplit('/', 1)[-1]} {s.get('title', '')} {desc}"
            key = re.sub(r"\W+", " ", desc.lower()).strip()
            if pattern.search(text) and usable(desc) and key not in seen:
                seen.add(key)
                hits.append(s)
        print(f"## {cluster['id']}: {len(hits)} candidates, {len(chosen)} selected")
        shown = [s for s in hits if s["name"] in chosen]
        rest = [s for s in hits if s["name"] not in chosen]
        random.Random(seed).shuffle(rest)
        for s in shown + rest[: max(0, limit - len(shown))]:
            mark = "*" if s["name"] in chosen else " "
            print(f"{mark} {s['name']}@{s['version']} | {s['description']}")


def build(out: Path, meta_out: Path) -> None:
    # решателю видны только id, name, description; кластер — наша разметка hard negatives,
    # её и источник храним отдельно, чтобы не подсказывать ранжировщику
    rows, meta, ids = [], [], set()
    for cluster in load_selection():
        for entry in cluster.get("servers", []):
            name = urllib.parse.quote(entry["name"], safe="")
            server = get(f"{REGISTRY}/servers/{name}/versions/{entry['version']}")["server"]
            skill_id = entry.get("id") or entry["name"].rsplit("/", 1)[-1].lower()
            if skill_id in ids:
                raise SystemExit(f"duplicate skill id {skill_id!r}: set an explicit id in the selection")
            ids.add(skill_id)
            # без title берём последний сегмент: пространство имён (io.github.<user>) — шум для поиска
            name = server.get("title") or server["name"].rsplit("/", 1)[-1]
            rows.append({"id": skill_id, "name": name, "description": server["description"]})
            meta.append({
                "id": skill_id,
                "cluster": cluster["id"],
                "source": f"mcp-registry:{server['name']}@{server['version']}",
            })
    for path, items in ((out, rows), (meta_out, meta)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"{len(rows)} skills -> {out}, meta -> {meta_out}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--snapshot", type=Path, required=True)
    c.add_argument("--cluster")
    c.add_argument("--limit", type=int, default=40, help="сколько кандидатов показать на кластер")
    c.add_argument("--seed", type=int, default=0)
    b = sub.add_parser("build")
    b.add_argument("--out", type=Path, default=Path("case/assets/catalog.jsonl"))
    b.add_argument("--meta-out", type=Path, default=Path("case/dataset/catalog_meta.jsonl"))
    a = p.parse_args()
    if a.cmd == "snapshot":
        snapshot(a.out)
    elif a.cmd == "candidates":
        candidates(a.snapshot, a.cluster, a.limit, a.seed)
    else:
        build(a.out, a.meta_out)


if __name__ == "__main__":
    main()
