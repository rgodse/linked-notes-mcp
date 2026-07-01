from linked_notes_mcp.embeddings import EmbeddingIndex, cosine


def fake_embed(texts):
    # deterministic 3-dim bag vector over letters a/b/c
    out = []
    for t in texts:
        tl = t.lower()
        out.append([float(tl.count("a")), float(tl.count("b")), float(tl.count("c"))])
    return out


def test_cosine_basic():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0


def test_index_search_ranks_by_similarity():
    idx = EmbeddingIndex(embed_fn=fake_embed)
    idx.build({"aaa": "aaa", "bbb": "bbb", "ab": "ab"})
    # query "aa" closest to "aaa"
    assert idx.search("aa", k=1) == ["aaa"]


def test_search_empty_index_returns_empty():
    idx = EmbeddingIndex(embed_fn=fake_embed)
    idx.build({})
    assert idx.search("x", k=3) == []
