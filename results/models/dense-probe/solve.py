import json, sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
task = json.load(sys.stdin)
assets = Path(task["assets_dir"])
cat = [json.loads(l) for l in (assets / "catalog.jsonl").open()]
m = SentenceTransformer(str(assets / "models/all-MiniLM-L6-v2"), device="cpu")
d = m.encode([c["name"] + ": " + c["description"] for c in cat], normalize_embeddings=True)
q = m.encode([task["input"]], normalize_embeddings=True)[0]
top = sorted(range(len(cat)), key=lambda i: -float(d[i] @ q))[:3]
print(json.dumps({"answer": json.dumps([cat[i]["id"] for i in top])}))
