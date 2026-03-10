"""
Knowledge graph built from markdown notes.

Uses NetworkX for graph operations. Supports:
- Building graph from notes
- Traversing connections
- Finding paths between notes
- Getting subgraphs within N hops
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

import networkx as nx
import yaml

from .parser import Note, is_markdown_file, normalize_id, parse_note


@dataclass
class GraphStats:
    """Statistics about the knowledge graph."""
    total_notes: int
    total_links: int
    total_tags: int
    orphan_notes: int  # Notes with no connections
    most_connected: list[tuple[str, int]]  # Top 10 by connection count


@dataclass
class TraversalResult:
    """Result of traversing the graph from a starting node."""
    start_id: str
    depth: int
    nodes: list[str]  # All node IDs found
    edges: list[tuple[str, str]]  # All edges traversed


class KnowledgeGraph:
    """A knowledge graph built from markdown notes."""
    
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path
        self.graph = nx.DiGraph()  # Directed graph for link direction
        self.notes: dict[str, Note] = {}  # id -> Note
        self._tag_index: dict[str, set[str]] = {}  # tag -> set of note ids
        self._title_index: dict[str, str] = {}  # lowercase title -> note id
        
        if vault_path:
            self.rebuild()
    
    def rebuild(self, vault_path: Optional[Path] = None) -> int:
        """Rebuild the graph from the vault directory.
        
        Returns:
            Number of notes indexed
        """
        if vault_path:
            self.vault_path = vault_path
        
        if not self.vault_path:
            raise ValueError("No vault path specified")
        
        # Clear existing data
        self.graph.clear()
        self.notes.clear()
        self._tag_index.clear()
        self._title_index.clear()
        
        # Find all markdown files
        vault = Path(self.vault_path)
        if not vault.exists():
            raise ValueError(f"Vault path does not exist: {vault}")
        
        # Parse all notes first
        for md_file in self._find_markdown_files(vault):
            try:
                note = parse_note(md_file)
                self._add_note(note)
            except Exception as e:
                # Log but continue on parse errors
                print(f"Warning: Failed to parse {md_file}: {e}")
        
        # Build edges from links
        for note_id, note in self.notes.items():
            for link in note.outgoing_links:
                # Only add edge if target exists
                if link.target in self.notes:
                    self.graph.add_edge(note_id, link.target)
        
        return len(self.notes)
    
    def _find_markdown_files(self, directory: Path) -> Iterator[Path]:
        """Recursively find all markdown files in directory."""
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                yield from self._find_markdown_files(item)
            elif is_markdown_file(item):
                yield item
    
    def _add_note(self, note: Note) -> None:
        """Add a note to the graph."""
        self.notes[note.id] = note
        self.graph.add_node(note.id)
        
        # Index by title
        self._title_index[note.title.lower()] = note.id
        
        # Index by tags
        for tag in note.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(note.id)
    
    def get_note(self, identifier: str) -> Optional[Note]:
        """Get a note by ID or title."""
        # Try direct ID lookup
        normalized = normalize_id(identifier)
        if normalized in self.notes:
            return self.notes[normalized]
        
        # Try title lookup
        lower_id = identifier.lower()
        if lower_id in self._title_index:
            return self.notes[self._title_index[lower_id]]
        
        return None
    
    def get_links(
        self,
        note_id: str,
        direction: str = "both"
    ) -> dict[str, list[str]]:
        """Get links for a note.
        
        Args:
            note_id: The note identifier
            direction: "outgoing", "incoming", or "both"
        
        Returns:
            Dict with "outgoing" and/or "incoming" lists
        """
        normalized = normalize_id(note_id)
        if normalized not in self.notes:
            # Try title lookup
            lower_id = note_id.lower()
            if lower_id in self._title_index:
                normalized = self._title_index[lower_id]
            else:
                return {"outgoing": [], "incoming": []}
        
        result = {}
        
        if direction in ("outgoing", "both"):
            result["outgoing"] = list(self.graph.successors(normalized))
        
        if direction in ("incoming", "both"):
            result["incoming"] = list(self.graph.predecessors(normalized))
        
        return result
    
    def traverse(
        self,
        start_id: str,
        depth: int = 2,
        direction: str = "both"
    ) -> TraversalResult:
        """Traverse the graph from a starting note.
        
        Args:
            start_id: Starting note identifier
            depth: Maximum hops from start
            direction: "outgoing", "incoming", or "both"
        
        Returns:
            TraversalResult with all nodes and edges within depth
        """
        normalized = normalize_id(start_id)
        if normalized not in self.notes:
            # Try title lookup
            lower_id = start_id.lower()
            if lower_id in self._title_index:
                normalized = self._title_index[lower_id]
            else:
                return TraversalResult(start_id, depth, [], [])
        
        visited = {normalized}
        edges = []
        frontier = {normalized}
        
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                # Get neighbors based on direction
                neighbors = set()
                if direction in ("outgoing", "both"):
                    neighbors.update(self.graph.successors(node))
                if direction in ("incoming", "both"):
                    neighbors.update(self.graph.predecessors(node))
                
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
                    
                    # Track edges
                    if direction in ("outgoing", "both") and self.graph.has_edge(node, neighbor):
                        edges.append((node, neighbor))
                    if direction in ("incoming", "both") and self.graph.has_edge(neighbor, node):
                        edges.append((neighbor, node))
            
            frontier = next_frontier
            if not frontier:
                break
        
        return TraversalResult(
            start_id=normalized,
            depth=depth,
            nodes=list(visited),
            edges=edges
        )
    
    def find_path(
        self,
        start_id: str,
        end_id: str
    ) -> Optional[list[str]]:
        """Find shortest path between two notes.
        
        Returns:
            List of note IDs forming the path, or None if no path exists
        """
        start = normalize_id(start_id)
        end = normalize_id(end_id)
        
        # Try title lookups
        if start not in self.notes:
            if start_id.lower() in self._title_index:
                start = self._title_index[start_id.lower()]
        if end not in self.notes:
            if end_id.lower() in self._title_index:
                end = self._title_index[end_id.lower()]
        
        if start not in self.notes or end not in self.notes:
            return None
        
        try:
            # Use undirected view for pathfinding
            undirected = self.graph.to_undirected()
            path = nx.shortest_path(undirected, start, end)
            return path
        except nx.NetworkXNoPath:
            return None
    
    def search(self, query: str, limit: int = 20) -> list[Note]:
        """Full-text search across all notes.
        
        Searches in: title, content, tags
        """
        query_lower = query.lower()
        results = []
        
        for note in self.notes.values():
            score = 0
            
            # Title match (highest weight)
            if query_lower in note.title.lower():
                score += 10
            
            # Tag match
            for tag in note.tags:
                if query_lower in tag:
                    score += 5
            
            # Content match
            if query_lower in note.content.lower():
                score += 1
            
            if score > 0:
                results.append((score, note))
        
        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [note for _, note in results[:limit]]
    
    def list_tags(self) -> list[tuple[str, int]]:
        """List all tags with their note counts.
        
        Returns:
            List of (tag, count) tuples sorted by count descending
        """
        tag_counts = [(tag, len(note_ids)) for tag, note_ids in self._tag_index.items()]
        tag_counts.sort(key=lambda x: x[1], reverse=True)
        return tag_counts
    
    def notes_by_tag(self, tag: str) -> list[Note]:
        """Get all notes with a specific tag."""
        tag_lower = tag.lower()
        note_ids = self._tag_index.get(tag_lower, set())
        return [self.notes[nid] for nid in note_ids if nid in self.notes]
    
    def get_stats(self) -> GraphStats:
        """Get statistics about the knowledge graph."""
        # Find orphan notes (no incoming or outgoing links)
        orphans = [
            nid for nid in self.notes
            if self.graph.in_degree(nid) == 0 and self.graph.out_degree(nid) == 0
        ]
        
        # Find most connected (by total degree)
        degrees = [(nid, self.graph.in_degree(nid) + self.graph.out_degree(nid))
                   for nid in self.notes]
        degrees.sort(key=lambda x: x[1], reverse=True)
        
        return GraphStats(
            total_notes=len(self.notes),
            total_links=self.graph.number_of_edges(),
            total_tags=len(self._tag_index),
            orphan_notes=len(orphans),
            most_connected=degrees[:10]
        )
    
    def list_all_notes(self) -> list[Note]:
        """Get all notes in the graph."""
        return list(self.notes.values())

    # ==================== Write Operations ====================

    def _generate_frontmatter(self, title: str, tags: list[str], extra: Optional[dict] = None) -> str:
        """Generate YAML frontmatter string."""
        fm = {"title": title}
        if tags:
            fm["tags"] = tags
        fm["created"] = datetime.now().isoformat()
        if extra:
            fm.update(extra)
        return f"---\n{yaml.dump(fm, default_flow_style=False)}---\n\n"

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        filename: Optional[str] = None
    ) -> Note:
        """Create a new note in the vault.

        Args:
            title: Note title
            content: Markdown content (without frontmatter)
            tags: Optional list of tags
            filename: Optional filename (defaults to normalized title)

        Returns:
            The created Note object

        Raises:
            ValueError: If vault path not set or note already exists
        """
        if not self.vault_path:
            raise ValueError("No vault path specified")

        tags = tags or []
        tags_lower = [t.lower() for t in tags]

        # Generate filename from title if not provided
        if not filename:
            filename = normalize_id(title)
        else:
            filename = normalize_id(filename)

        # Check if note already exists
        if filename in self.notes:
            raise ValueError(f"Note already exists: {filename}")

        # Build full content with frontmatter
        frontmatter = self._generate_frontmatter(title, tags_lower)
        full_content = frontmatter + content

        # Write file
        file_path = Path(self.vault_path) / f"{filename}.md"
        file_path.write_text(full_content, encoding='utf-8')

        # Parse and add to graph
        note = parse_note(file_path)
        self._add_note(note)

        # Rebuild edges for new links
        for link in note.outgoing_links:
            if link.target in self.notes:
                self.graph.add_edge(note.id, link.target)

        return note

    def update_note(
        self,
        identifier: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        append: bool = False
    ) -> Note:
        """Update an existing note.

        Args:
            identifier: Note ID or title
            content: New content (replaces body, keeps frontmatter updated)
            title: New title (optional)
            tags: New tags (optional, replaces existing)
            append: If True, append content instead of replacing

        Returns:
            The updated Note object

        Raises:
            ValueError: If note not found
        """
        note = self.get_note(identifier)
        if not note:
            raise ValueError(f"Note not found: {identifier}")

        # Read current content
        current_content = note.path.read_text(encoding='utf-8')
        current_fm = note.frontmatter.copy()
        current_body = note.body

        # Update frontmatter fields
        if title:
            current_fm['title'] = title
        if tags is not None:
            current_fm['tags'] = [t.lower() for t in tags]
        current_fm['modified'] = datetime.now().isoformat()

        # Update body
        if content is not None:
            if append:
                new_body = current_body + "\n\n" + content
            else:
                new_body = content
        else:
            new_body = current_body

        # Rebuild full content
        fm_str = f"---\n{yaml.dump(current_fm, default_flow_style=False)}---\n\n"
        full_content = fm_str + new_body

        # Write file
        note.path.write_text(full_content, encoding='utf-8')

        # Remove old note from graph
        old_id = note.id
        if old_id in self.notes:
            del self.notes[old_id]
        if old_id in self.graph:
            self.graph.remove_node(old_id)

        # Re-parse and add
        updated_note = parse_note(note.path)
        self._add_note(updated_note)

        # Rebuild edges
        for link in updated_note.outgoing_links:
            if link.target in self.notes:
                self.graph.add_edge(updated_note.id, link.target)

        return updated_note

    def append_to_note(self, identifier: str, content: str) -> Note:
        """Append content to an existing note.

        Args:
            identifier: Note ID or title
            content: Content to append

        Returns:
            The updated Note object
        """
        return self.update_note(identifier, content=content, append=True)

    def delete_note(self, identifier: str) -> bool:
        """Delete a note from the vault.

        Args:
            identifier: Note ID or title

        Returns:
            True if deleted, False if not found
        """
        note = self.get_note(identifier)
        if not note:
            return False

        # Remove from filesystem
        note.path.unlink()

        # Remove from graph
        if note.id in self.notes:
            del self.notes[note.id]
        if note.id in self.graph:
            self.graph.remove_node(note.id)

        # Remove from title index
        title_lower = note.title.lower()
        if title_lower in self._title_index:
            del self._title_index[title_lower]

        # Remove from tag index
        for tag in note.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(note.id)

        return True
