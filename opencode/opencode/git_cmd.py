"""从 GitHub 拉取仓库并覆盖本地 Pony 目录下的 desktop-pet / opencode / game。"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from . import records, ui
from .paths import record_dir

FOLDERS = ("desktop-pet", "opencode", "game")
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
        help="目标根目录（默认: OPENCODE_RECORD_DIR，未设置时为 D:\\Pony）",
    )
    p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="跳过「发起软件」询问与最终确认",
    )
    ns = p.parse_args(argv)

    repo = (ns.repo or os.environ.get("PONY_GIT_REPO") or "").strip() or DEFAULT_REPO
    pony_root = (ns.root or "").strip() or record_dir()
    pony_root = os.path.expandvars(os.path.expanduser(pony_root))

    if not _which_git():
        print("未找到 git 可执行文件，请安装 Git 并加入 PATH。", file=sys.stderr)
        return 2

    dest_paths = [os.path.join(pony_root, name) for name in FOLDERS]
    preview = "\n".join(f"  {d}" for d in dest_paths)

    software = ui.ask_initiator_software(skip=ns.yes)
    if software is None:
        return 1

    if not ui.confirm_or_abort(
        "将从仓库浅克隆（depth=1）并覆盖以下目录（原目录将整棵删除后替换）:\n"
        f"{preview}\n\n"
        f"仓库: {repo}\n根目录: {pony_root}",
        skip=ns.yes,
    ):
        return 1

    tmp = tempfile.mkdtemp(prefix="pony_git_")
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", repo, tmp],
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

        missing = [name for name in FOLDERS if not os.path.isdir(os.path.join(tmp, name))]
        if missing:
            print(f"仓库中缺少目录: {', '.join(missing)}", file=sys.stderr)
            return 2

        os.makedirs(pony_root, exist_ok=True)
        for name in FOLDERS:
            src = os.path.join(tmp, name)
            dst = os.path.join(pony_root, name)
            if os.path.lexists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

        名称 = "；".join(FOLDERS)
        目标 = "；".join(dest_paths)
        try:
            records.append_path_operation_log(
                发起路径=os.getcwd(),
                目标路径=目标,
                名称=名称,
                简称="pony git",
                发起软件=software,
                session_ids=[],
            )
        except OSError as e:
            print(f"（警告）路径操作记录写入失败: {e}", file=sys.stderr)

        print(f"已用 GitHub 内容覆盖:\n{preview}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
