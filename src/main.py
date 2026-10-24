"""Точка входа графического эмулятора UNIX."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import VFS_STAGE, parse_args
from src.scripts import read_script, run_script
from src.shell import Shell
from src.vfs import VFS, VFSError


def prepare(config):
    """Загрузить CSV и сценарий до запуска окна; ничего не записывать."""
    vfs = VFS.from_csv(config.vfs) if config.stage >= VFS_STAGE else VFS()
    lines = read_script(config.script) if config.script else []
    return Shell(vfs, config.stage), lines


def main(argv=None):
    """Запустить GUI либо выполнить сценарий для автоматической проверки."""
    config = parse_args(argv)
    try:
        shell, lines = prepare(config)
    except (OSError, UnicodeError, VFSError) as error:
        print(f"Ошибка запуска: {error}", file=sys.stderr)
        return 1
    if config.headless:
        for line in config.debug_lines():
            print(line)
        return 0 if run_script(shell, lines, print) else 1
    try:
        from src.gui import EmulatorWindow, tk

        root = tk.Tk()
        EmulatorWindow(root, shell, config, lines)
        root.mainloop()
    except (ImportError, RuntimeError) as error:
        print(f"Не удалось запустить GUI: {error}", file=sys.stderr)
        return 1
    except tk.TclError as error:
        print(f"Ошибка Tkinter: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
