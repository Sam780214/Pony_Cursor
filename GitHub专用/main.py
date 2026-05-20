"""Hi AI — 自动选择 Ollama 版或完整版（含 DeepSeek）。"""
from dpi import enable_high_dpi
from edition import edition_label, use_deepseek_edition
from ui import HiAIApp


def main() -> None:
    enable_high_dpi()
    use_deepseek_edition()
    print(f"启动 {edition_label()}…")
    HiAIApp().run()


if __name__ == "__main__":
    main()
