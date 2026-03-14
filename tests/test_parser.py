"""Tests for the parser module."""

import tempfile
from pathlib import Path

import pytest

from linked_notes_mcp.parser import (
    Link,
    extract_relationships,
    extract_markdown_links,
    extract_tags,
    extract_title,
    extract_wikilinks,
    normalize_id,
    parse_frontmatter,
    parse_note,
)


class TestNormalizeId:
    def test_simple_name(self):
        assert normalize_id("My Note") == "my-note"
    
    def test_with_special_chars(self):
        assert normalize_id("My Note (2024)") == "my-note-2024"
    
    def test_with_path(self):
        assert normalize_id("folder/My Note.md") == "my-note"
    
    def test_already_normalized(self):
        assert normalize_id("my-note") == "my-note"


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = """---
title: Test Note
tags:
  - tag1
  - tag2
---

# Content here
"""
        fm, remaining = parse_frontmatter(content)
        assert fm["title"] == "Test Note"
        assert fm["tags"] == ["tag1", "tag2"]
        assert "# Content here" in remaining
    
    def test_no_frontmatter(self):
        content = "# Just a heading\n\nSome content"
        fm, remaining = parse_frontmatter(content)
        assert fm == {}
        assert remaining == content
    
    def test_invalid_yaml(self):
        content = """---
title: [invalid
---

Content
"""
        fm, remaining = parse_frontmatter(content)
        assert fm == {}


class TestExtractWikilinks:
    def test_simple_wikilink(self):
        content = "Link to [[Another Note]] here."
        links = extract_wikilinks(content)
        assert len(links) == 1
        assert links[0].target == "another-note"
        assert links[0].display_text is None
    
    def test_wikilink_with_display(self):
        content = "See [[Target Note|custom text]] for details."
        links = extract_wikilinks(content)
        assert len(links) == 1
        assert links[0].target == "target-note"
        assert links[0].display_text == "custom text"
    
    def test_multiple_wikilinks(self):
        content = "Links to [[Note A]] and [[Note B|B]] here."
        links = extract_wikilinks(content)
        assert len(links) == 2
    
    def test_wikilink_line_numbers(self):
        content = "Line 1\n[[Link on line 2]]\nLine 3"
        links = extract_wikilinks(content)
        assert links[0].line_number == 2


class TestExtractMarkdownLinks:
    def test_markdown_link_to_md(self):
        content = "See [my link](other-note.md) for details."
        links = extract_markdown_links(content)
        assert len(links) == 1
        assert links[0].target == "other-note"
        assert links[0].display_text == "my link"
    
    def test_ignores_non_md_links(self):
        content = "See [external](https://example.com) and [doc](file.pdf)"
        links = extract_markdown_links(content)
        assert len(links) == 0


class TestExtractTitle:
    def test_title_from_frontmatter(self):
        title = extract_title("# Heading", {"title": "FM Title"}, "filename")
        assert title == "FM Title"
    
    def test_title_from_heading(self):
        title = extract_title("# My Heading\n\nContent", {}, "filename")
        assert title == "My Heading"
    
    def test_title_from_filename(self):
        title = extract_title("No heading here", {}, "my-note-file")
        assert title == "My Note File"


class TestExtractTags:
    def test_list_tags(self):
        tags = extract_tags({"tags": ["tag1", "tag2"]})
        assert tags == ["tag1", "tag2"]
    
    def test_string_tags(self):
        tags = extract_tags({"tags": "tag1, tag2, tag3"})
        assert tags == ["tag1", "tag2", "tag3"]
    
    def test_no_tags(self):
        tags = extract_tags({})
        assert tags == []


class TestExtractRelationships:
    def test_string_relationship(self):
        relationships = extract_relationships({"depends_on": "Auth Service"})
        assert len(relationships) == 1
        assert relationships[0].target == "auth-service"
        assert relationships[0].relation_type == "depends_on"

    def test_list_relationships(self):
        relationships = extract_relationships(
            {"blocks": ["Beta Note", "Gamma Note"], "ignored": "value"}
        )
        assert [r.target for r in relationships] == ["beta-note", "gamma-note"]
        assert all(r.relation_type == "blocks" for r in relationships)


class TestParseNote:
    def test_full_note(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            note_path = Path(tmpdir) / "test-note.md"
            note_path.write_text("""---
title: Test Note
tags:
  - testing
depends_on:
  - Another Note
related_to: Third
---

# Test Note

This links to [[Another Note]] and [[Third|display]].

Also see [markdown link](other.md).
""")
            note = parse_note(note_path)
            
            assert note.id == "test-note"
            assert note.title == "Test Note"
            assert note.tags == ["testing"]
            assert len(note.outgoing_links) == 3
            assert len(note.explicit_relationships) == 2
