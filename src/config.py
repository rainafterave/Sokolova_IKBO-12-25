"""Параметры запуска приложения."""

import argparse
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FINAL_STAGE = 4
VFS_STAGE = 3


@dataclass(frozen=True)
class Config:
    """Итоговые настройки одного запуска."""

    vfs: Path
    script: Path | None = None
    stage: int = FINAL_STAGE
    headless: bool = False

    def debug_lines(self):
        """Показать все настройки, в том числе значения по умолчанию."""
        return [
            f"[config] vfs = {self.vfs}",
            f"[config] script = {self.script or 'не задан'}",
            f"[config] stage = {self.stage}",
            f"[config] headless = {self.headless}",
        ]


def parse_args(argv=None):
    """Прочитать пути CSV и сценария, режим этапа и режим проверки."""
    parser = argparse.ArgumentParser(
        description="Графический эмулятор UNIX: вариант 23, этапы 1-4."
    )
    parser.add_argument(
        "--vfs", type=Path,
        default=PROJECT_ROOT / "vfs-samples" / "deep.csv",
        help="путь к CSV с виртуальной файловой системой",
    )
    parser.add_argument(
        "--script", type=Path, help="путь к стартовому скрипту UTF-8"
    )
    parser.add_argument(
        "--stage", type=int, choices=range(1, FINAL_STAGE + 1),
        default=FINAL_STAGE, help="этап демонстрации (по умолчанию 4)",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="выполнить скрипт без окна для автоматической проверки",
    )
    args = parser.parse_args(argv)
    if args.headless and args.script is None:
        parser.error("--headless требует --script")
    return Config(
        args.vfs.resolve(),
        args.script.resolve() if args.script else None,
        args.stage, args.headless,
    )
