"""Tool registry: merges HANDLERS and TOOL_DEFS from all tool modules."""

from typing import Callable

from mcp.types import Tool

from ..graph import KnowledgeGraph
from .graph_query import HANDLERS as _GQ, TOOL_DEFS as _GQ_TOOLS
from .maintenance import HANDLERS as _MT, TOOL_DEFS as _MT_TOOLS
from .note_write import HANDLERS as _NW, TOOL_DEFS as _NW_TOOLS
from .session import HANDLERS as _SS, TOOL_DEFS as _SS_TOOLS

HANDLERS: dict[str, Callable[[dict, KnowledgeGraph], str]] = {
    **_GQ,
    **_NW,
    **_MT,
    **_SS,
}

TOOL_DEFS: list[Tool] = [
    *_GQ_TOOLS,
    *_NW_TOOLS,
    *_MT_TOOLS,
    *_SS_TOOLS,
]
