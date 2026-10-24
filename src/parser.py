"""Разбор команд с одинарными и двойными кавычками."""

import shlex


def parse(line):
    """Вернуть команду и аргументы; не исполнять команды реальной ОС."""
    tokens = shlex.split(line, comments=False, posix=True)
    return (tokens[0], tokens[1:]) if tokens else (None, [])
