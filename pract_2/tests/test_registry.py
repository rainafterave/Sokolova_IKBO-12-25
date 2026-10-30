"""Проверка чтения настоящего формата Cargo без сетевых зависимостей."""

import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from src.graph import Builder
from src.models import AnalysisError, Dependency, Package
from src.registry import CargoRegistry, fetch_text, index_path


def record(name="example", version="1.0.0", **changes):
    """Подготовить запись в том же формате, что sparse-индекс."""
    return dict(name=name, vers=version, deps=[], features={}, yanked=False) \
        | changes


def dependency(name, **changes):
    """Подготовить запись зависимости с обычными значениями по умолчанию."""
    return dict(name=name, req="^1", optional=False, kind="normal",
                default_features=True, features=[]) | changes


class RegistryTests(unittest.TestCase):
    """Проверять настоящий разбор и выбор версий на сохраненных HTTP-ответах."""

    def test_index_paths(self):
        """Пакеты разной длины размещаются в правильных папках индекса."""
        for name, expected in (("a", "1/a"), ("ab", "2/ab"),
                               ("csv", "3/c/csv"), ("Serde", "se/rd/serde")):
            self.assertEqual(index_path(name), expected)
        with self.assertRaises(AnalysisError):
            index_path("../../file")

    def test_resolution_yanked_prerelease_and_cache(self):
        """Выбор версии учитывает диапазон, yanked, prerelease и кеш."""
        rows = [record(version="1.0.0"), record(version="1.8.0"),
                record(version="1.9.0", yanked=True),
                record(version="2.0.0-beta"), record(version="2.0.0")]
        calls = []

        def fetch(url):
            """Зафиксировать число обращений к источнику."""
            calls.append(url)
            return "\n".join(map(json.dumps, rows))

        repo = CargoRegistry("https://index.test", fetch)
        self.assertEqual(repo.resolve(Dependency("example", "^1")).version,
                         "1.8.0")
        self.assertEqual(repo.resolve(Dependency("example", "*")).version,
                         "2.0.0")
        self.assertEqual(len(calls), 1)
        with self.assertRaises(AnalysisError):
            repo.resolve(Dependency("example", "=3.0.0"))

    def test_default_features_optional_alias_and_weak(self):
        """Features активируют optional, переименование и дочерние features."""
        row = record(deps=[dependency("base"),
                           dependency("alias", optional=True, package="actual"),
                           dependency("unused", optional=True),
                           dependency("dev", kind="dev")],
                     features={"default": ["format"],
                               "format": ["dep:alias", "alias/derive",
                                          "unused?/extra"]})
        repo = CargoRegistry("https://index.test", lambda url: json.dumps(row))
        values = repo.dependencies(Package("example", "1.0.0"))
        self.assertEqual({item.name for item in values}, {"base", "actual"})
        actual = next(item for item in values if item.name == "actual")
        self.assertEqual(actual.features, ("derive",))
        values = repo.dependencies(Package("example", "1.0.0"), defaults=False)
        self.assertEqual([item.name for item in values], ["base"])

    def test_features2_cycles_build_and_target(self):
        """Цикл features завершается; build и условные зависимости доступны."""
        row = record(deps=[dependency("builder", kind="build"),
                           dependency("opt", optional=True,
                                      target="cfg(unix)")],
                     features={"default": ["a"], "a": ["b"]},
                     features2={"b": ["a", "dep:opt", "opt?/extra"]})
        repo = CargoRegistry("https://index.test", lambda url: json.dumps(row))
        values = repo.dependencies(Package("example", "1.0.0"))
        self.assertEqual({item.name for item in values}, {"builder", "opt"})
        self.assertEqual(next(d for d in values if d.name == "opt").features,
                         ("extra",))

    def test_invalid_metadata(self):
        """Неверный JSON и неверная схема дают сообщение приложения."""
        for raw in ("not JSON", "{}", "[]", '{"deps":42}',
                    json.dumps(record(name="other"))):
            repo = CargoRegistry("https://index.test", lambda url: raw)
            with self.subTest(raw=raw), self.assertRaises(AnalysisError):
                repo.resolve(Dependency("example"))

    def test_network_error_is_readable(self):
        """Отказ сети превращается в понятную ошибку с адресом запроса."""
        with patch("src.registry.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(AnalysisError, "index.test"):
                fetch_text("https://index.test/1/a")

    def test_incompatible_versions_are_distinct_nodes(self):
        """Две несовместимые версии одного crate сохраняются как разные узлы."""
        rows = {
            "root": [record(name="root", deps=[dependency("b"),
                                               dependency("c")])],
            "b": [record(name="b"), record(name="b", version="2.0.0")],
            "c": [record(name="c", deps=[dependency("b", req="^2")])],
        }

        def fetch(url):
            """Вернуть записи пакета в формате JSON Lines."""
            name = url.rsplit("/", 1)[-1]
            return "\n".join(map(json.dumps, rows[name]))

        graph = Builder(CargoRegistry("https://index.test", fetch), 10)
        nodes = graph.build("root").edges
        self.assertIn(Package("b", "1.0.0"), nodes)
        self.assertIn(Package("b", "2.0.0"), nodes)
