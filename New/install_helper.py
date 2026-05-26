#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pony_Cursor 依赖勾选安装助手（仓库根目录 New/，与 GitHub专用/ 无关）。
读取同目录 dependencies.json，按项目预选 pip 包并一键安装。
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

# 国内访问 PyPI 较慢时可选镜像
PYPI_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

if TYPE_CHECKING:
    import tkinter as tk

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "dependencies.json"


def load_catalog() -> dict:
    with JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def pip_installable(deps: list[dict]) -> list[dict]:
    return [d for d in deps if d.get("pip_spec")]


class InstallHelperApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import messagebox, scrolledtext, ttk

        self.tk = tk
        self.messagebox = messagebox
        self.scrolledtext = scrolledtext
        self.ttk = ttk

        self.catalog = load_catalog()
        self.dep_by_id = {d["id"]: d for d in self.catalog["dependencies"]}
        self.tool_by_id = {t["id"]: t for t in self.catalog["tools"]}
        self.vars: dict = {}
        self._pip_busy = False
        self._pip_proc: subprocess.Popen[str] | None = None

        self.root = tk.Tk()
        self.root.title("Pony_Cursor 依赖安装助手")
        self.root.minsize(720, 520)
        self.root.geometry("900x640")

        self._build_ui()
        self._select_tool("game")

    def _build_ui(self) -> None:
        tk = self.tk
        ttk = self.ttk
        meta = self.catalog.get("meta", {})
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(
            top,
            text=f"{meta.get('title', '依赖清单')}  ·  Python {meta.get('python_min', '3.10')}+",
            font=("", 11, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            top,
            text=meta.get("description", ""),
            wraplength=860,
        ).pack(anchor=tk.W, pady=(4, 0))

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left = ttk.LabelFrame(body, text="按项目预选", padding=6)
        body.add(left, weight=1)
        self.tool_list = tk.Listbox(left, exportselection=False, height=12)
        self.tool_list.pack(fill=tk.BOTH, expand=True)
        for t in self.catalog["tools"]:
            self.tool_list.insert(tk.END, t["name"])
        self.tool_list.bind("<<ListboxSelect>>", self._on_tool_select)
        ttk.Button(left, text="全选 pip 包", command=self._select_all_pip).pack(
            fill=tk.X, pady=(6, 2)
        )
        ttk.Button(left, text="清空 pip 勾选", command=self._clear_pip).pack(fill=tk.X)

        right = ttk.Frame(body)
        body.add(right, weight=3)

        canvas_frame = ttk.LabelFrame(right, text="依赖项（勾选后参与 pip 安装）", padding=4)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.dep_inner = ttk.Frame(canvas)
        self.dep_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.dep_inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for dep in self.catalog["dependencies"]:
            self._add_dep_row(dep)

        cmd_frame = ttk.LabelFrame(right, text="生成的 pip 命令", padding=6)
        cmd_frame.pack(fill=tk.X, pady=(8, 0))
        self.cmd_text = self.scrolledtext.ScrolledText(
            cmd_frame, height=3, wrap=tk.WORD, font=("Consolas", 10)
        )
        self.cmd_text.pack(fill=tk.X)

        opt_row = ttk.Frame(right)
        opt_row.pack(fill=tk.X, pady=(4, 0))
        self.use_mirror = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opt_row,
            text="使用清华 PyPI 镜像（国内网络推荐，可减少卡住/未响应）",
            variable=self.use_mirror,
            command=self._refresh_command,
        ).pack(anchor=tk.W)

        btn_row = ttk.Frame(right)
        btn_row.pack(fill=tk.X, pady=8)
        ttk.Button(btn_row, text="刷新命令", command=self._refresh_command).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="复制命令", command=self._copy_command).pack(side=tk.LEFT, padx=6)
        self.btn_install = ttk.Button(btn_row, text="执行 pip 安装", command=self._run_pip)
        self.btn_install.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="打开 JSON", command=self._open_json).pack(side=tk.RIGHT)

        notes = self.catalog.get("notes", [])
        if notes:
            note_frame = ttk.LabelFrame(self.root, text="说明", padding=6)
            note_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
            ttk.Label(
                note_frame,
                text="\n".join(f"• {n}" for n in notes[:4]),
                wraplength=860,
                justify=tk.LEFT,
            ).pack(anchor=tk.W)

    def _kind_label(self, kind: str) -> str:
        return {
            "pip": "pip",
            "stdlib": "标准库",
            "runtime": "运行时",
            "system": "系统软件",
        }.get(kind, kind)

    def _add_dep_row(self, dep: dict) -> None:
        tk = self.tk
        ttk = self.ttk
        row = ttk.Frame(self.dep_inner, padding=(2, 4))
        row.pack(fill=tk.X, anchor=tk.W)

        dep_id = dep["id"]
        has_pip = bool(dep.get("pip_spec"))
        var = self.tk.BooleanVar(value=False)
        self.vars[dep_id] = var

        kind = dep.get("kind", "")
        cb = ttk.Checkbutton(
            row,
            text=f"[{self._kind_label(kind)}] {dep.get('display_name', dep_id)}",
            variable=var,
            command=self._refresh_command,
            state=tk.NORMAL if has_pip else tk.DISABLED,
        )
        cb.pack(anchor=tk.W)

        ver = dep.get("version") or dep.get("version_constraint") or ""
        opt = "（可选）" if dep.get("optional") else ""
        sub = f"{ver} {opt}".strip()
        if sub:
            ttk.Label(row, text=sub, foreground="#555").pack(anchor=tk.W, padx=(22, 0))

        ttk.Label(
            row,
            text=dep.get("role", ""),
            wraplength=620,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=(22, 0), pady=(2, 0))

        if kind in ("system", "runtime", "stdlib") and not has_pip:
            install = dep.get("install") or {}
            hint = install.get("windows") or install.get("linux") or ""
            if hint:
                ttk.Label(
                    row,
                    text=f"安装：{hint}",
                    wraplength=620,
                    foreground="#0066aa",
                ).pack(anchor=tk.W, padx=(22, 0))

    def _on_tool_select(self, _event=None) -> None:
        sel = self.tool_list.curselection()
        if not sel:
            return
        tool = self.catalog["tools"][sel[0]]
        self._select_tool(tool["id"])

    def _select_tool(self, tool_id: str) -> None:
        tk = self.tk
        tool = self.tool_by_id.get(tool_id)
        if not tool:
            return
        for i, t in enumerate(self.catalog["tools"]):
            if t["id"] == tool_id:
                self.tool_list.selection_clear(0, tk.END)
                self.tool_list.selection_set(i)
                self.tool_list.see(i)
                break
        wanted = set(tool.get("dependency_ids", []))
        for dep_id, var in self.vars.items():
            dep = self.dep_by_id.get(dep_id, {})
            if dep.get("pip_spec"):
                var.set(dep_id in wanted)
        self._refresh_command()

    def _select_all_pip(self) -> None:
        for dep_id, var in self.vars.items():
            if self.dep_by_id.get(dep_id, {}).get("pip_spec"):
                var.set(True)
        self._refresh_command()

    def _clear_pip(self) -> None:
        for dep_id, var in self.vars.items():
            if self.dep_by_id.get(dep_id, {}).get("pip_spec"):
                var.set(False)
        self._refresh_command()

    def _selected_pip_specs(self) -> list[str]:
        specs: list[str] = []
        for dep_id, var in self.vars.items():
            if not var.get():
                continue
            dep = self.dep_by_id.get(dep_id, {})
            spec = dep.get("pip_spec")
            if spec:
                specs.append(spec)
        return specs

    def _pip_argv(self, specs: list[str], *, use_mirror: bool | None = None) -> list[str]:
        mirror = (
            use_mirror
            if use_mirror is not None
            else bool(getattr(self, "use_mirror", None) and self.use_mirror.get())
        )
        argv = [sys.executable, "-m", "pip", "install"]
        if mirror:
            argv.extend(["-i", PYPI_MIRROR])
        argv.extend(["--no-input", "-v", *specs])
        return argv

    def _refresh_command(self) -> None:
        tk = self.tk
        specs = self._selected_pip_specs()
        py = sys.executable
        if specs:
            parts = [f'"{py}"', "-m", "pip", "install", "--no-input"]
            if getattr(self, "use_mirror", None) and self.use_mirror.get():
                parts += ["-i", PYPI_MIRROR]
            parts.append(" ".join(f'"{s}"' for s in specs))
            cmd = " ".join(parts)
        else:
            cmd = "# 请勾选至少一个 pip 包（带 [pip] 标记的项）"
        self.cmd_text.delete("1.0", tk.END)
        self.cmd_text.insert(tk.END, cmd)

    def _copy_command(self) -> None:
        tk = self.tk
        text = self.cmd_text.get("1.0", tk.END).strip()
        if text.startswith("#"):
            self.messagebox.showinfo("提示", "当前没有可复制的 pip 命令。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.messagebox.showinfo("已复制", "pip 命令已复制到剪贴板。")

    def _set_pip_busy(self, busy: bool) -> None:
        self._pip_busy = busy
        if busy:
            self.btn_install.state(["disabled"])
        else:
            self.btn_install.state(["!disabled"])

    def _run_pip(self) -> None:
        if self._pip_busy:
            self.messagebox.showinfo("请稍候", "正在安装中，请查看安装进度窗口。")
            return
        specs = self._selected_pip_specs()
        if not specs:
            self.messagebox.showwarning("未选择", "请先勾选要安装的 pip 包。")
            return
        mirror_hint = "\n\n已勾选清华镜像（国内网络更快）。" if self.use_mirror.get() else ""
        if not self.messagebox.askyesno(
            "确认安装",
            f"将执行 pip 安装 {len(specs)} 个包：\n"
            + "\n".join(specs)
            + "\n\n安装过程会打开进度窗口；下载较大时可能需几分钟，并非死机。"
            + mirror_hint,
        ):
            return
        self._open_pip_progress_window(specs)

    def _open_pip_progress_window(self, specs: list[str]) -> None:
        tk = self.tk
        ttk = self.ttk
        win = tk.Toplevel(self.root)
        win.title("pip 安装进度")
        win.geometry("720x420")
        win.transient(self.root)
        ttk.Label(
            win,
            text="正在安装，主窗口可继续操作；下方会实时显示 pip 输出。",
            wraplength=680,
        ).pack(anchor=tk.W, padx=8, pady=8)
        log = self.scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas", 9))
        log.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        bar = ttk.Progressbar(win, mode="indeterminate")
        bar.pack(fill=tk.X, padx=8, pady=4)
        bar.start(12)
        btn_close = ttk.Button(win, text="关闭", state=tk.DISABLED, command=win.destroy)
        btn_close.pack(pady=8)

        argv = self._pip_argv(specs)
        log.insert(tk.END, "命令: " + " ".join(argv) + "\n\n")
        log.see(tk.END)

        self._set_pip_busy(True)

        def append_line(line: str) -> None:
            log.insert(tk.END, line)
            log.see(tk.END)

        def on_done(code: int, err: str | None) -> None:
            bar.stop()
            self._set_pip_busy(False)
            self._pip_proc = None
            btn_close.state(["!disabled"])
            if err:
                append_line(f"\n[错误] {err}\n")
            append_line(f"\n--- 结束，退出码 {code} ---\n")
            if code == 0:
                self.messagebox.showinfo("安装完成", "pip 安装已成功完成。")
            else:
                self.messagebox.showerror(
                    "安装失败",
                    f"退出码 {code}。请查看进度窗口输出；国内网络可勾选「清华镜像」后重试。",
                )

        def worker() -> None:
            code = -1
            err: str | None = None
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            try:
                proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=flags,
                )
                self._pip_proc = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.root.after(0, append_line, line)
                code = proc.wait()
            except OSError as e:
                err = str(e)
            finally:
                self.root.after(0, on_done, code, err)

        threading.Thread(target=worker, daemon=True).start()

    def _open_json(self) -> None:
        try:
            if sys.platform == "win32":
                import os

                os.startfile(JSON_PATH)  # noqa: S606
            else:
                subprocess.run(["xdg-open", str(JSON_PATH)], check=False)
        except OSError:
            self.messagebox.showinfo("路径", str(JSON_PATH))

    def run(self) -> None:
        self._refresh_command()
        self.root.mainloop()


def _cli_list_tools(catalog: dict) -> None:
    print("项目 / 工具：")
    for i, t in enumerate(catalog["tools"], 1):
        print(f"  {i}. {t['name']}  ({t['id']})")
        print(f"     路径: {t['path']}  入口: {t.get('entry', '')}")


def _cli_install(tool_id: str | None, specs: list[str] | None, dry_run: bool) -> int:
    catalog = load_catalog()
    dep_by_id = {d["id"]: d for d in catalog["dependencies"]}
    chosen: list[str] = []

    if tool_id:
        tool = next((t for t in catalog["tools"] if t["id"] == tool_id), None)
        if not tool:
            print(f"未知工具 id: {tool_id}", file=sys.stderr)
            return 2
        for did in tool.get("dependency_ids", []):
            dep = dep_by_id.get(did, {})
            if dep.get("pip_spec"):
                chosen.append(dep["pip_spec"])
    if specs:
        for sid in specs:
            dep = dep_by_id.get(sid)
            if dep and dep.get("pip_spec"):
                chosen.append(dep["pip_spec"])
            elif "." in sid or ">=" in sid:
                chosen.append(sid)
            else:
                print(f"警告: 未知依赖 id，跳过: {sid}", file=sys.stderr)

    chosen = list(dict.fromkeys(chosen))
    if not chosen:
        print("没有可安装的 pip 包。", file=sys.stderr)
        return 1
    cmd = [sys.executable, "-m", "pip", "install", "--no-input", "-v", *chosen]
    print(" ".join(cmd))
    print("（安装中请耐心等待；若卡住可改用: pip install -i", PYPI_MIRROR, "...）")
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Pony_Cursor 依赖安装助手")
    parser.add_argument("--list-tools", action="store_true", help="列出 JSON 中的项目")
    parser.add_argument("--tool", metavar="ID", help="按工具 id 安装其 pip 依赖，如 game")
    parser.add_argument(
        "--deps",
        nargs="+",
        metavar="ID",
        help="按依赖 id 安装，如 pygame keyboard",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="只打印 pip 命令")
    parser.add_argument("--gui", action="store_true", help="强制打开图形界面")
    args = parser.parse_args()

    if not JSON_PATH.is_file():
        print(f"找不到 {JSON_PATH}", file=sys.stderr)
        raise SystemExit(1)

    if args.list_tools:
        _cli_list_tools(load_catalog())
        return

    if args.tool or args.deps:
        raise SystemExit(_cli_install(args.tool, args.deps, args.dry_run))

    if args.gui:
        InstallHelperApp().run()
        return

    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("当前环境无 tkinter，请使用：")
        print("  python install_helper.py --list-tools")
        print("  python install_helper.py --tool game")
        print("  python install_helper.py --deps pygame questionary -n")
        raise SystemExit(0)

    InstallHelperApp().run()


if __name__ == "__main__":
    main()
