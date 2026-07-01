"""Salience reranking for get_context (server-local copy).

Logic is intentionally duplicated from optimize/salience.py to preserve
import isolation: server code must never import from optimize/ or evals/.
See tests/test_eval_isolation.py for the enforcement rule.
"""
from __future__ import annotations

IMPORTANCE = {"high": 1.0, "medium": 0.6, "low": 0.3}


def importance_weight(frontmatter: dict) -> float:
    return IMPORTANCE.get(str(frontmatter.get("importance", "")).lower(), 0.5)


def salience_scores(notes, w=(0.6, 0.4)) -> dict:
    """note.id -> salience score, from search-rank order (best first).
    Single source of truth for the score, used for both ordering and display."""
    return {
        note.id: w[0] * (1.0 / (rank + 1)) + w[1] * importance_weight(note.frontmatter)
        for rank, note in enumerate(notes)
    }


def salience_rerank(notes, w=(0.6, 0.4)):
    """notes: list[Note] in search-rank order (best first) -> reordered by salience."""
    scores = salience_scores(notes, w)
    ranked = sorted(enumerate(notes), key=lambda t: (scores[t[1].id], -t[0]), reverse=True)
    return [note for _, note in ranked]
