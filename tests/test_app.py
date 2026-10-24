"""Интеграционные проверки запуска и стартовых сценариев."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT, parse_args
from src.main import main
from src.scripts import read_script, run_script
from src.shell import Shell


class ApplicationTests(unittest.TestCase):
    """Проверить всю цепочку: настройки, загрузка, исполнение, код выхода."""

    def invoke(self, *args):
        """Вызвать точку входа и перехватить текстовые потоки."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output), \
                contextlib.redirect_stderr(output):
            code = main(list(args))
        return code, output.getvalue()

    def test_all_stages(self):
        """Каждый демонстрационный сценарий соответствует своему этапу."""
        for stage in range(1, 5):
            script = str(PROJECT_ROOT / f"scripts/stage{stage}.txt")
            with self.subTest(stage=stage):
                code, output = self.invoke(
                    "--headless", "--stage", str(stage), "--script", script
                )
                self.assertEqual(code, 0, output)
                self.assertIn("[config] stage", output)
                self.assertIn("Завершение работы.", output)

    def test_each_error_script_stops(self):
        """Каждый вид ошибки прерывает сценарий до следующей команды."""
        for script in (PROJECT_ROOT / "scripts/errors").glob("*.txt"):
            with self.subTest(script=script.name):
                code, output = self.invoke(
                    "--headless", "--script", str(script)
                )
                self.assertEqual(code, 1, output)
                self.assertIn("ошибка в строке 1", output)
                self.assertNotIn("SHOULD_NOT_RUN", output)

    def test_all_vfs_samples(self):
        """Все варианты CSV можно выбрать через параметр --vfs."""
        for name in ("minimal", "several", "deep"):
            code, output = self.invoke(
                "--headless", "--vfs",
                str(PROJECT_ROOT / f"vfs-samples/{name}.csv"),
                "--script", str(PROJECT_ROOT / "scripts/list.txt"),
            )
            self.assertEqual(code, 0, output)

    def test_startup_errors(self):
        """Отсутствующие VFS и сценарий дают понятную ошибку запуска."""
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / "missing")
            script = str(PROJECT_ROOT / "scripts/list.txt")
            for args in (("--script", missing),
                         ("--vfs", missing, "--script", script)):
                code, output = self.invoke("--headless", *args)
                self.assertEqual(code, 1)
                self.assertIn("Ошибка запуска:", output)

    def test_config_validation(self):
        """Неизвестные опции, пропущенные значения и этапы отклоняются."""
        for args in (["--unknown"], ["--vfs"], ["--script"],
                     ["--headless"], ["--stage", "5"]):
            with self.subTest(args=args), contextlib.redirect_stderr(
                io.StringIO()
            ), self.assertRaises(SystemExit) as error:
                parse_args(args)
            self.assertEqual(error.exception.code, 2)
        config = parse_args([])
        self.assertEqual(config.stage, 4)
        self.assertFalse(config.headless)
        self.assertIsNone(config.script)

    def test_paths_with_spaces(self):
        """Физические пути с пробелами и кириллицей читаются без потерь."""
        with tempfile.TemporaryDirectory(prefix="эмулятор 23 ") as directory:
            vfs = Path(directory) / "файловая система.csv"
            script = Path(directory) / "стартовый скрипт.txt"
            source = PROJECT_ROOT / "vfs-samples/deep.csv"
            vfs.write_bytes(source.read_bytes())
            script.write_text('cd "/home/student/My Documents"\nls\nexit',
                              encoding="utf-8")
            code, output = self.invoke(
                "--headless", "--vfs", str(vfs), "--script", str(script)
            )
            self.assertEqual(code, 0, output)
            self.assertIn("read me.txt", output)

    def test_comments_line_numbers_and_recovery(self):
        """После ошибки скрипта интерактивная оболочка остается доступной."""
        shell, output = Shell(), []
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "script.txt"
            script.write_text("\ufeff# comment\n\nunknown\nexit\n",
                              encoding="utf-8")
            success = run_script(shell, read_script(script), output.append)
        self.assertFalse(success)
        self.assertIn("ошибка в строке 3", output[-1])
        self.assertEqual(shell.history, ["unknown"])
        self.assertTrue(shell.running)
        self.assertTrue(shell.execute("date")[0])

    def test_exit_stops_script(self):
        """После exit остальные строки сценария не выполняются."""
        shell = Shell()
        self.assertTrue(run_script(shell, [(1, "exit"), (2, "unknown")],
                                   lambda text: None))
        self.assertEqual(shell.history, ["exit"])
