"""Ollama HTTP API 客户端：模型列表、对话（流式/非流式）。"""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Callable


def resolve_ollama_base_url(configured: str | None = None) -> str:
    """优先使用环境变量 OLLAMA_HOST（如 127.0.0.1:11623），否则用配置或默认 11434。"""
    host = os.environ.get("OLLAMA_HOST", "").strip()
    if host:
        if not host.startswith("http"):
            host = f"http://{host}"
        return host.rstrip("/")
    return (configured or "http://localhost:11434").rstrip("/")


class OllamaClient:
    def __init__(
        self,
        model: str = "gemma3:4b",
        base_url: str = "http://localhost:11434",
        system_prompt: str | None = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.system_prompt = system_prompt or (
            "你是 Hi AI，一个友好、专业的本地 AI 助手。"
            "请用清晰、准确的中文回答用户问题。"
        )
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self._request_lock = threading.Lock()

    def reset_conversation(self) -> None:
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def ping(self) -> tuple[bool, str]:
        """检查 Ollama 服务是否可达。"""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "已连接"
        except urllib.error.URLError as e:
            return False, f"无法连接：{e.reason}"
        except Exception as e:
            return False, str(e)
        return False, "未知错误"

    def list_models(self) -> list[str]:
        """获取本机已安装的模型名称列表。"""
        req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names: list[str] = []
        for item in data.get("models", []):
            name = item.get("name")
            if name:
                names.append(name)
        return sorted(names)

    def chat(
        self,
        message: str,
        *,
        on_token: Callable[[str], None] | None = None,
        on_done: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        stream: bool = True,
        history_limit: int = 20,
    ) -> None:
        """在后台线程发送消息；流式时 on_token 逐段回调，结束时 on_done 传入完整回复。"""
        self.messages.append({"role": "user", "content": message})

        def worker() -> None:
            try:
                if stream and on_token:
                    full = self._chat_stream(on_token, history_limit)
                else:
                    full = self._chat_once(history_limit)
                    if on_token:
                        on_token(full)
                self.messages.append({"role": "assistant", "content": full})
                if on_done:
                    on_done(full)
            except Exception as e:
                self.messages.pop()
                if on_error:
                    on_error(str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _payload(self, history_limit: int, stream: bool) -> dict:
        msgs = self.messages
        if history_limit > 0:
            system = msgs[:1]
            rest = msgs[1:][-history_limit:]
            msgs = system + rest
        return {
            "model": self.model,
            "messages": msgs,
            "stream": stream,
        }

    def _chat_once(self, history_limit: int) -> str:
        payload = self._payload(history_limit, stream=False)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result.get("message", {}).get("content", "")

    def _iter_chat_tokens(self, history_limit: int) -> Iterator[str]:
        payload = self._payload(history_limit, stream=True)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break

    def stream_reply(self, message: str, history_limit: int = 20) -> Iterator[str]:
        """同步流式生成；yield 每个 token，并更新对话历史（串行，避免并发请求互相干扰）。"""
        with self._request_lock:
            self.messages.append({"role": "user", "content": message})
            parts: list[str] = []
            try:
                for token in self._iter_chat_tokens(history_limit):
                    parts.append(token)
                    yield token
                self.messages.append(
                    {"role": "assistant", "content": "".join(parts)}
                )
            except Exception:
                if self.messages and self.messages[-1].get("role") == "user":
                    self.messages.pop()
                raise

    def _chat_stream(
        self, on_token: Callable[[str], None], history_limit: int
    ) -> str:
        parts: list[str] = []
        for token in self._iter_chat_tokens(history_limit):
            parts.append(token)
            on_token(token)
        return "".join(parts)
