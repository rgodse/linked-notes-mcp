"""
Knowledge graph built from markdown notes.

Uses NetworkX for graph operations. Supports:
- Building graph from notes
- Traversing connections
- Finding paths between notes
- Typed relationships from note frontmatter
- Graph-first context retrieval
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

import networkx as nx
import yaml

from .parser import (
    RELATIONSHIP_FIELDS,
    Note,
    Relationship,
    is_markdown_file,
    normalize_id,
    parse_note,
)


@dataclass
class GraphStats:
    """Statistics about the knowledge graph."""

    total_notes: int
    total_links: int
    total_tags: int
    orphan_notes: int
    most_connected: list[tuple[str, int]]
    total_relationships: int
    relationship_counts: list[tuple[str, int]]


@dataclass
class LintIssue:
    """Quality issue found in the memory graph."""

    note_id: str
    severity: str
    issue_type: str
    message: str


@dataclass
class RelationshipSuggestion:
    """Suggested relationship between two notes."""

    source_id: str
    target_id: str
    suggested_type: str
    score: int
    reasons: list[str]


@dataclass
class NoteHealth:
    """Health score for a memory node."""

    note_id: str
    score: int
    max_score: int
    issues: list[str]


@dataclass
class TraversalResult:
    """Result of traversing the graph from a starting node."""

    start_id: str
    depth: int
    nodes: list[str]
    edges: list[tuple[str, str]]


class KnowledgeGraph:
    """A knowledge graph built from markdown notes."""

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path
        self.graph = nx.DiGraph()
        self.notes: dict[str, Note] = {}
        self._tag_index: dict[str, set[str]] = {}
        self._title_index: dict[str, str] = {}
        self._alias_index: dict[str, str] = {}

        if vault_path:
            self.rebuild()

    def rebuild(self, vault_path: Optional[Path] = None) -> int:
        """Rebuild the graph from the vault directory."""

        if vault_path:
            self.vault_path = vault_path

        if not self.vault_path:
            raise ValueError("No vault path specified")

        self.graph.clear()
        self.notes.clear()
        self._tag_index.clear()
        self._title_index.clear()
        self._alias_index.clear()

        vault = Path(self.vault_path)
        if not vault.exists():
            raise ValueError(f"Vault path does not exist: {vault}")

        for md_file in self._find_markdown_files(vault):
            try:
                note = parse_note(md_file)
                self._add_note(note)
            except Exception as exc:
                print(f"Warning: Failed to parse {md_file}: {exc}")

        for note_id, note in self.notes.items():
            for link in note.outgoing_links:
                if link.target in self.notes:
                    self._add_edge(
                        note_id,
                        link.target,
                        relationship_type=link.link_type,
                        evidence="inline_link",
                        display_text=link.display_text,
                        line_number=link.line_number,
                    )

            for relationship in note.explicit_relationships:
                target_id = self._resolve_relationship_target(relationship)
                if target_id is not None:
                    self._add_edge(
                        note_id,
                        target_id,
                        relationship_type=relationship.relation_type,
                        evidence="frontmatter",
                        source_field=relationship.source_field,
                    )

        return len(self.notes)

    def _find_markdown_files(self, directory: Path) -> Iterator[Path]:
        """Recursively find all markdown files in directory."""

        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                yield from self._find_markdown_files(item)
            elif is_markdown_file(item):
                yield item

    def _resolve_note_id(self, identifier: str) -> Optional[str]:
        """Resolve a note ID or title to a note ID."""

        normalized = normalize_id(identifier)
        if normalized in self.notes:
            return normalized
        lower_id = identifier.lower()
        if lower_id in self._title_index:
            return self._title_index[lower_id]
        if lower_id in self._alias_index:
            return self._alias_index[lower_id]
        return None

    def _add_note(self, note: Note) -> None:
        """Add a note to the graph."""

        self.notes[note.id] = note
        self.graph.add_node(note.id)

        title_key = note.title.lower()
        if title_key in self._title_index:
            print(
                f"Warning: title collision '{note.title}' — keeping "
                f"'{self._title_index[title_key]}', ignoring '{note.id}'"
            )
        else:
            self._title_index[title_key] = note.id

        for alias in note.aliases:
            alias_key = alias.lower()
            if alias_key not in self._alias_index:
                self._alias_index[alias_key] = note.id

        for tag in note.tags:
            self._tag_index.setdefault(tag, set()).add(note.id)

    def _resolve_relationship_target(self, relationship: Relationship) -> Optional[str]:
        """Resolve a relationship target by title first, then by normalized ID."""

        resolved = self._resolve_note_id(relationship.raw_target)
        if resolved is not None:
            return resolved
        if relationship.target in self.notes:
            return relationship.target
        return None

    def _add_edge(
        self,
        source: str,
        target: str,
        relationship_type: str,
        **metadata: Any,
    ) -> None:
        """Add or enrich an edge with relationship metadata."""

        if self.graph.has_edge(source, target):
            edge = self.graph[source][target]
            edge.setdefault("relationship_types", [])
            if relationship_type not in edge["relationship_types"]:
                edge["relationship_types"].append(relationship_type)
            edge.setdefault("relationships", []).append(
                {"type": relationship_type, **metadata}
            )
            return

        self.graph.add_edge(
            source,
            target,
            relationship_types=[relationship_type],
            relationships=[{"type": relationship_type, **metadata}],
        )

    def get_note(self, identifier: str) -> Optional[Note]:
        """Get a note by ID or title."""

        resolved = self._resolve_note_id(identifier)
        if resolved is None:
            return None
        return self.notes[resolved]

    def get_links(self, note_id: str, direction: str = "both") -> dict[str, list[str]]:
        """Get neighboring note IDs for a note."""

        resolved = self._resolve_note_id(note_id)
        if resolved is None:
            return {"outgoing": [], "incoming": []}

        result = {}
        if direction in ("outgoing", "both"):
            result["outgoing"] = list(self.graph.successors(resolved))
        if direction in ("incoming", "both"):
            result["incoming"] = list(self.graph.predecessors(resolved))
        return result

    def get_relationships(
        self,
        identifier: str,
        direction: str = "both",
        relation_type: Optional[str] = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return typed relationship metadata for a note."""

        resolved = self._resolve_note_id(identifier)
        if resolved is None:
            return {"outgoing": [], "incoming": []}

        result = {"outgoing": [], "incoming": []}

        if direction in ("outgoing", "both"):
            for target in self.graph.successors(resolved):
                result["outgoing"].extend(
                    self._relationship_records(resolved, target, relation_type)
                )

        if direction in ("incoming", "both"):
            for source in self.graph.predecessors(resolved):
                result["incoming"].extend(
                    self._relationship_records(source, resolved, relation_type)
                )

        return result

    def _relationship_records(
        self,
        source: str,
        target: str,
        relation_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Expand edge metadata into relationship records."""

        edge = self.graph[source][target]
        records = []
        for relation in edge.get("relationships", []):
            if relation_type and relation["type"] != relation_type:
                continue
            records.append(
                {
                    "from": source,
                    "to": target,
                    "type": relation["type"],
                    **{k: v for k, v in relation.items() if k != "type"},
                }
            )
        return records

    def traverse(
        self,
        start_id: str,
        depth: int = 2,
        direction: str = "both",
        relation_types: Optional[list[str]] = None,
    ) -> TraversalResult:
        """Traverse the graph from a starting note."""

        resolved = self._resolve_note_id(start_id)
        if resolved is None:
            return TraversalResult(start_id, depth, [], [])

        allowed = set(relation_types or [])
        visited = {resolved}
        edges: list[tuple[str, str]] = []
        frontier = {resolved}

        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                neighbors = set()
                if direction in ("outgoing", "both"):
                    neighbors.update(self.graph.successors(node))
                if direction in ("incoming", "both"):
                    neighbors.update(self.graph.predecessors(node))

                for neighbor in neighbors:
                    if direction in ("outgoing", "both") and self.graph.has_edge(node, neighbor):
                        if self._edge_matches(node, neighbor, allowed):
                            edges.append((node, neighbor))
                            if neighbor not in visited:
                                visited.add(neighbor)
                                next_frontier.add(neighbor)

                    if direction in ("incoming", "both") and self.graph.has_edge(neighbor, node):
                        if self._edge_matches(neighbor, node, allowed):
                            edges.append((neighbor, node))
                            if neighbor not in visited:
                                visited.add(neighbor)
                                next_frontier.add(neighbor)

            frontier = next_frontier
            if not frontier:
                break

        return TraversalResult(
            start_id=resolved,
            depth=depth,
            nodes=list(visited),
            edges=list(dict.fromkeys(edges)),
        )

    def _edge_matches(self, source: str, target: str, allowed: set[str]) -> bool:
        """Check whether an edge matches the requested relationship types."""

        if not allowed:
            return True
        edge_types = set(self.graph[source][target].get("relationship_types", []))
        return bool(edge_types.intersection(allowed))

    def _note_priority(self, note: Note) -> int:
        """Score structured priority metadata for retrieval."""

        score = 0
        importance = str(note.frontmatter.get("importance", "")).lower()
        if importance == "high":
            score += 4
        elif importance == "medium":
            score += 2

        confidence_raw = note.frontmatter.get("confidence")
        try:
            confidence = float(confidence_raw)
            if confidence >= 0.8:
                score += 3
            elif confidence >= 0.5:
                score += 1
        except (TypeError, ValueError):
            pass

        last_reviewed_raw = note.frontmatter.get("last_reviewed")
        if last_reviewed_raw:
            try:
                reviewed = datetime.fromisoformat(str(last_reviewed_raw))
                now = datetime.now(reviewed.tzinfo) if reviewed.tzinfo else datetime.now()
                age_days = max(0, (now - reviewed).days)
                if age_days <= 14:
                    score += 2
                elif age_days <= 60:
                    score += 1
            except (TypeError, ValueError):
                pass

        return score

    def find_path(self, start_id: str, end_id: str) -> Optional[list[str]]:
        """Find shortest path between two notes."""

        start = self._resolve_note_id(start_id)
        end = self._resolve_note_id(end_id)
        if start is None or end is None:
            return None

        try:
            undirected = self.graph.to_undirected()
            return nx.shortest_path(undirected, start, end)
        except nx.NetworkXNoPath:
            return None

    def get_path_details(self, start_id: str, end_id: str) -> Optional[list[dict[str, Any]]]:
        """Return a path with relationship metadata on each hop."""

        path = self.find_path(start_id, end_id)
        if path is None:
            return None

        detailed_path: list[dict[str, Any]] = []
        for index, node_id in enumerate(path):
            step: dict[str, Any] = {"id": node_id}
            if index < len(path) - 1:
                next_node = path[index + 1]
                if self.graph.has_edge(node_id, next_node):
                    step["to_next"] = self._relationship_records(node_id, next_node)
                elif self.graph.has_edge(next_node, node_id):
                    step["to_next"] = self._relationship_records(next_node, node_id)
            detailed_path.append(step)
        return detailed_path

    def search(self, query: str, limit: int = 20) -> list[Note]:
        """Full-text search across all notes."""

        query_lower = query.lower()
        results = []

        for note in self.notes.values():
            score = 0
            if query_lower in note.title.lower():
                score += 10
            for alias in note.aliases:
                alias_lower = alias.lower()
                if query_lower == alias_lower:
                    score += 9
                elif query_lower in alias_lower:
                    score += 6
            for tag in note.tags:
                if query_lower in tag:
                    score += 5
            summary = str(note.frontmatter.get("summary", "")).lower()
            if query_lower in summary:
                score += 6
            project = str(note.frontmatter.get("project", "")).lower()
            if query_lower in project:
                score += 5
            note_type = str(note.frontmatter.get("entity_type", "")).lower()
            if query_lower in note_type:
                score += 4
            status = str(note.frontmatter.get("status", "")).lower()
            if query_lower in status:
                score += 3
            score += self._note_priority(note)
            for relationship in note.explicit_relationships:
                if query_lower in relationship.relation_type:
                    score += 4
            if query_lower in note.content.lower():
                score += 1
            if score > 0:
                results.append((score, note))

        results.sort(key=lambda item: item[0], reverse=True)
        return [note for _, note in results[:limit]]

    def list_tags(self) -> list[tuple[str, int]]:
        """List all tags with note counts."""

        tag_counts = [(tag, len(note_ids)) for tag, note_ids in self._tag_index.items()]
        tag_counts.sort(key=lambda item: item[1], reverse=True)
        return tag_counts

    def notes_by_tag(self, tag: str) -> list[Note]:
        """Get all notes with a specific tag."""

        return [
            self.notes[note_id]
            for note_id in self._tag_index.get(tag.lower(), set())
            if note_id in self.notes
        ]

    def graph_context(
        self,
        identifier: str,
        depth: int = 2,
        relation_types: Optional[list[str]] = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        """Return graph-first context centered on a note."""

        resolved = self._resolve_note_id(identifier)
        if resolved is None:
            return {"error": f"Note not found: {identifier}"}

        allowed = set(relation_types or [])
        lengths = nx.single_source_shortest_path_length(
            self.graph.to_undirected(),
            resolved,
            cutoff=depth,
        )
        nodes = []
        for node_id, distance in sorted(lengths.items(), key=lambda item: (item[1], item[0])):
            if node_id == resolved:
                continue
            relationship_counts = self._relationship_type_counts_between(resolved, node_id, depth, allowed)
            if allowed and not relationship_counts:
                continue
            note = self.notes[node_id]
            score = max(1, (depth + 1) - distance) + len(relationship_counts) * 2
            score += self._note_priority(note)
            nodes.append(
                {
                    "id": note.id,
                    "title": note.title,
                    "distance": distance,
                    "score": score,
                    "tags": note.tags,
                    "relationship_counts": relationship_counts,
                }
            )

        nodes.sort(key=lambda item: (-item["score"], item["distance"], item["title"]))

        traversal = self.traverse(resolved, depth=depth, relation_types=relation_types)
        edge_details = []
        for source, target in traversal.edges:
            relationships = self._relationship_records(source, target, None)
            if allowed:
                relationships = [
                    relation for relation in relationships if relation["type"] in allowed
                ]
            if not relationships:
                continue
            edge_details.append(
                {
                    "from": source,
                    "to": target,
                    "relationships": relationships,
                }
            )

        return {
            "anchor": resolved,
            "depth": depth,
            "relation_filter": sorted(allowed),
            "nodes": nodes[:limit],
            "edges": edge_details,
        }

    def _relationship_type_counts_between(
        self,
        start: str,
        target: str,
        depth: int,
        allowed: set[str],
    ) -> dict[str, int]:
        """Count relationship types touching a node within a local path neighborhood."""

        counts: dict[str, int] = {}
        undirected = self.graph.to_undirected()
        try:
            path = nx.shortest_path(undirected, start, target)
        except nx.NetworkXNoPath:
            return counts

        if len(path) - 1 > depth:
            return counts

        for index in range(len(path) - 1):
            source = path[index]
            next_node = path[index + 1]
            if self.graph.has_edge(source, next_node):
                relationships = self._relationship_records(source, next_node)
            else:
                relationships = self._relationship_records(next_node, source)
            for relation in relationships:
                relation_name = relation["type"]
                if allowed and relation_name not in allowed:
                    continue
                counts[relation_name] = counts.get(relation_name, 0) + 1

        return counts

    def get_stats(self) -> GraphStats:
        """Get graph statistics."""

        orphans = [
            note_id
            for note_id in self.notes
            if self.graph.in_degree(note_id) == 0 and self.graph.out_degree(note_id) == 0
        ]
        degrees = [
            (note_id, self.graph.in_degree(note_id) + self.graph.out_degree(note_id))
            for note_id in self.notes
        ]
        degrees.sort(key=lambda item: item[1], reverse=True)

        relationship_counts: dict[str, int] = {}
        for _source, _target, data in self.graph.edges(data=True):
            for relation in data.get("relationships", []):
                relation_name = relation["type"]
                relationship_counts[relation_name] = relationship_counts.get(relation_name, 0) + 1

        return GraphStats(
            total_notes=len(self.notes),
            total_links=self.graph.number_of_edges(),
            total_tags=len(self._tag_index),
            orphan_notes=len(orphans),
            most_connected=degrees[:10],
            total_relationships=sum(relationship_counts.values()),
            relationship_counts=sorted(
                relationship_counts.items(),
                key=lambda item: (-item[1], item[0]),
            ),
        )

    def list_all_notes(self) -> list[Note]:
        """Get all notes in the graph."""

        return list(self.notes.values())

    def list_stale_notes(self) -> list[Note]:
        """Get notes whose 'expires' frontmatter date is in the past."""

        from datetime import date

        today = date.today()
        stale = []
        for note in self.notes.values():
            raw = note.frontmatter.get("expires")
            if not raw:
                continue
            try:
                if date.fromisoformat(str(raw)) < today:
                    stale.append(note)
            except (ValueError, TypeError):
                pass
        return stale

    def _generate_frontmatter(
        self,
        title: str,
        tags: list[str],
        extra: Optional[dict] = None,
    ) -> str:
        """Generate YAML frontmatter string."""

        frontmatter = {"title": title}
        if tags:
            frontmatter["tags"] = tags
        frontmatter["created"] = datetime.now().isoformat()
        if extra:
            frontmatter.update(extra)
        return f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n"

    def _reload_note_from_disk(self, old_note: Note) -> Note:
        """Re-parse a note from disk and refresh graph/index state."""

        if old_note.id in self.notes:
            del self.notes[old_note.id]
        if old_note.id in self.graph:
            self.graph.remove_node(old_note.id)
        self._title_index = {
            key: value for key, value in self._title_index.items() if value != old_note.id
        }
        self._alias_index = {
            key: value for key, value in self._alias_index.items() if value != old_note.id
        }
        for tag in list(self._tag_index):
            self._tag_index[tag].discard(old_note.id)
            if not self._tag_index[tag]:
                del self._tag_index[tag]

        updated_note = parse_note(old_note.path)
        self._add_note(updated_note)

        for link in updated_note.outgoing_links:
            if link.target in self.notes:
                self._add_edge(
                    updated_note.id,
                    link.target,
                    relationship_type=link.link_type,
                    evidence="inline_link",
                    display_text=link.display_text,
                    line_number=link.line_number,
                )

        for relationship in updated_note.explicit_relationships:
            target_id = self._resolve_relationship_target(relationship)
            if target_id is not None:
                self._add_edge(
                    updated_note.id,
                    target_id,
                    relationship_type=relationship.relation_type,
                    evidence="frontmatter",
                    source_field=relationship.source_field,
                )

        return updated_note

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        filename: Optional[str] = None,
    ) -> Note:
        """Create a new note in the vault."""

        if not self.vault_path:
            raise ValueError("No vault path specified")

        tags = tags or []
        tags_lower = [tag.lower() for tag in tags]
        filename = normalize_id(filename or title)

        if filename in self.notes:
            raise ValueError(f"Note already exists: {filename}")

        full_content = self._generate_frontmatter(title, tags_lower) + content
        file_path = Path(self.vault_path) / f"{filename}.md"
        file_path.write_text(full_content, encoding="utf-8")
        note = parse_note(file_path)
        self._add_note(note)

        for link in note.outgoing_links:
            if link.target in self.notes:
                self._add_edge(
                    note.id,
                    link.target,
                    relationship_type=link.link_type,
                    evidence="inline_link",
                    display_text=link.display_text,
                    line_number=link.line_number,
                )

        for relationship in note.explicit_relationships:
            target_id = self._resolve_relationship_target(relationship)
            if target_id is not None:
                self._add_edge(
                    note.id,
                    target_id,
                    relationship_type=relationship.relation_type,
                    evidence="frontmatter",
                    source_field=relationship.source_field,
                )

        return note

    def update_note(
        self,
        identifier: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        append: bool = False,
    ) -> Note:
        """Update an existing note."""

        note = self.get_note(identifier)
        if not note:
            raise ValueError(f"Note not found: {identifier}")

        current_frontmatter = note.frontmatter.copy()
        current_body = note.body
        if title:
            current_frontmatter["title"] = title
        if tags is not None:
            current_frontmatter["tags"] = [tag.lower() for tag in tags]
        current_frontmatter["modified"] = datetime.now().isoformat()

        if content is not None:
            new_body = f"{current_body}\n\n{content}" if append else content
        else:
            new_body = current_body

        full_content = (
            f"---\n{yaml.dump(current_frontmatter, default_flow_style=False)}---\n\n{new_body}"
        )
        note.path.write_text(full_content, encoding="utf-8")
        return self._reload_note_from_disk(note)

    def upsert_memory_node(
        self,
        title: str,
        summary: str,
        entity_type: str,
        project: Optional[str] = None,
        status: Optional[str] = None,
        aliases: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        relationships: Optional[list[dict[str, str]]] = None,
        body: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Note:
        """Create or update a structured memory node optimized for agent retrieval."""

        identifier = filename or title
        existing = self.get_note(identifier) or self.get_note(title)

        relationship_fields: dict[str, list[str]] = {}
        for relationship in relationships or []:
            relation_type = relationship["type"]
            if relation_type not in RELATIONSHIP_FIELDS:
                raise ValueError(f"Unsupported relationship type: {relation_type}")
            relationship_fields.setdefault(relation_type, []).append(relationship["target"])

        if existing is None:
            extra = {
                "aliases": aliases or [],
                "entity_type": entity_type,
                "summary": summary,
            }
            if project:
                extra["project"] = project
            if status:
                extra["status"] = status
            extra.update(relationship_fields)
            content_body = body if body is not None else summary
            frontmatter = self._generate_frontmatter(title, [t.lower() for t in (tags or [])], extra)
            file_path = Path(self.vault_path) / f"{normalize_id(filename or title)}.md"
            file_path.write_text(frontmatter + content_body, encoding="utf-8")
            note = parse_note(file_path)
            self._add_note(note)
            for link in note.outgoing_links:
                if link.target in self.notes:
                    self._add_edge(
                        note.id,
                        link.target,
                        relationship_type=link.link_type,
                        evidence="inline_link",
                        display_text=link.display_text,
                        line_number=link.line_number,
                    )
            for relationship in note.explicit_relationships:
                target_id = self._resolve_relationship_target(relationship)
                if target_id is not None:
                    self._add_edge(
                        note.id,
                        target_id,
                        relationship_type=relationship.relation_type,
                        evidence="frontmatter",
                        source_field=relationship.source_field,
                    )
            return note

        frontmatter = existing.frontmatter.copy()
        frontmatter["title"] = title
        frontmatter["aliases"] = aliases or frontmatter.get("aliases", [])
        frontmatter["entity_type"] = entity_type
        frontmatter["summary"] = summary
        if project is not None:
            frontmatter["project"] = project
        if status is not None:
            frontmatter["status"] = status
        if tags is not None:
            frontmatter["tags"] = [tag.lower() for tag in tags]

        for relation_type in RELATIONSHIP_FIELDS:
            frontmatter.pop(relation_type, None)
        frontmatter.update(relationship_fields)
        frontmatter["modified"] = datetime.now().isoformat()

        body_content = existing.body if body is None else body
        existing.path.write_text(
            f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{body_content}",
            encoding="utf-8",
        )
        return self._reload_note_from_disk(existing)

    def update_relationships(
        self,
        identifier: str,
        add: Optional[list[dict[str, str]]] = None,
        remove: Optional[list[dict[str, str]]] = None,
        replace: Optional[list[dict[str, str]]] = None,
    ) -> Note:
        """Mutate a note's typed frontmatter relationships."""

        note = self.get_note(identifier)
        if not note:
            raise ValueError(f"Note not found: {identifier}")

        frontmatter = note.frontmatter.copy()
        current: dict[str, list[str]] = {}
        for relation_type in RELATIONSHIP_FIELDS:
            value = frontmatter.get(relation_type)
            if isinstance(value, str):
                current[relation_type] = [value]
            elif isinstance(value, list):
                current[relation_type] = [str(item) for item in value]

        if replace is not None:
            current = {}
            add = replace
            remove = None

        for relationship in add or []:
            relation_type = relationship["type"]
            if relation_type not in RELATIONSHIP_FIELDS:
                raise ValueError(f"Unsupported relationship type: {relation_type}")
            current.setdefault(relation_type, [])
            if relationship["target"] not in current[relation_type]:
                current[relation_type].append(relationship["target"])

        for relationship in remove or []:
            relation_type = relationship["type"]
            if relation_type in current and relationship["target"] in current[relation_type]:
                current[relation_type].remove(relationship["target"])

        for relation_type in RELATIONSHIP_FIELDS:
            frontmatter.pop(relation_type, None)
        for relation_type, targets in current.items():
            if targets:
                frontmatter[relation_type] = targets

        frontmatter["modified"] = datetime.now().isoformat()
        note.path.write_text(
            f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{note.body}",
            encoding="utf-8",
        )
        return self._reload_note_from_disk(note)

    def lint_graph(self) -> list[LintIssue]:
        """Find notes that are weak for agent retrieval."""

        issues: list[LintIssue] = []
        for note in self.notes.values():
            frontmatter = note.frontmatter
            if not frontmatter.get("entity_type"):
                issues.append(LintIssue(note.id, "warning", "missing_entity_type", "Missing entity_type"))
            if not frontmatter.get("summary"):
                issues.append(LintIssue(note.id, "warning", "missing_summary", "Missing summary"))
            if self.graph.in_degree(note.id) + self.graph.out_degree(note.id) == 0:
                issues.append(LintIssue(note.id, "info", "orphan", "No graph connections"))
            if not note.aliases:
                issues.append(LintIssue(note.id, "info", "missing_aliases", "No aliases configured"))
            if frontmatter.get("confidence") is None:
                issues.append(LintIssue(note.id, "info", "missing_confidence", "Missing confidence score"))
            if not frontmatter.get("last_reviewed"):
                issues.append(
                    LintIssue(note.id, "info", "missing_last_reviewed", "Missing last_reviewed timestamp")
                )
        return issues

    def suggest_relationships(self, limit: int = 20) -> list[RelationshipSuggestion]:
        """Suggest new relationships using shared structure."""

        suggestions: list[RelationshipSuggestion] = []
        note_ids = sorted(self.notes)
        for index, source_id in enumerate(note_ids):
            source = self.notes[source_id]
            for target_id in note_ids[index + 1 :]:
                target = self.notes[target_id]
                if self.graph.has_edge(source_id, target_id) or self.graph.has_edge(target_id, source_id):
                    continue

                score = 0
                reasons: list[str] = []
                shared_tags = sorted(set(source.tags).intersection(target.tags))
                if shared_tags:
                    score += len(shared_tags) * 2
                    reasons.append(f"shared tags: {', '.join(shared_tags)}")

                source_project = source.frontmatter.get("project")
                target_project = target.frontmatter.get("project")
                if source_project and source_project == target_project:
                    score += 3
                    reasons.append(f"same project: {source_project}")

                source_summary = str(source.frontmatter.get("summary", "")).lower()
                target_summary = str(target.frontmatter.get("summary", "")).lower()
                if source.title.lower() in target_summary or target.title.lower() in source_summary:
                    score += 2
                    reasons.append("title mentioned in counterpart summary")

                if score < 3:
                    continue

                suggested_type = "related_to"
                if source.frontmatter.get("entity_type") == "decision":
                    suggested_type = "decision_for"
                suggestions.append(
                    RelationshipSuggestion(
                        source_id=source_id,
                        target_id=target_id,
                        suggested_type=suggested_type,
                        score=score,
                        reasons=reasons,
                    )
                )

        suggestions.sort(key=lambda item: (-item.score, item.source_id, item.target_id))
        return suggestions[:limit]

    def merge_memory_nodes(
        self,
        source_identifier: str,
        target_identifier: str,
        archive_source: bool = True,
    ) -> Note:
        """Merge one memory node into another."""

        source = self.get_note(source_identifier)
        target = self.get_note(target_identifier)
        if not source or not target:
            raise ValueError("Both source and target notes must exist")
        if source.id == target.id:
            raise ValueError("Source and target must be different notes")

        target_frontmatter = target.frontmatter.copy()
        source_frontmatter = source.frontmatter.copy()
        target_frontmatter["aliases"] = list(
            dict.fromkeys(target.aliases + [source.title] + source.aliases)
        )

        for field in ("summary", "project", "status", "entity_type"):
            if not target_frontmatter.get(field) and source_frontmatter.get(field):
                target_frontmatter[field] = source_frontmatter[field]

        for relation_type in RELATIONSHIP_FIELDS:
            combined: list[str] = []
            for frontmatter in (target_frontmatter, source_frontmatter):
                value = frontmatter.get(relation_type)
                if isinstance(value, str):
                    combined.append(value)
                elif isinstance(value, list):
                    combined.extend(str(item) for item in value)
            if combined:
                target_frontmatter[relation_type] = list(dict.fromkeys(combined))

        merged_body = target.body
        if source.body and source.body not in merged_body:
            merged_body = merged_body.rstrip() + f"\n\n## Merged Context From {source.title}\n\n" + source.body

        target.path.write_text(
            f"---\n{yaml.dump(target_frontmatter, default_flow_style=False)}---\n\n{merged_body}",
            encoding="utf-8",
        )
        updated_target = self._reload_note_from_disk(target)

        if archive_source:
            source_frontmatter["status"] = "merged"
            source_frontmatter["merged_into"] = updated_target.title
            source.path.write_text(
                f"---\n{yaml.dump(source_frontmatter, default_flow_style=False)}---\n\nMerged into [[{updated_target.title}]].",
                encoding="utf-8",
            )
            self._reload_note_from_disk(source)
        else:
            self.delete_note(source.id)

        return updated_target

    def get_note_health(self, identifier: str) -> Optional[NoteHealth]:
        """Compute health for a single note."""

        note = self.get_note(identifier)
        if not note:
            return None

        max_score = 10
        score = 0
        issues: list[str] = []
        frontmatter = note.frontmatter

        if frontmatter.get("entity_type"):
            score += 2
        else:
            issues.append("missing entity_type")

        if frontmatter.get("summary"):
            score += 2
        else:
            issues.append("missing summary")

        if note.aliases:
            score += 1
        else:
            issues.append("missing aliases")

        if self.graph.in_degree(note.id) + self.graph.out_degree(note.id) > 0:
            score += 2
        else:
            issues.append("no graph connections")

        if frontmatter.get("confidence") is not None:
            score += 1
        else:
            issues.append("missing confidence")

        if frontmatter.get("last_reviewed"):
            score += 1
        else:
            issues.append("missing last_reviewed")

        if frontmatter.get("importance"):
            score += 1
        else:
            issues.append("missing importance")

        return NoteHealth(note_id=note.id, score=score, max_score=max_score, issues=issues)

    def get_graph_health(self, limit: int = 50) -> list[NoteHealth]:
        """Rank notes by health so weak memory nodes are easy to improve."""

        health = [self.get_note_health(note.id) for note in self.notes.values()]
        health = [item for item in health if item is not None]
        health.sort(key=lambda item: (item.score, len(item.issues), item.note_id))
        return health[:limit]

    def append_to_note(self, identifier: str, content: str) -> Note:
        """Append content to an existing note."""

        return self.update_note(identifier, content=content, append=True)

    def delete_note(self, identifier: str) -> bool:
        """Delete a note from the vault."""

        note = self.get_note(identifier)
        if not note:
            return False

        note.path.unlink()
        if note.id in self.notes:
            del self.notes[note.id]
        if note.id in self.graph:
            self.graph.remove_node(note.id)

        title_lower = note.title.lower()
        if title_lower in self._title_index:
            del self._title_index[title_lower]
        for alias in note.aliases:
            alias_lower = alias.lower()
            if alias_lower in self._alias_index:
                del self._alias_index[alias_lower]

        for tag in note.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(note.id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        return True
