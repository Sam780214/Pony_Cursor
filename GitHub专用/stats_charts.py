"""统计图：科技风柱状图 + 折线面积图（独立统计窗口）。"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field


@dataclass
class StatsTracker:
    thinking_times: list[float] = field(default_factory=list)
    word_counts: list[int] = field(default_factory=list)
    max_points: int = 24

    def add_turn(self, thinking_sec: float, word_count: int) -> None:
        self.thinking_times.append(max(0.0, thinking_sec))
        self.word_counts.append(max(0, word_count))
        if len(self.thinking_times) > self.max_points:
            self.thinking_times.pop(0)
            self.word_counts.pop(0)

    def clear(self) -> None:
        self.thinking_times.clear()
        self.word_counts.clear()


def _nice_max(values: list[float], floor: float) -> float:
    if not values:
        return floor
    return max(max(values) * 1.15, floor)


def _format_val(v: float, unit: str) -> str:
    if unit == "秒":
        return f"{v:.1f}" if v < 100 else f"{int(v)}"
    return str(int(v))


class TechChart(tk.Canvas):
    """科技风图表：bar=柱状图，line=折线面积图。"""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        unit: str,
        chart_type: str,
        font_fn=None,
        **kwargs,
    ):
        super().__init__(
            master,
            height=220,
            bg="#0c1e3d",
            highlightthickness=2,
            highlightbackground="#3b82f6",
            **kwargs,
        )
        self._title = title
        self._unit = unit
        self._chart_type = chart_type
        self._font_fn = font_fn or (
            lambda pt, bold=False: (
                ("Microsoft YaHei UI", pt, "bold")
                if bold
                else ("Microsoft YaHei UI", pt)
            )
        )
        self._values: list[float] = []
        self.bind("<Configure>", lambda _e: self._redraw())

    def set_data(self, values: list[float]) -> None:
        self._values = list(values)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 280)
        h = max(self.winfo_height(), 200)
        self.create_text(
            w // 2, 16, text=self._title, font=self._font_fn(13, bold=True), fill="#e0f2fe"
        )
        values = self._values
        if not values:
            self.create_text(
                w // 2, h // 2, text="暂无数据", font=self._font_fn(12), fill="#64748b"
            )
            self.create_text(
                w // 2, h // 2 + 18, text="发送消息后将记录各轮", font=self._font_fn(11), fill="#475569"
            )
            return

        pad_l, pad_r, pad_t, pad_b = 44, 16, 36, 40
        cw = w - pad_l - pad_r
        ch = h - pad_t - pad_b
        floor = 2.0 if self._unit == "秒" else 40.0
        vmax = _nice_max(values, floor)
        n = len(values)
        baseline = pad_t + ch

        for i in range(5):
            frac = i / 4
            y = pad_t + ch * (1 - frac)
            val = vmax * frac
            self.create_line(pad_l, y, pad_l + cw, y, fill="#1e3a5f")
            self.create_text(
                pad_l - 6, y, text=_format_val(val, self._unit), anchor="e",
                font=self._font_fn(10), fill="#64748b",
            )

        if self._chart_type == "bar":
            self._draw_bars(values, pad_l, pad_t, cw, ch, baseline, vmax, n)
        else:
            self._draw_line_area(values, pad_l, pad_t, cw, ch, baseline, vmax, n)

        self.create_text(
            w // 2, h - 8, text=self._unit, font=self._font_fn(11), fill="#94a3b8"
        )

    def _draw_bars(
        self,
        values: list[float],
        pad_l: int,
        pad_t: int,
        cw: int,
        ch: int,
        baseline: int,
        vmax: float,
        n: int,
    ) -> None:
        bar_w = min(36, max(10, cw // max(n * 2, 2)))
        gap = max(4, (cw - bar_w * n) // max(n + 1, 1))
        for i, v in enumerate(values):
            x0 = pad_l + gap + i * (bar_w + gap)
            x1 = x0 + bar_w
            bh = min(ch, (v / vmax) * ch)
            y0 = baseline - bh
            self.create_rectangle(
                x0, y0, x1, baseline, fill="#2563eb", outline="#60a5fa", width=1
            )
            cx = (x0 + x1) / 2
            self.create_text(
                cx, y0 - 8, text=_format_val(v, self._unit),
                font=self._font_fn(11, bold=True), fill="#ffffff",
            )
            self.create_text(
                cx, baseline + 12, text=f"第{i + 1}轮",
                font=self._font_fn(10), fill="#94a3b8",
            )

    def _draw_line_area(
        self,
        values: list[float],
        pad_l: int,
        pad_t: int,
        cw: int,
        ch: int,
        baseline: int,
        vmax: float,
        n: int,
    ) -> None:
        if n == 1:
            xs = [pad_l + cw / 2]
        else:
            xs = [pad_l + (cw * i / (n - 1)) for i in range(n)]
        pts: list[tuple[float, float]] = []
        for i, v in enumerate(values):
            bh = min(ch, (v / vmax) * ch)
            pts.append((xs[i], baseline - bh))

        if len(pts) >= 2:
            area = [(pts[0][0], baseline)] + pts + [(pts[-1][0], baseline)]
            flat = [c for p in area for c in p]
            self.create_polygon(*flat, fill="#1d4ed8", outline="")

        if len(pts) >= 2:
            flat = [c for p in pts for c in p]
            self.create_line(*flat, fill="#60a5fa", width=3, smooth=True)

        for i, (cx, cy) in enumerate(pts):
            v = values[i]
            self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#ffffff", outline="#3b82f6", width=2)
            self.create_text(
                cx, cy - 12, text=_format_val(v, self._unit),
                font=self._font_fn(11, bold=True), fill="#e0f2fe",
            )
            self.create_text(
                cx, baseline + 12, text=f"第{i + 1}轮",
                font=self._font_fn(10), fill="#94a3b8",
            )


class StatsWindow:
    """独立统计界面（四张图）。"""

    def __init__(self, parent: tk.Tk, tracker: StatsTracker, font_fn=None) -> None:
        self._tracker = tracker
        self._win: tk.Toplevel | None = None
        self._charts: dict[str, TechChart] = {}
        self._parent = parent
        self._font_fn = font_fn

    def is_open(self) -> bool:
        return self._win is not None and self._win.winfo_exists()

    def open(self) -> None:
        if self.is_open():
            self._win.lift()
            self.refresh()
            return

        win = tk.Toplevel(self._parent)
        win.title("Hi AI · 统计")
        win.geometry("1000x680")
        win.minsize(880, 560)
        win.configure(bg="#060d1f")
        self._win = win

        tk.Label(
            win,
            text="对话统计",
            font=self._font_fn(18, bold=True) if self._font_fn else ("Microsoft YaHei UI", 18, "bold"),
            fg="#e0f2fe",
            bg="#060d1f",
        ).pack(pady=(12, 4))

        tk.Label(
            win,
            text="左：思考时间（秒）　右：回复字数（字）　上：柱状　下：折线趋势",
            font=self._font_fn(12) if self._font_fn else ("Microsoft YaHei UI", 12),
            fg="#64748b",
            bg="#060d1f",
        ).pack(pady=(0, 10))

        grid = tk.Frame(win, bg="#060d1f", padx=12, pady=4)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

        specs = [
            ("think_bar", "思考时间 · 柱状图", "秒", "bar", 0, 0),
            ("words_bar", "回复字数 · 柱状图", "字", "bar", 0, 1),
            ("think_line", "思考时间 · 折线图", "秒", "line", 1, 0),
            ("words_line", "回复字数 · 折线图", "字", "line", 1, 1),
        ]
        for key, title, unit, ctype, row, col in specs:
            cell = tk.Frame(grid, bg="#060d1f", padx=6, pady=6)
            cell.grid(row=row, column=col, sticky="nsew")
            chart = TechChart(cell, title, unit, ctype, font_fn=self._font_fn)
            chart.pack(fill=tk.BOTH, expand=True)
            self._charts[key] = chart

        btn_row = tk.Frame(win, bg="#060d1f", pady=10)
        btn_row.pack(fill=tk.X)
        tk.Button(
            btn_row,
            text="刷新",
            font=self._font_fn(13) if self._font_fn else ("Microsoft YaHei UI", 13),
            command=self.refresh,
            bg="#1e40af",
            fg="white",
            relief=tk.FLAT,
            padx=16,
            pady=4,
        ).pack(side=tk.LEFT, padx=12)
        tk.Button(
            btn_row,
            text="关闭",
            font=self._font_fn(13) if self._font_fn else ("Microsoft YaHei UI", 13),
            command=win.destroy,
            bg="#334155",
            fg="white",
            relief=tk.FLAT,
            padx=16,
            pady=4,
        ).pack(side=tk.RIGHT, padx=12)

        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self.refresh()

    def refresh(self) -> None:
        if not self.is_open():
            return
        t = [float(x) for x in self._tracker.thinking_times]
        w = [float(x) for x in self._tracker.word_counts]
        self._charts["think_bar"].set_data(t)
        self._charts["words_bar"].set_data(w)
        self._charts["think_line"].set_data(t)
        self._charts["words_line"].set_data(w)
