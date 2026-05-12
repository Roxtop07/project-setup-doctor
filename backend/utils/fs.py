from __future__ import annotations

import os
from typing import Iterator

SKIP_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", ".output", ".cache",
    "coverage", ".tox", ".mypy_cache", ".pytest_cache",
})

MAX_FILE_READ = 512_000
MAX_FILES_PER_SCAN = 2000


def walk_project(
    root_path: str,
    extensions: set[str] | None = None,
    dotfiles: set[str] | None = None,
    max_files: int = MAX_FILES_PER_SCAN,
) -> Iterator[str]:
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d))
        ]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if os.path.islink(fpath):
                continue
            ext = os.path.splitext(fname)[1]
            name_match = dotfiles and fname in dotfiles
            ext_match = extensions and ext in extensions
            if extensions is None and dotfiles is None:
                pass
            elif not name_match and not ext_match:
                continue
            count += 1
            if count > max_files:
                return
            yield fpath


def safe_read(path: str, max_bytes: int = MAX_FILE_READ) -> str | None:
    try:
        with open(path, errors="ignore") as f:
            return f.read(max_bytes)
    except OSError:
        return None
