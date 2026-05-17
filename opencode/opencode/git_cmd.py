"""在 Pony 根目录下维护 Pony_Cursor_repo：清理后浅克隆 GitHub 仓库到该文件夹内。"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import time

from . import records, ui
from .paths import record_dir

REPO_DIR_NAME = "Pony_Cursor_repo"
EXPECTED_TOPLEVEL = ("desktop-pet", "opencode", "game")
DEFAULT_REPO = "https://github.com/Sam780214/Pony_Cursor.git"


def _which_git() -> str | None:
    return shutil.which("git")


def _pony_install_dir() -> str | None:
    """全局 pony 命令对应的源码目录（pip install -e 时通常在 Pony_Cursor_repo\\opencode）。"""
    try:
        import opencode.cli as cli_mod

        return os.path.dirname(os.path.abspath(cli_mod.__file__))
    except Exception:
        return None


def _warn_global_install_inside_repo(repo_dest: str) -> None:
    repo_dest = os.path.abspath(repo_dest)
    pkg = _pony_install_dir()
    if not pkg:
        return
    pkg = os.path.abspath(pkg)
    if pkg == repo_dest or pkg.startswith(repo_dest + os.sep):
        print(
            "（说明）pony 已通过 pip 全局安装，当前加载的代码就在待重建的 "
            f"{REPO_DIR_NAME} 内。\n"
            "  · 请勿在本目录内运行 pony git；应先 cd /d D:\\Pony\n"
            "  · 克隆完成后请重新执行: "
            f"cd /d {repo_dest}\\opencode && py -3 -m pip install -e .",
            file=sys.stderr,
        )


def _on_rm_error(func, path: str, exc_info) -> None:
    if not os.path.lexists(path):
        return
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        raise


def _leave_tree_if_inside(tree: str, fallback_dir: str) -> None:
    """若当前工作目录在待删目录内，先切到 Pony 根目录，避免 WinError 5。"""
    tree = os.path.abspath(tree)
    fallback_dir = os.path.abspath(fallback_dir)
    try:
        cwd = os.path.abspath(os.getcwd())
    except OSError:
        return
    if cwd == tree or cwd.startswith(tree + os.sep):
        os.chdir(fallback_dir)
        print(f"（已离开待删目录，当前工作目录: {os.getcwd()}）", file=sys.stderr)


def _remove_tree(path: str, pony_root: str) -> None:
    path = os.path.abspath(path)
    if not os.path.lexists(path):
        return
    _leave_tree_if_inside(path, pony_root)

    if sys.platform == "win32":
        for attempt in range(3):
            subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if not os.path.lexists(path):
                return
            if attempt < 2:
                time.sleep(0.5)
        if os.path.lexists(path):
            print(
                "（提示）Windows 仍无法删除部分文件。请关闭占用 "
                f"{REPO_DIR_NAME} 的程序（Cursor、在本目录打开的 cmd 等），"
                f"在 D:\\Pony 下重新执行: pony git -y",
                file=sys.stderr,
            )

    shutil.rmtree(path, onerror=_on_rm_error)


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

    _warn_global_install_inside_repo(repo_dest)

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
    try:
        os.chdir(pony_root)
    except OSError:
        pass
    if os.path.lexists(repo_dest):
        try:
            _remove_tree(repo_dest, pony_root)
        except OSError as e:
            print(f"删除失败: {repo_dest}\n{e}", file=sys.stderr)
            print(
                "请先关闭 Cursor / 结束在 Pony_Cursor_repo 内的终端，"
                f"在 cmd 执行: cd /d {pony_root}  再运行 pony git -y",
                file=sys.stderr,
            )
            return 1
        if os.path.lexists(repo_dest):
            print(f"删除未完成，目录仍在: {repo_dest}", file=sys.stderr)
            return 1

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
    print(
        f"\n请在新 cmd 中重新注册全局 pony 命令:\n"
        f"  cd /d {os.path.join(repo_dest, 'opencode')}\n"
        f"  py -3 -m pip install -e .",
        file=sys.stderr,
    )
    return 0
