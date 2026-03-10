"""Tests for the graph module."""

import tempfile
from pathlib import Path

import pytest

from linked_notes_mcp.graph import KnowledgeGraph


@pytest.fixture
def sample_vault():
    """Create a temporary vault with sample notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        
        # Create interconnected notes
        (vault / "note-a.md").write_text("""---
title: Note A
tags: [alpha]
---
# Note A
Links to [[Note B]] and [[Note C]].
""")
        
        (vault / "note-b.md").write_text("""---
title: Note B
tags: [beta]
---
# Note B
Links back to [[Note A]].
""")
        
        (vault / "note-c.md").write_text("""---
title: Note C
tags: [alpha, gamma]
---
# Note C
Links to [[Note D]].
""")
        
        (vault / "note-d.md").write_text("""---
title: Note D
tags: [delta]
---
# Note D
Terminal node, no outgoing links.
""")
        
        (vault / "orphan.md").write_text("""---
title: Orphan Note
---
# Orphan
No links at all.
""")
        
        yield vault


class TestKnowledgeGraph:
    def test_build_graph(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        assert len(graph.notes) == 5
    
    def test_get_note_by_id(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        note = graph.get_note("note-a")
        assert note is not None
        assert note.title == "Note A"
    
    def test_get_note_by_title(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        note = graph.get_note("Note B")
        assert note is not None
        assert note.id == "note-b"
    
    def test_get_links_outgoing(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        links = graph.get_links("note-a", "outgoing")
        assert "note-b" in links["outgoing"]
        assert "note-c" in links["outgoing"]
    
    def test_get_links_incoming(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        links = graph.get_links("note-b", "incoming")
        assert "note-a" in links["incoming"]
    
    def test_traverse_depth_1(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        result = graph.traverse("note-a", depth=1)
        assert "note-a" in result.nodes
        assert "note-b" in result.nodes
        assert "note-c" in result.nodes
        # note-d should not be included (2 hops away)
        assert "note-d" not in result.nodes
    
    def test_traverse_depth_2(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        result = graph.traverse("note-a", depth=2)
        assert "note-d" in result.nodes
    
    def test_find_path(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        path = graph.find_path("note-a", "note-d")
        assert path is not None
        assert path[0] == "note-a"
        assert path[-1] == "note-d"
        assert len(path) == 3  # A -> C -> D
    
    def test_find_path_no_connection(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        path = graph.find_path("note-a", "orphan")
        assert path is None
    
    def test_search(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        results = graph.search("Note A")
        assert len(results) > 0
        assert results[0].id == "note-a"
    
    def test_list_tags(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        tags = graph.list_tags()
        tag_names = [t[0] for t in tags]
        assert "alpha" in tag_names
        assert "beta" in tag_names
    
    def test_notes_by_tag(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        notes = graph.notes_by_tag("alpha")
        note_ids = [n.id for n in notes]
        assert "note-a" in note_ids
        assert "note-c" in note_ids
    
    def test_stats(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        stats = graph.get_stats()
        assert stats.total_notes == 5
        assert stats.orphan_notes == 1  # orphan.md
        assert stats.total_links > 0
    
    def test_rebuild(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        initial_count = len(graph.notes)

        # Add a new note
        (sample_vault / "new-note.md").write_text("# New Note")

        # Rebuild
        graph.rebuild()
        assert len(graph.notes) == initial_count + 1


class TestWriteOperations:
    """Tests for write operations (create, update, append, delete)."""

    def test_create_note(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        initial_count = len(graph.notes)

        note = graph.create_note(
            title="My New Note",
            content="This is the content.\n\nLinks to [[Note A]].",
            tags=["test", "new"]
        )

        assert note.id == "my-new-note"
        assert note.title == "My New Note"
        assert "test" in note.tags
        assert len(graph.notes) == initial_count + 1

        # Verify file was created
        file_path = sample_vault / "my-new-note.md"
        assert file_path.exists()
        content = file_path.read_text()
        assert "title: My New Note" in content
        assert "This is the content." in content

    def test_create_note_with_custom_filename(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        note = graph.create_note(
            title="A Very Long Title",
            content="Content here",
            filename="short-name"
        )

        assert note.id == "short-name"
        assert (sample_vault / "short-name.md").exists()

    def test_create_note_duplicate_error(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        with pytest.raises(ValueError, match="already exists"):
            graph.create_note(title="Note A", content="Duplicate")

    def test_update_note_content(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        note = graph.update_note(
            identifier="note-a",
            content="Completely new content"
        )

        assert "Completely new content" in note.content
        assert "modified" in note.frontmatter

    def test_update_note_title(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        note = graph.update_note(
            identifier="note-a",
            title="Note A Renamed"
        )

        assert note.title == "Note A Renamed"

    def test_update_note_tags(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        note = graph.update_note(
            identifier="note-a",
            tags=["new-tag", "another"]
        )

        assert "new-tag" in note.tags
        assert "another" in note.tags
        assert "alpha" not in note.tags  # Old tag removed

    def test_update_note_not_found(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        with pytest.raises(ValueError, match="not found"):
            graph.update_note(identifier="nonexistent", content="test")

    def test_append_to_note(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        original_note = graph.get_note("note-a")
        original_body = original_note.body

        note = graph.append_to_note(
            identifier="note-a",
            content="## New Section\nAppended content here."
        )

        # Should contain both original and new content
        assert original_body.strip() in note.body
        assert "## New Section" in note.body
        assert "Appended content here." in note.body

    def test_delete_note(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)
        initial_count = len(graph.notes)

        # Verify file exists
        assert (sample_vault / "orphan.md").exists()
        assert graph.get_note("orphan") is not None

        result = graph.delete_note("orphan")

        assert result is True
        assert len(graph.notes) == initial_count - 1
        assert graph.get_note("orphan") is None
        assert not (sample_vault / "orphan.md").exists()

    def test_delete_note_not_found(self, sample_vault):
        graph = KnowledgeGraph(sample_vault)

        result = graph.delete_note("nonexistent")
        assert result is False

    def test_create_note_links_indexed(self, sample_vault):
        """Verify that links in newly created notes are indexed."""
        graph = KnowledgeGraph(sample_vault)

        note = graph.create_note(
            title="Linker",
            content="This links to [[Note B]] and [[Note C]]."
        )

        # Check that outgoing links are parsed
        link_targets = [link.target for link in note.outgoing_links]
        assert "note-b" in link_targets
        assert "note-c" in link_targets

        # Check that edges exist in graph
        links = graph.get_links("linker", "outgoing")
        assert "note-b" in links["outgoing"]
        assert "note-c" in links["outgoing"]
