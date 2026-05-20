"""Windows 高 DPI 清晰显示（须在创建 Tk 窗口之前调用）。"""
from __future__ import annotations

import sys


def enable_high_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        # 2 = Per-Monitor V2，避免 125%/150% 缩放下界面发糊
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def apply_tk_scaling(root) -> float:
    """按系统 DPI 调整 Tk 缩放，返回比例（1.0 = 96 DPI）。"""
    try:
        dpi = float(root.winfo_fpixels("1i"))
        scale = max(1.0, dpi / 96.0)
        root.tk.call("tk", "scaling", scale)
        return scale
    except Exception:
        return 1.0
