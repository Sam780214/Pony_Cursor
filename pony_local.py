"""Pony 项目：解析 local-only 目录（构建产物、缓存、用户数据）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 工作区 canonical local-only（优先于克隆仓库内的 local-only/）
_CANONICAL_LOCAL_ONLY = Path(r"D:\Pony\local-only")
_ENV_LOCAL_ONLY_ROOT = "PONY_LOCAL_ONLY_ROOT"


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
    """定位含 pony_local.py 与项目子目录的 Git 仓库根（如 Pony_Cursor_repo）。"""
    p = (start or Path.cwd()).resolve()
    if p.is_file():
        p = p.parent
    for d in (p, *p.parents):
        if not (d / "pony_local.py").is_file():
            continue
        if (d / "desktop-pet").is_dir() or (d / "game").is_dir() or (d / "opencode").is_dir():
            return d
    raise FileNotFoundError("找不到 Pony 仓库根（需含 pony_local.py 与 desktop-pet/game/opencode）")


def _env_local_only_root() -> Path | None:
    raw = (os.environ.get(_ENV_LOCAL_ONLY_ROOT) or "").strip()
    if not raw:
        return None
    p = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
    return p if p.is_dir() else None


def local_only_root(start: Path | None = None) -> Path:
    """解析 local-only 根目录；优先环境变量与 D:\\Pony\\local-only。"""
    env_root = _env_local_only_root()
    if env_root is not None:
        return env_root
    if _CANONICAL_LOCAL_ONLY.is_dir():
        return _CANONICAL_LOCAL_ONLY
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
