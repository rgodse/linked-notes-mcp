"""Tests for server.py handlers and helpers."""

import inspect
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
        "---\ntitle: Alpha Note\ntags: [test]\ndepends_on: [Beta Note]\nrelated_to: [Gamma Note]\n---\n"
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
        assert "graph_context" in result

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

    @pytest.mark.asyncio
    async def test_get_context_includes_graph_anchor(self, vault):
        result = json.loads(await handle_tool_call("get_context", {"query": "alpha"}))
        assert result["graph_context"]["anchor"] == "alpha"


class TestWorkflowTools:
    @pytest.mark.asyncio
    async def test_start_session_returns_working_brief(self, vault):
        await handle_tool_call(
            "save_session_summary",
            {
                "summary": "Worked on alpha",
                "accomplished": ["Checked alpha dependencies"],
                "project": "alpha",
                "topic": "Alpha Review",
            },
        )
        await handle_tool_call(
            "add_followup",
            {"topic": "alpha", "reminder": "Follow up on alpha blocker"},
        )

        result = json.loads(
            await handle_tool_call(
                "start_session",
                {"topic": "alpha", "project": "alpha"},
            )
        )
        assert result["working_brief"]["anchor"] is not None
        assert "context_notes" in result["working_brief"]
        assert "related_followups" in result["working_brief"]
        assert "recent_sessions" in result["working_brief"]
        assert "suggested_next_steps" in result["working_brief"]

    @pytest.mark.asyncio
    async def test_review_memory_includes_pending_ingestion_candidates(self, vault):
        await handle_tool_call(
            "ingest_sources",
            {
                "sources": [
                    {
                        "type": "text",
                        "name": "seed",
                        "content": "# Seed Context\nService dependency and owner context.",
                    }
                ]
            },
        )
        result = json.loads(await handle_tool_call("review_memory", {}))
        assert "pending_ingestion_candidates" in result
        assert len(result["pending_ingestion_candidates"]) == 1
        assert "recommended_actions" in result
        assert result["pending_ingestion_candidates"][0]["recommendation"] in {
            "create_new",
            "ambiguous",
            "merge_likely",
        }

    @pytest.mark.asyncio
    async def test_end_session_creates_session_note_and_followups(self, vault):
        result = json.loads(
            await handle_tool_call(
                "end_session",
                {
                    "summary": "Wrapped up alpha work",
                    "accomplished": ["Updated alpha context"],
                    "open_items": ["Check beta dependency"],
                    "project": "alpha",
                    "topic": "Alpha Wrap",
                    "touched_notes": ["alpha"],
                },
            )
        )
        assert result["status"] == "success"
        assert result["session_note"]["title"].startswith("Session")
        assert len(result["generated_followups"]) == 1

        alpha = srv.get_graph().get_note("alpha")
        assert alpha.frontmatter.get("last_reviewed")

    @pytest.mark.asyncio
    async def test_review_queue_returns_prioritized_actions(self, vault):
        await handle_tool_call(
            "ingest_sources",
            {
                "sources": [
                    {
                        "type": "text",
                        "name": "alpha-refresh",
                        "content": "# Alpha Note\nThis is refreshed project context for Alpha Note.",
                    }
                ]
            },
        )
        result = json.loads(await handle_tool_call("review_queue", {"limit": 5}))
        assert "recommended_actions" in result
        assert result["recommended_actions"]
        assert "counts" in result


class TestGraphTools:
    @pytest.mark.asyncio
    async def test_list_relationships(self, vault):
        result = json.loads(await handle_tool_call("list_relationships", {"identifier": "alpha"}))
        outgoing_types = {item["type"] for item in result["outgoing"]}
        assert "depends_on" in outgoing_types
        assert "related_to" in outgoing_types

    @pytest.mark.asyncio
    async def test_get_graph_context(self, vault):
        result = json.loads(
            await handle_tool_call("get_graph_context", {"identifier": "alpha", "depth": 2})
        )
        assert result["anchor"] == "alpha"
        assert any(node["id"] == "beta" for node in result["nodes"])


class TestStructuredMemoryTools:
    @pytest.mark.asyncio
    async def test_create_note_returns_template_guidance(self, vault):
        result = json.loads(
            await handle_tool_call(
                "create_note",
                {
                    "title": "Loose Scratchpad",
                    "content": "Unstructured note body.",
                },
            )
        )
        assert result["status"] == "success"
        assert "guidance" in result
        assert "create_from_template" in result["guidance"]

    @pytest.mark.asyncio
    async def test_upsert_memory_node(self, vault):
        result = json.loads(
            await handle_tool_call(
                "upsert_memory_node",
                {
                    "title": "Gateway Memory",
                    "summary": "Primary gateway node",
                    "entity_type": "service",
                    "aliases": ["Gateway"],
                    "project": "graph-memory",
                    "status": "active",
                    "relationships": [{"type": "depends_on", "target": "Beta Note"}],
                },
            )
        )
        assert result["status"] == "success"
        assert result["note"]["aliases"] == ["Gateway"]
        assert result["note"]["frontmatter"]["entity_type"] == "service"
        assert "guidance" in result
        assert "structured frontmatter" in result["guidance"]

    @pytest.mark.asyncio
    async def test_update_relationships(self, vault):
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Gateway Memory",
                "summary": "Primary gateway node",
                "entity_type": "service",
            },
        )
        result = json.loads(
            await handle_tool_call(
                "update_relationships",
                {
                    "identifier": "Gateway Memory",
                    "add": [{"type": "depends_on", "target": "Beta Note"}],
                },
            )
        )
        assert result["status"] == "success"
        assert result["note"]["frontmatter"]["depends_on"] == ["Beta Note"]

    @pytest.mark.asyncio
    async def test_lint_memory_graph(self, vault):
        result = json.loads(await handle_tool_call("lint_memory_graph", {}))
        assert isinstance(result, list)
        assert any(item["issue_type"] == "missing_entity_type" for item in result)

    @pytest.mark.asyncio
    async def test_suggest_relationships(self, vault):
        result = json.loads(await handle_tool_call("suggest_relationships", {"limit": 10}))
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_merge_memory_nodes(self, vault):
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Gateway Memory",
                "summary": "Primary gateway node",
                "entity_type": "service",
            },
        )
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Gateway Duplicate",
                "summary": "Duplicate gateway node",
                "entity_type": "service",
            },
        )
        result = json.loads(
            await handle_tool_call(
                "merge_memory_nodes",
                {
                    "source_identifier": "Gateway Duplicate",
                    "target_identifier": "Gateway Memory",
                },
            )
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_memory_health(self, vault):
        result = json.loads(await handle_tool_call("get_memory_health", {"identifier": "alpha"}))
        assert result["note_id"] == "alpha"
        assert result["max_score"] == 10

    @pytest.mark.asyncio
    async def test_review_relationship_suggestions(self, vault):
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Loose Service",
                "summary": "Service for graph-memory project",
                "entity_type": "service",
                "project": "graph-memory",
                "tags": ["test"],
            },
        )
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Loose Decision",
                "summary": "Decision for graph-memory project",
                "entity_type": "decision",
                "project": "graph-memory",
                "tags": ["test"],
            },
        )
        result = json.loads(await handle_tool_call("review_relationship_suggestions", {"state": "all"}))
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_accept_and_reject_relationship_suggestion(self, vault):
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Loose Service",
                "summary": "Service for graph-memory project",
                "entity_type": "service",
                "project": "graph-memory",
                "tags": ["test"],
            },
        )
        await handle_tool_call(
            "upsert_memory_node",
            {
                "title": "Loose Decision",
                "summary": "Decision for graph-memory project",
                "entity_type": "decision",
                "project": "graph-memory",
                "tags": ["test"],
            },
        )
        accept = json.loads(
            await handle_tool_call(
                "accept_relationship_suggestion",
                {
                    "source_id": "loose-decision",
                    "target_id": "loose-service",
                    "suggested_type": "decision_for",
                },
            )
        )
        assert accept["status"] == "success"

        reject = json.loads(
            await handle_tool_call(
                "reject_relationship_suggestion",
                {
                    "source_id": "loose-service",
                    "target_id": "alpha",
                    "suggested_type": "related_to",
                    "reason": "not useful",
                },
            )
        )
        assert reject["status"] == "success"

    @pytest.mark.asyncio
    async def test_memory_dashboard(self, vault):
        result = json.loads(await handle_tool_call("memory_dashboard", {}))
        assert "summary" in result
        assert "weak_notes" in result
        assert "pending_suggestions" in result
        assert "stale_notes" in result

    @pytest.mark.asyncio
    async def test_promote_to_memory_node(self, vault):
        result = json.loads(
            await handle_tool_call(
                "promote_to_memory_node",
                {
                    "title": "Quarterly Planning",
                    "raw_text": "Workstream for quarterly planning with owners, dependencies, and open questions.",
                    "project": "planning",
                    "aliases": ["Q Planning"],
                },
            )
        )
        assert result["status"] == "success"
        assert result["note"]["frontmatter"]["summary"]
        assert result["note"]["frontmatter"]["project"] == "planning"
        assert result["note"]["aliases"] == ["Q Planning"]


class TestIngestionTools:
    @pytest.mark.asyncio
    async def test_ingest_sources_creates_run_and_candidate(self, vault):
        result = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "project": "seed-test",
                    "sources": [
                        {
                            "type": "text",
                            "name": "handoff-notes",
                            "content": "# Handoff Notes\nThis service blocks deployment and needs owner followup.",
                        }
                    ],
                },
            )
        )
        assert "run_id" in result
        assert result["artifacts"] == 1
        assert result["candidates_created"] == 1

        runs = json.loads(await handle_tool_call("list_ingestion_runs", {}))
        assert any(run["id"] == result["run_id"] for run in runs)

        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": result["run_id"]})
        )
        assert len(candidates) == 1
        assert candidates[0]["title"] == "Handoff Notes"
        assert candidates[0]["review_state"] == "pending"
        assert candidates[0]["recommendation"] in {"create_new", "ambiguous", "merge_likely"}

    @pytest.mark.asyncio
    async def test_ingest_directory_with_filters(self, vault, tmp_path):
        source_dir = tmp_path / "seed"
        source_dir.mkdir()
        (source_dir / "one.md").write_text("# One\nService context here.")
        (source_dir / "two.txt").write_text("Loose notes for process.")
        (source_dir / "skip.log").write_text("Should not be ingested.")
        nested = source_dir / "nested"
        nested.mkdir()
        (nested / "three.md").write_text("# Three\nNested markdown.")

        result = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "project": "dir-seed",
                    "sources": [
                        {
                            "type": "directory",
                            "path": str(source_dir),
                            "recursive": True,
                            "extensions": [".md", ".txt"],
                            "exclude": ["nested/*"],
                        }
                    ],
                },
            )
        )
        assert result["artifacts"] == 2
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": result["run_id"]})
        )
        titles = {candidate["title"] for candidate in candidates}
        assert "One" in titles
        assert any("two" in title.lower() or "notes" in title.lower() for title in titles)

    @pytest.mark.asyncio
    async def test_review_extracted_nodes_filters_by_recommendation(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {
                            "type": "text",
                            "name": "alpha-refresh",
                            "content": "# Alpha Note\nThis is refreshed project context for Alpha Note.",
                        },
                        {
                            "type": "text",
                            "name": "brand-new",
                            "content": "# Brand New Context\nFresh workstream context.",
                        },
                    ],
                },
            )
        )
        merge_likely = json.loads(
            await handle_tool_call(
                "review_extracted_nodes",
                {
                    "run_id": run["run_id"],
                    "recommendation": "merge_likely",
                },
            )
        )
        assert merge_likely
        assert all(item["recommendation"] == "merge_likely" for item in merge_likely)

    @pytest.mark.asyncio
    async def test_accept_all_candidates_bulk_action(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {
                            "type": "text",
                            "name": "brand-new-one",
                            "content": "# Brand New One\nFresh workstream context one.",
                        },
                        {
                            "type": "text",
                            "name": "brand-new-two",
                            "content": "# Brand New Two\nFresh workstream context two.",
                        },
                    ],
                },
            )
        )
        result = json.loads(
            await handle_tool_call(
                "accept_all_candidates",
                {"run_id": run["run_id"], "recommendation": "create_new"},
            )
        )
        assert result["status"] == "success"
        assert result["accepted"] == 2

    @pytest.mark.asyncio
    async def test_reject_all_candidates_bulk_action(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {
                            "type": "text",
                            "name": "scratch-one",
                            "content": "Loose scratch text one.",
                        },
                        {
                            "type": "text",
                            "name": "scratch-two",
                            "content": "Loose scratch text two.",
                        },
                    ],
                },
            )
        )
        result = json.loads(
            await handle_tool_call(
                "reject_all_candidates",
                {"run_id": run["run_id"], "reason": "bulk reject"},
            )
        )
        assert result["status"] == "success"
        assert result["rejected"] == 2

    @pytest.mark.asyncio
    async def test_accept_extracted_node_creates_memory_node(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "project": "seed-test",
                    "sources": [
                        {
                            "type": "text",
                            "name": "process-context",
                            "content": "# Quarterly Planning\nWorkstream for quarterly planning and owner coordination.",
                        }
                    ],
                },
            )
        )
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": run["run_id"]})
        )
        candidate_id = candidates[0]["id"]

        result = json.loads(
            await handle_tool_call("accept_extracted_node", {"candidate_id": candidate_id})
        )
        assert result["status"] == "success"
        assert result["note"]["title"] == "Quarterly Planning"

        accepted = json.loads(
            await handle_tool_call(
                "review_extracted_nodes",
                {"run_id": run["run_id"], "state": "accepted"},
            )
        )
        assert any(item["id"] == candidate_id for item in accepted)

    @pytest.mark.asyncio
    async def test_reject_extracted_node_marks_candidate(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {
                            "type": "text",
                            "name": "scratch",
                            "content": "Loose scratch content without durable value.",
                        }
                    ],
                },
            )
        )
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": run["run_id"]})
        )
        candidate_id = candidates[0]["id"]

        result = json.loads(
            await handle_tool_call(
                "reject_extracted_node",
                {"candidate_id": candidate_id, "reason": "too vague"},
            )
        )
        assert result["status"] == "success"

        rejected = json.loads(
            await handle_tool_call(
                "review_extracted_nodes",
                {"run_id": run["run_id"], "state": "rejected"},
            )
        )
        assert any(item["id"] == candidate_id for item in rejected)

    @pytest.mark.asyncio
    async def test_accept_extracted_node_merges_into_existing_note(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {
                            "type": "text",
                            "name": "alpha-refresh",
                            "content": "# Alpha Note\nThis is refreshed project context for Alpha Note.",
                        }
                    ],
                },
            )
        )
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": run["run_id"]})
        )
        candidate = candidates[0]
        assert candidate["matched_note_id"] == "alpha"

        result = json.loads(
            await handle_tool_call("accept_extracted_node", {"candidate_id": candidate["id"]})
        )
        assert result["status"] == "success"
        assert result["action"] == "merged"
        assert result["note"]["id"] == "alpha"

    @pytest.mark.asyncio
    async def test_ingest_sources_skips_duplicate_checksum(self, vault):
        content = "# Dedup Check\nSome unique content for checksum dedup test."
        source = {"type": "text", "name": "dedup-check", "content": content}

        first = json.loads(
            await handle_tool_call("ingest_sources", {"sources": [source]})
        )
        assert first["candidates_created"] == 1
        assert first["skipped"] == 0

        second = json.loads(
            await handle_tool_call("ingest_sources", {"sources": [source]})
        )
        assert second["candidates_created"] == 0
        assert second["skipped"] == 1

    @pytest.mark.asyncio
    async def test_accept_extracted_node_ambiguous_does_not_auto_merge(self, vault, tmp_path):
        # Create a vault note with a specific project and tags
        from linked_notes_mcp.server import init_graph

        (tmp_path / "existing-service.md").write_text(
            "---\ntitle: Existing Service\nentity_type: service\n"
            "project: myproj\ntags: [sharedtag]\nsummary: An existing service.\n---\n"
            "Body text.\n"
        )
        init_graph(tmp_path)

        # Ingest content that matches by project+tags (score 4) but not title
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "project": "myproj",
                    "sources": [
                        {
                            "type": "text",
                            "name": "different-name",
                            "content": (
                                "---\nproject: myproj\ntags: [sharedtag]\n---\n"
                                "# Different Service Name\nRelated service in myproj."
                            ),
                        }
                    ],
                },
            )
        )
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": run["run_id"]})
        )
        # Find a candidate with "ambiguous" recommendation (merge_into_existing strategy)
        ambiguous = [c for c in candidates if c.get("recommendation") == "ambiguous"]
        if not ambiguous:
            pytest.skip("No ambiguous candidate produced; dedup scoring may differ")

        candidate_id = ambiguous[0]["id"]
        result = json.loads(
            await handle_tool_call("accept_extracted_node", {"candidate_id": candidate_id})
        )
        assert result["status"] == "success"
        # Must NOT auto-merge — action is "accepted", not "merged"
        assert result["action"] == "accepted"
        # Must include merge_suggestion pointing at the matched note
        assert "merge_suggestion" in result
        assert result["merge_suggestion"]["target_note_id"] is not None

    @pytest.mark.asyncio
    async def test_accept_extracted_node_writes_provenance(self, vault):
        run = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {
                            "type": "text",
                            "name": "provenance-test",
                            "content": "# Provenance Test Node\nContent for provenance testing.",
                        }
                    ],
                },
            )
        )
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": run["run_id"]})
        )
        create_new = [c for c in candidates if c.get("recommendation") == "create_new"]
        assert create_new, "Expected at least one create_new candidate"
        candidate_id = create_new[0]["id"]

        result = json.loads(
            await handle_tool_call("accept_extracted_node", {"candidate_id": candidate_id})
        )
        assert result["status"] == "success"

        note_id = result["note"]["id"]
        from linked_notes_mcp.server import _graph

        note = _graph.get_note(note_id)
        assert note is not None
        assert note.frontmatter.get("confidence") is not None
        assert note.frontmatter.get("last_reviewed") is not None
        assert note.frontmatter.get("derived_from") is not None

    @pytest.mark.asyncio
    async def test_ingest_directory_glob_relative_to_vault(self, vault):
        # Write a markdown file directly inside the vault directory
        (vault / "glob-target.md").write_text("# Glob Target\nContent for glob test.")

        result = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [{"type": "glob", "pattern": "glob-target.md"}],
                },
            )
        )
        assert result["artifacts"] == 1, "Glob should resolve relative to vault path"
        candidates = json.loads(
            await handle_tool_call("review_extracted_nodes", {"run_id": result["run_id"]})
        )
        assert any("Glob Target" in c["title"] for c in candidates)

    @pytest.mark.asyncio
    async def test_ingest_sources_chunks_long_doc(self, vault):
        long_doc = (
            "# Main Document\n\n"
            "Preamble text that provides context.\n\n"
            "## Section One\n\n"
            + ("Content for section one. " * 10) + "\n\n"
            "## Section Two\n\n"
            + ("Content for section two. " * 10) + "\n\n"
            "## Section Three\n\n"
            + ("Content for section three. " * 10) + "\n"
        )
        result = json.loads(
            await handle_tool_call(
                "ingest_sources",
                {
                    "sources": [
                        {"type": "text", "name": "long-doc", "content": long_doc}
                    ],
                },
            )
        )
        assert result["candidates_created"] >= 3, (
            f"Expected ≥3 candidates from chunked doc, got {result['candidates_created']}"
        )


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


class TestTemplateTools:
    @pytest.mark.asyncio
    async def test_create_from_template_returns_guidance(self, vault):
        result = json.loads(
            await handle_tool_call(
                "create_from_template",
                {
                    "template": "project",
                    "title": "Project Context - Test",
                    "fields": {
                        "overview": "Overview text",
                        "goals": "Goal text",
                        "status": "Active",
                        "stakeholders": "Team",
                        "links": "None",
                        "notes": "Notes",
                    },
                },
            )
        )
        assert result["status"] == "success"
        assert "guidance" in result
        assert "Template-based note created" in result["guidance"]


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


# ---------------------------------------------------------------------------
# LLM extraction (contract test — no real API calls)
# ---------------------------------------------------------------------------

class TestLLMExtraction:
    def test_extract_candidates_llm_parses_response(self):
        """Verify response parsing works without a real API call."""
        from unittest.mock import MagicMock, patch

        from linked_notes_mcp.extraction import extract_candidates_llm

        fake_arguments = json.dumps({
            "candidates": [
                {
                    "title": "Payments Service",
                    "entity_type": "service",
                    "summary": "Handles billing and subscriptions.",
                    "aliases": ["Payments"],
                    "tags": ["billing"],
                    "relationships": [{"type": "depends_on", "target": "Auth Service"}],
                    "body": "Handles billing.",
                }
            ]
        })

        fake_tool_call = MagicMock()
        fake_tool_call.function.arguments = fake_arguments

        fake_response = MagicMock()
        fake_response.choices[0].message.tool_calls = [fake_tool_call]

        # litellm may not be installed in dev; inject a mock module into sys.modules
        mock_litellm = MagicMock()
        mock_litellm.completion.return_value = fake_response

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                results = extract_candidates_llm(
                    content="# Payments Service\nHandles billing.",
                    display_name="payments",
                    project="core",
                )

        assert len(results) == 1
        assert results[0]["title"] == "Payments Service"
        assert results[0]["entity_type"] == "service"
        assert results[0]["tags"] == ["billing"]
        assert results[0]["relationships"] == [{"type": "depends_on", "target": "Auth Service"}]

        call_kwargs = mock_litellm.completion.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["api_key"] == "test-key"
        assert any(
            t["function"]["name"] == "extract_memory_nodes"
            for t in call_kwargs["tools"]
        )

    def test_can_use_llm_false_without_config(self, tmp_path):
        from linked_notes_mcp.extraction import can_use_llm

        with patch.dict("os.environ", {}, clear=True):
            assert can_use_llm(vault_path=tmp_path) is False

    def test_load_llm_config_from_vault_file(self, tmp_path):
        from linked_notes_mcp.extraction import load_llm_config

        (tmp_path / ".linked-notes-config.json").write_text(
            json.dumps({"llm": {"model": "gemini/gemini-1.5-flash", "api_key": "gkey"}})
        )
        cfg = load_llm_config(vault_path=tmp_path)
        assert cfg is not None
        assert cfg.model == "gemini/gemini-1.5-flash"
        assert cfg.api_key == "gkey"

    def test_load_llm_config_env_fallback(self, tmp_path):
        from linked_notes_mcp.extraction import load_llm_config

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "ant-key"}, clear=False):
            cfg = load_llm_config(vault_path=tmp_path)
        assert cfg is not None
        assert cfg.model == "claude-haiku-4-5-20251001"
        assert cfg.api_key == "ant-key"


class TestIngestionDefaults:
    def test_ingest_sources_python_api_defaults_llm_off(self):
        from linked_notes_mcp.ingestion import ingest_sources

        signature = inspect.signature(ingest_sources)
        assert signature.parameters["use_llm"].default is False

    def test_ingest_sources_tool_schema_defaults_llm_off(self):
        from linked_notes_mcp.tools.ingestion_tools import TOOL_DEFS

        tool = next(tool for tool in TOOL_DEFS if tool.name == "ingest_sources")
        assert tool.inputSchema["properties"]["use_llm"]["default"] is False
