from __future__ import annotations

from pathlib import Path
from typing import Any
import json

CATALOG_ROOT = Path(__file__).parent / "catalogs" / "domains"

def load_domain_catalogs(root: Path | None = None) -> list[dict[str, Any]]:
    active_root = root or CATALOG_ROOT
    if not active_root.exists():
        return []
    nodes: list[dict[str, Any]] = []
    for path in sorted(path for path in active_root.glob("*.json") if not path.name.startswith("_")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            nodes.extend(data)
        elif isinstance(data, dict):
            nodes.append(data)
        else:
            raise ValueError(f"Unsupported catalog root in {path.name}")
    return nodes

def walk_nodes(nodes: list[dict[str, Any]], path: tuple[str, ...] = ()):
    for node in nodes:
        name = str(node.get("name", "")).strip()
        if not name:
            continue
        current_path = (*path, name)
        yield node, current_path
        children = node.get("children", [])
        if isinstance(children, list):
            yield from walk_nodes(children, current_path)

def _search_text(node: dict[str, Any], path: tuple[str, ...]) -> str:
    values: list[str] = [*path, str(node.get("description", ""))]
    for key in ("aliases", "tags"):
        raw = node.get(key, [])
        if isinstance(raw, str):
            values.append(raw)
        elif isinstance(raw, list):
            values.extend(str(item) for item in raw)
    return " ".join(values).casefold()

def search_catalog(query: str, nodes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    from ranked_catalog_search import ranked_search_catalog
    return ranked_search_catalog(query, nodes=nodes)

def validate_catalog(nodes: list[dict[str, Any]]) -> tuple[int, int]:
    total = 0
    leaves = 0
    seen: set[str] = set()
    for node, _ in walk_nodes(nodes):
        node_id = str(node.get("id", "")).strip()
        if not node_id or not node.get("name"):
            raise ValueError("Every node needs non-empty id and name")
        if node_id in seen:
            raise ValueError(f"Duplicate node id: {node_id}")
        seen.add(node_id)
        total += 1
        if not node.get("children"):
            leaves += 1
    return total, leaves

