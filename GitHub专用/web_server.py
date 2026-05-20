"""Hi AI Web 服务 — 本机 Ollama 对话。"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ollama_client import OllamaClient, resolve_ollama_base_url

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
SETTINGS_PATH = APP_DIR / "settings.json"
HOST = "127.0.0.1"
PORT = 8765

_client_lock = threading.Lock()
_client: OllamaClient | None = None


def _load_settings() -> dict:
    defaults = {
        "ollama_model": "gemma3:4b",
        "ollama_base_url": "http://localhost:11434",
        "system_prompt": "",
    }
    if SETTINGS_PATH.is_file():
        with SETTINGS_PATH.open(encoding="utf-8") as f:
            defaults.update(json.load(f))
    defaults["ollama_base_url"] = resolve_ollama_base_url(defaults.get("ollama_base_url"))
    return defaults


def get_client() -> OllamaClient:
    global _client
    with _client_lock:
        if _client is None:
            s = _load_settings()
            prompt = s.get("system_prompt") or None
            _client = OllamaClient(
                model=s["ollama_model"],
                base_url=s["ollama_base_url"],
                system_prompt=prompt,
            )
        return _client


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            html = (STATIC_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/api/health":
            ok, msg = get_client().ping()
            self._json(200, {"ok": ok, "message": msg})
            return
        if self.path == "/api/models":
            client = get_client()
            try:
                models = client.list_models()
                self._json(200, {"models": models, "current": client.model})
            except Exception as e:
                self._json(503, {"models": [], "current": client.model, "error": str(e)})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/clear":
            get_client().reset_conversation()
            self._json(200, {"ok": True})
            return
        if self.path in ("/api/chat", "/api/chat/stream"):
            data = self._read_json()
            message = (data.get("message") or "").strip()
            if not message:
                self._json(400, {"error": "消息不能为空"})
                return
            client = get_client()
            model = (data.get("model") or "").strip()
            if model:
                client.model = model
            if self.path == "/api/chat/stream":
                self._chat_sse(client, message)
                return
            result: dict = {}
            done = threading.Event()

            def on_done(reply: str) -> None:
                result["reply"] = reply
                done.set()

            def on_error(err: str) -> None:
                result["error"] = err
                done.set()

            client.chat(
                message,
                stream=False,
                on_done=on_done,
                on_error=on_error,
            )
            done.wait(timeout=180)
            if result.get("error"):
                self._json(502, {"error": result["error"]})
            elif "reply" in result:
                self._json(200, {"reply": result["reply"]})
            else:
                self._json(504, {"error": "请求超时"})
            return
        self.send_error(404)

    def _sse_event(self, payload: dict) -> None:
        line = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        self.wfile.write(line.encode("utf-8"))
        self.wfile.flush()

    def _chat_sse(self, client: OllamaClient, message: str) -> None:
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for token in client.stream_reply(message):
                self._sse_event({"token": token})
        except Exception as e:
            self._sse_event({"error": str(e)})
        finally:
            self._sse_event({"done": True})


def main() -> None:
    if not STATIC_DIR.joinpath("index.html").is_file():
        raise SystemExit(f"缺少静态页面: {STATIC_DIR / 'index.html'}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Hi AI Web: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
