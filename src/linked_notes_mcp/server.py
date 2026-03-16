"""
MCP Server for linked-notes-mcp.

Exposes tools for navigating markdown knowledge graphs via the Model Context Protocol.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from .graph import KnowledgeGraph
from .tools import HANDLERS, TOOL_DEFS
from .tools.helpers import (
    _extract_excerpt,
    _load_followups as _load_followups_impl,
    _save_followups as _save_followups_impl,
)

# Global graph instance
_graph: KnowledgeGraph | None = None


def get_graph() -> KnowledgeGraph:
    """Get the global graph instance."""
    if _graph is None:
        raise RuntimeError("Graph not initialized. Call init_graph first.")
    return _graph


def init_graph(vault_path: Path) -> KnowledgeGraph:
    """Initialize the global graph."""
    global _graph
    _graph = KnowledgeGraph(vault_path)
    return _graph


# Backwards-compatible re-exports used by tests
def _load_followups() -> list[dict]:
    return _load_followups_impl(get_graph())


def _save_followups(followups: list[dict]) -> None:
    _save_followups_impl(get_graph(), followups)


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Handle a tool call and return the result as JSON."""
    graph = get_graph()
    handler = HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return handler(arguments, graph)


def create_server(vault_path: Path) -> Server:
    """Create and configure the MCP server."""
    server = Server("linked-notes-mcp")

    # Initialize the graph
    init_graph(vault_path)

    @server.list_tools()
    async def list_tools():
        return TOOL_DEFS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]):
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=result)]

    return server


async def run_server(vault_path: Path):
    """Run the MCP server."""
    server = create_server(vault_path)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP server for markdown knowledge graphs")
    parser.add_argument("vault_path", type=Path, help="Path to the markdown vault/folder")
    args = parser.parse_args()

    if not args.vault_path.exists():
        print(f"Error: Vault path does not exist: {args.vault_path}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run_server(args.vault_path))


if __name__ == "__main__":
    main()
