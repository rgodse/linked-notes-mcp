"""Integration tests: salience reranking is wired into _handle_get_context.

Vault design (query = "foobar"):
  x-anchor  title match (score 13)  importance=medium  rank 0
  y-mid     tag   match (score  6)  importance=low     rank 1
  z-low     body  match (score  5)  importance=high    rank 2

Salience scores (w = 0.6, 0.4):
  x-anchor  rank 0  0.6*1.0 + 0.4*0.6 = 0.84
  y-mid     rank 1  0.6*0.5 + 0.4*0.3 = 0.42
  z-low     rank 2  0.6*(1/3) + 0.4*1.0 = 0.60

After reranking: [x-anchor, z-low, y-mid]  (y-mid and z-low flip)
"""

import json
from pathlib import Path

from linked_notes_mcp.graph import KnowledgeGraph
from linked_notes_mcp.tools.session import _handle_get_context


def _build_vault(tmp_path: Path) -> KnowledgeGraph:
    """Three-note vault designed so salience provably reorders the last two notes."""
    # x-anchor: title = "Foobar Anchor" → +10 title, +1 body, +2 importance(medium) = 13
    (tmp_path / "x-anchor.md").write_text(
        "---\ntitle: Foobar Anchor\nimportance: medium\n---\n\n"
        "This is the anchor note about foobar.\n"
    )
    # y-mid: tag foobar → +5, +1 body, +0 importance(low) = 6
    (tmp_path / "y-mid.md").write_text(
        "---\ntitle: Mid Note\ntags: [foobar]\nimportance: low\n---\n\n"
        "Content about foobar here.\n"
    )
    # z-low: body only → +1, +4 importance(high) = 5  (below y-mid in raw search)
    (tmp_path / "z-low.md").write_text(
        "---\ntitle: Low Note\nimportance: high\n---\n\n"
        "Content mentioning foobar somewhere.\n"
    )
    return KnowledgeGraph(tmp_path)


def test_salience_rerank_changes_context_notes_order(tmp_path):
    """Salience reranking changes the order of context_notes vs raw search order."""
    graph = _build_vault(tmp_path)
    raw_ids = [n.id for n in graph.search("foobar", 10)]

    result = json.loads(_handle_get_context({"query": "foobar", "limit": 10}, graph))
    context_ids = [n["id"] for n in result["context_notes"]]

    # Same set of notes, different order
    assert set(context_ids) == set(raw_ids)
    assert context_ids != raw_ids, "Salience reranking should change the order"


def test_high_importance_note_rises_above_low_importance(tmp_path):
    """z-low (high importance, rank 2 in search) overtakes y-mid (low importance, rank 1)."""
    graph = _build_vault(tmp_path)
    result = json.loads(_handle_get_context({"query": "foobar", "limit": 10}, graph))
    context_ids = [n["id"] for n in result["context_notes"]]

    z_pos = context_ids.index("z-low")
    y_pos = context_ids.index("y-mid")
    assert z_pos < y_pos, (
        f"z-low (high importance) should rank above y-mid (low importance) after salience "
        f"reranking; got context_ids={context_ids}"
    )


def test_relevance_field_is_meaningful_float(tmp_path):
    """brief['relevance'] is a float salience score, not the hardcoded int 1."""
    graph = _build_vault(tmp_path)
    result = json.loads(_handle_get_context({"query": "foobar", "limit": 10}, graph))
    for note in result["context_notes"]:
        assert "relevance" in note
        assert isinstance(note["relevance"], float), (
            f"relevance should be float, got {type(note['relevance'])} = {note['relevance']}"
        )
        assert 0.0 < note["relevance"] <= 1.0


def test_graph_context_anchors_on_salience_first_note(tmp_path):
    """graph_context anchor is the first note after salience reranking, not raw search."""
    graph = _build_vault(tmp_path)
    result = json.loads(_handle_get_context({"query": "foobar", "limit": 10}, graph))
    context_ids = [n["id"] for n in result["context_notes"]]
    anchor = result["graph_context"]["anchor"]
    assert anchor == context_ids[0], (
        f"graph_context anchor should be first note after salience reranking; "
        f"got anchor={anchor!r}, context_ids[0]={context_ids[0]!r}"
    )
