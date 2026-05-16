import os
import shutil
import sqlite3
from .paths import opencode_db_path


def _maybe_migrate_legacy_db() -> None:
    p = opencode_db_path()
    if os.path.isfile(p):
        return
    legacy = os.path.join(
        os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db"
    )
    if os.path.isfile(legacy):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        shutil.copy2(legacy, p)


def connect() -> sqlite3.Connection:
    _maybe_migrate_legacy_db()
    p = opencode_db_path()
    if not os.path.isfile(p):
        raise FileNotFoundError(f"找不到数据库: {p}")
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    return conn


def session_columns(conn: sqlite3.Connection) -> list[str]:
    return [r[1] for r in conn.execute("PRAGMA table_info(session)")]


def fetch_archived_sessions(
    conn: sqlite3.Connection, name_substr: str | None = None
) -> list[sqlite3.Row]:
    cols = session_columns(conn)
    if "time_archived" not in cols or "title" not in cols:
        raise RuntimeError("session 表缺少 time_archived 或 title 列，可能不是 OpenCode 数据库。")
    q = "SELECT id, title, path, directory, time_archived FROM session WHERE time_archived IS NOT NULL"
    args: tuple = ()
    if name_substr:
        q += " AND title LIKE ?"
        args = (f"%{name_substr}%",)
    q += " ORDER BY time_archived DESC"
    return list(conn.execute(q, args))


def fetch_paths_titles_for_ids(conn: sqlite3.Connection, ids: list[str]) -> tuple[str, str]:
    """按 ids 顺序返回（名称合并；目标路径为 path/directory 去重合并，可能为空）。"""
    if not ids:
        return "", ""
    ph = ",".join("?" * len(ids))
    rows = list(
        conn.execute(
            f"SELECT id, title, path, directory FROM session WHERE id IN ({ph})",
            ids,
        )
    )
    by_id = {str(r["id"]): r for r in rows}
    titles: list[str] = []
    paths: list[str] = []
    for i in ids:
        sid = str(i)
        r = by_id.get(sid)
        if not r:
            titles.append(sid)
            continue
        titles.append(str(r["title"]))
        loc = (r["path"] or r["directory"] or "").strip()
        if loc:
            paths.append(loc)
    seen: set[str] = set()
    uniq_paths: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            uniq_paths.append(p)
    return "；".join(titles), "；".join(uniq_paths)


def unarchive_sessions(conn: sqlite3.Connection, ids: list[str]) -> int:
    if not ids:
        return 0
    ph = ",".join("?" * len(ids))
    cur = conn.execute(
        f"UPDATE session SET time_archived = NULL WHERE id IN ({ph})", ids
    )
    conn.commit()
    return cur.rowcount
