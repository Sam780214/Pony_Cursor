import argparse
import json
import os
import re
import sys
import time

from . import db as dbmod
from . import records
from . import ui
from .paths import backups_dir


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", s.strip())[:80]
    return s.strip("_") or "backup"


def _会话名称与目标路径(rows, chosen, fallback: str) -> tuple[str, str]:
    m = {str(r["id"]): r for r in rows}
    titles: list[str] = []
    paths: list[str] = []
    for cid in chosen:
        r = m.get(str(cid))
        if not r:
            titles.append(str(cid))
            continue
        titles.append(str(r["title"]))
        loc = (r["path"] or r["directory"] or "").strip()
        if loc:
            paths.append(loc)
    seen: set[str] = set()
    uniq: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    tgs = "；".join(uniq)
    return "；".join(titles), (tgs if tgs else fallback)


def _write_manifest(
    path: str, note: str, session_ids: list[str], cwd: str, initiator_software: str = ""
) -> None:
    os.makedirs(path, exist_ok=True)
    man = os.path.join(path, "manifest.json")
    payload = {
        "note": note,
        "session_ids": session_ids,
        "terminal_cwd": cwd,
        "time": int(time.time() * 1000),
    }
    if initiator_software:
        payload["initiator_software"] = initiator_software
    with open(man, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pony list", add_help=True)
    p.add_argument("--name", default=None, help="按标题模糊匹配（仅已归档）")
    p.add_argument(
        "--note",
        default=None,
        help="非交互：备份说明；对当前匹配结果全部取消归档并写 manifest",
    )
    p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="跳过最终确认（仍写路径操作记录）",
    )
    ns, _rest = p.parse_known_args(argv)

    try:
        conn = dbmod.connect()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2

    rows = dbmod.fetch_archived_sessions(conn, ns.name)
    if not rows:
        print("没有符合条件的已归档会话（time_archived 非空）。")
        conn.close()
        return 0

    note = (ns.note or "").strip()
    chosen: list[str] = []

    if note:
        chosen = [str(r["id"]) for r in rows]
    else:
        try:
            import questionary  # type: ignore
        except ImportError:
            print(
                "请安装 questionary 以直接多选（不先刷屏列出全部标题）：pip install questionary\n"
                "或改用非交互：pony list --name 片段 --note \"备份说明\"",
                file=sys.stderr,
            )
            conn.close()
            return 2

        labels = [f"{r['title'][:72]} | {r['id'][:20]}…" for r in rows]
        picked = questionary.checkbox(
            "选择要恢复（取消归档）的会话（空格切换，回车确认）:",
            choices=[
                questionary.Choice(title, value=rows[i]["id"]) for i, title in enumerate(labels)
            ],
        ).ask()
        if not picked:
            print("已取消。")
            conn.close()
            return 0
        chosen = [str(x) for x in picked]

    if not note:
        note = input("输入一句话备份说明（将写入 backups 下 manifest）: ").strip()
    if not note:
        print("未提供备份说明，已中止。", file=sys.stderr)
        conn.close()
        return 1

    bdir = backups_dir()
    dest = os.path.join(bdir, _slug(note))
    manifest_path = os.path.join(dest, "manifest.json")

    software = ui.ask_initiator_software(skip=ns.yes)
    if software is None:
        print("已取消。")
        conn.close()
        return 1

    if not ui.confirm_or_abort(
        f"确定执行？\n  发起软件: {software}\n"
        f"  将取消 {len(chosen)} 条会话的归档，并写入备份目录:\n  {dest}",
        skip=ns.yes,
    ):
        conn.close()
        return 1

    _write_manifest(dest, note, chosen, os.getcwd(), initiator_software=software)
    n = dbmod.unarchive_sessions(conn, chosen)
    名称, 目标路径 = _会话名称与目标路径(rows, chosen, manifest_path)
    try:
        records.append_path_operation_log(
            发起路径=os.getcwd(),
            目标路径=目标路径,
            名称=名称,
            简称=note,
            发起软件=software,
            session_ids=chosen,
        )
    except OSError as e:
        print(f"（警告）路径操作记录写入失败: {e}", file=sys.stderr)

    print(f"已取消归档 {n} 条会话；备份元数据: {manifest_path}")
    conn.close()
    return 0
