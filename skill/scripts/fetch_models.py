#!/usr/bin/env python3
"""Download the three encoders the selector uses, pinned to the same Hugging Face revisions as the arena case
(case/assets/models.toml). About 660 MB; weights, configs and tokenizers only.

  python scripts/fetch_models.py [--models-dir DIR]
"""
import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

MODELS = [
    ("bge-base-en-v1.5", "BAAI/bge-base-en-v1.5", "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"),
    ("e5-small-v2", "intfloat/e5-small-v2", "ffb93f3bd4047442299a41ebb6fa998a38507c52"),
    ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"),
]
ALLOW = ["*.json", "*.txt", "*.safetensors", "1_Pooling/*"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", type=Path, default=Path(__file__).resolve().parent.parent / "models")
    a = p.parse_args()
    for name, repo, revision in MODELS:
        path = snapshot_download(repo, revision=revision, allow_patterns=ALLOW, local_dir=a.models_dir / name)
        print(f"{name} @ {revision[:10]} -> {path}")


if __name__ == "__main__":
    main()
