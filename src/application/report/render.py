"""Layer 4: Render — entity report Jinja2 rendering."""

from __future__ import annotations


def group_clusters(topics: list) -> dict[str, list]:
    result: dict[str, list] = {}
    for t in topics:
        layer = getattr(t, "layer", "AI应用")
        result.setdefault(layer, []).append(t)
    return result
