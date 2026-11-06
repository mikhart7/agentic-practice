---
name: skill-selector
description: Pick the right skill, tool or MCP server for a user request from a catalog of many (JSONL with id, name, description). Use when you must choose among dozens of similar skills, or when the request describes the goal without naming the tool.
---

# Skill selector

Ranks a skill catalog against a user request and returns the best matches. On a held-out test set of 376 requests over 189 MCP skills, it puts the right skill first in about 84% of cases. BM25 manages about 58%.

## When to use
- A user asks for something, and you have to decide which of many skills, tools or MCP servers should handle it.
- The catalog has near-duplicates: several Slack servers, several spreadsheet tools, several backup services.
- The request is indirect and never names the tool. For example, "is anyone testing new treatments for my condition I could join?" needs a clinical-trials search skill.

## How to use
One-time setup, from this skill's directory. It downloads about 660 MB of model weights:
```bash
pip install -r scripts/requirements.txt
python scripts/fetch_models.py
```

Rank a catalog for one request:
```bash
python scripts/select_skill.py --catalog path/to/catalog.jsonl --query "the user's request"
```

The script prints one JSON line:
```json
{"query": "...", "top": [{"id": "aria-mcp-server", "name": "aria-mcp-server", "score": 5.471}, {"id": "...", "name": "...", "score": 4.046}, {"id": "...", "name": "...", "score": 2.741}]}
```

Options:
- `--k N` returns N skills instead of 3.
- `--queries-file FILE` ranks one request per line, loading the models once. This is much faster for batches.
- `--models-dir DIR` points to the weights if they are not in `models/` next to `scripts/`.

**Catalog format:** JSONL, one skill per line, with string fields `id`, `name`, `description`. Other fields are ignored.

## How to read the result
- `top[0]` is the pick. The next entries are the closest alternatives, often near-duplicates of the pick.
- `score` is a fused z-score within this one request. Use it to compare candidates for the same request. It is not a probability, so do not compare scores across requests or apply a fixed threshold.
- The script always returns `k` skills, even when nothing in the catalog fits. Read the description of `top[0]` before acting on it. If it plainly does not match the request, say that no suitable skill was found.
- When `top[0]` and `top[1]` are near-duplicates (for example, two Slack servers), check their descriptions against the specifics of the request, or ask the user.

## Errors
- **`model ... not found`:** run `python scripts/fetch_models.py`, or pass `--models-dir`.
- **`missing fields` or `duplicate skill ids`:** fix the catalog file.
- **Slow first run:** the first run on a new catalog embeds it, about 30–40 s for 200 skills on CPU. The result is cached in `~/.cache/select-skill`; set `SELECT_SKILL_CACHE` to move the cache. After that, a call takes a few seconds, mostly loading the encoders.

## Limitations
- English requests and descriptions only.
- Tested on catalogs of about 200 skills. The cost per request barely depends on catalog size, but accuracy on much larger catalogs is untested.
- Indirect requests with no word overlap with any description are the weak spot: about 0.62 quality, against 0.85–0.98 for other phrasings.
- CPU only. Uses about 1 GB of RAM for three encoders; no GPU or network is needed after setup.

## Origin
Grown on the DeepPavlov arena in campaign c1 of this repository: candidate `r9-02`, first of 5 finalists on the private set. It scores 0.856 against 0.608 for BM25, with metric `0.7·acc@1 + 0.3·nP@3`. `enc.py`, `lex.py` and `hyb.py` are the candidate's own files, unchanged. `params/` is the output of its build: ensemble weights, centering vectors and fusion parameters. On the 54 requests the arena completed for this candidate, the script reproduces the candidate's answers exactly. For the mechanism, see `docs/solution.md` in the repository; for how the arena found it, see `docs/evolution.md`.
