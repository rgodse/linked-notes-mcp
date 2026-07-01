"""Salience reranking for get_context (server-local copy).

Logic is intentionally duplicated from optimize/salience.py to preserve
import isolation: server code must never import from optimize/ or evals/.
See tests/test_eval_isolation.py for the enforcement rule.
"""
from __future__ import annotations

IMPORTANCE = {"high": 1.0, "medium": 0.6, "low": 0.3}


def importance_weight(frontmatter: dict) -> float:
    return IMPORTANCE.get(str(frontmatter.get("importance", "")).lower(), 0.5)


def salience_rerank(notes, w=(0.6, 0.4)):
    """notes: list[Note] in search-rank order (best first) -> reordered by salience."""
    scored = []
    for rank, note in enumerate(notes):
        relevance = 1.0 / (rank + 1)
        score = w[0] * relevance + w[1] * importance_weight(note.frontmatter)
        scored.append((score, rank, note))
    scored.sort(key=lambda t: (t[0], -t[1]), reverse=True)
    return [n for _, _, n in scored]
