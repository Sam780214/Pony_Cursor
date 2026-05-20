# Hi AI

与本机 [Ollama](https://ollama.com/) 对话的轻量聊天工具，支持桌面版（Tkinter）与 Web 版，回复为**流式逐字显示**。

## 功能

- 连接本机 Ollama API（自动识别 `OLLAMA_HOST` 环境变量）
- 模型列表、对话历史、系统提示词
- Web：`http://127.0.0.1:8765`

## 环境要求

- Python 3.10+
- 已安装并运行 Ollama（例如 `ollama serve`）
- 已拉取模型，例如：`ollama pull gemma3:4b`

## 快速开始

```bat
cd "Hi AI"
python main.py
```

Web 版：

```bat
python web_server.py
```

或双击 `run.bat` / `run_web.bat`。

## 配置

编辑 `settings.json`：

```json
{
  "ollama_model": "gemma3:4b",
  "ollama_base_url": "http://127.0.0.1:11434",
  "system_prompt": ""
}
```

若设置了 `OLLAMA_HOST`（如 `127.0.0.1:11623`），将优先使用该地址。

## 项目结构

```
Hi AI/
  main.py           # 桌面入口
  ui.py             # Tkinter 界面
  web_server.py     # Web 服务
  ollama_client.py  # Ollama API
  static/index.html # Web 页面
  settings.json     # 配置
```

## 许可证

MIT（可按需修改）
