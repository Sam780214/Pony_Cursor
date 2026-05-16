"""单字段最高分存档。"""
from __future__ import annotations

import json
from dataclasses import dataclass

from constants import SAVE_PATH


@dataclass
class SaveData:
    best_score: int = 0


class SaveManager:
    def __init__(self) -> None:
        self.data = SaveData()
        self._load()

    def _load(self) -> None:
        try:
            raw = SAVE_PATH.read_text(encoding="utf-8")
            obj = json.loads(raw)
            self.data.best_score = int(obj.get("best_score", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.data = SaveData()

    def flush(self) -> None:
        try:
            SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            SAVE_PATH.write_text(
                json.dumps({"best_score": self.data.best_score}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def maybe_update_best(self, score: int) -> None:
        if score > self.data.best_score:
            self.data.best_score = score
