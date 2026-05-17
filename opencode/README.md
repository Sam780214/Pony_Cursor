# Pony CLI（`pony` 命令）

与官方 OpenCode 的 `opencode` 区分，入口为 **`pony`**。数据库与备份默认在 `D:\Pony\local-only\opencode\`（可用环境变量覆盖）。

## 安装（推荐：双击 bat）

在资源管理器中双击（**GBK/ANSI，cmd 可直接运行**）：

| 文件 | 位置 |
|------|------|
| `install_pony.bat` | `D:\Pony\` 或克隆后的 `Pony_Cursor_repo\` |
| `git_log.bat` | 同上，查看最近一次 Git 提交 |

## 安装（手写 cmd）

**重要：** 在 cmd 里请**一行一条命令**；多条写在同一行时用 `&&` 连接，中间要有空格。

错误示例（不要这样）：

```text
cd /d D:\Pony\Pony_Cursor_repo\opencodepy -3 -m pip install -e .
```

正确示例：

```cmd
cd /d D:\Pony\Pony_Cursor_repo\opencode
```

```cmd
py -3 -m pip install -e .
```

或一行：

```cmd
cd /d D:\Pony\Pony_Cursor_repo\opencode && py -3 -m pip install -e .
```

可选交互依赖：

```cmd
py -3 -m pip install questionary
```

安装后**新开 cmd**，执行 `pony help`。若看不到 `pony git`，请重新运行 `install_pony.bat`。

## `pony git`（从 GitHub 同步仓库）

默认在 `D:\Pony` 下重建 `Pony_Cursor_repo`（会删除旧克隆；**不删** `local-only`）。

```cmd
set PONY_SOFTWARE=cmd
pony git -y
```

或双击 / 运行：

```cmd
D:\Pony\Pony_Cursor_repo\opencode\pony_git.cmd -y
```

查看参数：

```cmd
pony git --help
```

试验目录（不碰正式仓库）：

```cmd
pony git --root D:\Pony\_test -y
```

其它子命令见 `pony help`。
