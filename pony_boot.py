"""将含 pony_local.py 的仓库根目录加入 sys.path（须在 import pony_local 之前使用）。"""
from __future__ import annotations

import sys
from pathlib import Path


def prepare(start: Path | None = None) -> Path:
    p = (start or Path(__file__).resolve().parent).resolve()
    if p.is_file():
        p = p.parent
    for d in (p, *p.parents):
        if (d / "pony_local.py").is_file():
            root = str(d)
            if root not in sys.path:
                sys.path.insert(0, root)
            return d
    raise ImportError(
        "找不到 pony_local.py。请在含 desktop-pet、game、local-only 的 Pony 根目录"
        "或其子目录中运行（例如 D:\\Pony 或 Pony_Cursor_repo）。"
    )
