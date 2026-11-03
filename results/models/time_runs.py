import statistics, subprocess, sys, time
base = ["docker", "run", "--rm", "-i", "--network", "none", "--cpus", "2", "--memory", "2g", "--read-only",
        "--tmpfs", "/tmp:size=256m", "--user", "10001:10001", "-v", "/srv/arena/assets:/assets:ro"]
cases = {
    "container only (python -c pass)": base + ["--entrypoint", "python", "ar04a-runner:local", "-E", "-s", "-c", "pass"],
    "import torch": base + ["--entrypoint", "python", "ar04a-runner:local", "-E", "-s", "-c", "import torch"],
    "import torch+transformers": base + ["--entrypoint", "python", "ar04a-runner:local", "-E", "-s", "-c",
                                         "import torch; from transformers import AutoModel, AutoTokenizer"],
    "import sentence_transformers": base + ["--entrypoint", "python", "ar04a-runner:local", "-E", "-s", "-c",
                                            "from sentence_transformers import SentenceTransformer"],
    "baseline BM25 via runner": base + ["-v", sys.argv[1] + ":/candidate:ro", "ar04a-runner:local"],
    "dense MiniLM via runner (catalog encoded per query)": base + ["-v", sys.argv[2] + ":/candidate:ro", "ar04a-runner:local"],
}
task = b'{"input":"merge my pdfs into one","uses_model":false}'
for name, argv in cases.items():
    ts = []
    for _ in range(5):
        t = time.monotonic(); subprocess.run(argv, input=task, capture_output=True, check=True); ts.append(time.monotonic() - t)
    print(f"{name:52s} median {statistics.median(ts):5.1f}s  min {min(ts):5.1f}s  max {max(ts):5.1f}s")
