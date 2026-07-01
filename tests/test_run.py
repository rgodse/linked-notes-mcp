from linked_notes_mcp.graph import KnowledgeGraph
from optimize.run import evaluate, render


def _vault(tmp_path):
    (tmp_path / "auth.md").write_text("---\ntitle: Auth\nimportance: high\n---\n\ntokens\n")
    (tmp_path / "gw.md").write_text("---\ntitle: Gateway\nimportance: low\n---\n\nrouting\n")
    g = KnowledgeGraph(tmp_path); g.rebuild(); return g


def test_evaluate_scores_and_cis(tmp_path):
    g = _vault(tmp_path)
    ds = [{"id": "q1", "query": "tokens", "gold_note_ids": ["auth"]}]
    r = evaluate(g, ds, "text", k=5)
    assert r["recall@5"] == 1.0
    assert r["recall_ci"][0] <= r["recall@5"] <= r["recall_ci"][1]


def test_render_table():
    md = render({"text": {"recall@5": 1.0, "mrr": 1.0, "recall_ci": (0.9, 1.0)}})
    assert "text" in md and "1.00" in md and md.count("|") >= 6
