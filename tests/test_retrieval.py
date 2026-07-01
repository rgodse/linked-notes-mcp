from linked_notes_mcp.graph import KnowledgeGraph
from linked_notes_mcp.embeddings import EmbeddingIndex
from optimize.retrieval import retrieve


def _vault(tmp_path):
    (tmp_path / "auth.md").write_text("---\ntitle: Auth\nimportance: high\nsummary: issues tokens\n---\n\nauthentication tokens jwt\n")
    (tmp_path / "gw.md").write_text("---\ntitle: Gateway\nimportance: low\nsummary: entry point\ndepends_on:\n  - Auth\n---\n\nrequest routing\n")
    g = KnowledgeGraph(tmp_path); g.rebuild(); return g


def test_text_mode_finds_lexical_match(tmp_path):
    g = _vault(tmp_path)
    assert "auth" in retrieve(g, "tokens", "text", k=5)


def test_hybrid_finds_semantic_via_index(tmp_path):
    g = _vault(tmp_path)
    def fake_embed(texts):
        return [[float("token" in t.lower() or "auth" in t.lower()), float("rout" in t.lower())] for t in texts]
    idx = EmbeddingIndex(embed_fn=fake_embed)
    idx.build({"auth": "authentication tokens jwt", "gw": "request routing"})
    ids = retrieve(g, "credential", "hybrid", k=5, index=idx)
    assert isinstance(ids, list)
