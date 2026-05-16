import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

from . import git_cmd
from . import help_text
from . import list_cmd
from . import rollback_cmd
from . import rm_cmd


def main() -> None:
    raise SystemExit(_main_code())


def _main_code() -> int:
    argv = sys.argv[1:]

    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(help_text.HELP)
        return 0

    cmd = argv[0]
    rest = argv[1:]

    if cmd == 'git':
        return git_cmd.run(rest)
    if cmd == 'list':
        return list_cmd.run(rest)
    if cmd == 'rollback':
        return rollback_cmd.run(rest)
    if cmd == 'rm':
        return rm_cmd.run(rest)
    if cmd == 'game':
        import subprocess
        from pathlib import Path

        game_main = Path(__file__).resolve().parents[2] / "game" / "main.py"
        if not game_main.is_file():
            print(f"找不到游戏入口: {game_main}", file=sys.stderr)
            return 2
        return subprocess.run([sys.executable, str(game_main)]).returncode

    print(f'未知命令: {cmd}\n请运行 pony help', file=sys.stderr)
    return 2