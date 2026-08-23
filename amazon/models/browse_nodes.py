"""Browse Node Models for Amazon API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from amazon.models.common import APIErrorDetail, BaseResponse


@dataclass
class BrowseNodeAncestor:
    """Ancestor browse node in category hierarchy."""

    id: str
    display_name: str
    context_free_name: str | None = None
    ancestor: BrowseNodeAncestor | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BrowseNodeAncestor | None:
        if not data:
            return None

        anc_data = data.get("Ancestor") or data.get("ancestor")
        parent_ancestor = cls.from_dict(anc_data) if anc_data else None

        return cls(
            id=str(data.get("Id") or data.get("id") or ""),
            display_name=str(data.get("DisplayName") or data.get("displayName") or ""),
            context_free_name=data.get("ContextFreeName") or data.get("contextFreeName"),
            ancestor=parent_ancestor,
            raw=data,
        )


@dataclass
class BrowseNodeChild:
    """Child browse node in category hierarchy."""

    id: str
    display_name: str
    context_free_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowseNodeChild:
        return cls(
            id=str(data.get("Id") or data.get("id") or ""),
            display_name=str(data.get("DisplayName") or data.get("displayName") or ""),
            context_free_name=data.get("ContextFreeName") or data.get("contextFreeName"),
            raw=data,
        )


@dataclass
class BrowseNode:
    """Amazon Browse Node (Product Category)."""

    id: str
    display_name: str
    context_free_name: str | None = None
    is_root: bool = False
    ancestor: BrowseNodeAncestor | None = None
    children: list[BrowseNodeChild] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowseNode:
        anc_data = data.get("Ancestor") or data.get("ancestor")
        ancestor = BrowseNodeAncestor.from_dict(anc_data) if anc_data else None

        children_data = data.get("Children") or data.get("children") or []
        children = [BrowseNodeChild.from_dict(c) for c in children_data if isinstance(c, dict)]

        return cls(
            id=str(data.get("Id") or data.get("id") or ""),
            display_name=str(data.get("DisplayName") or data.get("displayName") or ""),
            context_free_name=data.get("ContextFreeName") or data.get("contextFreeName"),
            is_root=bool(data.get("IsRoot") or data.get("isRoot")),
            ancestor=ancestor,
            children=children,
            raw=data,
        )


@dataclass
class BrowseNodesResult(BaseResponse):
    """Response wrapper for get_browse_nodes operation."""

    browse_nodes: list[BrowseNode] = field(default_factory=list)

    @property
    def browse_node(self) -> BrowseNode | None:
        """Return the first browse node or None if empty."""
        return self.browse_nodes[0] if self.browse_nodes else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowseNodesResult:
        nodes_result = data.get("BrowseNodesResult") or data.get("browseNodesResult") or data
        raw_nodes = nodes_result.get("BrowseNodes") or nodes_result.get("browseNodes") or []
        nodes = [BrowseNode.from_dict(node) for node in raw_nodes if isinstance(node, dict)]

        errors_raw = data.get("Errors") or data.get("errors") or []
        errors = [APIErrorDetail.from_dict(e) for e in errors_raw]

        return cls(raw=data, errors=errors, browse_nodes=nodes)
