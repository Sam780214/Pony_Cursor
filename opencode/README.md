# Pony CLI（`pony` 命令）

与官方 OpenCode 的 `opencode` 区分，入口为 **`pony`**。数据库与备份默认在 `D:\Pony\local-only\opencode\`（可用环境变量覆盖）。

## 安装（cmd）

```cmd
cd /d D:\Pony\Pony_Cursor_repo\opencode
py -3 -m pip install -e .
py -3 -m pip install questionary
```

安装后在新开的 **cmd** 里应能运行 `pony help`。若提示未知命令 `git`，说明仍是旧版，请重新执行上面的 `pip install -e .`。

## `pony git`（从 GitHub 同步仓库）

在 **Pony 根目录**（默认 `D:\Pony`）下删除并浅克隆 `Pony_Cursor_repo`：

```cmd
:: 跳过交互（推荐在 cmd 里用）
set PONY_SOFTWARE=cmd
pony git -y

:: 仅查看参数
pony git --help

:: 同步到其它目录（试验用，不碰正式仓库）
pony git --root D:\Pony\_test -y
```

**注意：** 不带 `--root` 时会整棵删除 `D:\Pony\Pony_Cursor_repo` 再重新克隆。`local-only` 不会被删。

其它子命令见 `pony help`。
