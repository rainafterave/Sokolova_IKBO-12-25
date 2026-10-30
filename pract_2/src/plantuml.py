"""Преобразование графа в текст PlantUML и необязательную SVG-картинку."""

from pathlib import Path

from .graph import find_cycle
from .models import AnalysisError
from .registry import fetch_text


def plantuml(graph):
    """Получить воспроизводимую диаграмму компонентов с безопасными именами."""
    nodes = sorted(graph.edges)
    aliases = {node: f"N{index}" for index, node in enumerate(nodes)}
    cycle = find_cycle(graph)
    cycle_edges = set(zip(cycle, cycle[1:]))
    lines = ["@startuml", "left to right direction",
             "skinparam componentStyle rectangle", "skinparam shadowing false",
             "skinparam defaultFontName Monospaced",
             "skinparam defaultFontSize 13"]
    for node in nodes:
        label = node.label.replace("\\", "\\\\").replace('"', '\\"')
        color = " #D6EAF8" if node == graph.root else ""
        lines.append(f'component "{label}" as {aliases[node]}{color}')
    for parent in nodes:
        for child in sorted(graph.edges[parent]):
            arrow = "-[#red]->" if (parent, child) in cycle_edges else "-->"
            lines.append(f"{aliases[parent]} {arrow} {aliases[child]}")
    lines.extend(["legend bottom", "Arrow: package -> dependency", "endlegend",
                  "@enduml"])
    return "\n".join(lines) + "\n"


def save_text(path, text):
    """Сохранить текстовый результат, создав папку при необходимости."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise AnalysisError(f"не удалось сохранить {path}: {error}") from error


def render_svg(text, path):
    """Отрисовать публичный граф официальным сервером PlantUML по запросу."""
    url = "https://www.plantuml.com/plantuml/svg/~h" + text.encode().hex()
    svg = fetch_text(url)
    if "<svg" not in svg or "Syntax Error" in svg:
        raise AnalysisError("PlantUML не вернул корректную SVG-диаграмму")
    save_text(path, svg)
