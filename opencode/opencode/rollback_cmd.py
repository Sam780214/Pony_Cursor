import json
import os
import sys

from . import db as dbmod
from . import records
from . import ui
from .paths import backups_dir


def _iter_manifests():
    root = backups_dir()
    if not os.path.isdir(root):
        return
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        mf = os.path.join(d, "manifest.json")
        if os.path.isfile(mf):
            try:
                with open(mf, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                data = {}
            yield d, name, data


def run(argv: list[str]) -> int:
    yes = "-y" in argv or "--yes" in argv
    argv = [a for a in argv if a not in ("-y", "--yes")]

    if not argv or argv[0] == "--list":
        items = list(_iter_manifests())
        if not items:
            print("backups 目录下无 manifest.json。")
            return 0
        for d, name, data in items:
            note = data.get("note") or name
            ids = data.get("session_ids") or []
            cwd = data.get("terminal_cwd") or ""
            print(f"- {note}\n  目录: {d}\n  会话数: {len(ids)}  cwd: {cwd}\n")
        return 0

    note_arg = " ".join(argv).strip()
    if not note_arg:
        print("用法: pony rollback --list | pony rollback \"备份说明\" [-y]", file=sys.stderr)
        return 2

    match = None
    for d, name, data in _iter_manifests():
        note = str(data.get("note") or name)
        if note_arg in note or note in note_arg or name == note_arg:
            match = (d, data)
            break

    if not match:
        print(f"未找到与「{note_arg}」匹配的备份。", file=sys.stderr)
        return 1

    d, data = match
    ids = [str(x) for x in (data.get("session_ids") or []) if x]
    if not ids:
        print(f"manifest 无 session_ids: {os.path.join(d, 'manifest.json')}", file=sys.stderr)
        return 1

    manifest_path = os.path.join(d, "manifest.json")

    software = ui.ask_initiator_software(skip=yes)
    if software is None:
        print("已取消。")
        return 1

    if not ui.confirm_or_abort(
        f"确定按备份还原（取消 {len(ids)} 条会话归档）？\n"
        f"  发起软件: {software}\n"
        f"  manifest: {manifest_path}",
        skip=yes,
    ):
        return 1

    try:
        conn = dbmod.connect()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2

    n = dbmod.unarchive_sessions(conn, ids)
    名称, 路径合并 = dbmod.fetch_paths_titles_for_ids(conn, ids)
    简称 = str(data.get("note") or note_arg or os.path.basename(d))
    if not 名称.strip():
        名称 = 简称
    目标路径 = 路径合并 if 路径合并.strip() else manifest_path
    try:
        records.append_path_operation_log(
            发起路径=os.getcwd(),
            目标路径=目标路径,
            名称=名称,
            简称=简称,
            发起软件=software,
            session_ids=ids,
        )
    except OSError as e:
        print(f"（警告）路径操作记录写入失败: {e}", file=sys.stderr)
    conn.close()
    print(f"已从备份还原（取消归档）{n} 条会话。manifest: {manifest_path}")
    return 0
