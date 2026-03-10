"""Tests for server.py handlers and helpers."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from linked_notes_mcp import server as srv
from linked_notes_mcp.graph import KnowledgeGraph
from linked_notes_mcp.server import (
    _extract_excerpt,
    _load_followups,
    _save_followups,
    handle_tool_call,
    init_graph,
)


@pytest.fixture
def vault(tmp_path):
    """Create a minimal vault and initialize the global graph."""
    (tmp_path / "alpha.md").write_text(
        "---\ntitle: Alpha Note\ntags: [test]\n---\n"
        "This is the alpha note body. It contains the word python.\n"
        "More content here about programming.\n"
    )
    (tmp_path / "beta.md").write_text(
        "---\ntitle: Beta Note\ntags: [other]\nexpires: 2020-01-01\n---\n"
        "Beta note body with some content.\n"
    )
    (tmp_path / "gamma.md").write_text(
        "---\ntitle: Gamma Note\ntags: [test]\nexpires: 2099-12-31\n---\n"
        "Gamma note body.\n"
    )
    init_graph(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# _extract_excerpt
# ---------------------------------------------------------------------------

class TestExtractExcerpt:
    def test_match_in_middle(self, vault):
        graph = KnowledgeGraph(vault)
        note = graph.get_note("alpha")
        excerpt = _extract_excerpt(note, "python")
        assert "python" in excerpt.lower()

    def test_no_match_returns_start(self, vault):
        graph = KnowledgeGraph(vault)
        note = graph.get_note("alpha")
        excerpt = _extract_excerpt(note, "xyznotfound")
        # Should return the beginning of the body
        assert len(excerpt) <= 178  # max_chars + "..."

    def test_empty_body(self, tmp_path):
        """Notes with empty body return empty string."""
        (tmp_path / "empty.md").write_text("---\ntitle: Empty\n---\n")
        init_graph(tmp_path)
        graph = KnowledgeGraph(tmp_path)
        note = graph.get_note("empty")
        result = _extract_excerpt(note, "python")
        assert result == ""

    def test_ellipsis_added_when_truncated(self, tmp_path):
        """When body exceeds max_chars, excerpt ends with ..."""
        long_body = "x" * 300
        (tmp_path / "long.md").write_text(f"---\ntitle: Long\n---\n{long_body}")
        init_graph(tmp_path)
        graph = KnowledgeGraph(tmp_path)
        note = graph.get_note("long")
        result = _extract_excerpt(note, "notfound", max_chars=50)
        assert result.endswith("...")


# ---------------------------------------------------------------------------
# search — excerpt field
# ---------------------------------------------------------------------------

class TestSearchWithExcerpt:
    @pytest.mark.asyncio
    async def test_search_returns_excerpt_field(self, vault):
        result = json.loads(await handle_tool_call("search", {"query": "alpha"}))
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert "excerpt" in item


# ---------------------------------------------------------------------------
# get_context
# ---------------------------------------------------------------------------

class TestGetContext:
    @pytest.mark.asyncio
    async def test_get_context_structure(self, vault):
        result = json.loads(await handle_tool_call("get_context", {"query": "alpha"}))
        assert "query" in result
        assert "context_notes" in result
        assert "related_followups" in result

    @pytest.mark.asyncio
    async def test_get_context_notes_have_excerpt(self, vault):
        result = json.loads(await handle_tool_call("get_context", {"query": "alpha"}))
        for note in result["context_notes"]:
            assert "excerpt" in note
            assert "relevance" in note

    @pytest.mark.asyncio
    async def test_get_context_followup_matching(self, vault):
        # Add a followup about alpha
        await handle_tool_call("add_followup", {"topic": "alpha topic", "reminder": "check alpha note"})
        result = json.loads(await handle_tool_call("get_context", {"query": "alpha"}))
        topics = [f["topic"] for f in result["related_followups"]]
        assert any("alpha" in t for t in topics)


# ---------------------------------------------------------------------------
# get_note_summary
# ---------------------------------------------------------------------------

class TestGetNoteSummary:
    @pytest.mark.asyncio
    async def test_truncation(self, vault):
        result = json.loads(await handle_tool_call("get_note_summary", {
            "identifier": "alpha",
            "max_chars": 10
        }))
        assert result["truncated"] is True
        assert result["body_preview"].endswith("...")
        assert len(result["body_preview"]) <= 13  # 10 + "..."

    @pytest.mark.asyncio
    async def test_no_truncation_when_body_short(self, vault):
        result = json.loads(await handle_tool_call("get_note_summary", {
            "identifier": "gamma",
            "max_chars": 5000
        }))
        assert result["truncated"] is False
        assert not result["body_preview"].endswith("...")

    @pytest.mark.asyncio
    async def test_not_found_error(self, vault):
        result = json.loads(await handle_tool_call("get_note_summary", {
            "identifier": "nonexistent-note-xyz"
        }))
        assert "error" in result


# ---------------------------------------------------------------------------
# followups: add → list → dismiss cycle
# ---------------------------------------------------------------------------

class TestFollowups:
    @pytest.mark.asyncio
    async def test_add_list_dismiss_cycle(self, vault):
        # Add
        add_result = json.loads(await handle_tool_call("add_followup", {
            "topic": "test topic",
            "reminder": "remember to do something"
        }))
        assert add_result["status"] == "success"
        followup_id = add_result["followup"]["id"]
        assert followup_id

        # List
        list_result = json.loads(await handle_tool_call("list_followups", {}))
        assert list_result["count"] >= 1
        ids = [f["id"] for f in list_result["followups"]]
        assert followup_id in ids

        # Dismiss
        dismiss_result = json.loads(await handle_tool_call("dismiss_followup", {"id": followup_id}))
        assert dismiss_result["status"] == "success"
        assert dismiss_result["dismissed_id"] == followup_id

        # Verify removed
        list_result2 = json.loads(await handle_tool_call("list_followups", {}))
        ids_after = [f["id"] for f in list_result2["followups"]]
        assert followup_id not in ids_after

    @pytest.mark.asyncio
    async def test_dismiss_nonexistent_returns_error(self, vault):
        result = json.loads(await handle_tool_call("dismiss_followup", {
            "id": "00000000-0000-0000-0000-000000000000"
        }))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_add_followup_has_required_fields(self, vault):
        result = json.loads(await handle_tool_call("add_followup", {
            "topic": "my topic",
            "reminder": "my reminder"
        }))
        followup = result["followup"]
        assert "id" in followup
        assert "topic" in followup
        assert "reminder" in followup
        assert "created" in followup


# ---------------------------------------------------------------------------
# list_stale_notes
# ---------------------------------------------------------------------------

class TestListStaleNotesHandler:
    @pytest.mark.asyncio
    async def test_expired_in_results(self, vault):
        result = json.loads(await handle_tool_call("list_stale_notes", {}))
        assert isinstance(result, list)
        ids = [n["id"] for n in result]
        assert "beta" in ids  # beta.md has expires: 2020-01-01

    @pytest.mark.asyncio
    async def test_future_expiry_absent(self, vault):
        result = json.loads(await handle_tool_call("list_stale_notes", {}))
        ids = [n["id"] for n in result]
        assert "gamma" not in ids  # gamma.md expires 2099

    @pytest.mark.asyncio
    async def test_expires_field_present(self, vault):
        result = json.loads(await handle_tool_call("list_stale_notes", {}))
        for item in result:
            assert "expires" in item
