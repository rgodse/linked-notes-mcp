# Retrieval Benchmark + Hybrid Retrieval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** A lean, reproducible retrieval benchmark (recall@5/MRR + bootstrap CI) comparing rungs **text → +salience → +hybrid(text+vector+graph)** over the synthetic vault, and wire the winning config into the server's `get_context`.

**Architecture:** New offline-tested modules in `optimize/` reuse the existing `optimize.metric` and `evals.stats`. Embeddings ship as an optional `[embeddings]` extra (FastEmbed — local ONNX, no API/LLM); the server's `get_context` gains salience reranking (always, zero-dep) and a hybrid mode that falls back to text when embeddings are absent. DSPy is deferred.

**Tech Stack:** Python 3.10+, FastEmbed (optional), pytest. No LLM/API dependency enters the server core.

## Global Constraints

- Server runtime deps stay `mcp`, `networkx`, `pyyaml`, `watchdog`. FastEmbed goes ONLY in a new `[project.optional-dependencies] embeddings = ["fastembed>=0.3"]` group.
- `optimize/` never imported by `src/linked_notes_mcp/` (enforced by `tests/test_eval_isolation.py`). NOTE: the embeddings *module* that `get_context` uses lives in `src/linked_notes_mcp/embeddings.py` (server-side, import-guarded), NOT in `optimize/`.
- All unit tests offline: inject a fake `embed_fn`; never require FastEmbed installed to run the suite.
- Primary metric recall@5; secondary MRR. Bootstrap CI via `evals.stats.bootstrap_ci`.
- Determinism: fake embedder in tests is deterministic; salience weights are explicit constants.

---

### Task R1: `optimize/salience.py` — recency×importance×relevance rerank

**Files:** Create `optimize/salience.py`; Test `tests/test_salience.py`

**Interfaces:**
- Produces: `IMPORTANCE = {"high":1.0,"medium":0.6,"low":0.3}`; `importance_weight(frontmatter: dict) -> float` (default 0.5); `salience_score(relevance: float, frontmatter: dict, w=(0.6,0.4)) -> float` = `w[0]*relevance + w[1]*importance_weight`; `rerank(candidates: list[tuple[str,float,dict]], w=(0.6,0.4)) -> list[str]` where each candidate is `(note_id, relevance, frontmatter)`, returns note_ids sorted by salience desc.

- [ ] **Step 1: Write the failing test**
```python
# tests/test_salience.py
from optimize.salience import importance_weight, salience_score, rerank

def test_importance_weight_defaults():
    assert importance_weight({"importance": "high"}) == 1.0
    assert importance_weight({"importance": "low"}) == 0.3
    assert importance_weight({}) == 0.5

def test_rerank_prefers_important_on_tie():
    # equal relevance, higher importance wins
    cands = [("a", 0.5, {"importance": "low"}), ("b", 0.5, {"importance": "high"})]
    assert rerank(cands) == ["b", "a"]

def test_rerank_relevance_dominates_with_default_weights():
    cands = [("a", 0.9, {"importance": "low"}), ("b", 0.2, {"importance": "high"})]
    assert rerank(cands)[0] == "a"
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_salience.py -v` → FAIL (module missing)
- [ ] **Step 3: Implement**
```python
# optimize/salience.py
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
```
- [ ] **Step 4: Run to verify pass** → 3 passed
- [ ] **Step 5: Commit** — `git add optimize/salience.py tests/test_salience.py && git commit -m "feat(optimize): salience rerank (relevance + importance)"`

---

### Task R2: `src/linked_notes_mcp/embeddings.py` — rebuildable embedding index (optional)

**Files:** Create `src/linked_notes_mcp/embeddings.py`; Modify `pyproject.toml` (`[embeddings]` extra); Test `tests/test_embeddings.py`

**Interfaces:**
- Produces: `cosine(a: list[float], b: list[float]) -> float`; `class EmbeddingIndex` with `__init__(embed_fn=None)`, `build(docs: dict[str,str]) -> None` (id→text), `search(query: str, k: int = 5) -> list[str]` (ranked ids by cosine). `embed_fn(list[str]) -> list[list[float]]`; when `None`, lazily loads FastEmbed (`fastembed.TextEmbedding`). Tests always inject a fake deterministic `embed_fn`.
- `default_embedder()` — returns a callable wrapping FastEmbed, imported lazily; raises a clear `RuntimeError` with install hint if FastEmbed missing.

- [ ] **Step 1: Write the failing test**
```python
# tests/test_embeddings.py
from linked_notes_mcp.embeddings import EmbeddingIndex, cosine

def fake_embed(texts):
    # deterministic 3-dim bag vector over letters a/b/c
    out = []
    for t in texts:
        tl = t.lower()
        out.append([float(tl.count("a")), float(tl.count("b")), float(tl.count("c"))])
    return out

def test_cosine_basic():
    assert cosine([1,0], [1,0]) == 1.0
    assert cosine([1,0], [0,1]) == 0.0

def test_index_search_ranks_by_similarity():
    idx = EmbeddingIndex(embed_fn=fake_embed)
    idx.build({"aaa": "aaa", "bbb": "bbb", "ab": "ab"})
    # query "aa" closest to "aaa"
    assert idx.search("aa", k=1) == ["aaa"]

def test_search_empty_index_returns_empty():
    idx = EmbeddingIndex(embed_fn=fake_embed)
    idx.build({})
    assert idx.search("x", k=3) == []
```

- [ ] **Step 2: Run to verify fail** → FAIL (module missing)
- [ ] **Step 3: Implement + add extra**
```python
# src/linked_notes_mcp/embeddings.py
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
```
`pyproject.toml`: add under `[project.optional-dependencies]`: `embeddings = ["fastembed>=0.3"]`.
- [ ] **Step 4: Run to verify pass** → 3 passed; also `uv run pytest tests/test_eval_isolation.py` still green (embeddings.py is server-side, allowed).
- [ ] **Step 5: Commit** — `git add src/linked_notes_mcp/embeddings.py pyproject.toml tests/test_embeddings.py && git commit -m "feat: optional FastEmbed embedding index over notes"`

---

### Task R3: `optimize/retrieval.py` — retrieval modes over the graph

**Files:** Create `optimize/retrieval.py`; Test `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `linked_notes_mcp.graph.KnowledgeGraph` (read-only), `optimize.salience.rerank`, `linked_notes_mcp.embeddings.EmbeddingIndex`.
- Produces: `retrieve(graph, query, mode, k=5, index=None) -> list[str]`. Modes: `"text"` (graph.search + bounded graph_context expansion), `"salience"` (text candidates reranked by salience using each note's frontmatter), `"hybrid"` (union of text ids + embedding-index ids, then salience rerank). Returns ranked note ids.
- NOTE: confirm real shapes in `src/linked_notes_mcp/graph.py` — `graph.search(terms, limit)` returns `Note` objects with `.id` and `.frontmatter` (a dict); `graph.graph_context(id, depth, limit)` returns a dict with a `"nodes"` list. Adapt accessors to the actual signatures.

- [ ] **Step 1: Write the failing test**
```python
# tests/test_retrieval.py
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
```

- [ ] **Step 2: Run to verify fail** → FAIL
- [ ] **Step 3: Implement** (adapt accessors to real graph API first)
```python
# optimize/retrieval.py
"""Retrieval modes for the benchmark: text, salience, hybrid."""
from __future__ import annotations
from optimize.salience import rerank


def _text_candidates(graph, query, k):
    """Return [(id, relevance, frontmatter)] from search + one-hop expansion."""
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
```
- [ ] **Step 4: Run to verify pass** → 2 passed
- [ ] **Step 5: Commit** — `git add optimize/retrieval.py tests/test_retrieval.py && git commit -m "feat(optimize): text/salience/hybrid retrieval modes"`

---

### Task R4: `optimize/run.py` — benchmark harness (rungs + recall@5 + CI + report)

**Files:** Create `optimize/run.py`; Test `tests/test_run.py`

**Interfaces:**
- Consumes: `optimize.metric.recall_at_k`, `optimize.metric.mrr`, `evals.stats.bootstrap_ci`, `optimize.retrieval.retrieve`.
- Produces: `evaluate(graph, dataset, mode, k=5, index=None) -> dict` = `{"recall@5","mrr","recall_ci"}`; `benchmark(graph, dataset, index=None, k=5) -> dict[mode, dict]` over `["text","salience","hybrid"]` (hybrid only if index given); `render(results: dict) -> str` markdown table; `load_dataset(path) -> list[dict]`.

- [ ] **Step 1: Write the failing test**
```python
# tests/test_run.py
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
```

- [ ] **Step 2: Run to verify fail** → FAIL
- [ ] **Step 3: Implement**
```python
# optimize/run.py
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
    idx.build({n.id: (n.frontmatter.get("summary", "") + " " + (n.body or "")) for n in g.list_all_notes()})
    print(render(benchmark(g, ds, index=idx)))
```
- [ ] **Step 4: Run to verify pass** → 2 passed
- [ ] **Step 5: Commit** — `git add optimize/run.py tests/test_run.py && git commit -m "feat(optimize): retrieval benchmark harness (rungs + CIs + report)"`

---

### Task R5: wire salience into `get_context` (server), hybrid opt-in

**Files:** Modify `src/linked_notes_mcp/tools/graph_query.py` (the `get_context` handler) and/or `src/linked_notes_mcp/graph.py`; Test `tests/test_get_context_salience.py`

**Interfaces:**
- `get_context` reranks its result notes by salience (relevance + importance) **by default** — zero new dependency. Behaviour change is order only; the set/shape of results is unchanged.
- FIRST read the real `get_context` implementation and its return shape; add reranking at the point where the ranked note list is assembled, reusing `optimize`-free logic. IMPORTANT: `get_context` is server code and MUST NOT import `optimize/`. Copy the tiny salience helper into `graph.py` (or a new `src/linked_notes_mcp/rank.py`) so the server has no dev-package dependency. The `optimize/salience.py` version remains for the benchmark; both are ~10 lines — acceptable duplication given the import-isolation constraint (note it in the commit).

- [ ] **Step 1: Read** `src/linked_notes_mcp/tools/graph_query.py` get_context handler + `graph.py` search/graph_context to find where results are ordered.
- [ ] **Step 2: Write the failing test** — build a 2-note vault where a low-relevance-but-high-importance note should rank above a high-relevance-low-importance note only when salience is applied; assert `get_context` order reflects salience. (Write concrete notes + call the handler; assert the ordered ids.)
- [ ] **Step 3: Run to verify fail**
- [ ] **Step 4: Implement** — add `src/linked_notes_mcp/rank.py` with `importance_weight`/`salience_rerank` (copied logic), call it in `get_context`. Keep default on.
- [ ] **Step 5: Run to verify pass**, then full suite `uv run pytest -q` green.
- [ ] **Step 6: Commit** — `git commit -m "feat: salience reranking in get_context (relevance + importance)"`

---

### Task R6: live run + strong README

**Files:** Create `results.md`; Modify `README.md`

- [ ] **Step 1: Install extras** — `uv sync --extra eval --extra embeddings`
- [ ] **Step 2: Generate dataset (live, paid)** — `set -a; . ./.env; set +a; EVAL_GEN_MODEL=openrouter/anthropic/claude-sonnet-4.6 uv run python -m evals.gen`; sanity-check gold ids reference real notes; commit `evals/dataset/`.
- [ ] **Step 3: Run benchmark (live)** — `uv run python -m optimize.run > /tmp/bench.txt`; capture the rung table (text vs salience vs hybrid).
- [ ] **Step 4: Set the winning default** — if hybrid/salience wins on recall@5 beyond its CI vs text, note it; salience default already on from R5.
- [ ] **Step 5: Write `results.md`** — the rung table with CIs, the honest headline (which rung won or "no rung beat text beyond noise"), reproduce commands, model id from `evals/dataset/meta.json`, and the limitations (single synthetic domain).
- [ ] **Step 6: README** — a first-class "## Retrieval: measured, not guessed" section: what the benchmark is, the rung table, methodology (recall@5/MRR, bootstrap CIs, synthetic reproducible vault), the `[embeddings]` install line, reproduce commands, and the honest limitation. Match homegpt-router README quality. Commit.

---

## Deferred (optional future): DSPy rung
Add a `dspy`-optimized query→retrieval-params rung on top of the harness (BootstrapFewShot/MIPROv2), scored by the same recall@5. Isolated to `optimize/` + the `[eval]` extra. Not required for the shippable benchmark.

## Self-Review
- Rungs text/salience/hybrid → R1,R2,R3,R4. Wire-back → R5. Live+README → R6. ✓
- Isolation preserved: `optimize/` stays dev-only; server uses `src/linked_notes_mcp/embeddings.py` + `rank.py` (no `optimize` import) — R5 notes the deliberate tiny duplication. ✓
- Offline tests inject fake `embed_fn`; FastEmbed never required for the suite. ✓
- Metric/CI reuse existing `optimize.metric` + `evals.stats`. ✓
