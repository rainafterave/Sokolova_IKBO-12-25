"""Поведение команд, история и независимость от реальной файловой системы."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.config import PROJECT_ROOT
from src.shell import Shell
from src.vfs import VFS


class ShellTests(unittest.TestCase):
    """Исполнять команды на глубокой тестовой VFS."""

    def setUp(self):
        """Каждому тесту предоставить новое состояние оболочки."""
        path = PROJECT_ROOT / "vfs-samples/deep.csv"
        self.shell = Shell(VFS.from_csv(path))

    def test_real_identity(self):
        """Заголовок использует данные ОС, а приглашение - виртуальный путь."""
        with patch("src.shell.getpass.getuser", return_value="student"), \
                patch("src.shell.socket.gethostname", return_value="host"):
            shell = Shell()
        self.assertEqual(shell.title, "Эмулятор - [student@host]")
        self.assertEqual(shell.prompt, "student@host:/$ ")

    def test_prototypes(self):
        """Этапы 1-2 воспроизводят заглушки без настоящей VFS."""
        for stage in (1, 2):
            shell = Shell(stage=stage)
            self.assertEqual(shell.execute('ls "a b"'),
                             (True, "ls ['a b']"))
            self.assertEqual(shell.execute("cd /missing"),
                             (True, "cd ['/missing']"))
            self.assertFalse(shell.execute("date")[0])

    def test_ls_modes(self):
        """Листинг каталога, файла, нескольких путей и скрытых узлов."""
        self.assertIn("home/", self.shell.execute("ls")[1])
        self.assertNotIn(".hidden", self.shell.execute("ls")[1])
        self.assertIn(".hidden", self.shell.execute("ls -a")[1])
        self.assertIn("dir", self.shell.execute("ls -l")[1])
        self.assertIn("hosts", self.shell.execute("ls /etc/hosts")[1])
        self.assertIn("/etc:\n", self.shell.execute("ls /etc /empty")[1])
        self.assertTrue(self.shell.execute("ls -- /etc")[0])
        self.assertEqual(self.shell.execute("ls /empty"), (True, ""))

    def test_cd_relative_quotes_root(self):
        """Навигация поддерживает пробелы, . и .. и не выходит из VFS."""
        for command, cwd in [
            ("cd /home/student", "/home/student"),
            ('cd "My Documents"', "/home/student/My Documents"),
            ("cd ../docs/drafts", "/home/student/docs/drafts"),
            ("cd .", "/home/student/docs/drafts"),
            ("cd", "/"), ("cd ..", "/"),
        ]:
            self.assertTrue(self.shell.execute(command)[0])
            self.assertEqual(self.shell.cwd, cwd)

    def test_failed_cd_keeps_directory(self):
        """Ошибка перехода сохраняет старый текущий каталог."""
        for command in ("cd /missing", "cd /etc/hosts", 'cd ""', "cd a b"):
            self.assertFalse(self.shell.execute(command)[0])
            self.assertEqual(self.shell.cwd, "/")

    def test_invalid_commands_and_arguments(self):
        """Неверные команды, опции и кавычки возвращают ошибку."""
        for command in (
            "unknown", 'ls "bad', "ls -z", "ls /missing", "cd -x",
            "uptime x", "history x", "history -1", "history 1 2",
            "date bad", "date +a +b", "exit extra",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell.execute(command)[0])
                self.assertTrue(self.shell.running)

    def test_history_includes_errors_and_itself(self):
        """История содержит непустой ввод, ошибки и текущий history."""
        self.shell.execute("   ")
        self.shell.execute("ls")
        self.shell.execute("unknown")
        self.assertEqual(self.shell.execute("history 2")[1],
                         "    2  unknown\n    3  history 2")
        self.assertEqual(self.shell.execute("history 0"), (True, ""))

    def test_uptime(self):
        """Время работы отсчитывается монотонными часами эмулятора."""
        self.shell.started = 0
        with patch("src.shell.time.monotonic", return_value=90061):
            self.assertEqual(self.shell.execute("uptime"),
                             (True, "up 1 days, 01:01:01"))

    def test_date_formats_and_utc(self):
        """Время ОС можно вывести в UTC и пользовательском формате."""
        now = datetime(2026, 10, 24, 12, 34, 56, tzinfo=timezone.utc)
        with patch("src.shell.datetime") as clock:
            clock.now.return_value = now
            self.assertEqual(self.shell.execute('date -u "+%Y-%m-%d"'),
                             (True, "2026-10-24"))
            clock.now.assert_called_with(timezone.utc)
            expected = now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            self.assertEqual(self.shell.execute("date"), (True, expected))

    def test_exit(self):
        """exit завершает оболочку, а ошибочный exit оставляет ее открытой."""
        self.assertTrue(self.shell.execute("exit")[0])
        self.assertFalse(self.shell.running)
