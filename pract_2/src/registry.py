"""Самостоятельное чтение sparse-индекса Cargo по HTTP(S)."""

import json
import re
from http.client import HTTPException
from urllib.error import URLError
from urllib.request import Request, urlopen

from .features import active_dependencies
from .models import AnalysisError, Package
from .semver import Version, matches

TIMEOUT = 30
MAX_RESPONSE = 16 * 1024 * 1024


def index_path(name):
    """Вычислить расположение записи пакета по правилам Cargo index."""
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) is None:
        raise AnalysisError(f"неверное имя пакета: {name}")
    name = name.lower()
    size = len(name)
    if size < 3:
        return f"{size}/{name}"
    if size == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def fetch_text(url):
    """Получить открытые метаданные через стандартную библиотеку Python."""
    request = Request(url, headers={"User-Agent": "pract2-cargo-graph/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            data = response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise AnalysisError("ответ репозитория слишком большой")
        return data.decode("utf-8")
    except (URLError, OSError, UnicodeError,
            HTTPException, ValueError) as error:
        raise AnalysisError(f"ошибка запроса {url}: {error}") from error


class CargoRegistry:
    """Кешировать прочитанные версии и раскрывать зависимости самостоятельно."""

    def __init__(self, url, fetcher=fetch_text):
        """Принять корневой URL sparse-индекса и функцию загрузки."""
        self.url = url.rstrip("/")
        self.fetcher = fetcher
        self.cache = {}

    def _records(self, name):
        """Прочитать JSON Lines всех версий одного пакета один раз."""
        key = name.lower()
        if key not in self.cache:
            raw = self.fetcher(self.url + "/" + index_path(name))
            try:
                rows = [json.loads(line) for line in raw.splitlines() if line]
                for row in rows:
                    _validate_record(row)
                    if row["name"].lower() != key:
                        raise ValueError("имя в ответе не совпадает с запросом")
            except (ValueError, KeyError, TypeError) as error:
                raise AnalysisError(f"неверные данные пакета {name}: {error}") \
                    from error
            self.cache[key] = rows
        return self.cache[key]

    def resolve(self, dependency):
        """Выбрать максимальную подходящую версию, исключая yanked."""
        candidates = [row for row in self._records(dependency.name)
                      if not row.get("yanked", False)
                      and matches(row["vers"], dependency.requirement)]
        if not candidates:
            raise AnalysisError(f"нет версии {dependency.name} "
                                f"для {dependency.requirement}")
        row = max(candidates, key=lambda item: Version.parse(item["vers"]))
        return Package(row["name"], row["vers"])

    def dependencies(self, package, features=(), defaults=True):
        """Получить normal/build зависимости выбранной версии и features."""
        row = next(item for item in self._records(package.name)
                   if item["vers"] == package.version)
        for dependency in row["deps"]:
            registry = dependency.get("registry")
            if registry and "crates.io-index" not in registry:
                raise AnalysisError("зависимости из сторонних registry "
                                    "не поддерживаются")
        return active_dependencies(row, features, defaults)


def _validate_record(row):
    """Проверить минимальную схему строки индекса Cargo."""
    if not isinstance(row, dict) or not isinstance(row["deps"], list):
        raise ValueError("ожидается объект с массивом deps")
    index_path(row["name"])
    Version.parse(row["vers"])
    for dependency in row["deps"]:
        if not isinstance(dependency, dict):
            raise ValueError("неверная запись зависимости")
        index_path(dependency["name"])
        if not isinstance(dependency["req"], str):
            raise ValueError("req должен быть строкой")
