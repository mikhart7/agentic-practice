import json, resource, sys, time
t0 = time.perf_counter()
from sentence_transformers import CrossEncoder, SentenceTransformer
import torch
torch.set_num_threads(int(sys.argv[3]))
t_import = time.perf_counter() - t0
path, kind = sys.argv[1], sys.argv[2]
cat = [json.loads(l) for l in open("case/assets/catalog.jsonl")]
docs = [c["name"] + ": " + c["description"] for c in cat]
q = "transcribe this interview recording offline"
t1 = time.perf_counter()
if kind == "bi-encoder":
    m = SentenceTransformer(path, device="cpu"); t_load = time.perf_counter() - t1
    t2 = time.perf_counter(); m.encode(docs, batch_size=64); t_docs = time.perf_counter() - t2
    t3 = time.perf_counter(); m.encode([q]); t_q = time.perf_counter() - t3
else:
    m = CrossEncoder(path, device="cpu"); t_load = time.perf_counter() - t1
    t2 = time.perf_counter(); m.predict([(q, d) for d in docs[:20]]); t_docs = time.perf_counter() - t2
    t3 = time.perf_counter(); m.predict([(q, d) for d in docs], batch_size=64); t_q = time.perf_counter() - t3
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(json.dumps({"import": t_import, "load": t_load, "a": t_docs, "b": t_q, "rss_mb": rss, "total": time.perf_counter() - t0}))
