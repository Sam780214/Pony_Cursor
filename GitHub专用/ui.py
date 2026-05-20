"""Hi AI 聊天界面（Tkinter）。"""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ollama_client import OllamaClient, resolve_ollama_base_url

APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "ollama_model": "gemma3:4b",
    "ollama_base_url": "http://localhost:11434",
    "system_prompt": "",
}


def load_settings() -> dict:
    if SETTINGS_PATH.is_file():
        try:
            with SETTINGS_PATH.open(encoding="utf-8") as f:
                data = json.load(f)
            merged = {**DEFAULT_SETTINGS, **data}
            merged["ollama_base_url"] = resolve_ollama_base_url(
                merged.get("ollama_base_url")
            )
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    defaults = dict(DEFAULT_SETTINGS)
    defaults["ollama_base_url"] = resolve_ollama_base_url(defaults.get("ollama_base_url"))
    return defaults


def save_settings(data: dict) -> None:
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

FONT_UI = ("Microsoft YaHei UI", 10)
FONT_TITLE = ("Microsoft YaHei UI", 11, "bold")
FONT_CHAT = ("Microsoft YaHei UI", 10)

COLORS = {
    "bg": "#f4f6f9",
    "panel": "#ffffff",
    "accent": "#4f6ef7",
    "accent_hover": "#3d5ce0",
    "user_bubble": "#e8eeff",
    "ai_bubble": "#ffffff",
    "text": "#1a1d26",
    "muted": "#6b7280",
    "border": "#e2e8f0",
    "input_bg": "#fafbfc",
}


class HiAIApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        prompt = self.settings.get("system_prompt") or None
        self.client = OllamaClient(
            model=self.settings["ollama_model"],
            base_url=self.settings["ollama_base_url"],
            system_prompt=prompt,
        )
        self._streaming = False
        self._assistant_start: str | None = None

        self.root = tk.Tk()
        self.root.title("Hi AI · Ollama 对话")
        self.root.minsize(720, 520)
        self.root.geometry("880x640")
        self.root.configure(bg=COLORS["bg"])

        self._build_ui()
        self.root.after(300, self._refresh_connection)

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg=COLORS["panel"], padx=16, pady=12)
        top.pack(fill=tk.X)

        tk.Label(
            top,
            text="Hi AI",
            font=("Microsoft YaHei UI", 16, "bold"),
            fg=COLORS["accent"],
            bg=COLORS["panel"],
        ).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="正在检查连接…")
        tk.Label(
            top,
            textvariable=self.status_var,
            font=FONT_UI,
            fg=COLORS["muted"],
            bg=COLORS["panel"],
        ).pack(side=tk.LEFT, padx=(16, 0))

        btn_frame = tk.Frame(top, bg=COLORS["panel"])
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="设置", command=self._open_settings).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="清空对话", command=self._clear_chat).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="刷新模型", command=self._refresh_models).pack(
            side=tk.LEFT, padx=4
        )

        model_bar = tk.Frame(self.root, bg=COLORS["bg"], padx=16, pady=(0, 8))
        model_bar.pack(fill=tk.X)

        tk.Label(
            model_bar, text="模型", font=FONT_UI, bg=COLORS["bg"], fg=COLORS["text"]
        ).pack(side=tk.LEFT)

        self.model_var = tk.StringVar(value=self.settings["ollama_model"])
        self.model_combo = ttk.Combobox(
            model_bar,
            textvariable=self.model_var,
            width=36,
            state="readonly",
        )
        self.model_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_change)

        chat_outer = tk.Frame(self.root, bg=COLORS["bg"], padx=16, pady=0)
        chat_outer.pack(fill=tk.BOTH, expand=True)

        self.chat_text = tk.Text(
            chat_outer,
            wrap=tk.WORD,
            font=FONT_CHAT,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=14,
            pady=12,
            spacing1=4,
            spacing3=8,
            state=tk.DISABLE,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(chat_outer, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chat_text.tag_configure("user_label", foreground=COLORS["accent"], font=FONT_TITLE)
        self.chat_text.tag_configure("ai_label", foreground="#059669", font=FONT_TITLE)
        self.chat_text.tag_configure("system", foreground=COLORS["muted"], font=FONT_UI)
        self.chat_text.tag_configure("error", foreground="#dc2626")

        input_outer = tk.Frame(self.root, bg=COLORS["panel"], padx=16, pady=14)
        input_outer.pack(fill=tk.X)

        self.input_box = tk.Text(
            input_outer,
            height=3,
            wrap=tk.WORD,
            font=FONT_CHAT,
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=10,
            pady=8,
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)

        self.send_btn = tk.Button(
            input_outer,
            text="发送",
            font=FONT_UI,
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_hover"],
            activeforeground="white",
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._send_message,
        )
        self.send_btn.pack(side=tk.RIGHT, padx=(12, 0))

        hint = tk.Label(
            self.root,
            text="Enter 发送 · Shift+Enter 换行",
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["muted"],
            bg=COLORS["bg"],
        )
        hint.pack(pady=(0, 10))

        self._append_system("欢迎使用 Hi AI。请确保本机 Ollama 已运行。")

    def _append_system(self, text: str) -> None:
        self._append_chat("系统", text, "system")

    def _append_chat(self, label: str, text: str, tag: str) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        label_tag = "user_label" if label == "你" else "ai_label" if label == "AI" else "system"
        if label in ("你", "AI"):
            self.chat_text.insert(tk.END, f"{label}\n", label_tag)
        self.chat_text.insert(tk.END, f"{text}\n\n", tag)
        self.chat_text.configure(state=tk.DISABLE)
        self.chat_text.see(tk.END)

    def _append_token(self, token: str) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.insert(tk.END, token, "ai")
        self.chat_text.configure(state=tk.DISABLE)
        self.chat_text.see(tk.END)

    def _on_enter(self, event: tk.Event) -> str:
        if not event.state & 0x1:
            self._send_message()
            return "break"
        return None

    def _send_message(self) -> None:
        if self._streaming:
            return
        text = self.input_box.get("1.0", tk.END).strip()
        if not text:
            return

        self.input_box.delete("1.0", tk.END)
        self._append_chat("你", text, "user")
        self._set_busy(True)

        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.insert(tk.END, "AI\n", "ai_label")
        self.chat_text.configure(state=tk.DISABLE)
        self._assistant_start = self.chat_text.index(tk.END)
        self._streaming = True

        def on_token(token: str) -> None:
            self.root.after(0, lambda t=token: self._append_token(t))

        def on_done(_full: str) -> None:
            def finish() -> None:
                self._streaming = False
                self._assistant_start = None
                self.chat_text.configure(state=tk.NORMAL)
                self.chat_text.insert(tk.END, "\n", "ai")
                self.chat_text.configure(state=tk.DISABLE)
                self._set_busy(False)

            self.root.after(0, finish)

        def on_error(msg: str) -> None:
            def show_err() -> None:
                self._streaming = False
                self._set_busy(False)
                if self._assistant_start:
                    self.chat_text.configure(state=tk.NORMAL)
                    self.chat_text.delete(self._assistant_start, tk.END)
                    self.chat_text.configure(state=tk.DISABLE)
                self._append_chat("系统", f"请求失败：{msg}", "error")

            self.root.after(0, show_err)

        self.client.model = self.model_var.get().strip()
        self.client.chat(text, on_token=on_token, on_done=on_done, on_error=on_error)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.send_btn.configure(state=state)
        self.input_box.configure(state=state)

    def _clear_chat(self) -> None:
        self.client.reset_conversation()
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.configure(state=tk.DISABLE)
        self._append_system("对话已清空。")

    def _on_model_change(self, _event: tk.Event | None = None) -> None:
        model = self.model_var.get()
        self.client.model = model
        self.settings["ollama_model"] = model
        save_settings(self.settings)

    def _refresh_connection(self) -> None:
        ok, msg = self.client.ping()
        self.status_var.set(msg if ok else f"● {msg}")
        if ok:
            self._refresh_models(silent=True)

    def _refresh_models(self, silent: bool = False) -> None:
        try:
            models = self.client.list_models()
            if not models:
                if not silent:
                    messagebox.showinfo(
                        "提示", "未检测到已安装的模型，请先执行 ollama pull。"
                    )
                return
            current = self.model_var.get()
            self.model_combo["values"] = models
            if current in models:
                self.model_var.set(current)
            elif models:
                self.model_var.set(models[0])
                self.client.model = models[0]
            if not silent:
                self.status_var.set(f"已加载 {len(models)} 个模型")
        except Exception as e:
            if not silent:
                messagebox.showerror("错误", f"获取模型列表失败：{e}")

    def _open_settings(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.geometry("480x320")
        win.transient(self.root)
        win.grab_set()

        url_var = tk.StringVar(value=self.settings["ollama_base_url"])
        model_var = tk.StringVar(value=self.settings["ollama_model"])
        prompt_var = tk.StringVar(value=self.settings.get("system_prompt", ""))

        pad = {"padx": 16, "pady": 6, "sticky": "ew"}
        win.columnconfigure(1, weight=1)

        tk.Label(win, text="Ollama 地址", font=FONT_UI).grid(row=0, column=0, **pad)
        tk.Entry(win, textvariable=url_var, font=FONT_UI).grid(row=0, column=1, **pad)

        tk.Label(win, text="默认模型", font=FONT_UI).grid(row=1, column=0, **pad)
        tk.Entry(win, textvariable=model_var, font=FONT_UI).grid(row=1, column=1, **pad)

        tk.Label(win, text="系统提示（可选）", font=FONT_UI).grid(
            row=2, column=0, padx=16, pady=6, sticky="nw"
        )
        prompt_box = tk.Text(win, height=5, font=FONT_UI, wrap=tk.WORD)
        prompt_box.grid(row=2, column=1, padx=16, pady=6, sticky="nsew")
        if prompt_var.get():
            prompt_box.insert("1.0", prompt_var.get())
        win.rowconfigure(2, weight=1)

        def apply() -> None:
            url = url_var.get().strip()
            model = model_var.get().strip()
            if not url or not model:
                messagebox.showerror("提示", "请填写 Ollama 地址和模型名称。", parent=win)
                return
            prompt = prompt_box.get("1.0", tk.END).strip()
            self.settings["ollama_base_url"] = url
            self.settings["ollama_model"] = model
            self.settings["system_prompt"] = prompt
            save_settings(self.settings)

            self.client.base_url = url.rstrip("/")
            self.client.model = model
            if prompt:
                self.client.system_prompt = prompt
                self.client.reset_conversation()
            self.model_var.set(model)
            win.destroy()
            self._refresh_connection()
            self._append_system("设置已保存。")

        ttk.Button(win, text="保存", command=apply).grid(
            row=3, column=0, columnspan=2, pady=16
        )

    def run(self) -> None:
        self.root.mainloop()
