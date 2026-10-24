"""Состояние оболочки и команды варианта 23."""

import getpass
import socket
import time
from datetime import datetime, timezone

from .config import FINAL_STAGE, VFS_STAGE
from .parser import parse
from .vfs import VFS, VFSError

MAX_SINGLE_ARG = 1
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24


class CommandError(ValueError):
    """Пользовательская ошибка команды."""


class Shell:
    """Исполнять только встроенные команды, не обращаясь к оболочке ОС."""

    def __init__(self, vfs=None, stage=FINAL_STAGE):
        """Запомнить реальные имя пользователя, имя компьютера и время."""
        self.vfs = vfs if vfs is not None else VFS()
        self.stage = stage
        self.cwd = "/"
        self.running = True
        self.history = []
        self.username = getpass.getuser()
        self.hostname = socket.gethostname()
        self.started = time.monotonic()
        self.commands = {"ls": self.cmd_ls, "cd": self.cmd_cd,
                         "exit": self.cmd_exit}
        if stage == FINAL_STAGE:
            self.commands.update(uptime=self.cmd_uptime,
                                 history=self.cmd_history, date=self.cmd_date)

    @property
    def title(self):
        """Заголовок GUI на основе данных настоящей ОС."""
        return f"Эмулятор - [{self.username}@{self.hostname}]"

    @property
    def prompt(self):
        """Приглашение с текущим виртуальным каталогом."""
        return f"{self.username}@{self.hostname}:{self.cwd}$ "

    def execute(self, line):
        """Вернуть (успех, вывод); сохранить непустой ввод в истории."""
        if not line.strip():
            return True, ""
        self.history.append(line)
        try:
            command, args = parse(line)
            if command not in self.commands:
                raise CommandError(f"{command}: команда не найдена")
            return True, self.commands[command](args)
        except (ValueError, VFSError) as error:
            return False, str(error)

    @staticmethod
    def _one_arg(command, args):
        """Ограничить команды с одним необязательным аргументом."""
        if len(args) > MAX_SINGLE_ARG:
            raise CommandError(f"{command}: слишком много аргументов")

    @staticmethod
    def _no_args(command, args):
        """Проверить отсутствие аргументов."""
        if args:
            raise CommandError(f"{command}: аргументы не поддерживаются")

    def cmd_ls(self, args):
        """Показать каталог или файл; поддержать -a, -l и --."""
        if self.stage < VFS_STAGE:
            return f"ls {args!r}"
        flags, paths = self._ls_options(args)
        paths = paths or ["."]
        blocks = []
        for path in paths:
            resolved = self.vfs.resolve(path, self.cwd)
            block = self._listing(resolved, flags)
            if len(paths) > MAX_SINGLE_ARG:
                block = path + ":\n" + block
            blocks.append(block)
        return "\n\n".join(blocks)

    @staticmethod
    def _ls_options(args):
        """Разобрать сочетания -a/-l, пути и конец опций --."""
        flags, paths = set(), []
        options = True
        for arg in args:
            if options and arg == "--":
                options = False
            elif options and arg.startswith("-") and arg != "-":
                if not set(arg[1:]) <= {"a", "l"}:
                    raise CommandError(f"ls: неизвестная опция: {arg}")
                flags.update(arg[1:])
            else:
                paths.append(arg)
        return flags, paths

    def _listing(self, path, flags):
        """Сформировать компактный или подробный список узлов."""
        node = self.vfs.nodes[path]
        if node.kind == "file":
            return self._entry(path, path.rsplit("/", 1)[-1], flags)
        names = self.vfs.children(path)
        if "a" not in flags:
            names = [name for name in names if not name.startswith(".")]
        lines = [self._entry(path.rstrip("/") + "/" + name, name, flags)
                 for name in names]
        return ("\n" if "l" in flags else "  ").join(lines)

    def _entry(self, path, name, flags):
        """Показать имя, а для -l также тип и число байтов данных."""
        node = self.vfs.nodes[path]
        label = name + ("/" if node.kind == "dir" else "")
        if "l" in flags:
            return f"{node.kind:4} {len(node.data):6} {label}"
        return label

    def cmd_cd(self, args):
        """Перейти в каталог VFS; без аргумента перейти в корень."""
        self._one_arg("cd", args)
        if self.stage < VFS_STAGE:
            return f"cd {args!r}"
        if args and args[0].startswith("-"):
            raise CommandError("cd: опции не поддерживаются")
        path = self.vfs.resolve(args[0] if args else "/", self.cwd)
        if self.vfs.nodes[path].kind != "dir":
            raise CommandError(f"cd: не является каталогом: {path}")
        self.cwd = path
        return ""

    def cmd_uptime(self, args):
        """Показать время работы текущего экземпляра эмулятора."""
        self._no_args("uptime", args)
        minutes, seconds = divmod(
            int(time.monotonic() - self.started), SECONDS_PER_MINUTE
        )
        hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
        days, hours = divmod(hours, HOURS_PER_DAY)
        return f"up {days} days, {hours:02}:{minutes:02}:{seconds:02}"

    def cmd_history(self, args):
        """Показать историю с нумерацией или последние N команд."""
        self._one_arg("history", args)
        if args and (not args[0].isascii() or not args[0].isdigit()):
            raise CommandError("history: ожидается неотрицательное число")
        count = int(args[0]) if args else len(self.history)
        start = max(0, len(self.history) - count)
        return "\n".join(f"{i + 1:5}  {self.history[i]}"
                         for i in range(start, len(self.history)))

    def cmd_date(self, args):
        """Показать реальное время ОС, опционально UTC и +FORMAT."""
        utc = bool(args and args[0] == "-u")
        formats = args[1:] if utc else args
        self._one_arg("date", formats)
        if formats and not formats[0].startswith("+"):
            raise CommandError("date: ожидается [-u] [+FORMAT]")
        pattern = formats[0][1:] if formats else "%Y-%m-%d %H:%M:%S %Z"
        now = datetime.now(timezone.utc) if utc else datetime.now().astimezone()
        return now.strftime(pattern)

    def cmd_exit(self, args):
        """Завершить работу при отсутствии аргументов."""
        self._no_args("exit", args)
        self.running = False
        return "Завершение работы."
