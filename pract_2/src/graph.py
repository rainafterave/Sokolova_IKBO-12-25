"""Обход зависимостей BFS и операции над графом без рекурсии."""

import heapq
from collections import deque
from dataclasses import dataclass, field

from .models import Dependency


@dataclass
class Graph:
    """Ориентированные ребра: пакет -> его непосредственные зависимости."""

    root: object
    edges: dict = field(default_factory=dict)
    depths: dict = field(default_factory=dict)


class Builder:
    """Обрабатывать очередь BFS и объединять features общих зависимостей."""

    def __init__(self, repository, max_depth, exclude=""):
        """Запомнить источник, границу глубины и подстроку исключения."""
        self.repository = repository
        self.max_depth, self.exclude = max_depth, exclude
        self.queue = deque()
        self.requests, self.processed = {}, {}

    def build(self, name):
        """Построить граф; каждая вершина содержит конкретную версию."""
        package, marker, version = name.partition("@")
        request = Dependency(package, "=" + version if marker else "*")
        root = self.repository.resolve(request)
        self.graph = Graph(root)
        self._request(root, request, 0)
        while self.queue:
            parent = self.queue.popleft()
            features, defaults = self.requests[parent]
            state = (frozenset(features), defaults, self.graph.depths[parent])
            if self.processed.get(parent) == state:
                continue
            self.processed[parent] = state
            if self.graph.depths[parent] < self.max_depth:
                self._expand(parent, features, defaults)
        return self.graph

    def _request(self, package, request, depth):
        """Поставить пакет в очередь при новом пути или новом feature."""
        is_new = package not in self.requests
        features, defaults = self.requests.get(package, (set(), False))
        merged = features | set(request.features)
        default = defaults or request.default_features
        previous_depth = self.graph.depths.get(package, depth)
        changed = (merged != features or default != defaults
                   or depth < previous_depth)
        self.requests[package] = (merged, default)
        self.graph.edges.setdefault(package, set())
        self.graph.depths[package] = min(depth, previous_depth)
        if is_new or changed:
            self.queue.append(package)

    def _expand(self, parent, features, defaults):
        """Добавить ребра к подходящим зависимостям и запросить их обработку."""
        requests = self.repository.dependencies(parent, features, defaults)
        for request in sorted(requests, key=lambda item: (item.name,
                                                        item.requirement)):
            if self.exclude and self.exclude in request.name:
                continue
            child = self.repository.resolve(request)
            self.graph.edges[parent].add(child)
            self._request(child, request, self.graph.depths[parent] + 1)


def load_order(graph):
    """Алгоритм Кана: сначала зависимости, затем использующие их пакеты."""
    remaining = {node: len(children) for node, children in graph.edges.items()}
    parents = {node: set() for node in graph.edges}
    for parent, children in graph.edges.items():
        for child in children:
            parents[child].add(parent)
    ready = [node for node, count in remaining.items() if count == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for parent in sorted(parents[node]):
            remaining[parent] -= 1
            if remaining[parent] == 0:
                heapq.heappush(ready, parent)
    return result, sorted(node for node, count in remaining.items() if count)


def find_cycle(graph):
    """Найти один цикл итеративным DFS, сохранив точную цепочку вершин."""
    done = set()
    for start in sorted(graph.edges):
        if start in done:
            continue
        path, active = [start], {start: 0}
        stack = [(start, iter(sorted(graph.edges[start])))]
        while stack:
            parent, children = stack[-1]
            child = next(children, None)
            if child is None:
                stack.pop()
                done.add(parent)
                active.pop(parent)
                path.pop()
            elif child in active:
                return path[active[child]:] + [child]
            elif child not in done:
                active[child] = len(path)
                path.append(child)
                stack.append((child, iter(sorted(graph.edges[child]))))
    return []
