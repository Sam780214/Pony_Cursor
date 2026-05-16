"""新游戏常量（星屑回避）。"""
from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


SCREEN_W = 1280
SCREEN_H = 800
FPS = 60

TITLE = "Pony · 星屑回避"

SAVE_FILENAME = "dodge_save.json"
SAVE_PATH = app_base_dir() / SAVE_FILENAME

COLOR_BG = (12, 14, 28)
COLOR_STAR_FIELD = (40, 48, 72)
COLOR_PLAYER = (255, 180, 100)
COLOR_HAZARD = (200, 80, 120)
COLOR_HAZARD_CORE = (255, 220, 240)
COLOR_TEXT = (235, 238, 250)
COLOR_ACCENT = (120, 220, 255)
COLOR_BUTTON = (55, 65, 95)
COLOR_BUTTON_HOVER = (80, 95, 130)

PLAYER_W = 52
PLAYER_H = 28
PLAYER_SPEED = 420.0
PLAYER_MARGIN_BOTTOM = 100

# 隐藏关「元素余晖」进入分数（两档，每局各可进一次）
HIDDEN_GATE_STANDARD = 2000
HIDDEN_GATE_TWILIGHT = 10000
# 兼容旧名
HIDDEN_GATE_SCORE = HIDDEN_GATE_TWILIGHT
