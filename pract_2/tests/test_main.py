"""Проверка всех пяти этапов CLI и создания PlantUML."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.main import main
from src.plantuml import plantuml
from src.graph import Builder
from src.test_repository import TestRepository


class ApplicationTests(unittest.TestCase):
    """Исполнять настоящее приложение на тестовых данных без сети."""

    def invoke(self, *args):
        """Получить код выхода и весь диалог одной команды."""
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), \
                contextlib.redirect_stderr(stream):
            code = main(list(args))
        return code, stream.getvalue()

    def test_all_stages(self):
        """Каждый этап выводит именно предусмотренный им результат."""
        for stage, expected in ((1, "package=A"), (2, "B\nC"),
                                (3, "[2] D -> -"), (4, "D -> B -> C -> A"),
                                (5, "@startuml")):
            code, output = self.invoke("--stage", str(stage))
            self.assertEqual(code, 0, output)
            self.assertIn(expected, output)
            if stage != 1:
                self.assertNotIn("test_mode=", output)

    def test_cycle_draws_but_has_no_order(self):
        """Цикл отображается, а запрос порядка дает явную ошибку."""
        config = str(PROJECT_ROOT / "configs/cycle.ini")
        code, output = self.invoke("--config", config, "--stage", "4")
        self.assertEqual(code, 1)
        self.assertIn("цикл", output)
        code, output = self.invoke("--config", config)
        self.assertEqual(code, 0, output)
        self.assertIn("-[#red]->", output)

    def test_output_file(self):
        """Выведенный PlantUML совпадает с сохраненным в файл."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagram.puml"
            code, output = self.invoke("--output", str(path))
            self.assertEqual(code, 0, output)
            self.assertEqual(path.read_text(encoding="utf-8"), output)

    def test_invalid_config_and_cli(self):
        """Ошибки данных дают код 1, ошибки CLI — код 2."""
        code, output = self.invoke("--config", "missing-file.ini")
        self.assertEqual(code, 1)
        self.assertIn("Ошибка:", output)
        for args in (("--stage", "6"), ("--stage", "1", "--output", "x"),
                     ("--unknown",)):
            with contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as error:
                main(list(args))
            self.assertEqual(error.exception.code, 2)

    def test_single_and_deterministic_plantuml(self):
        """Изолированный пакет тоже показывается; результат воспроизводим."""
        repo = TestRepository(PROJECT_ROOT / "tests/graphs/single.txt")
        graph = Builder(repo, 0).build("A")
        text = plantuml(graph)
        self.assertIn('component "A"', text)
        self.assertEqual(text, plantuml(graph))
        self.assertIn("@enduml", text)
