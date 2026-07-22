"""Sync knowledge graph nodes into facts_json fields."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.knowledge.graph.schema import KnowledgeGraph, NodeType


def sync_facts_from_graph(
    facts: dict[str, Any] | None,
    graph: KnowledgeGraph,
    *,
    overwrite_lists: bool = True,
    fill_icp_if_empty: bool = True,
) -> dict[str, Any]:
    """
    Merge graph nodes into facts_json.
    Lists (products / pain_points / differentiators) are replaced when overwrite_lists
    and the graph has at least one matching node; otherwise existing values are kept.
    """
    out = dict(facts or {})

    products = _labels_for(graph, NodeType.product)
    pains = _labels_for(graph, NodeType.pain)
    diffs = _labels_for(graph, NodeType.differentiator)
    audiences = _labels_for(graph, NodeType.audience)

    if overwrite_lists and products:
        out["products"] = products
    else:
        out.setdefault("products", list(out.get("products") or []) if isinstance(out.get("products"), list) else [])

    if overwrite_lists and pains:
        out["pain_points"] = pains
    else:
        out.setdefault(
            "pain_points",
            list(out.get("pain_points") or []) if isinstance(out.get("pain_points"), list) else [],
        )

    if overwrite_lists and diffs:
        out["differentiators"] = diffs
    else:
        out.setdefault(
            "differentiators",
            list(out.get("differentiators") or []) if isinstance(out.get("differentiators"), list) else [],
        )

    if fill_icp_if_empty and audiences:
        current_icp = str(out.get("icp") or "").strip()
        if not current_icp:
            out["icp"] = audiences[0]

    out.setdefault("industry", str(out.get("industry") or "").strip())
    return out


def _labels_for(graph: KnowledgeGraph, node_type: NodeType) -> list[str]:
    labels: list[str] = []
    for node in graph.nodes:
        if node.type != node_type:
            continue
        label = node.label.strip()
        if label and label not in labels:
            labels.append(label)
    return labels
