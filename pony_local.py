"""Pony 项目：解析 local-only 目录（构建产物、缓存、用户数据）。"""
from __future__ import annotations

import sys
from pathlib import Path


def ensure_repo_on_path(start: Path | None = None) -> Path:
    """把含 pony_local.py 的仓库根加入 sys.path，便于子目录 import。"""
    p = (start or Path.cwd()).resolve()
    if p.is_file():
        p = p.parent
    for d in (p, *p.parents):
        if (d / "pony_local.py").is_file():
            s = str(d)
            if s not in sys.path:
                sys.path.insert(0, s)
            return d
    raise ImportError("找不到 pony_local.py（请在 Pony 仓库根或克隆根运行）")


def find_repo_root(start: Path | None = None) -> Path:
    """定位含 local-only/ 的仓库根（Pony 根或 Pony_Cursor 克隆根）。"""
    p = (start or Path.cwd()).resolve()
    if p.is_file():
        p = p.parent
    for d in (p, *p.parents):
        lo = d / "local-only"
        if not lo.is_dir():
            continue
        if (d / "desktop-pet").is_dir() or (d / "game").is_dir() or (d / "opencode").is_dir():
            return d
    return p.parent


def local_only_root(start: Path | None = None) -> Path:
    return find_repo_root(start) / "local-only"


def project_local_dir(project: str, start: Path | None = None) -> Path:
    """例如 project_local_dir('game') -> .../local-only/game"""
    d = local_only_root(start) / project
    d.mkdir(parents=True, exist_ok=True)
    return d


def configure_pycache(project: str, start: Path | None = None) -> Path:
    """将 __pycache__ 定向到 local-only/<project>/__pycache__。"""
    cache = project_local_dir(project, start) / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    import sys

    sys.pycache_prefix = str(cache)
    return cache
