# local-only

本目录存放**不推送到 GitHub** 的本地文件：构建产物、`__pycache__`、用户设置与存档等。

| 路径 | 内容 |
|------|------|
| `desktop-pet/build/`、`dist/` | PyInstaller 构建输出 |
| `desktop-pet/pet_settings.json` | 桌面宠物用户设置 |
| `desktop-pet/software_modes.txt` | 软件模式配置（运行时可改） |
| `desktop-pet/__pycache__/` | Python 缓存 |
| `opencode/data/` | OpenCode 数据库（`opencode.db`） |
| `opencode/backups/` | 备份 |
| `opencode/__pycache__/` | Python 缓存 |
| `game/dodge_save.json` | 游戏最高分存档 |
| `game/__pycache__/` | Python 缓存 |

代码通过仓库根目录的 `pony_local.py` 自动解析 `local-only/` 路径。

**Canonical 路径**：当 `D:\Pony\local-only` 存在时，所有缓存/存档/构建输出写入该目录（而非克隆仓库内的 `local-only/`）。可通过环境变量 `PONY_LOCAL_ONLY_ROOT` 覆盖。

重新打包桌面宠物：在 `desktop-pet` 下运行 `快速更新.bat`。
