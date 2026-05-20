"""检测本机是否安装 DeepSeek 扩展版。"""
from __future__ import annotations

import shutil
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
STASH_DIR = APP_DIR / "local-only"

_DEEPSEEK_MARKERS = ("deepseek_client.py", "config.py")


def _stash_has_deepseek() -> bool:
    return all((STASH_DIR / name).is_file() for name in _DEEPSEEK_MARKERS)


def _root_has_deepseek() -> bool:
    return all((APP_DIR / name).is_file() for name in _DEEPSEEK_MARKERS)


def ensure_deepseek_files() -> bool:
    """若仅 local-only 有 DeepSeek 版，复制到根目录以便导入（不覆盖已有文件）。"""
    if _root_has_deepseek():
        return True
    if not _stash_has_deepseek():
        return False
    for name in _DEEPSEEK_MARKERS:
        src = STASH_DIR / name
        dst = APP_DIR / name
        if not dst.exists():
            shutil.copy2(src, dst)
    return _root_has_deepseek()


def use_deepseek_edition() -> bool:
    """本机存在 DeepSeek 版模块时使用完整版，否则仅 Ollama。"""
    ensure_deepseek_files()
    return _root_has_deepseek()


def edition_label() -> str:
    return "完整版（Ollama + DeepSeek）" if use_deepseek_edition() else "Ollama 版"
