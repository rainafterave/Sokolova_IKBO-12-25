"""CLI-инструмент анализа зависимостей Cargo, вариант 23."""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PROJECT_ROOT, read_config
from src.graph import Builder, find_cycle, load_order
from src.models import AnalysisError
from src.plantuml import plantuml, render_svg, save_text
from src.registry import CargoRegistry
from src.test_repository import TestRepository

FINAL_STAGE = 5


def parse_args(argv=None):
    """Выбрать INI, демонстрационный этап и выходные файлы."""
    parser = argparse.ArgumentParser(description="Граф зависимостей Cargo")
    parser.add_argument("--config", type=Path,
                        default=PROJECT_ROOT / "configs/test.ini",
                        help="INI с настройками анализа")
    parser.add_argument("--stage", type=int, choices=range(1, FINAL_STAGE + 1),
                        default=FINAL_STAGE, help="этап 1-5; по умолчанию 5")
    parser.add_argument("--output", type=Path, help="сохранить PlantUML в файл")
    parser.add_argument("--svg", type=Path,
                        help="SVG через сервер PlantUML (нужна сеть)")
    args = parser.parse_args(argv)
    if args.stage != FINAL_STAGE and (args.output or args.svg):
        parser.error("--output и --svg используются на этапе 5")
    return args


def analyze(config, stage):
    """Выбрать источник и построить граф BFS с заданными ограничениями."""
    source = TestRepository(config.repository) if config.test_mode else \
        CargoRegistry(config.repository)
    depth = min(1, config.max_depth) if stage == 2 else config.max_depth
    return Builder(source, depth, config.exclude).build(config.package)


def describe_graph(graph):
    """Вывести вершины и ребра в порядке уровней BFS, включая листья."""
    for node in sorted(graph.edges, key=lambda n: (graph.depths[n], n)):
        children = ", ".join(child.label for child in sorted(graph.edges[node]))
        print(f"[{graph.depths[node]}] {node.label} -> {children or '-'}")
    cycle = find_cycle(graph)
    if cycle:
        print("Цикл: " + " -> ".join(node.label for node in cycle))


def show_result(graph, args):
    """Показать результат, предусмотренный выбранным этапом."""
    if args.stage == 2:
        children = sorted(graph.edges[graph.root])
        print("\n".join(node.label for node in children) or "Нет зависимостей")
    elif args.stage == 3:
        describe_graph(graph)
    elif args.stage == 4:
        order, blocked = load_order(graph)
        if blocked:
            cycle = " -> ".join(node.label for node in find_cycle(graph))
            raise AnalysisError(f"порядок загрузки невозможен, цикл: {cycle}")
        print(" -> ".join(node.label for node in order))
    else:
        text = plantuml(graph)
        print(text, end="")
        if args.output:
            save_text(args.output, text)
        if args.svg:
            render_svg(text, args.svg)


def main(argv=None):
    """Вернуть 0 при успехе, 1 при ошибке данных и 2 при неверном CLI."""
    args = parse_args(argv)
    try:
        config = read_config(args.config)
        if args.stage == 1:
            print("\n".join(config.lines()))
        else:
            show_result(analyze(config, args.stage), args)
    except (AnalysisError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
