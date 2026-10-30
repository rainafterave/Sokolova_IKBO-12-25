"""Выбор зависимостей с учетом default и запрошенных features Cargo."""

from collections import deque

from .models import Dependency


def active_dependencies(record, requested, defaults):
    """Раскрыть возможности без рекурсии и выбрать normal/build зависимости."""
    rows = [row for row in record["deps"]
            if row.get("kind") in (None, "normal", "build")]
    features = dict(record.get("features", {}))
    features.update(record.get("features2", {}))
    active = {row["name"] for row in rows if not row.get("optional", False)}
    initial = set(requested) | ({"default"} if defaults else set())
    pending = deque(sorted(initial))
    seen, child_features, weak = set(), {}, []
    while pending:
        item = pending.popleft()
        if item in seen:
            continue
        seen.add(item)
        if item in features:
            pending.extend(features[item])
        else:
            _activate(item, rows, active, child_features, weak)
    for alias, feature in weak:
        if alias in active:
            child_features.setdefault(alias, set()).add(feature)
    return _dependencies(rows, active, child_features)


def _activate(item, rows, active, child_features, weak):
    """Обработать dep:alias, alias/feature и слабое alias?/feature."""
    if item.startswith("dep:"):
        active.add(item[4:])
    elif "/" in item:
        alias, feature = item.split("/", 1)
        if alias.endswith("?"):
            weak.append((alias[:-1], feature))
        else:
            active.add(alias)
            child_features.setdefault(alias, set()).add(feature)
    elif any(row["name"] == item and row.get("optional") for row in rows):
        active.add(item)


def _dependencies(rows, active, child_features):
    """Собрать запросы реальных имен, версий и дочерних features."""
    result = []
    for row in rows:
        alias = row["name"]
        if alias not in active:
            continue
        features = set(row.get("features", []))
        features |= child_features.get(alias, set())
        result.append(Dependency(row.get("package") or alias, row["req"],
                                 tuple(sorted(features)),
                                 row.get("default_features", True)))
    return result
