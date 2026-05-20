"""Hi AI Web 服务 — 自动检测 Ollama 版或完整版（含 DeepSeek）。"""
from __future__ import annotations

import json
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from edition import edition_label, use_deepseek_edition
from version import APP_VERSION
from model_aliases import display_name, load_model_aliases, resolve_model_id
from ollama_client import OllamaClient, resolve_ollama_base_url

HAS_DEEPSEEK = use_deepseek_edition()
if HAS_DEEPSEEK:
    from config import PROVIDERS, create_chat_client, client_signature
    from config import load_settings as _load_settings
    from config import save_settings as _save_settings

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
SETTINGS_PATH = APP_DIR / "settings.json"
HOST = "127.0.0.1"
PORT = 8765

_client_lock = threading.Lock()
_client: OllamaClient | object | None = None
_client_sig: tuple | None = None


def _load_settings_ollama_only() -> dict:
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


def load_app_settings() -> dict:
    if HAS_DEEPSEEK:
        return _load_settings()
    return _load_settings_ollama_only()


def save_app_settings(data: dict) -> None:
    if HAS_DEEPSEEK:
        _save_settings(data)
        return
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_client():
    global _client, _client_sig
    with _client_lock:
        settings = load_app_settings()
        sig = client_signature(settings) if HAS_DEEPSEEK else (
            settings.get("ollama_model"),
            settings.get("ollama_base_url"),
            settings.get("system_prompt"),
        )
        if _client is None or _client_sig != sig:
            prompt = settings.get("system_prompt") or None
            if HAS_DEEPSEEK:
                _client = create_chat_client(settings)
            else:
                _client = OllamaClient(
                    model=settings["ollama_model"],
                    base_url=settings["ollama_base_url"],
                    system_prompt=prompt,
                )
            _client_sig = sig
        return _client


def reset_client() -> None:
    global _client, _client_sig
    with _client_lock:
        _client = None
        _client_sig = None


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

    def _serve_index_html(self) -> bytes:
        path = STATIC_DIR / "index.html"
        html = path.read_text(encoding="utf-8")
        aliases = load_model_aliases()
        settings = load_app_settings()
        edition = {
            "has_deepseek": HAS_DEEPSEEK,
            "label": edition_label(),
            "provider": settings.get("provider", "ollama") if HAS_DEEPSEEK else "ollama",
            "providers": PROVIDERS if HAS_DEEPSEEK else {},
        }
        inject = (
            "<script>"
            f"window.HI_AI_ALIASES={json.dumps(aliases, ensure_ascii=False)};"
            f"window.HI_AI_EDITION={json.dumps(edition, ensure_ascii=False)};"
            f"window.HI_AI_VERSION={json.dumps(APP_VERSION)};"
            "</script>\n"
        )
        if "</head>" in html:
            html = html.replace("</head>", inject + "</head>", 1)
        else:
            html = inject + html
        return html.encode("utf-8")

    def _serve_static_file(self, rel: str) -> bool:
        safe = Path(rel).name if "/" not in rel.strip("/") else Path(rel.lstrip("/")).name
        path = STATIC_DIR / safe
        if not path.is_file() or path.resolve().parent != STATIC_DIR.resolve():
            return False
        mime = "application/javascript" if path.suffix == ".js" else "text/plain"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return True

    def do_GET(self) -> None:
        if self.path.startswith("/static/"):
            rel = self.path[len("/static/") :]
            if self._serve_static_file(rel):
                return
            self.send_error(404)
            return
        if self.path in ("/", "/index.html"):
            html = self._serve_index_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/api/edition":
            settings = load_app_settings()
            payload = {
                "has_deepseek": HAS_DEEPSEEK,
                "label": edition_label(),
                "provider": settings.get("provider", "ollama") if HAS_DEEPSEEK else "ollama",
            }
            if HAS_DEEPSEEK:
                payload["providers"] = PROVIDERS
            self._json(200, payload)
            return
        if self.path == "/api/health":
            ok, msg = get_client().ping()
            self._json(200, {"ok": ok, "message": msg})
            return
        if self.path == "/api/aliases":
            self._json(200, {"aliases": load_model_aliases()})
            return
        if self.path == "/api/reload-aliases":
            self._json(200, {"aliases": load_model_aliases()})
            return
        if self.path == "/api/models":
            client = get_client()
            aliases = load_model_aliases()
            try:
                ids = client.list_models()
                items = [{"id": m, "label": display_name(m, aliases)} for m in ids]
                self._json(
                    200,
                    {
                        "models": items,
                        "current": client.model,
                        "current_label": display_name(client.model, aliases),
                    },
                )
            except Exception as e:
                self._json(503, {"models": [], "error": str(e)})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/provider" and HAS_DEEPSEEK:
            data = self._read_json()
            provider = (data.get("provider") or "").strip()
            if provider not in PROVIDERS:
                self._json(400, {"error": "无效来源"})
                return
            settings = load_app_settings()
            settings["provider"] = provider
            save_app_settings(settings)
            reset_client()
            self._json(200, {"ok": True, "provider": provider})
            return
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
                client.model = resolve_model_id(model, load_model_aliases())
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

    def _chat_sse(self, client, message: str) -> None:
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        t0 = time.time()
        first_token: float | None = None
        chars = 0
        try:
            for token in client.stream_reply(message):
                if first_token is None:
                    first_token = time.time()
                chars += len(token)
                self._sse_event({"token": token})
        except Exception as e:
            self._sse_event({"error": str(e)})
        finally:
            thinking = (first_token or time.time()) - t0
            self._sse_event(
                {"done": True, "thinking_sec": round(thinking, 2), "word_count": chars}
            )


def main() -> None:
    if not STATIC_DIR.joinpath("index.html").is_file():
        raise SystemExit(f"缺少静态页面: {STATIC_DIR / 'index.html'}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Hi AI Web ({edition_label()}): http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
