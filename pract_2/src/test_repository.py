"""Тестовый репозиторий: текстовый граф с большими латинскими именами."""

import re
from pathlib import Path

from .models import AnalysisError, Dependency, Package


class TestRepository:
    """Читать строки A: B C; все используемые вершины должны быть объявлены."""

    def __init__(self, path):
        """Прочитать весь файл и проверить ссылки до начала анализа."""
        self.adjacency = {}
        try:
            lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError) as error:
            raise AnalysisError(f"ошибка чтения тестового графа: {error}") \
                from error
        for number, raw in enumerate(lines, start=1):
            line = raw.split("#", 1)[0].strip()
            if line:
                self._line(line, number)
        if not self.adjacency:
            raise AnalysisError("тестовый граф пуст")
        missing = {name for values in self.adjacency.values() for name in values
                   if name not in self.adjacency}
        if missing:
            names = ", ".join(sorted(missing))
            raise AnalysisError("не объявлены пакеты: " + names)

    def _line(self, line, number):
        """Проверить синтаксис и запретить повторное объявление вершины."""
        match = re.fullmatch(r"([A-Z]+)\s*:\s*([A-Z\s]*)", line)
        if match is None:
            raise AnalysisError(f"строка {number}: ожидается A: B C")
        name, children = match[1], match[2].split()
        if name in self.adjacency:
            raise AnalysisError(f"строка {number}: повтор пакета {name}")
        self.adjacency[name] = sorted(set(children))

    def resolve(self, dependency):
        """Найти тестовый пакет без обращения в сеть."""
        if dependency.name not in self.adjacency:
            raise AnalysisError(f"пакет не найден: {dependency.name}")
        return Package(dependency.name)

    def dependencies(self, package, features=(), defaults=True):
        """Вернуть прямые зависимости тестового пакета."""
        return [Dependency(name) for name in self.adjacency[package.name]]
