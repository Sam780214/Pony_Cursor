"""从 D:\\Pony\\Hi AI.json 读取模型显示名称（Ollama / DeepSeek 通用，仅 UI）。"""
from __future__ import annotations

import json
import re
from pathlib import Path

PONY_ALIAS_PATH = Path(r"D:\Pony\Hi AI.json")
LOCAL_ALIAS_PATH = Path(__file__).resolve().parent / "Hi AI.json"

_LINE_RE = re.compile(
    r'^\s*["\']?([^"\']+?)["\']?\s*=\s*["\']?(.+?)["\']?\s*$'
)


def _parse_text(content: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if m:
            aliases[m.group(1).strip()] = m.group(2).strip()
    return aliases


def load_model_aliases() -> dict[str, str]:
    """返回 {真实模型名: 显示名}。"""
    for path in (PONY_ALIAS_PATH, LOCAL_ALIAS_PATH):
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                continue
            if raw.startswith("{"):
                data = json.loads(raw)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
            return _parse_text(raw)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return {}


def display_name(model_id: str, aliases: dict[str, str] | None = None) -> str:
    m = aliases if aliases is not None else load_model_aliases()
    return m.get(model_id, model_id)


def resolve_model_id(selected: str, aliases: dict[str, str] | None = None) -> str:
    """下拉框选中项 -> 真实模型 id。"""
    m = aliases if aliases is not None else load_model_aliases()
    if selected in m:
        return selected
    rev = {v: k for k, v in m.items()}
    return rev.get(selected, selected)
