"""Optional rebuildable embedding index over note text. FastEmbed is lazy + optional."""
from __future__ import annotations
import math


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def default_embedder():
    try:
        from fastembed import TextEmbedding
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("hybrid retrieval needs the embeddings extra: pip install 'linked-notes-mcp[embeddings]'") from e
    model = TextEmbedding()
    def embed(texts: list[str]) -> list[list[float]]:
        return [list(v) for v in model.embed(texts)]
    return embed


class EmbeddingIndex:
    def __init__(self, embed_fn=None):
        self._embed_fn = embed_fn
        self._ids: list[str] = []
        self._vecs: list[list[float]] = []

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if self._embed_fn is None:
            self._embed_fn = default_embedder()
        return self._embed_fn(texts)

    def build(self, docs: dict[str, str]) -> None:
        self._ids = list(docs.keys())
        self._vecs = self._embed(list(docs.values())) if docs else []

    def search(self, query: str, k: int = 5) -> list[str]:
        if not self._ids:
            return []
        qv = self._embed([query])[0]
        scored = sorted(zip(self._ids, self._vecs), key=lambda t: cosine(qv, t[1]), reverse=True)
        return [nid for nid, _ in scored[:k]]
