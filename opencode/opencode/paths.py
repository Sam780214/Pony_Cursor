import os
import sys
from pathlib import Path

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
import _load_pony  # noqa: F401

import pony_local

_PKG_ROOT = Path(__file__).resolve().parent.parent
pony_local.ensure_repo_on_path(_PKG_ROOT)


def opencode_data_dir() -> str:
    d = (os.environ.get("OPENCODE_DATA_DIR") or "").strip()
    if d:
        return os.path.expandvars(os.path.expanduser(d))
    return str(pony_local.project_local_dir("opencode", start=_PKG_ROOT) / "data")


def opencode_db_path() -> str:
    db = (os.environ.get("OPENCODE_DB") or "").strip()
    if db:
        return os.path.expandvars(os.path.expanduser(db))
    return os.path.join(opencode_data_dir(), "opencode.db")


def backups_dir() -> str:
    d = (os.environ.get("OPENCODE_BACKUPS_DIR") or "").strip()
    if d:
        return os.path.expandvars(os.path.expanduser(d))
    return str(pony_local.project_local_dir("opencode", start=_PKG_ROOT) / "backups")


def record_dir() -> str:
    rd = (os.environ.get("OPENCODE_RECORD_DIR") or "").strip()
    if rd:
        return os.path.expandvars(os.path.expanduser(rd))
    return str(pony_local.pony_workspace_root(_PKG_ROOT))
