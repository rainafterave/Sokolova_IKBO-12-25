"""Проверка своего обработчика версий Cargo."""

import unittest

from src.models import AnalysisError
from src.semver import Version, matches


class SemverTests(unittest.TestCase):
    """Проверить границы диапазонов и порядок предварительных версий."""

    def test_caret_ranges(self):
        """Нулевая major-версия имеет более строгие границы обновлений."""
        cases = [("1.9.0", "1.2", True), ("2.0.0", "^1.2.3", False),
                 ("0.2.9", "^0.2.3", True), ("0.3.0", "0.2.3", False),
                 ("0.0.4", "0.0.3", False), ("0.0.9", "0.0", True),
                 ("0.1.0", "0.0", False), ("0.9.0", "0", True),
                 ("1.0.0", "0", False)]
        for version, requirement, expected in cases:
            with self.subTest(version=version, requirement=requirement):
                self.assertEqual(matches(version, requirement), expected)

    def test_tilde_wildcards_and_comparisons(self):
        """Проверить интервалы и включительность их границ."""
        cases = [("1.2.9", "~1.2", True), ("1.3.0", "~1.2", False),
                 ("1.9.0", "~1", True), ("3.0.0", "*", True),
                 ("1.2.9", "1.2.*", True), ("1.3.0", "1.2.x", False),
                 ("1.5.0", ">=1.2, <2", True),
                 ("2.0.0", ">=1.2, <2", False),
                 ("1.2.3", "=1.2.3", True), ("1.2.4", "=1.2.3", False),
                 ("1.2.9", "=1.2", True), ("1.3.0", "<=1.2", False),
                 ("2.0.0", ">1", True), ("1.9.0", ">1", False)]
        for version, requirement, expected in cases:
            with self.subTest(version=version, requirement=requirement):
                self.assertEqual(matches(version, requirement), expected)

    def test_prerelease(self):
        """Предварительные версии включаются только при явном запросе."""
        self.assertFalse(matches("1.2.3-beta.1", "*"))
        self.assertTrue(matches("1.2.3-beta.2", "^1.2.3-beta.1"))
        self.assertFalse(matches("1.3.0-beta", "^1.2.3-beta.1"))
        self.assertLess(Version.parse("1.2.3-beta.2"),
                        Version.parse("1.2.3-beta.11"))
        self.assertLess(Version.parse("1.2.3-rc"), Version.parse("1.2.3"))
        self.assertEqual(Version.parse("1.2.3+abc"), Version.parse("1.2.3"))

    def test_invalid_input(self):
        """Поврежденные версии и неподдерживаемые выражения дают ошибку."""
        for version in ("1.2", "01.2.3", "1.2.3-01", "broken"):
            with self.subTest(v=version), self.assertRaises(AnalysisError):
                Version.parse(version)
        for requirement in ("", "1.2.3.4", "banana", "1.*.2", "1 || 2"):
            with self.subTest(r=requirement), self.assertRaises(AnalysisError):
                matches("1.2.3", requirement)
