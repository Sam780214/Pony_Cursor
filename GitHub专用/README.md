# Hi AI

与本机 [Ollama](https://ollama.com/) 对话的轻量聊天工具，支持**桌面版**（Tkinter）与 **Web 版**，回复为流式逐字显示。

> 本目录为 **GitHub 公开版**（仅 Ollama，不含 DeepSeek API）。完整版请使用主项目 `Hi AI` 目录。

## 功能

- 连接本机 Ollama（自动识别 `OLLAMA_HOST`）
- 模型显示名：`Hi AI.json` 或 `D:\Pony\Hi AI.json`（见 `Hi AI.json.example`）
- 左下角 **统计**：四张科技风图表（思考时间 / 回复字数 × 柱状 + 折线）
- Web：`http://127.0.0.1:8765`
- 当前版本：**V1.3**（界面右下角）

## 环境要求

- Python 3.10+
- Ollama 已运行（如 `ollama serve`）
- 已拉取模型，例如：`ollama pull gemma3:4b`

## 快速开始

**桌面版：**

```bat
python main.py
```

**Web 版：**

```bat
run_web.bat
```

浏览器打开 http://127.0.0.1:8765 ，**Ctrl+F5** 强制刷新。

## 配置

`settings.json`：

```json
{
  "ollama_model": "gemma3:4b",
  "ollama_base_url": "http://127.0.0.1:11434",
  "system_prompt": ""
}
```

模型别名示例见 `Hi AI.json.example`。

## 项目结构

```
├── main.py / ui.py          # 桌面
├── web_server.py            # Web
├── static/index.html        # 浏览器界面
├── stats_charts.py          # 统计窗口
├── model_aliases.py
├── edition.py               # 版本检测（本包仅 Ollama）
└── version.py               # V1.3
```

## 许可证

MIT
