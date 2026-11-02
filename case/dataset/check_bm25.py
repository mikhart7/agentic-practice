import json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path
root = Path(sys.argv[1]); priv = Path(sys.argv[2])
cat = [json.loads(l) for l in open(root/"case/assets/catalog.jsonl")]
tok = lambda s: re.findall(r"[a-z0-9]+", s.lower())
docs = [tok(c["name"] + " " + c["description"]) for c in cat]
N = len(docs); avg = sum(map(len, docs))/N
df = Counter(t for d in docs for t in set(d)); tfs = [Counter(d) for d in docs]
def score(q, k1=1.5, b=0.75):
    out = []
    for i, tf in enumerate(tfs):
        s = 0.0
        for t in tok(q):
            if t in tf:
                idf = math.log(1 + (N - df[t] + .5)/(df[t] + .5))
                s += idf * tf[t]*(k1+1)/(tf[t] + k1*(1-b+b*len(docs[i])/avg))
        out.append((s, i))
    return [cat[i]["id"] for s, i in sorted(out, key=lambda x: (-x[0], x[1]))[:3]]
fams = {}
for name, d in [("train", root/"case/dataset"), ("public", priv), ("private", priv)]:
    rows = [json.loads(l) for l in open(d/f"{name}.jsonl")]
    meta = {m["id"]: m for m in map(json.loads, open(d/f"{name}.meta.jsonl"))}
    fams[name] = {meta[r["id"]]["family"] for r in rows}
    agg = defaultdict(list)
    for r in rows:
        ref = json.loads(r["reference"]); rel = {ref["primary"], *ref["acceptable"]}
        top = score(r["input"]); m = meta[r["id"]]
        a1 = float(top[0] in rel); p3 = len(set(top) & rel)/min(3, len(rel))
        for key in ["all", m["style"], "hard" if m["tags"] else "easy"]:
            agg[key].append((a1, p3))
    line = " ".join(f"{k}={sum(a for a,_ in v)/len(v):.2f}" for k, v in sorted(agg.items()))
    print(f"{name:8s} n={len(rows)} acc@1: {line}")
print("family overlap:", len(fams["train"] & fams["public"]), len(fams["train"] & fams["private"]), len(fams["public"] & fams["private"]))
