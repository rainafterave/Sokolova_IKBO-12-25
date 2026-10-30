"""Проверки всех пяти параметров INI и понятных ошибок."""

import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT, read_config
from src.models import AnalysisError


class ConfigTests(unittest.TestCase):
    """Создавать независимые настройки с временным тестовым графом."""

    def setUp(self):
        """Подготовить каталог, граф и корректный INI."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "graph.txt").write_text("A:\n", encoding="utf-8")
        self.path = self.root / "config.ini"
        self.values = dict(package="A", repository="graph.txt",
                           test_mode="true", max_depth="3", filter="")

    def write(self, **changes):
        """Записать настройки с измененными значениями."""
        values = self.values | changes
        text = "[analysis]\n" + "\n".join(f"{k}={v}" for k, v in values.items())
        self.path.write_text(text, encoding="utf-8")

    def test_valid_and_relative_path(self):
        """Путь к графу отсчитывается от INI, а не от текущей папки."""
        self.write()
        config = read_config(self.path)
        self.assertEqual(config.repository, str(self.root / "graph.txt"))
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(len(config.lines()), 5)

    def test_invalid_each_parameter(self):
        """Неверное значение каждого обязательного параметра отклоняется."""
        for change in (dict(package="a"), dict(repository="missing.txt"),
                       dict(test_mode="perhaps"), dict(max_depth="-1"),
                       dict(max_depth="1.5"), dict(filter="A"),
                       dict(filter="B\n C"), dict(repository="")):
            with self.subTest(change=change):
                self.write(**change)
                with self.assertRaises(AnalysisError):
                    read_config(self.path)

    def test_real_url_and_version(self):
        """Реальный режим принимает sparse-URL и фиксированную версию."""
        self.write(package="serde_json@1.0.154", test_mode="false",
                   repository="https://index.crates.io")
        self.assertFalse(read_config(self.path).test_mode)
        for url in ("file:///tmp", "index.crates.io", "https://x/?token=x"):
            self.write(package="csv", test_mode="false", repository=url)
            with self.subTest(url=url), self.assertRaises(AnalysisError):
                read_config(self.path)

    def test_sections_missing_and_unknown_keys(self):
        """Опечатки в настройках не игнорируются."""
        for text in ("[wrong]\npackage=A", "[analysis]\npackage=A",
                     "[DEFAULT]\npackage=A\n[analysis]\n"):
            self.path.write_text(text, encoding="utf-8")
            with self.subTest(text=text), self.assertRaises(AnalysisError):
                read_config(self.path)
        self.write(extra="unknown")
        with self.assertRaises(AnalysisError):
            read_config(self.path)

    def test_missing_file(self):
        """Отсутствующий конфигурационный файл дает ошибку приложения."""
        with self.assertRaises(AnalysisError):
            read_config(self.root / "missing.ini")

    def test_all_example_configs(self):
        """Все включенные в работу INI корректны без сетевого запроса."""
        for path in (PROJECT_ROOT / "configs").glob("*.ini"):
            with self.subTest(path=path):
                read_config(path)
