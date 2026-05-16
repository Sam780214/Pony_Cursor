"""
路径操作记录：与 D:\\Pony\\路径操作记录.json 模板完全一致（仅含 7 个键，均为字符串）。
多条路径/名称用「；」分隔；会话 ID 用「, 」（逗号+空格）连接，与模板一致。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from .paths import record_dir

LOG_NAME = "路径操作记录.json"

# 与模板完全一致的键顺序与含义
_KEYS = ("时间", "发起路径", "目标路径", "名称", "简称", "发起软件", "ID")


def _format_time_cn() -> str:
    n = datetime.now()
    return f"{n.year}年{n.month}月{n.day}日，{n.hour:02d}:{n.minute:02d}"


def _normalize_path(p: str) -> str:
    if not p:
        return ""
    p = os.path.expandvars(os.path.expanduser(p))
    if "；" in p:
        parts = [os.path.normpath(x.strip()) for x in p.split("；") if x.strip()]
        return "；".join(parts)
    return os.path.normpath(p)


def append_path_operation_log(
    *,
    发起路径: str,
    目标路径: str,
    名称: str,
    简称: str,
    发起软件: str,
    session_ids: list[str] | None = None,
) -> str:
    """
    向 OPENCODE_RECORD_DIR / 路径操作记录.json 追加一条记录。
    每条记录对象仅含 7 个键，值均为 str；无会话时 ID 为空字符串。
    """
    ids = session_ids or []
    id_str = ", ".join(str(x) for x in ids)

    entry: dict[str, str] = {
        "时间": _format_time_cn(),
        "发起路径": _normalize_path(发起路径),
        "目标路径": _normalize_path(目标路径) if 目标路径 else "",
        "名称": 名称 or "",
        "简称": 简称 or "",
        "发起软件": 发起软件 or "",
        "ID": id_str,
    }
    if tuple(entry.keys()) != _KEYS:
        raise ValueError("internal: path log keys mismatch template")

    root = record_dir()
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, LOG_NAME)

    existing: list[Any] = []
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            raw = []
        if isinstance(raw, dict):
            if set(raw.keys()) == set(_KEYS):
                existing = [raw]
            else:
                existing = []
        elif isinstance(raw, list):
            existing = [
                x for x in raw if isinstance(x, dict) and set(x.keys()) == set(_KEYS)
            ]
        else:
            existing = []

    existing.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return path
