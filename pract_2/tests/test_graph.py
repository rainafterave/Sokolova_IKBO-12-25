"""Проверки BFS, фильтра, глубины, общих зависимостей и циклов."""

import tempfile
import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.graph import Builder, find_cycle, load_order
from src.models import AnalysisError, Dependency, Package
from src.test_repository import TestRepository

GRAPHS = PROJECT_ROOT / "tests/graphs"


class GraphTests(unittest.TestCase):
    """Проверить точные вершины и ребра, а не только текст вывода."""

    def graph(self, name, depth=10, exclude=""):
        """Построить один из включенных тестовых графов."""
        repo = TestRepository(GRAPHS / f"{name}.txt")
        return Builder(repo, depth, exclude).build("A")

    def test_diamond_and_shortest_depth(self):
        """Общая зависимость существует один раз и имеет минимальную глубину."""
        graph = self.graph("diamond")
        self.assertEqual(len(graph.edges), 4)
        self.assertEqual(graph.depths[Package("D")], 2)
        self.assertEqual(sum(map(len, graph.edges.values())), 4)
        self.assertEqual(find_cycle(graph), [])

    def test_depth_boundaries(self):
        """Глубина 0 означает только корень, 1 — прямые зависимости."""
        for depth, expected in ((0, {"A"}), (1, {"A", "B"}),
                                (2, {"A", "B", "C"})):
            graph = self.graph("chain", depth)
            self.assertEqual({n.name for n in graph.edges}, expected)
            self.assertEqual(max(graph.depths.values()), depth)

    def test_filter_prunes_branch(self):
        """Исключенная вершина не добавляется и не обходится."""
        graph = self.graph("diamond", exclude="B")
        self.assertEqual({n.name for n in graph.edges}, {"A", "C", "D"})
        graph = self.graph("chain", exclude="B")
        self.assertEqual({n.name for n in graph.edges}, {"A"})

    def test_cycle_and_self_loop(self):
        """BFS завершается, сохраняет циклические ребра, порядок невозможен."""
        graph = self.graph("cycle")
        cycle = [n.name for n in find_cycle(graph)]
        self.assertEqual(cycle, ["A", "B", "C", "A"])
        order, blocked = load_order(graph)
        self.assertEqual([n.name for n in order], ["D"])
        self.assertEqual({n.name for n in blocked}, {"A", "B", "C"})
        graph = self.graph("self_loop")
        self.assertEqual(find_cycle(graph), [Package("A"), Package("A")])

    def test_load_order_is_dependency_first(self):
        """Зависимость всегда находится раньше использующего пакета."""
        for name in ("diamond", "complex", "single"):
            graph = self.graph(name)
            order, blocked = load_order(graph)
            self.assertFalse(blocked)
            positions = {node: index for index, node in enumerate(order)}
            for parent, children in graph.edges.items():
                for child in children:
                    self.assertLess(positions[child], positions[parent])
            self.assertEqual(order[-1], Package("A"))

    def test_invalid_and_missing_nodes(self):
        """Отсутствующие вершины и неправильные файлы не скрываются."""
        with self.assertRaises(AnalysisError):
            TestRepository(GRAPHS / "missing.txt")
        repo = TestRepository(GRAPHS / "single.txt")
        with self.assertRaises(AnalysisError):
            repo.resolve(Dependency("Z"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.txt"
            for text in ("", "a: B", "A:\nA:", "A B", "A: B\nB: c"):
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaises(AnalysisError):
                    TestRepository(path)

    def test_long_chain_without_recursion(self):
        """Цепь длиннее стандартного лимита рекурсии успешно обрабатывается."""
        class Chain:
            """Репозиторий из 1501 пакета для проверки обхода без рекурсии."""

            def resolve(self, request):
                """Вернуть пакет по идентификатору."""
                return Package(request.name)

            def dependencies(self, package, features, defaults):
                """Каждый пакет зависит от следующего, кроме последнего."""
                number = int(package.name)
                return [Dependency(str(number + 1))] if number < 1500 else []

        graph = Builder(Chain(), 2000).build("0")
        self.assertEqual(len(graph.edges), 1501)
        self.assertFalse(find_cycle(graph))
        self.assertEqual(len(load_order(graph)[0]), 1501)

    def test_feature_unification_revisits_shared_node(self):
        """Поздний запрос feature расширяет уже обработанный общий пакет."""
        class Features:
            """Источники A->B,C; C->B(extra); B(extra)->D."""

            def resolve(self, request):
                """Создать идентификатор узла."""
                return Package(request.name)

            def dependencies(self, package, features, defaults):
                """Активировать новое ребро после объединения features."""
                values = {"A": [Dependency("B"), Dependency("C")],
                          "C": [Dependency("B", features=("extra",))],
                          "B": [Dependency("D")] if "extra" in features else []}
                return values.get(package.name, [])

        graph = Builder(Features(), 10).build("A")
        self.assertIn(Package("D"), graph.edges[Package("B")])
        self.assertEqual(graph.depths[Package("D")], 2)
