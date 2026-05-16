# Pony_Cursor

给 Cursor 的代码。

仓库根目录的 **`pony_local.py`** 负责把各项目的缓存、存档与构建输出解析到 `local-only/`。

## 目录

| 目录 | 说明 |
|------|------|
| `desktop-pet/` | 桌面宠物（Python + PyInstaller） |
| `opencode/` | OpenCode CLI 相关 |
| `game/` | Python 小游戏 |

## 本地专用目录

未上传的构建产物、缓存与存档统一放在 **`local-only/`**（仅 `README.md` 进 Git，其余被 `.gitignore` 忽略）。详见 [local-only/README.md](local-only/README.md)。

## 本地运行

```bash
# 桌面宠物
cd desktop-pet
pip install -r requirements.txt
python pet.py

# 游戏
cd game
pip install -r requirements.txt
python main.py

# OpenCode CLI（需在仓库根或子目录，以便找到 pony_local.py）
cd opencode
pip install -e .
opencode list
```
