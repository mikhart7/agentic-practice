"""sha256 содержимого каталога: ARENA_INPUT_ASSETS_DIGEST и digest пакета метрики для ARENA_RELEASE_ID.

Считается по отсортированным парам (относительный путь, sha256 файла); символические ссылки не допускаются.
Запуск: python tree_digest.py <каталог> [--exclude имя ...]
"""
import argparse
import hashlib
import sys
from pathlib import Path


def tree_digest(root: Path, exclude: frozenset[str] = frozenset()) -> str:
    outer = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] in exclude or path.is_dir():
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"только обычные файлы: {relative}")
        inner = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                inner.update(block)
        outer.update(f"{relative.as_posix()}\0{inner.hexdigest()}\n".encode())
    return outer.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--exclude", action="append", default=[], help="имя элемента верхнего уровня")
    arguments = parser.parse_args()
    if not arguments.directory.is_dir():
        sys.exit(f"нет каталога: {arguments.directory}")
    print(tree_digest(arguments.directory, frozenset(arguments.exclude)))
