"""Общие типы данных для реального и тестового репозитория."""

from dataclasses import dataclass


class AnalysisError(ValueError):
    """Ошибка настроек, репозитория или анализа зависимостей."""


@dataclass(frozen=True, order=True)
class Package:
    """Уникальный пакет: название и выбранная версия."""

    name: str
    version: str = ""

    @property
    def label(self):
        """Читаемая подпись вершины графа."""
        return f"{self.name} v{self.version}" if self.version else self.name


@dataclass(frozen=True)
class Dependency:
    """Запрос зависимости с диапазоном версии и набором возможностей."""

    name: str
    requirement: str = "*"
    features: tuple = ()
    default_features: bool = True
