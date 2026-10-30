"""Самостоятельная обработка версий и диапазонов Cargo без библиотек."""

import re
from dataclasses import dataclass
from functools import total_ordering

from .models import AnalysisError

CORE = r"(0|[1-9][0-9]*)"
VERSION = re.compile(rf"^{CORE}\.{CORE}\.{CORE}"
                     r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")


@total_ordering
@dataclass(frozen=True)
class Version:
    """Сравнивать major.minor.patch и prerelease по правилам SemVer."""

    core: tuple
    pre: tuple = ()

    @classmethod
    def parse(cls, text):
        """Прочитать полную версию, игнорируя build metadata."""
        match = VERSION.fullmatch(text)
        if match is None:
            raise AnalysisError(f"некорректная версия: {text}")
        pre = tuple((match[4] or "").split(".")) if match[4] else ()
        if any(not item or (item.isdigit() and len(item) > 1
                            and item.startswith("0")) for item in pre):
            raise AnalysisError(f"некорректный prerelease: {text}")
        return cls(tuple(int(match[i]) for i in (1, 2, 3)), pre)

    def __lt__(self, other):
        """Стабильная версия старше предварительной с тем же номером."""
        if self.core != other.core:
            return self.core < other.core
        if not self.pre or not other.pre:
            return bool(self.pre) and not other.pre
        left = tuple((0, int(p)) if p.isdigit() else (1, p) for p in self.pre)
        right = tuple((0, int(p)) if p.isdigit() else (1, p) for p in other.pre)
        return left < right


def matches(version, requirement):
    """Проверить caret, tilde, wildcard и пересечение условий сравнения."""
    version = Version.parse(version) if isinstance(version, str) else version
    parts = [part.strip() for part in requirement.split(",")]
    if not all(_comparator(version, part) for part in parts):
        return False
    if not version.pre:
        return True
    return any(_prerelease_core(part) == version.core for part in parts)


def _prerelease_core(part):
    """Предварительные версии допускаются только при явном запросе."""
    text = part.lstrip("^~<>= ")
    return Version.parse(text).core if "-" in text else None


def _components(text):
    """Прочитать неполный номер и обозначения звездочек."""
    chunks = text.split(".")
    if len(chunks) > 3 or not chunks:
        raise AnalysisError(f"неверный диапазон версии: {text}")
    numbers = []
    wildcard = False
    for chunk in chunks:
        if chunk in ("*", "x", "X"):
            wildcard = True
        elif wildcard or not re.fullmatch(CORE, chunk):
            raise AnalysisError(f"неверный диапазон версии: {text}")
        else:
            numbers.append(int(chunk))
    return numbers, wildcard


def _upper(numbers, position):
    """Сформировать исключительную верхнюю границу диапазона."""
    result = list(numbers) + [0] * (3 - len(numbers))
    result[position] += 1
    for index in range(position + 1, 3):
        result[index] = 0
    return Version(tuple(result))


def _comparator(version, text):
    """Применить одно условие к версии."""
    match = re.fullmatch(r"(>=|<=|>|<|=|\^|~)?\s*(\S+)", text)
    if match is None:
        raise AnalysisError(f"неверный диапазон версии: {text}")
    operator, value = match[1] or "^", match[2]
    if "-" in value or "+" in value:
        lower = Version.parse(value)
        numbers, wildcard = list(lower.core), False
    else:
        numbers, wildcard = _components(value)
        lower = Version(tuple(numbers + [0] * (3 - len(numbers))))
    if not numbers:
        return True
    if wildcard:
        return lower <= version < _upper(numbers, len(numbers) - 1)
    if operator in (">", ">=", "<", "<=", "="):
        return _comparison(version, operator, lower, numbers)
    position = _caret_position(numbers) if operator == "^" else \
        min(1, len(numbers) - 1)
    return lower <= version < _upper(numbers, position)


def _caret_position(numbers):
    """Caret сохраняет первую значащую часть, учитывая неполный номер."""
    return next((i for i, value in enumerate(numbers) if value),
                len(numbers) - 1)


def _comparison(version, operator, lower, numbers):
    """Учесть особую семантику неполных номеров в операторах Cargo."""
    complete = len(numbers) == 3
    upper = _upper(numbers, len(numbers) - 1)
    choices = {">=": version >= lower, "<": version < lower,
               ">": version > lower if complete else version >= upper,
               "<=": version <= lower if complete else version < upper,
               "=": version == lower if complete else lower <= version < upper}
    return choices[operator]
