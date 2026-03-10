"""
linked-notes-mcp: MCP server for navigating markdown knowledge graphs.

Point it at any folder of markdown files with [[wikilinks]] and Claude
can traverse your knowledge graph.
"""

from .graph import KnowledgeGraph
from .parser import Note, Link, parse_note
from .server import create_server, run_server

__version__ = "0.1.0"
__all__ = [
    "KnowledgeGraph",
    "Note", 
    "Link",
    "parse_note",
    "create_server",
    "run_server",
]
