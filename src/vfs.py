"""Виртуальная файловая система из CSV, загружаемая только в память."""

import base64
import binascii
import csv
from dataclasses import dataclass

CSV_FIELDS = ["path", "type", "data"]


class VFSError(ValueError):
    """Ошибка формата CSV или обращения к виртуальному пути."""


@dataclass(frozen=True)
class Node:
    """Каталог или файл с двоичным содержимым в памяти."""

    kind: str
    data: bytes = b""


class VFS:
    """Хранить узлы по абсолютным POSIX-путям без распаковки на диск."""

    def __init__(self):
        """Создать пустую файловую систему с корневым каталогом."""
        self.nodes = {"/": Node("dir")}

    @classmethod
    def from_csv(cls, path):
        """Прочитать CSV и проверить все строки перед использованием VFS."""
        result = cls()
        explicit = set()
        try:
            with open(path, encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source, strict=True)
                if reader.fieldnames != CSV_FIELDS:
                    raise VFSError("ожидается заголовок path,type,data")
                for row in reader:
                    try:
                        result._add_row(row, explicit)
                    except VFSError as error:
                        raise VFSError(
                            f"CSV, строка {reader.line_num}: {error}"
                        ) from error
        except (OSError, UnicodeError, csv.Error) as error:
            raise VFSError(f"не удалось прочитать VFS: {error}") from error
        return result

    def _add_row(self, row, explicit):
        """Проверить путь, тип, уникальность и содержимое записи CSV."""
        if set(row) != set(CSV_FIELDS) or None in row.values():
            raise VFSError("неверное количество полей")
        path = row["path"]
        parts = path.split("/")[1:]
        if not path.startswith("/") or "\x00" in path:
            raise VFSError("нужен абсолютный POSIX-путь без NUL")
        if path != "/" and any(p in ("", ".", "..") for p in parts):
            raise VFSError("путь содержит пустой компонент, . или ..")
        if path in explicit:
            raise VFSError(f"повтор пути: {path}")
        node = self._decode(row["type"], row["data"])
        self._ensure_parents(path)
        previous = self.nodes.get(path)
        if previous is not None and (previous != node or node.kind != "dir"):
            raise VFSError(f"конфликт файла и каталога: {path}")
        self.nodes[path] = node
        explicit.add(path)

    @staticmethod
    def _decode(kind, data):
        """Декодировать base64 файлов; у каталогов данные пустые."""
        if kind == "dir" and not data:
            return Node("dir")
        if kind != "file":
            raise VFSError("тип должен быть dir (без данных) или file")
        try:
            return Node("file", base64.b64decode(data, validate=True))
        except (ValueError, binascii.Error) as error:
            raise VFSError("некорректный base64") from error

    def _ensure_parents(self, path):
        """Создать неявные родительские каталоги и проверить конфликты."""
        current = ""
        for part in path.split("/")[1:-1]:
            current += "/" + part
            node = self.nodes.setdefault(current, Node("dir"))
            if node.kind != "dir":
                raise VFSError(f"родитель не является каталогом: {current}")

    def resolve(self, path, cwd="/"):
        """Найти путь по компонентам, проверяя промежуточные каталоги."""
        if not path or "\x00" in path:
            raise VFSError("пустой или недопустимый путь")
        current = "/" if path.startswith("/") else cwd
        for part in path.split("/"):
            if self.nodes[current].kind != "dir":
                raise VFSError(f"не является каталогом: {current}")
            if part in ("", "."):
                continue
            if part == "..":
                current = current.rsplit("/", 1)[0] or "/"
            else:
                current = current.rstrip("/") + "/" + part
            if current not in self.nodes:
                raise VFSError(f"нет такого файла или каталога: {path}")
        return current

    def children(self, path):
        """Вернуть отсортированные имена прямых потомков каталога."""
        prefix = path.rstrip("/") + "/"
        return sorted(
            name[len(prefix):] for name in self.nodes
            if name.startswith(prefix) and name != path
            and "/" not in name[len(prefix):]
        )
