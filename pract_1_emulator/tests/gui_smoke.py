"""Отдельная проверка настоящих виджетов Tkinter, требующая рабочий стол."""

import unittest

from src.config import parse_args
from src.gui import EmulatorWindow, tk
from src.main import prepare


class GUITests(unittest.TestCase):
    """Выполнить сценарий и интерактивный ввод через настоящее окно."""

    def setUp(self):
        """Создать скрытое тестовое окно без вмешательства пользователя."""
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        config = parse_args([])
        self.shell, _ = prepare(config)
        lines = [(1, 'cd "/home/student/My Documents"'),
                 (2, "ls"), (3, "unknown"), (4, "uptime")]
        self.window = EmulatorWindow(self.root, self.shell, config, lines)
        self.root.update()

    def test_startup_script_and_manual_input(self):
        """Ошибка останавливает сценарий, но Enter продолжает работу."""
        transcript = self.window.output.get("1.0", "end")
        self.assertEqual(self.root.title(), self.shell.title)
        self.assertIn("read me.txt", transcript)
        self.assertIn("ошибка в строке 3", transcript)
        self.assertNotIn("uptime", self.shell.history)
        self.window.entry.insert(0, "date +%Y")
        self.window.submit()
        self.assertEqual(self.shell.history[-1], "date +%Y")
        self.assertIn(self.shell.cwd, self.window.prompt.get())
        self.assertEqual(self.window.output.cget("state"), "disabled")

    def test_history_keys_and_cancel(self):
        """Стрелки возвращают команды, Ctrl+C очищает строку."""
        self.window.recall(-1)
        self.assertEqual(self.window.entry.get(), "unknown")
        self.window.recall(1)
        self.assertEqual(self.window.entry.get(), "")
        self.window.entry.insert(0, "unfinished")
        self.window.cancel()
        self.assertEqual(self.window.entry.get(), "")
        self.assertTrue(self.shell.running)


if __name__ == "__main__":
    unittest.main()
