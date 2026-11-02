"""Скачивает разрешённые модели из models.toml в case/assets/models/<name> по закреплённой ревизии.

  uv run python case/assets/fetch_models.py
"""
import tomllib
from pathlib import Path

from huggingface_hub import snapshot_download

HERE = Path(__file__).parent
# только веса safetensors, конфиги и токенизатор: без дублей pytorch_model.bin / onnx / openvino
ALLOW = ["*.json", "*.txt", "*.safetensors", "*.model", "1_Pooling/*", "sentencepiece*"]


def main() -> None:
    for m in tomllib.loads((HERE / "models.toml").read_text())["model"]:
        path = snapshot_download(m["repo"], revision=m["revision"], allow_patterns=ALLOW,
                                 local_dir=HERE / "models" / m["name"])
        print(f"{m['name']} @ {m['revision'][:10]} -> {path}")


if __name__ == "__main__":
    main()
