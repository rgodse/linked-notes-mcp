"""Retrieval modes for the benchmark: text, salience, hybrid."""
from __future__ import annotations
from optimize.salience import rerank


def _text_candidates(graph, query, k):
    """Return [(id, relevance, frontmatter)] from lexical search (top-k). No graph expansion."""
    hits = graph.search(query, limit=k)
    cands, seen = [], set()
    for rank, note in enumerate(hits):
        if note.id in seen:
            continue
        seen.add(note.id)
        cands.append((note.id, 1.0 / (rank + 1), dict(note.frontmatter)))
    return cands


def retrieve(graph, query: str, mode: str, k: int = 5, index=None) -> list[str]:
    cands = _text_candidates(graph, query, k)
    if mode == "text":
        return [c[0] for c in cands][:k * 2]
    if mode == "salience":
        return rerank(cands)[:k * 2]
    if mode == "hybrid":
        ids = {c[0]: c for c in cands}
        if index is not None:
            for nid in index.search(query, k=k):
                if nid not in ids:
                    note = graph.get_note(nid)
                    fm = dict(note.frontmatter) if note else {}
                    ids[nid] = (nid, 0.5, fm)
        return rerank(list(ids.values()))[:k * 2]
    raise ValueError(f"unknown mode: {mode}")
