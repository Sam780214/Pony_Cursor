# Pony CLI（`pony` 命令）

与官方 OpenCode 的 `opencode` 区分，入口为 **`pony`**。读写 `%USERPROFILE%\.local\share\opencode\opencode.db`（或通过环境变量覆盖）中的会话数据。

安装：

```powershell
cd D:\Pony\opencode
pip install -e .
pip install questionary   # 可选，交互多选时需要
```

详见 `pony help`。
