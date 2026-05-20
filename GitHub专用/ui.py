"""Hi AI 聊天界面（Tkinter）。"""
from __future__ import annotations

import json
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from edition import edition_label, use_deepseek_edition
from model_aliases import display_name, load_model_aliases, resolve_model_id
from ollama_client import OllamaClient, resolve_ollama_base_url
from dpi import apply_tk_scaling
from stats_charts import StatsTracker, StatsWindow
from version import APP_VERSION

HAS_DEEPSEEK = use_deepseek_edition()
if HAS_DEEPSEEK:
    from config import PROVIDERS, create_chat_client
    from config import load_settings as _load_settings_ds
    from config import save_settings as _save_settings_ds

APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "ollama_model": "gemma3:4b",
    "ollama_base_url": "http://localhost:11434",
    "system_prompt": "",
}


def load_settings() -> dict:
    if HAS_DEEPSEEK:
        return _load_settings_ds()
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
    if HAS_DEEPSEEK:
        _save_settings_ds(data)
        return
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

FONT_FAMILY = "Microsoft YaHei UI"
# 桌面基准字号；UI_SIZE_SCALE 控制整体放大（2.0 的 0.75 倍 ≈ 缩小 25%）
UI_SIZE_SCALE = 1.5
FONT_PT_UI = 10
FONT_PT_TITLE = 11
FONT_PT_CHAT = 10
FONT_PT_HERO = 14
FONT_PT_SMALL = 9
FONT_PT_COMBO = 13
# 来源 / 模型选择框：框体与字号单独缩放（相对 UI_SIZE_SCALE）
SELECTOR_BOX_SCALE = 0.65
SELECTOR_FONT_SCALE = 0.75

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
        if HAS_DEEPSEEK:
            self.client = create_chat_client(self.settings)
        else:
            self.client = OllamaClient(
                model=self.settings["ollama_model"],
                base_url=self.settings["ollama_base_url"],
                system_prompt=prompt,
            )
        self._streaming = False
        self._assistant_start: str | None = None
        self._aliases = load_model_aliases()
        self._stats = StatsTracker()
        self._turn_t0 = 0.0
        self._first_token_at: float | None = None
        self._reply_chars = 0

        self.root = tk.Tk()
        self._ui_scale = apply_tk_scaling(self.root)
        self._stats_win = StatsWindow(self.root, self._stats, self._font)
        self.FONT_UI = self._font(FONT_PT_UI)
        self.FONT_TITLE = self._font(FONT_PT_TITLE, bold=True)
        self.FONT_CHAT = self._font(FONT_PT_CHAT)
        self.FONT_HERO = self._font(FONT_PT_HERO, bold=True)
        self.FONT_SMALL = self._font(FONT_PT_SMALL)
        self.FONT_COMBO = self._font(FONT_PT_COMBO)
        self.root.title(f"Hi AI · {edition_label()}")
        self.root.minsize(int(920 * UI_SIZE_SCALE), int(560 * UI_SIZE_SCALE))
        self.root.geometry(f"{int(1060 * UI_SIZE_SCALE)}x{int(640 * UI_SIZE_SCALE)}")
        self.root.configure(bg=COLORS["bg"])

        self._build_ui()
        self.root.after(300, self._refresh_connection)

    def _font(self, pt: int, bold: bool = False) -> tuple:
        size = max(9, int(round(pt * UI_SIZE_SCALE)))
        if bold:
            return (FONT_FAMILY, size, "bold")
        return (FONT_FAMILY, size)

    def _combo_font(self, font_scale: float = 1.0) -> tuple:
        size = max(9, int(round(FONT_PT_COMBO * UI_SIZE_SCALE * font_scale)))
        return (FONT_FAMILY, size)

    def _create_menu_selector(
        self,
        parent: tk.Misc,
        variable: tk.StringVar,
        command,
        *,
        box_scale: float = 1.0,
        font_scale: float = 1.0,
    ) -> tuple[tk.Menubutton, tk.Menu, tuple]:
        """Menubutton 下拉；font_scale / box_scale 可单独调节模型框。"""
        combo_font = self._combo_font(font_scale)
        btn = tk.Menubutton(
            parent,
            textvariable=variable,
            font=combo_font,
            relief="solid",
            borderwidth=1,
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            activebackground="#e8eeff",
            activeforeground=COLORS["text"],
            anchor="w",
            padx=max(4, int(18 * UI_SIZE_SCALE * box_scale)),
            pady=max(2, int(10 * UI_SIZE_SCALE * box_scale)),
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        menu = tk.Menu(
            btn,
            tearoff=0,
            font=combo_font,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["accent"],
            activeforeground="white",
        )
        btn.configure(menu=menu)
        return btn, menu, combo_font

    def _fill_menu(
        self,
        menu: tk.Menu,
        items: list[tuple[str, str]],
        variable: tk.StringVar,
        command,
        menu_font: tuple | None = None,
    ) -> None:
        font = menu_font or self.FONT_COMBO
        menu.delete(0, tk.END)
        for value, label in items:
            menu.add_radiobutton(
                label=label,
                variable=variable,
                value=value,
                command=command,
                font=font,
            )

    def _set_model_menu(self, labels: list[str]) -> None:
        self._fill_menu(
            self.model_menu,
            [(label, label) for label in labels],
            self.model_var,
            self._on_model_change,
            menu_font=self.FONT_MODEL,
        )

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        style.configure("HiAI.TButton", font=self.FONT_UI, padding=int(4 * UI_SIZE_SCALE))

        header = tk.Frame(
            self.root,
            bg=COLORS["panel"],
            padx=int(16 * UI_SIZE_SCALE),
            pady=int(10 * UI_SIZE_SCALE),
        )
        header.pack(fill=tk.X)

        title_row = tk.Frame(header, bg=COLORS["panel"])
        title_row.pack(fill=tk.X)

        title_left = tk.Frame(title_row, bg=COLORS["panel"])
        title_left.pack(side=tk.LEFT)
        tk.Label(
            title_left,
            text="Hi AI",
            font=self.FONT_HERO,
            fg=COLORS["accent"],
            bg=COLORS["panel"],
        ).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="正在检查连接…")
        tk.Label(
            title_left,
            textvariable=self.status_var,
            font=self.FONT_UI,
            fg=COLORS["muted"],
            bg=COLORS["panel"],
        ).pack(side=tk.LEFT, padx=(14, 0))

        btn_box = tk.Frame(title_row, bg=COLORS["panel"])
        btn_box.pack(side=tk.RIGHT)
        for label, cmd in (
            ("重载别名", self._reload_aliases),
            ("清空", self._clear_chat),
            ("刷新模型", self._refresh_models),
            ("设置", self._open_settings),
        ):
            ttk.Button(btn_box, text=label, command=cmd, style="HiAI.TButton").pack(
                side=tk.LEFT, padx=int(4 * UI_SIZE_SCALE)
            )
        self.send_btn = tk.Button(
            btn_box,
            text="发送",
            font=self.FONT_UI,
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_hover"],
            activeforeground="white",
            relief=tk.FLAT,
            padx=int(14 * UI_SIZE_SCALE),
            pady=int(6 * UI_SIZE_SCALE),
            cursor="hand2",
            command=self._send_message,
        )
        self.send_btn.pack(side=tk.LEFT, padx=(int(8 * UI_SIZE_SCALE), 0))

        select_row = tk.Frame(header, bg=COLORS["panel"])
        select_row.pack(fill=tk.X, pady=(int(12 * UI_SIZE_SCALE), 0))
        select_row.columnconfigure(3, weight=1)

        col = 0
        if HAS_DEEPSEEK:
            tk.Label(
                select_row,
                text="来源",
                font=self.FONT_UI,
                bg=COLORS["panel"],
                fg=COLORS["text"],
            ).grid(row=0, column=col, padx=(0, int(8 * UI_SIZE_SCALE)), sticky="w")
            col += 1
            self.provider_var = tk.StringVar(
                value=self.settings.get("provider", "ollama")
            )
            prov_wrap = tk.Frame(select_row, bg=COLORS["panel"])
            prov_wrap.grid(row=0, column=col, padx=(0, int(20 * UI_SIZE_SCALE)), sticky="w")
            self.provider_btn, self.provider_menu, self.FONT_PROVIDER = (
                self._create_menu_selector(
                    prov_wrap,
                    self.provider_var,
                    self._on_provider_change,
                    box_scale=SELECTOR_BOX_SCALE,
                    font_scale=SELECTOR_FONT_SCALE,
                )
            )
            self.provider_btn.pack(fill=tk.X)
            self._fill_menu(
                self.provider_menu,
                [(k, v) for k, v in PROVIDERS.items()],
                self.provider_var,
                self._on_provider_change,
                menu_font=self.FONT_PROVIDER,
            )
            col += 1

        tk.Label(
            select_row,
            text="模型",
            font=self.FONT_UI,
            bg=COLORS["panel"],
            fg=COLORS["text"],
        ).grid(row=0, column=col, padx=(0, int(8 * UI_SIZE_SCALE)), sticky="w")
        col += 1
        init_model = self._default_model_id()
        self.model_var = tk.StringVar(value=display_name(init_model, self._aliases))
        model_wrap = tk.Frame(select_row, bg=COLORS["panel"])
        model_wrap.grid(row=0, column=col, columnspan=2, sticky="ew")
        model_wrap.columnconfigure(0, weight=1)
        self.model_btn, self.model_menu, self.FONT_MODEL = self._create_menu_selector(
            model_wrap,
            self.model_var,
            self._on_model_change,
            box_scale=SELECTOR_BOX_SCALE,
            font_scale=SELECTOR_FONT_SCALE,
        )
        self.model_btn.pack(fill=tk.X)
        self._set_model_menu([display_name(init_model, self._aliases)])

        body = tk.Frame(
            self.root,
            bg=COLORS["bg"],
            padx=int(16 * UI_SIZE_SCALE),
            pady=int(8 * UI_SIZE_SCALE),
        )
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        chat_card = tk.Frame(body, bg=COLORS["border"], padx=1, pady=1)
        chat_card.grid(row=0, column=0, sticky="nsew")

        chat_outer = tk.Frame(chat_card, bg=COLORS["panel"])
        chat_outer.pack(fill=tk.BOTH, expand=True)
        chat_outer.grid_rowconfigure(0, weight=1)
        chat_outer.grid_columnconfigure(0, weight=1)

        self.chat_text = tk.Text(
            chat_outer,
            wrap=tk.WORD,
            font=self.FONT_CHAT,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=int(14 * UI_SIZE_SCALE),
            pady=int(12 * UI_SIZE_SCALE),
            spacing1=int(4 * UI_SIZE_SCALE),
            spacing3=int(8 * UI_SIZE_SCALE),
            state=tk.DISABLED,
            cursor="arrow",
        )
        scroll = ttk.Scrollbar(chat_outer, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat_text.grid(row=0, column=0, sticky="nsew")

        self.chat_text.tag_configure("user_label", foreground=COLORS["accent"], font=self.FONT_TITLE)
        self.chat_text.tag_configure("ai_label", foreground="#059669", font=self.FONT_TITLE)
        self.chat_text.tag_configure("system", foreground=COLORS["muted"], font=self.FONT_UI)
        self.chat_text.tag_configure("error", foreground="#dc2626")

        composer = tk.Frame(body, bg=COLORS["bg"])
        composer.grid(row=1, column=0, sticky="ew", pady=(int(10 * UI_SIZE_SCALE), 0))
        self.input_box = tk.Text(
            composer,
            height=int(3 * UI_SIZE_SCALE),
            wrap=tk.WORD,
            font=self.FONT_CHAT,
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            padx=int(10 * UI_SIZE_SCALE),
            pady=int(8 * UI_SIZE_SCALE),
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.input_box.pack(fill=tk.X)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)

        bottom = tk.Frame(self.root, bg=COLORS["bg"])
        bottom.pack(
            fill=tk.X,
            padx=int(16 * UI_SIZE_SCALE),
            pady=(0, int(10 * UI_SIZE_SCALE)),
        )

        self.stats_btn = tk.Button(
            bottom,
            text="统计",
            font=self.FONT_UI,
            bg="#1e40af",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief=tk.FLAT,
            padx=int(18 * UI_SIZE_SCALE),
            pady=int(6 * UI_SIZE_SCALE),
            cursor="hand2",
            command=self._open_stats,
        )
        self.stats_btn.pack(side=tk.LEFT)

        tk.Label(
            bottom,
            text="Hi AI · 显示名来自 Hi AI.json",
            font=self.FONT_SMALL,
            fg=COLORS["muted"],
            bg=COLORS["bg"],
        ).pack(side=tk.LEFT, padx=(12, 0), expand=True)

        tk.Label(
            bottom,
            text=APP_VERSION,
            font=self.FONT_SMALL,
            fg=COLORS["muted"],
            bg=COLORS["bg"],
        ).pack(side=tk.RIGHT)

        if HAS_DEEPSEEK:
            self._append_system(
                "欢迎使用 Hi AI 完整版。可切换 Ollama / DeepSeek；显示名见 Hi AI.json。"
            )
        else:
            self._append_system("欢迎使用 Hi AI（Ollama 版）。请确保本机 Ollama 已运行。")

    def _append_system(self, text: str) -> None:
        self._append_chat("系统", text, "system")

    def _append_chat(self, label: str, text: str, tag: str) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        label_tag = "user_label" if label == "你" else "ai_label" if label == "AI" else "system"
        if label in ("你", "AI"):
            self.chat_text.insert(tk.END, f"{label}\n", label_tag)
        self.chat_text.insert(tk.END, f"{text}\n\n", tag)
        self.chat_text.configure(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def _append_token(self, token: str) -> None:
        if self._first_token_at is None:
            self._first_token_at = time.time()
        self._reply_chars += len(token)
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.insert(tk.END, token, "ai")
        self.chat_text.configure(state=tk.DISABLED)
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
        self.chat_text.configure(state=tk.DISABLED)
        self._assistant_start = self.chat_text.index(tk.END)
        self._streaming = True
        self._turn_t0 = time.time()
        self._first_token_at = None
        self._reply_chars = 0

        def on_token(token: str) -> None:
            self.root.after(0, lambda t=token: self._append_token(t))

        def on_done(_full: str) -> None:
            def finish() -> None:
                self._record_turn_stats()
                self._streaming = False
                self._assistant_start = None
                self.chat_text.configure(state=tk.NORMAL)
                self.chat_text.insert(tk.END, "\n", "ai")
                self.chat_text.configure(state=tk.DISABLED)
                self._set_busy(False)

            self.root.after(0, finish)

        def on_error(msg: str) -> None:
            def show_err() -> None:
                self._record_turn_stats()
                self._streaming = False
                self._set_busy(False)
                if self._assistant_start:
                    self.chat_text.configure(state=tk.NORMAL)
                    self.chat_text.delete(self._assistant_start, tk.END)
                    self.chat_text.configure(state=tk.DISABLED)
                self._append_chat("系统", f"请求失败：{msg}", "error")

            self.root.after(0, show_err)

        real_model = resolve_model_id(self.model_var.get().strip(), self._aliases)
        self.client.model = real_model
        self.client.chat(text, on_token=on_token, on_done=on_done, on_error=on_error)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.send_btn.configure(state=state)
        self.input_box.configure(state=state)

    def _clear_chat(self) -> None:
        self.client.reset_conversation()
        self._stats.clear()
        self._update_charts()
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.configure(state=tk.DISABLED)
        self._append_system("对话已清空。")

    def _record_turn_stats(self) -> None:
        if self._first_token_at is None:
            thinking = time.time() - self._turn_t0
        else:
            thinking = self._first_token_at - self._turn_t0
        self._stats.add_turn(thinking, self._reply_chars)
        self._update_charts()

    def _open_stats(self) -> None:
        self._stats_win.open()

    def _update_charts(self) -> None:
        if self._stats_win.is_open():
            self._stats_win.refresh()

    def _default_model_id(self) -> str:
        if HAS_DEEPSEEK and self.settings.get("provider") == "deepseek":
            return self.settings.get("deepseek_model", "deepseek-chat")
        return self.settings.get("ollama_model", "gemma3:4b")

    def _on_provider_change(self, _event: tk.Event | None = None) -> None:
        if not HAS_DEEPSEEK:
            return
        self.settings["provider"] = self.provider_var.get()
        save_settings(self.settings)
        self.client = create_chat_client(self.settings)
        self.model_var.set(display_name(self._default_model_id(), self._aliases))
        self.client.model = resolve_model_id(self.model_var.get(), self._aliases)
        self._refresh_connection()

    def _reload_aliases(self) -> None:
        self._aliases = load_model_aliases()
        self._refresh_models(silent=False)
        self._append_system("已重载 D:\\Pony\\Hi AI.json 显示名。")

    def _on_model_change(self, _event: tk.Event | None = None) -> None:
        real = resolve_model_id(self.model_var.get(), self._aliases)
        self.client.model = real
        if HAS_DEEPSEEK and self.settings.get("provider") == "deepseek":
            self.settings["deepseek_model"] = real
        else:
            self.settings["ollama_model"] = real
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
                    hint = (
                        "无法获取 DeepSeek 模型列表，请检查 API Key。"
                        if HAS_DEEPSEEK
                        and self.settings.get("provider") == "deepseek"
                        else "未检测到已安装的模型，请先执行 ollama pull。"
                    )
                    messagebox.showinfo("提示", hint)
                return
            labels = [display_name(m, self._aliases) for m in models]
            current_real = resolve_model_id(self.model_var.get(), self._aliases)
            self._set_model_menu(labels)
            if current_real in models:
                self.model_var.set(display_name(current_real, self._aliases))
            elif labels:
                self.model_var.set(labels[0])
                self.client.model = models[0]
            if not silent:
                self.status_var.set(f"已加载 {len(models)} 个模型")
        except Exception as e:
            if not silent:
                messagebox.showerror("错误", f"获取模型列表失败：{e}")

    def _open_settings(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("设置")
        win.geometry("500x380" if HAS_DEEPSEEK else "480x320")
        win.transient(self.root)
        win.grab_set()

        pad = {"padx": 16, "pady": 6, "sticky": "ew"}
        win.columnconfigure(1, weight=1)
        row = 0

        provider_var = None
        if HAS_DEEPSEEK:
            provider_var = tk.StringVar(value=self.settings.get("provider", "ollama"))
            tk.Label(win, text="默认来源", font=self.FONT_UI).grid(row=row, column=0, **pad)
            ttk.Combobox(
                win,
                textvariable=provider_var,
                values=list(PROVIDERS.keys()),
                state="readonly",
            ).grid(row=row, column=1, **pad)
            row += 1

        url_var = tk.StringVar(value=self.settings["ollama_base_url"])
        tk.Label(win, text="Ollama 地址", font=self.FONT_UI).grid(row=row, column=0, **pad)
        tk.Entry(win, textvariable=url_var, font=self.FONT_UI).grid(row=row, column=1, **pad)
        row += 1

        ollama_model_var = tk.StringVar(value=self.settings.get("ollama_model", ""))
        tk.Label(win, text="Ollama 模型", font=self.FONT_UI).grid(row=row, column=0, **pad)
        tk.Entry(win, textvariable=ollama_model_var, font=self.FONT_UI).grid(row=row, column=1, **pad)
        row += 1

        deepseek_model_var = None
        if HAS_DEEPSEEK:
            deepseek_model_var = tk.StringVar(
                value=self.settings.get("deepseek_model", "deepseek-chat")
            )
            tk.Label(win, text="DeepSeek 模型", font=self.FONT_UI).grid(row=row, column=0, **pad)
            tk.Entry(win, textvariable=deepseek_model_var, font=self.FONT_UI).grid(
                row=row, column=1, **pad
            )
            row += 1

        tk.Label(win, text="系统提示（可选）", font=self.FONT_UI).grid(
            row=row, column=0, padx=16, pady=6, sticky="nw"
        )
        prompt_box = tk.Text(win, height=5, font=self.FONT_UI, wrap=tk.WORD)
        prompt_box.grid(row=row, column=1, padx=16, pady=6, sticky="nsew")
        if self.settings.get("system_prompt"):
            prompt_box.insert("1.0", self.settings["system_prompt"])
        win.rowconfigure(row, weight=1)
        row += 1

        if HAS_DEEPSEEK:
            tk.Label(
                win,
                text="DeepSeek Key：secrets.json 或 local-only/secrets.json",
                font=self.FONT_SMALL,
                fg=COLORS["muted"],
            ).grid(row=row, column=0, columnspan=2, pady=(0, 4))
            row += 1

        def apply() -> None:
            url = url_var.get().strip()
            ollama_m = ollama_model_var.get().strip()
            if not url or not ollama_m:
                messagebox.showerror("提示", "请填写 Ollama 配置。", parent=win)
                return
            if HAS_DEEPSEEK:
                ds_m = deepseek_model_var.get().strip()
                if not ds_m:
                    messagebox.showerror("提示", "请填写 DeepSeek 模型。", parent=win)
                    return
            prompt = prompt_box.get("1.0", tk.END).strip()
            self.settings["ollama_base_url"] = url
            self.settings["ollama_model"] = ollama_m
            if HAS_DEEPSEEK:
                self.settings["provider"] = provider_var.get()
                self.settings["deepseek_model"] = ds_m
                self.provider_var.set(self.settings["provider"])
            self.settings["system_prompt"] = prompt
            save_settings(self.settings)

            if HAS_DEEPSEEK:
                self.client = create_chat_client(self.settings)
            else:
                self.client.base_url = url.rstrip("/")
                self.client.model = ollama_m
            if prompt:
                self.client.reset_conversation()
            self.model_var.set(
                display_name(self._default_model_id(), self._aliases)
            )
            self.client.model = resolve_model_id(self.model_var.get(), self._aliases)
            win.destroy()
            self._refresh_connection()
            self._append_system("设置已保存。")

        ttk.Button(win, text="保存", command=apply).grid(
            row=row, column=0, columnspan=2, pady=16
        )

    def run(self) -> None:
        self.root.mainloop()
