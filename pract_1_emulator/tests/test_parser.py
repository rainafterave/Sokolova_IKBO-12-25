"""Проверка кавычек и отсутствия исполнения реальной оболочки."""

import unittest

from src.parser import parse


class ParserTests(unittest.TestCase):
    """Проверить разбор аргументов, пустой ввод и ошибки синтаксиса."""

    def test_spaces_and_quotes(self):
        """Оба вида кавычек и пустые аргументы сохраняют границы."""
        self.assertEqual(parse('ls "My Documents" \'два слова\' ""'),
                         ("ls", ["My Documents", "два слова", ""]))
        self.assertEqual(parse("  cd   ..  "), ("cd", [".."]))
        self.assertEqual(parse("   "), (None, []))

    def test_escaping_and_concatenation(self):
        """Экранирование пробелов и соседние фрагменты образуют аргумент."""
        self.assertEqual(parse(r"ls My\ Documents"),
                         ("ls", ["My Documents"]))
        self.assertEqual(parse('ls ab"cd ef"'), ("ls", ["abcd ef"]))

    def test_unclosed_quote(self):
        """Незакрытые кавычки не принимаются как обычный путь."""
        with self.assertRaises(ValueError):
            parse('ls "broken')

    def test_shell_metacharacters_are_not_executed(self):
        """Пайпы, переменные и комментарии не интерпретируются."""
        self.assertEqual(parse("ls $HOME | date #text"),
                         ("ls", ["$HOME", "|", "date", "#text"]))
