"""Retrieval benchmark: score rungs on recall@5/MRR with bootstrap CIs."""
from __future__ import annotations
import json
from pathlib import Path
from optimize.metric import recall_at_k, mrr
from optimize.retrieval import retrieve
from evals.stats import bootstrap_ci


def load_dataset(path: str) -> list[dict]:
    return json.loads(Path(path).read_text())


def evaluate(graph, dataset: list[dict], mode: str, k: int = 5, index=None) -> dict:
    recalls, rrs = [], []
    for row in dataset:
        ids = retrieve(graph, row["query"], mode, k=k, index=index)
        recalls.append(recall_at_k(ids, row["gold_note_ids"], k))
        rrs.append(mrr(ids, row["gold_note_ids"]))
    n = len(dataset)
    return {"recall@5": sum(recalls) / n, "mrr": sum(rrs) / n, "recall_ci": bootstrap_ci(recalls, seed=0)}


def benchmark(graph, dataset: list[dict], index=None, k: int = 5) -> dict:
    modes = ["text", "salience"] + (["hybrid"] if index is not None else [])
    return {m: evaluate(graph, dataset, m, k=k, index=index) for m in modes}


def render(results: dict) -> str:
    lines = ["| Rung | recall@5 | 95% CI | MRR |", "|---|---|---|---|"]
    for mode, r in results.items():
        lo, hi = r["recall_ci"]
        lines.append(f"| {mode} | {r['recall@5']:.2f} | {lo:.2f}–{hi:.2f} | {r['mrr']:.2f} |")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    from linked_notes_mcp.graph import KnowledgeGraph
    from linked_notes_mcp.embeddings import EmbeddingIndex, default_embedder
    g = KnowledgeGraph(Path("evals/dataset/vault")); g.rebuild()
    ds = load_dataset("evals/dataset/queries.json")
    idx = EmbeddingIndex(embed_fn=default_embedder())
    idx.build({n.id: (n.frontmatter.get("summary", "") + " " + (n.content or "")) for n in g.list_all_notes()})
    print(render(benchmark(g, ds, index=idx)))
