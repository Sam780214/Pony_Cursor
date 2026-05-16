# local-only

本目录存放**不推送到 GitHub** 的本地文件（构建产物、缓存、存档等）。

与仓库源码目录对应：

| 路径 | 内容 |
|------|------|
| `desktop-pet/build/` | PyInstaller 中间文件 |
| `desktop-pet/dist/` | 打包后的 `DesktopPet` 可执行目录 |
| `opencode/opencode_cli.egg-info/` | pip 安装元数据 |
| `game/dodge_save.json` | 游戏最高分存档 |
| 各处的 `__pycache__/` | Python 字节码缓存 |

克隆后请在本机创建子目录，或将 `D:\Pony\local-only` 中的内容复制到此处。

重新打包桌面宠物：运行 `desktop-pet\快速更新.bat`，输出写入 `local-only/desktop-pet/`。
