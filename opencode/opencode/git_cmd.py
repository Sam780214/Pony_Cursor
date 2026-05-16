"""在 Pony 根目录下维护 Pony_Cursor_repo：清理后浅克隆 GitHub 仓库到该文件夹内。"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from . import records, ui
from .paths import record_dir

REPO_DIR_NAME = "Pony_Cursor_repo"
EXPECTED_TOPLEVEL = ("desktop-pet", "opencode", "game")
DEFAULT_REPO = "https://github.com/Sam780214/Pony_Cursor.git"


def _which_git() -> str | None:
    return shutil.which("git")


def run(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pony git", add_help=True)
    p.add_argument(
        "--repo",
        default=None,
        help="Git 仓库 URL（默认: 环境变量 PONY_GIT_REPO，否则 GitHub Sam780214/Pony_Cursor）",
    )
    p.add_argument(
        "--root",
        default=None,
        help="Pony 根目录（默认: OPENCODE_RECORD_DIR，未设置时为 D:\\Pony）；其下固定子目录名 Pony_Cursor_repo",
    )
    p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="跳过「发起软件」询问与最终确认",
    )
    ns = p.parse_args(argv)

    repo_url = (ns.repo or os.environ.get("PONY_GIT_REPO") or "").strip() or DEFAULT_REPO
    pony_root = (ns.root or "").strip() or record_dir()
    pony_root = os.path.expandvars(os.path.expanduser(pony_root))
    repo_dest = os.path.join(pony_root, REPO_DIR_NAME)

    if not _which_git():
        print("未找到 git 可执行文件，请安装 Git 并加入 PATH。", file=sys.stderr)
        return 2

    software = ui.ask_initiator_software(skip=ns.yes)
    if software is None:
        return 1

    exists_hint = "（若存在则整棵删除）" if os.path.lexists(repo_dest) else ""
    if not ui.confirm_or_abort(
        "将执行：\n"
        f"  1) 在「{pony_root}」下清理子目录「{REPO_DIR_NAME}」{exists_hint}\n"
        f"  2) 浅克隆（depth=1）仓库到「{repo_dest}」\n\n"
        f"仓库: {repo_url}",
        skip=ns.yes,
    ):
        return 1

    os.makedirs(pony_root, exist_ok=True)
    if os.path.lexists(repo_dest):
        shutil.rmtree(repo_dest)

    proc = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, repo_dest],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, file=sys.stderr, end="" if proc.stdout.endswith("\n") else "\n")
        print("git clone 失败。", file=sys.stderr)
        return proc.returncode if proc.returncode else 1

    missing = [name for name in EXPECTED_TOPLEVEL if not os.path.isdir(os.path.join(repo_dest, name))]
    if missing:
        print(f"（警告）克隆结果中缺少预期目录: {', '.join(missing)}", file=sys.stderr)

    名称 = f"{REPO_DIR_NAME}（含 desktop-pet；opencode；game）"
    try:
        records.append_path_operation_log(
            发起路径=os.getcwd(),
            目标路径=repo_dest,
            名称=名称,
            简称="pony git",
            发起软件=software,
            session_ids=[],
        )
    except OSError as e:
        print(f"（警告）路径操作记录写入失败: {e}", file=sys.stderr)

    print(f"已将 GitHub 内容导入:\n  {repo_dest}")
    return 0
