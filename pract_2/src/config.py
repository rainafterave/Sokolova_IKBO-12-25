"""Чтение и проверка пяти настроек из INI."""

import configparser
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .models import AnalysisError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS = {"package", "repository", "test_mode", "max_depth", "filter"}
CRATE_NAME = r"[A-Za-z][A-Za-z0-9_-]*"
PACKAGE_SPEC = rf"{CRATE_NAME}(?:@[0-9]+\.[0-9]+\.[0-9]+)?"


@dataclass(frozen=True)
class Config:
    """Настройки анализа, прочитанные из секции analysis."""

    package: str
    repository: str
    test_mode: bool
    max_depth: int
    exclude: str

    def lines(self):
        """Получить все настройки в формате ключ=значение для этапа 1."""
        return [f"package={self.package}", f"repository={self.repository}",
                f"test_mode={str(self.test_mode).lower()}",
                f"max_depth={self.max_depth}", f"filter={self.exclude}"]


def read_config(path):
    """Прочитать INI, разрешая относительные пути от его расположения."""
    path = Path(path).resolve()
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8-sig") as source:
            parser.read_file(source)
        if parser.sections() != ["analysis"] or parser.defaults():
            raise AnalysisError("INI должен содержать только секцию [analysis]")
        section = parser["analysis"]
        if set(section) != SETTINGS:
            names = ", ".join(sorted(SETTINGS))
            raise AnalysisError("нужны параметры: " + names)
        config = _values(section)
        return _validate(config, path.parent)
    except (OSError, UnicodeError, configparser.Error) as error:
        raise AnalysisError(f"не удалось прочитать INI: {error}") from error


def _values(section):
    """Проверить типы числа, логического значения и строки фильтра."""
    try:
        mode = section.getboolean("test_mode")
        depth = section.getint("max_depth")
    except ValueError as error:
        raise AnalysisError("test_mode: true/false; max_depth: целое число") \
            from error
    exclude = section["filter"].strip()
    if "\n" in exclude or "\r" in exclude:
        raise AnalysisError("filter должен быть одной строкой")
    return Config(section["package"].strip(), section["repository"].strip(),
                  mode, depth, exclude)


def _validate(config, directory):
    """Проверить имя, глубину, фильтр и источник репозитория."""
    pattern = r"[A-Z]+" if config.test_mode else PACKAGE_SPEC
    if re.fullmatch(pattern, config.package) is None:
        raise AnalysisError("неверное имя package для выбранного режима")
    if config.max_depth < 0:
        raise AnalysisError("max_depth должен быть неотрицательным")
    if config.exclude and config.exclude in config.package.split("@")[0]:
        raise AnalysisError("filter исключает сам анализируемый пакет")
    if not config.repository:
        raise AnalysisError("repository не должен быть пустым")
    if config.test_mode:
        source = (directory / config.repository).resolve()
        if not source.is_file():
            raise AnalysisError(f"файл тестового графа не найден: {source}")
        return Config(config.package, str(source), True,
                      config.max_depth, config.exclude)
    _validate_url(config.repository)
    return config


def _validate_url(repository):
    """Проверить адрес sparse-индекса, включая номер порта."""
    try:
        url = urlsplit(repository)
        port = url.port
    except ValueError as error:
        raise AnalysisError(f"неверный repository URL: {error}") from error
    if url.scheme not in ("https", "http") or not url.hostname:
        raise AnalysisError("repository должен быть HTTP(S)-URL sparse-индекса")
    if any(char.isspace() for char in repository) or port == 0:
        raise AnalysisError("repository: неверное имя хоста или порт")
    if url.query or url.fragment or url.username or url.password:
        raise AnalysisError("repository: URL без параметров и логина")
