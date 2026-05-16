"""终端确认（重要操作前）与发起软件询问。"""

from __future__ import annotations

import os
import sys


def confirm(message: str, *, skip: bool) -> bool:
    """
    skip=True 时视为已确认（用于 -y/--yes）。
    否则要求用户输入 y 才返回 True。
    """
    if skip:
        return True
    try:
        r = input(f"{message} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return r in ("y", "yes", "是")


def confirm_or_abort(message: str, *, skip: bool) -> bool:
    if confirm(message, skip=skip):
        return True
    print("已取消。")
    return False


def ask_initiator_software(*, skip: bool) -> str | None:
    """
    询问「发起软件」（写入路径操作记录中的 software 字段）。
    skip=True（如 -y）时不询问，优先读环境变量 PONY_SOFTWARE，否则为「未指定(-y)」。
    用户在 questionary 中取消时返回 None。
    """
    if skip:
        v = (os.environ.get("PONY_SOFTWARE") or "").strip()
        return v if v else "未指定(-y)"

    choices: list[tuple[str, str]] = [
        ("cmd.exe（命令提示符）", "cmd"),
        ("PowerShell（powershell.exe）", "powershell"),
        ("PowerShell 7（pwsh.exe）", "pwsh"),
        ("Windows Terminal（wt.exe）", "wt"),
        ("其他（手动输入名称）", "__other__"),
    ]

    try:
        import questionary  # type: ignore
    except ImportError:
        questionary = None  # type: ignore

    if questionary:
        sel = questionary.select(
            "请选择发起软件（将写入路径操作记录 / manifest）：",
            choices=[questionary.Choice(label, value=val) for label, val in choices],
        ).ask()
        if sel is None:
            return None
        if sel == "__other__":
            try:
                t = input("请填写发起软件名称（简短）: ").strip()
            except EOFError:
                return None
            return t or "其他"
        return sel

    print("请选择发起软件（将写入路径操作记录），输入序号：")
    for i, (lab, _val) in enumerate(choices, 1):
        print(f"  {i}) {lab}")
    try:
        line = input("序号 (1-5): ").strip()
    except EOFError:
        return None
    if not line.isdigit():
        print("无效输入，已取消。", file=sys.stderr)
        return None
    idx = int(line)
    if not 1 <= idx <= len(choices):
        print("序号超出范围，已取消。", file=sys.stderr)
        return None
    _lab, val = choices[idx - 1]
    if val == "__other__":
        try:
            t = input("请填写发起软件名称（简短）: ").strip()
        except EOFError:
            return None
        return t or "其他"
    return val
