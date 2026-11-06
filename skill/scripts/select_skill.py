#!/usr/bin/env python3
"""Pick the skills from a catalog that best match a user request.

The ranker was grown on the DeepPavlov arena (campaign c1, candidate r9-02): an ensemble of three
small sentence encoders with centering, plus a lexical score whose weight depends on how much the
request's words resemble the catalog's words. enc.py, lex.py and hyb.py are the candidate's own
files, unchanged; params/ is the output of its build on the training queries.

  python scripts/select_skill.py --catalog catalog.jsonl --query "turn these addresses into lat/long"
  python scripts/select_skill.py --catalog catalog.jsonl --queries-file queries.txt --k 5

Catalog: JSONL, one skill per line with "id", "name", "description".
Output: one JSON object per query on stdout: {"query": ..., "top": [{"id", "name", "score"}, ...]}.
Scores are fused z-scores within one query: compare candidates, do not threshold across queries.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np  # noqa: E402

import hyb  # noqa: E402
from enc import Encoder  # noqa: E402
from lex import Lexical  # noqa: E402

PARAMS = HERE / "params"
DEFAULT_MODELS = Path(os.environ.get("SELECT_SKILL_MODELS", HERE.parent / "models"))
CACHE = Path(os.environ.get("SELECT_SKILL_CACHE", Path.home() / ".cache" / "select-skill"))


def load_catalog(path: Path) -> tuple[list[dict], bytes]:
    raw = path.read_bytes()
    catalog = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    for i, c in enumerate(catalog, 1):
        missing = {"id", "name", "description"} - set(c)
        if missing:
            raise SystemExit(f"{path}:{i}: missing fields {sorted(missing)}")
    ids = [c["id"] for c in catalog]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: duplicate skill ids")
    if not catalog:
        raise SystemExit(f"{path}: empty catalog")
    return catalog, raw


def catalog_embeddings(catalog: list[dict], raw: bytes, cfg: dict, models_dir: Path) -> dict:
    """Embeddings of the catalog for each model, centered by the catalog mean (as the build did); cached."""
    key = hashlib.sha256(raw + json.dumps(cfg["models"], sort_keys=True).encode()).hexdigest()[:20]
    cached = CACHE / f"catalog-{key}.npz"
    try:
        with np.load(cached) as f:
            return {k: f[k] for k in f}
    except (OSError, ValueError):
        pass
    out = {}
    for spec in cfg["models"]:
        docs = [spec["doc_prefix"] + spec["doc_template"].format(name=c["name"], description=c["description"])
                for c in catalog]
        D = Encoder(models_dir / spec["name"], spec["pooling"], spec["max_len"]).encode(docs)
        out[spec["name"]] = hyb.norm(D - D.mean(0, keepdims=True)).astype(np.float32)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        np.savez(cached, **out)
    except OSError:
        pass  # the cache is a convenience; ranking works without it
    return out


def rank(queries: list[str], catalog: list[dict], raw: bytes, models_dir: Path, k: int):
    cfg = json.loads((PARAMS / "config.json").read_text())
    fusion = json.loads((PARAMS / "fusion.json").read_text())
    with np.load(PARAMS / "mu_q.npz") as f:
        mu = {n: f[n] for n in f}
    for spec in cfg["models"]:
        if not (models_dir / spec["name"] / "model.safetensors").exists():
            raise SystemExit(f"model {spec['name']} not found in {models_dir}: run scripts/fetch_models.py")
    D = catalog_embeddings(catalog, raw, cfg, models_dir)
    names = [s["name"] for s in cfg["models"]]
    encoders = {s["name"]: Encoder(models_dir / s["name"], s["pooling"], s["max_len"]) for s in cfg["models"]}
    lexical = Lexical(catalog)
    for query in queries:
        zs = {}
        for spec in cfg["models"]:
            name = spec["name"]
            q = encoders[name].encode([prefix + query for prefix in spec["query_prefixes"]])
            x = hyb.norm(hyb.norm(q.sum(axis=0, keepdims=True)) - mu[name])  # centering with the train query mean
            zs[name] = hyb.zscore(x @ D[name].T)
        bm, tri = lexical.features(query)
        F = hyb.features(zs, names, cfg["weights"], np.array([bm]), np.array([tri]), hyb.length_feature([query]))
        scores = hyb.score(fusion["method"], fusion["params"], F)[0]
        order = sorted(range(len(catalog)), key=lambda i: (-float(scores[i]), i))[:k]
        yield {"query": query, "top": [{"id": catalog[i]["id"], "name": catalog[i]["name"],
                                        "score": round(float(scores[i]), 3)} for i in order]}


def main() -> None:
    p = argparse.ArgumentParser(description="Pick the best-matching skills from a catalog for a user request.")
    p.add_argument("--catalog", type=Path, required=True, help="JSONL with id, name, description per skill")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--query", help="the user request")
    src.add_argument("--queries-file", type=Path, help="one request per line (models load once)")
    p.add_argument("--k", type=int, default=3, help="how many skills to return (default 3)")
    p.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS)
    a = p.parse_args()
    catalog, raw = load_catalog(a.catalog)
    if not 1 <= a.k <= len(catalog):
        raise SystemExit(f"--k must be between 1 and {len(catalog)}")
    queries = [a.query] if a.query is not None else [
        line.strip() for line in a.queries_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    log = os.environ.get("SELECT_SKILL_LOG")  # set by skill/tests to prove the agent called the skill
    for result in rank(queries, catalog, raw, a.models_dir, a.k):
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if log:
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"time": time.time(), "catalog": str(a.catalog), **result}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
