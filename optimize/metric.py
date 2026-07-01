"""Retrieval metrics: recall@k and MRR. Pure functions."""
from __future__ import annotations


def recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return 1.0
    topk = set(retrieved[:k])
    hits = sum(1 for g in gold if g in topk)
    return hits / len(gold)


def mrr(retrieved: list[str], gold: list[str]) -> float:
    gold_set = set(gold)
    for rank, note_id in enumerate(retrieved, start=1):
        if note_id in gold_set:
            return 1.0 / rank
    return 0.0
