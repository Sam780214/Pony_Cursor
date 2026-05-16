"""导入时自动定位仓库根，使子目录可直接 import pony_local。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_BOOT = "pony_boot.py"


def _run() -> None:
    here = Path(__file__).resolve().parent
    for d in (here, *here.parents):
        boot = d / _BOOT
        if not boot.is_file():
            continue
        spec = importlib.util.spec_from_file_location("pony_boot", boot)
        if spec is None or spec.loader is None:
            break
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("pony_boot", mod)
        spec.loader.exec_module(mod)
        mod.prepare(here)
        return
    raise ImportError(f"找不到 {_BOOT}（应与 pony_local.py 位于同一仓库根）")


_run()
