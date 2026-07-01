"""Rerank retrieval candidates by relevance + note importance."""
from __future__ import annotations

IMPORTANCE = {"high": 1.0, "medium": 0.6, "low": 0.3}


def importance_weight(frontmatter: dict) -> float:
    return IMPORTANCE.get(str(frontmatter.get("importance", "")).lower(), 0.5)


def salience_score(relevance: float, frontmatter: dict, w: tuple[float, float] = (0.6, 0.4)) -> float:
    return w[0] * relevance + w[1] * importance_weight(frontmatter)


def rerank(candidates: list[tuple[str, float, dict]], w: tuple[float, float] = (0.6, 0.4)) -> list[str]:
    scored = [(nid, salience_score(rel, fm, w)) for nid, rel, fm in candidates]
    scored.sort(key=lambda t: t[1], reverse=True)
    return [nid for nid, _ in scored]
