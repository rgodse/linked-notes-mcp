"""Unit tests for src/linked_notes_mcp/rank.py salience reranking."""

from types import SimpleNamespace

from linked_notes_mcp.rank import importance_weight, salience_rerank


def _note(frontmatter: dict, note_id: str = "x"):
    """Create a minimal Note-like object with only the attributes rank.py needs."""
    return SimpleNamespace(frontmatter=frontmatter, id=note_id)


class TestImportanceWeight:
    def test_high(self):
        assert importance_weight({"importance": "high"}) == 1.0

    def test_medium(self):
        assert importance_weight({"importance": "medium"}) == 0.6

    def test_low(self):
        assert importance_weight({"importance": "low"}) == 0.3

    def test_missing_defaults_to_0_5(self):
        assert importance_weight({}) == 0.5

    def test_unknown_value_defaults_to_0_5(self):
        assert importance_weight({"importance": "critical"}) == 0.5

    def test_case_insensitive(self):
        assert importance_weight({"importance": "HIGH"}) == 1.0
        assert importance_weight({"importance": "Medium"}) == 0.6


class TestSalienceRerank:
    def test_reorder_by_importance(self):
        """Notes at ranks 1 and 2 flip: rank-2 high-importance beats rank-1 low-importance.

        Scores:
          a rank 0: 0.6*1.0 + 0.4*0.6 = 0.84  (stays first)
          b rank 1: 0.6*0.5 + 0.4*0.3 = 0.42  (drops to third)
          c rank 2: 0.6*(1/3) + 0.4*1.0 = 0.60 (rises to second)
        """
        note_a = _note({"importance": "medium"}, "a")
        note_b = _note({"importance": "low"}, "b")
        note_c = _note({"importance": "high"}, "c")

        reranked = salience_rerank([note_a, note_b, note_c])

        assert [n.id for n in reranked] == ["a", "c", "b"]

    def test_preserves_complete_set(self):
        """All input notes appear in output exactly once."""
        note_x = _note({}, "x")
        note_y = _note({"importance": "high"}, "y")
        reranked = salience_rerank([note_x, note_y])
        assert {n.id for n in reranked} == {"x", "y"}
        assert len(reranked) == 2

    def test_single_note_unchanged(self):
        note = _note({"importance": "high"}, "solo")
        reranked = salience_rerank([note])
        assert reranked[0].id == "solo"

    def test_empty_list(self):
        assert salience_rerank([]) == []

    def test_high_importance_at_lower_rank_beats_medium_at_higher_rank(self):
        """Demonstrate that a lower-search-rank note with higher importance can beat
        a higher-search-rank note with medium importance (between ranks 1 and 2)."""
        note_a = _note({"importance": "medium"}, "a")  # rank 0
        note_b = _note({"importance": "medium"}, "b")  # rank 1: 0.6*0.5 + 0.4*0.6 = 0.54
        note_c = _note({"importance": "high"}, "c")    # rank 2: 0.6*(1/3) + 0.4*1.0 = 0.60

        reranked = salience_rerank([note_a, note_b, note_c])
        ids = [n.id for n in reranked]
        # c (rank 2) should outrank b (rank 1) after reranking
        assert ids.index("c") < ids.index("b")
