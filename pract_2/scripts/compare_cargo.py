"""Сравнить готовый анализатор с Cargo; Cargo используется только в проверке."""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PROJECT_ROOT, read_config
from src.graph import Graph, load_order
from src.main import analyze
from src.models import Package
from src.plantuml import save_text


def command(cargo, arguments, environment):
    """Запустить штатный Cargo только для независимого сравнения результатов."""
    result = subprocess.run([cargo, *arguments], env=environment,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def cargo_graph(metadata, name, version):
    """Выделить подграф выбранной зависимости из штатного cargo metadata."""
    packages = {item["id"]: Package(item["name"], item["version"])
                for item in metadata["packages"]}
    root_id = next(key for key, value in packages.items()
                   if value == Package(name, version))
    nodes = {item["id"]: item for item in metadata["resolve"]["nodes"]}
    graph = Graph(packages[root_id])
    pending, seen = deque([root_id]), set()
    while pending:
        current = pending.popleft()
        if current in seen:
            continue
        seen.add(current)
        children = [item["pkg"] for item in nodes[current]["deps"]
                    if any(kind["kind"] in (None, "build")
                           for kind in item["dep_kinds"])]
        graph.edges[packages[current]] = {packages[item] for item in children}
        pending.extend(children)
    return graph


def edge_set(graph):
    """Получить сравнимое множество подписанных ребер."""
    return {(parent.label, child.label)
            for parent, children in graph.edges.items() for child in children}


def explain(name, ours, reference, download_text):
    """Описать фактическое совпадение/расхождения и порядок зависимостей."""
    own_edges, cargo_edges = edge_set(ours), edge_set(reference)
    same = set(ours.edges) == set(reference.edges) and own_edges == cargo_edges
    order, blocked = load_order(ours)
    positions = {node: index for index, node in enumerate(order)}
    valid = not blocked and set(reference.edges) <= positions.keys()
    valid = valid and all(positions[child] < positions[parent]
                          for parent, children in reference.edges.items()
                          for child in children)
    downloaded = re.findall(r"Downloaded ([\w-]+) v([^\s]+)", download_text)
    lines = [f"## {name}", "", f"Наш граф: {len(ours.edges)} пакетов, "
             f"{len(own_edges)} ребер. Cargo: {len(reference.edges)} пакетов, "
             f"{len(cargo_edges)} ребер.", "",
             "Совпадение вершин и ребер: " + ("да." if same else "нет."), "",
             "Наш порядок: " + " -> ".join(node.label for node in order), "",
             "Порядок соблюдает ребра Cargo: " + ("да." if valid else "нет."),
             "", "Наблюдавшийся порядок скачивания Cargo: " +
             (", ".join(f"{n} v{v}" for n, v in downloaded)
              or "все архивы уже находились в кеше"), ""]
    for title, values in (("Только у нас", own_edges - cargo_edges),
                          ("Только у Cargo", cargo_edges - own_edges)):
        if values:
            lines.extend([title + ":", ""] +
                         [f"- {a} -> {b}" for a, b in sorted(values)] + [""])
    return lines


def compare_one(name, cargo, environment, output, directory):
    """Создать временный Cargo-проект с одной фиксированной зависимостью."""
    config = read_config(PROJECT_ROOT / f"configs/{name}.ini")
    crate, version = config.package.split("@")
    project = Path(directory) / name
    (project / "src").mkdir(parents=True)
    manifest = project / "Cargo.toml"
    manifest.write_text('[package]\nname="dependency-check"\nversion="0.0.0"\n'
                        'edition="2021"\n[workspace]\n[dependencies]\n'
                        f'{crate}="={version}"\n', encoding="utf-8")
    (project / "src/lib.rs").write_text("", encoding="utf-8")
    common = ["--manifest-path", str(manifest)]
    raw = command(cargo, ["metadata", "--format-version", "1", *common],
                  environment)
    reference = cargo_graph(json.loads(raw.stdout), crate, version)
    tree = command(cargo, ["tree", *common, "--target", "all", "--edges",
                          "normal,build", "--charset", "ascii", "-p",
                          f"{crate}@{version}"], environment)
    save_text(output / f"{name}-cargo-tree.txt", tree.stdout)
    save_text(output / f"{name}-cargo-download.txt", raw.stderr)
    ours = analyze(config, 5)
    print(f"Compared {crate}: own={len(ours.edges)}, "
          f"Cargo={len(reference.edges)}")
    return explain(config.package, ours, reference, raw.stderr)


def main():
    """Сохранить честный отчет сравнения трех пакетов и вывод cargo tree."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cargo", default="cargo", help="путь к cargo")
    parser.add_argument("--output", type=Path,
                        default=PROJECT_ROOT / "examples")
    args = parser.parse_args()
    environment = os.environ.copy()
    cache = PROJECT_ROOT / "tmp/cargo-home"
    environment.update(CARGO_HOME=str(cache), CARGO_TERM_COLOR="never")
    sibling = Path(args.cargo).resolve().with_name("rustc.exe")
    if sibling.is_file():
        environment["RUSTC"] = str(sibling)
    work = PROJECT_ROOT / "tmp"
    work.mkdir(exist_ok=True)
    try:
        version = command(args.cargo, ["--version"], environment).stdout.strip()
        lines = ["# Сравнение с Cargo", "", version, "",
                 "Дата: " + datetime.now(timezone.utc).isoformat(), ""]
        with tempfile.TemporaryDirectory(dir=work) as directory:
            for name in ("csv", "regex", "serde_json"):
                lines.extend(compare_one(name, args.cargo, environment,
                                         args.output, directory))
        lines.extend(_notes())
        save_text(args.output / "comparison.md", "\n".join(lines))
    except (OSError, ValueError, RuntimeError,
            subprocess.TimeoutExpired) as error:
        print(f"Сравнение не выполнено: {error}", file=sys.stderr)
        return 1
    return 0


def _notes():
    """Объяснить разные смыслы порядка и границы самостоятельного резолвера."""
    return ["## Как понимать результаты", "",
            "Сравниваются normal/build-зависимости для всех платформ. "
            "Включены default features и запрошенные дочерние возможности. "
            "Dev-зависимости исключены.", "",
            "Наш порядок ставит зависимости раньше использующих их пакетов. "
            "Cargo tree показывает дерево от корня; это другой порядок показа. "
            "Реальное скачивание Cargo зависит от сети и кеша и не обязано "
            "совпадать с топологическим порядком. Независимые пакеты допускают "
            "несколько правильных порядков обработки.", "",
            "У программы свой упрощенный выбор максимальной подходящей версии. "
            "Она не воспроизводит весь решатель Cargo, Cargo.lock, ограничения "
            "rust-version и resolver v2/v3. На сложных пакетах возможны "
            "отличия версий и features; отличающиеся ребра показаны выше.",
            ""]


if __name__ == "__main__":
    raise SystemExit(main())
