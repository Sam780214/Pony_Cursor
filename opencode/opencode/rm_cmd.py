import json
import os
import sys

from . import records
from . import ui
from .paths import backups_dir, record_dir


def _json_files(root: str):
    if not root or not os.path.isdir(root):
        return
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith(".json"):
                yield os.path.join(dirpath, fn)


def _is_valid_json(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            json.load(f)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def _record_json_files_top_level() -> list[str]:
    """默认只收录 record_dir 根目录下 record_*.json（路径操作记录）。"""
    rd = record_dir()
    if not os.path.isdir(rd):
        return []
    out: list[str] = []
    for fn in sorted(os.listdir(rd)):
        if not fn.lower().endswith(".json"):
            continue
        if not fn.lower().startswith("record_"):
            continue
        p = os.path.join(rd, fn)
        if os.path.isfile(p):
            out.append(p)
    return out


def _collect_pick_candidates(include_records: bool) -> list[tuple[str, str]]:
    """(绝对路径, 展示标签) — backups 下全部 .json；--all 时追加 record_*.json。"""
    items: list[tuple[str, str]] = []
    b = backups_dir()
    if os.path.isdir(b):
        for p in _json_files(b):
            tag = "正常" if _is_valid_json(p) else "损坏"
            try:
                rel = os.path.relpath(p, b)
            except ValueError:
                rel = p
            items.append((p, f"[{tag}] backups/{rel}"))
    if include_records:
        for p in _record_json_files_top_level():
            tag = "正常" if _is_valid_json(p) else "损坏"
            items.append((p, f"[{tag}] record/{os.path.basename(p)}"))
    return items


def run_pick(argv: list[str]) -> int:
    include_all = "--all" in argv
    yes = "-y" in argv or "--yes" in argv

    cands = _collect_pick_candidates(include_all)
    if not cands:
        print("无可选的 JSON 文件（检查 backups 与 OPENCODE_RECORD_DIR）。")
        return 0

    paths: list[str] = []
    try:
        import questionary  # type: ignore
    except ImportError:
        questionary = None  # type: ignore

    if questionary:
        picked = questionary.checkbox(
            "选择要删除的 JSON（含正常与损坏；--all 含路径操作记录 record_*.json）:",
            choices=[questionary.Choice(label, value=pth) for pth, label in cands],
        ).ask()
        if not picked:
            print("已取消。")
            return 0
        paths = list(picked)
    else:
        print("交互多选需要: pip install questionary", file=sys.stderr)
        return 2

    if not paths:
        return 0

    preview = "\n".join(f"  - {p}" for p in paths[:40])
    if len(paths) > 40:
        preview += f"\n  … 共 {len(paths)} 个文件"

    software = ui.ask_initiator_software(skip=yes)
    if software is None:
        print("已取消。")
        return 1

    if not ui.confirm_or_abort(
        f"确定永久删除以下 {len(paths)} 个文件？\n"
        f"  发起软件: {software}\n{preview}",
        skip=yes,
    ):
        return 1

    简称 = "rm pick --all" if include_all else "rm pick"
    名称 = "；".join(os.path.basename(x) for x in paths)
    目标路径 = "；".join(paths)
    try:
        records.append_path_operation_log(
            发起路径=os.getcwd(),
            目标路径=目标路径,
            名称=名称,
            简称=简称,
            发起软件=software,
            session_ids=[],
        )
    except OSError as e:
        print(f"（警告）路径操作记录写入失败: {e}", file=sys.stderr)

    for p in paths:
        try:
            os.remove(p)
            print("已删:", p)
        except OSError as e:
            print(f"删除失败 {p}: {e}", file=sys.stderr)
    return 0


def run_json(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    yes = "-y" in argv or "--yes" in argv
    pick = "--pick" in argv

    if pick:
        rest = [a for a in argv if a not in ("--dry-run", "--pick")]
        return run_pick(rest)

    bad = [p for p in _json_files(backups_dir()) if not _is_valid_json(p)]
    if not bad:
        print("未发现无效/孤立 JSON（在 backups 下）。")
        return 0
    print("将删除以下文件:" if not dry else "（预览）将删除:")
    for p in bad:
        print(" ", p)
    if dry:
        return 0

    software = ui.ask_initiator_software(skip=yes)
    if software is None:
        print("已取消。")
        return 1

    if not ui.confirm_or_abort(
        f"确定删除上述无效 JSON？\n  发起软件: {software}", skip=yes
    ):
        return 1
    try:
        records.append_path_operation_log(
            发起路径=os.getcwd(),
            目标路径="；".join(bad),
            名称="；".join(os.path.basename(x) for x in bad),
            简称="rm json",
            发起软件=software,
            session_ids=[],
        )
    except OSError as e:
        print(f"（警告）路径操作记录写入失败: {e}", file=sys.stderr)
    for p in bad:
        os.remove(p)
        print("已删:", p)
    return 0


def run(argv: list[str]) -> int:
    if not argv:
        print("用法: pony rm json ... | pony rm pick ...", file=sys.stderr)
        return 2
    if argv[0] == "json":
        return run_json(argv[1:])
    if argv[0] == "pick":
        return run_pick(argv[1:])
    print("未知子命令:", argv[0], file=sys.stderr)
    return 2
