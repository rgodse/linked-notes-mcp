"""Local-only graph visualizer for linked-notes-mcp."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .graph import KnowledgeGraph


def _extract_markdown_section(content: str, heading: str) -> str:
    """Extract a markdown section body by heading title."""

    lines = content.splitlines()
    capture = False
    collected: list[str] = []
    needle = heading.strip().lower()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip().lower()
            if capture and current != needle:
                break
            capture = current == needle
            continue
        if capture:
            collected.append(line)
    return "\n".join(collected).strip()


def _extract_repo_evidence(content: str) -> list[str]:
    """Extract repo evidence bullets from note content."""

    section = _extract_markdown_section(content, "Repo Evidence")
    evidence: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            evidence.append(stripped[2:].strip())
    return evidence


def _extract_local_clone(content: str) -> str | None:
    """Extract the local clone path from a note."""

    section = _extract_markdown_section(content, "Local Clone")
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            candidate = stripped[2:].strip().strip("`")
            if candidate:
                return candidate
    return None


def _split_path_and_line_span(raw_path: str) -> tuple[str, int | None, int | None]:
    """Split a repo evidence path into file path and optional line span."""

    cleaned = raw_path.strip().strip("`")
    if ":" not in cleaned:
        return cleaned, None, None
    path_part, suffix = cleaned.rsplit(":", 1)
    if "-" in suffix:
        start_raw, end_raw = suffix.split("-", 1)
    else:
        start_raw, end_raw = suffix, suffix
    try:
        start = int(start_raw)
        end = int(end_raw)
    except ValueError:
        return cleaned, None, None
    return path_part, start, end


def _format_note(note) -> dict[str, Any]:
    """Format a note payload for the browser detail panel."""

    return {
        "id": note.id,
        "title": note.title,
        "tags": note.tags,
        "aliases": note.aliases,
        "path": str(note.path),
        "frontmatter": note.frontmatter,
        "content": note.content,
        "outgoing_links": [
            {"target": link.target, "display": link.display_text, "type": link.link_type}
            for link in note.outgoing_links
        ],
        "repo_evidence": _extract_repo_evidence(note.content),
        "flow_body": _extract_markdown_section(note.content, "Flow"),
        "data_path_body": _extract_markdown_section(note.content, "Data Path"),
        "explicit_relationships": [
            {
                "target": relationship.target,
                "type": relationship.relation_type,
                "source_field": relationship.source_field,
            }
            for relationship in note.explicit_relationships
        ],
    }


def _json_default(value: Any) -> Any:
    """Serialize common Python objects used in note frontmatter."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


class VisualizerHandler(SimpleHTTPRequestHandler):
    """Serve the local browser UI and graph JSON endpoints."""

    def __init__(self, *args, graph: KnowledgeGraph, static_dir: Path, **kwargs):
        self.graph = graph
        self.static_dir = static_dir
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/graph":
            self._serve_graph(parsed.query)
            return
        if parsed.path == "/api/note":
            self._serve_note(parsed.query)
            return
        if parsed.path == "/api/path":
            self._serve_path(parsed.query)
            return
        if parsed.path == "/api/search":
            self._serve_search(parsed.query)
            return
        if parsed.path == "/api/source-preview":
            self._serve_source_preview(parsed.query)
            return
        if parsed.path == "/api/open-file":
            self._serve_open_file(parsed.query)
            return
        if parsed.path == "/health":
            self._write_json({"status": "ok"})
            return

        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, fmt: str, *args) -> None:
        """Keep request logs concise."""

        print(f"[linked-notes-ui] {self.address_string()} - {fmt % args}")

    def _serve_graph(self, query_string: str) -> None:
        params = parse_qs(query_string)
        anchor = params.get("anchor", [None])[0] or None
        query = params.get("query", [None])[0] or None
        depth = _coerce_int(params.get("depth", ["2"])[0], default=2, minimum=1, maximum=5)
        limit = _coerce_int(
            params.get("limit", ["80"])[0], default=80, minimum=10, maximum=250
        )
        relation_types = [item for item in params.get("relation_type", []) if item]
        demo_mode = params.get("demo_mode", ["false"])[0].lower() == "true"
        snapshot = self.graph.visual_graph(
            anchor=anchor,
            depth=depth,
            limit=limit,
            relation_types=relation_types or None,
            query=query,
            demo_mode=demo_mode,
        )
        payload = {
            "anchor": snapshot.anchor,
            "depth": snapshot.depth,
            "nodes": snapshot.nodes,
            "edges": snapshot.edges,
            "available_relation_types": snapshot.available_relation_types,
            "stats": snapshot.stats,
            "demo_mode": demo_mode,
        }
        self._write_json(payload)

    def _serve_note(self, query_string: str) -> None:
        params = parse_qs(query_string)
        identifier = params.get("id", [None])[0]
        if not identifier:
            self._write_json(
                {"error": "Missing `id` query parameter"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        note = self.graph.get_note(identifier)
        if note is None:
            self._write_json(
                {"error": f"Note not found: {identifier}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return
        self._write_json(_format_note(note))

    def _serve_path(self, query_string: str) -> None:
        params = parse_qs(query_string)
        start = params.get("start", [None])[0]
        end = params.get("end", [None])[0]
        if not start or not end:
            self._write_json(
                {"error": "Missing `start` or `end` query parameter"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        path = self.graph.get_path_details(start, end)
        if path is None:
            self._write_json({"path": None, "message": "No path found"})
            return
        self._write_json({"path": path, "length": len(path)})

    def _serve_search(self, query_string: str) -> None:
        params = parse_qs(query_string)
        query = params.get("q", [""])[0].strip()
        limit = _coerce_int(
            params.get("limit", ["10"])[0], default=10, minimum=1, maximum=25
        )
        if not query:
            self._write_json({"results": []})
            return
        results = [
            {
                "id": note.id,
                "title": note.title,
                "summary": note.frontmatter.get("summary", ""),
                "entity_type": note.frontmatter.get("entity_type", ""),
                "project": note.frontmatter.get("project", ""),
            }
            for note in self.graph.search(query, limit=limit)
        ]
        self._write_json({"results": results})

    def _serve_source_preview(self, query_string: str) -> None:
        params = parse_qs(query_string)
        identifier = params.get("id", [None])[0]
        raw_path = params.get("path", [None])[0]
        if not identifier or not raw_path:
            self._write_json(
                {"error": "Missing `id` or `path` query parameter"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        note = self.graph.get_note(identifier)
        if note is None:
            self._write_json(
                {"error": f"Note not found: {identifier}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        resolved, start_line, end_line = self._resolve_repo_evidence_path(note, raw_path)
        if resolved is None:
            self._write_json(
                {"error": f"Could not resolve source path: {raw_path}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        if resolved.is_dir():
            self._write_json(
                {
                    "path": str(resolved),
                    "kind": "directory",
                    "preview": None,
                    "start_line": None,
                }
            )
            return

        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        if start_line is None:
            start_index = 0
            end_index = min(len(lines), 80)
            start_line = 1
        else:
            start_index = max(0, start_line - 6)
            end_index = min(len(lines), max(end_line or start_line, start_line) + 5)
        preview_lines = lines[start_index:end_index]
        self._write_json(
            {
                "path": str(resolved),
                "kind": "file",
                "preview_lines": [
                    {"line_number": start_index + index + 1, "text": line}
                    for index, line in enumerate(preview_lines)
                ],
                "start_line": start_line,
            }
        )

    def _serve_open_file(self, query_string: str) -> None:
        params = parse_qs(query_string)
        identifier = params.get("id", [None])[0]
        raw_path = params.get("path", [None])[0]
        if not identifier or not raw_path:
            self._write_json(
                {"error": "Missing `id` or `path` query parameter"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        note = self.graph.get_note(identifier)
        if note is None:
            self._write_json(
                {"error": f"Note not found: {identifier}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        resolved, _start_line, _end_line = self._resolve_repo_evidence_path(note, raw_path)
        if resolved is None:
            self._write_json(
                {"error": f"Could not resolve source path: {raw_path}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        try:
            self._open_local_path(resolved)
        except Exception as exc:  # noqa: BLE001
            self._write_json(
                {"error": f"Failed to open path: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._write_json({"ok": True, "path": str(resolved)})

    def _resolve_repo_evidence_path(
        self, note, raw_path: str
    ) -> tuple[Path | None, int | None, int | None]:
        """Resolve a repo evidence path from a note into a local file path."""

        cleaned, start_line, end_line = _split_path_and_line_span(raw_path)
        if not cleaned:
            return None, None, None

        repo_root = self._resolve_repo_root(note)
        if repo_root is None:
            return None, None, None

        repo_root_resolved = repo_root.resolve()
        joined = (repo_root / cleaned).resolve()

        try:
            joined.relative_to(repo_root_resolved)
        except ValueError:
            return None, None, None

        if joined.exists():
            return joined, start_line, end_line
        return None, None, None

    def _resolve_repo_root(self, note) -> Path | None:
        """Find the local clone root for a note's repo anchor."""

        current = note
        visited: set[str] = set()
        while current is not None and current.id not in visited:
            visited.add(current.id)
            if str(current.frontmatter.get("entity_type", "")).lower() == "project":
                clone = _extract_local_clone(current.content)
                if clone:
                    candidate = Path(clone)
                    if candidate.exists():
                        return candidate
                return None

            parents = current.frontmatter.get("part_of", [])
            if isinstance(parents, str):
                parents = [parents]
            next_parent = None
            for parent in parents:
                resolved = self.graph.get_note(parent)
                if resolved is not None:
                    next_parent = resolved
                    break
            current = next_parent

        return None

    def _open_local_path(self, path: Path) -> None:
        """Open a local path with the platform-default application."""

        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
            return
        if sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=True)
            return
        if sys.platform.startswith("win"):
            subprocess.run(["cmd", "/c", "start", "", str(path)], check=True)
            return
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    def _write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, indent=2, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)


def _coerce_int(
    value: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse an integer query parameter safely."""

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def run_visualizer(vault_path: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the local-only graph visualizer."""

    graph = KnowledgeGraph(vault_path)
    static_dir = resources.files("linked_notes_mcp").joinpath("static")
    handler = partial(VisualizerHandler, graph=graph, static_dir=Path(static_dir))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"linked-notes-ui running at http://{host}:{port}")
    print(f"Vault: {vault_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down linked-notes-ui")
    finally:
        server.server_close()


def main() -> None:
    """CLI entry point for the local visualizer."""

    parser = argparse.ArgumentParser(
        description="Local-only graph visualizer for linked-notes-mcp"
    )
    parser.add_argument("vault_path", type=Path, help="Path to the markdown vault/folder")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    args = parser.parse_args()

    if not args.vault_path.exists():
        raise SystemExit(f"Vault path does not exist: {args.vault_path}")

    run_visualizer(args.vault_path, host=args.host, port=args.port)
