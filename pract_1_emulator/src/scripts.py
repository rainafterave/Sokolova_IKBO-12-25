"""Выполнение стартового сценария с остановкой при первой ошибке."""

from pathlib import Path


def read_script(path):
    """Прочитать сценарий UTF-8; сохранить реальные номера строк."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    return [(number, line.strip())
            for number, line in enumerate(lines, start=1)
            if line.strip() and not line.lstrip().startswith("#")]


def run_script(shell, lines, emit):
    """Вывести ввод и результат каждой команды, вернуть успех сценария."""
    for number, line in lines:
        if not shell.running:
            break
        emit(shell.prompt + line)
        success, output = shell.execute(line)
        if output:
            emit(output)
        if not success:
            emit(f"[script] остановлен: ошибка в строке {number}")
            return False
    return True
