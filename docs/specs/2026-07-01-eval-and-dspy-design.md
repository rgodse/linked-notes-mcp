# Design: Evaluation + Optimization Artifacts for linked-notes-mcp

**Date:** 2026-07-01
**Status:** Approved design, pre-implementation

## Goal

Add two **dev-only, reproducible** artifacts beside the lean MCP server:

1. `evals/` — a **G-Eval note-quality harness** (LLM-as-judge) that measures whether the server's notes are good, retrievable memory nodes.
2. `optimize/` — a **DSPy retrieval study** that optimizes natural-language-query → graph-retrieval and measures the gain.

Both are studies, not server features. They are never imported by `src/linked_notes_mcp/`. The server core keeps **zero LLM dependencies**; all LLM usage lives behind an optional `[eval]` dependency group. The purpose is a coherent "eval-driven AI systems" story alongside homegpt-router (eval-driven router + DSPy GSM8K study) and Crucible (LLM-as-judge harness), with the rigor lessons from those baked in from the start.

## Non-goals

- Wiring evals/DSPy into the runtime MCP server.
- Re-introducing the removed LLM ingestion path.
- Multi-domain or production-trace datasets (single synthetic domain for v1).
- Reintroducing any removed tool.

## Repository layout

```
evals/
  __init__.py
  gen.py            # synthesize the domain vault + query->gold dataset
  rubric.yaml       # note-quality criteria + anchor examples
  degrade.py        # deterministic degradation transforms for pairwise twins
  quality.py        # pairwise judge run + report
  report.py         # shared reporting/table rendering
  dataset/          # COMMITTED generated corpus (reproducible without re-spend)
    vault/          #   ~50 generated .md notes
    queries.json    #   [{id, query, gold_note_ids:[...]}]
    meta.json       #   generator model, seed prompt hash, counts
optimize/
  __init__.py
  retrieval.py      # DSPy program: query -> retrieval params
  metric.py         # recall@k, MRR
  run.py            # baseline -> BootstrapFewShot -> MIPROv2 ladder w/ CIs
tests/
  test_metric.py        # recall@k, MRR (offline)
  test_degrade.py       # degradation transforms deterministic (offline)
  test_pairwise.py      # counterbalanced tally + bootstrap CI (offline, mocked judge)
  test_gen_schema.py    # dataset shape validation (offline)
results.md          # measured tables for both artifacts (README-facing)
```

Shared config module: `evals/config.py` (also imported by `optimize/`) resolves models + API base from env.

## 1. Dataset generation (`evals/gen.py`)

One coherent synthetic domain: a **software system** (services, decisions, issues, workstreams) using the existing template entity types (`service`, `decision`, `issue`, `project`, `concept`, `workstream`) and relationship fields (`depends_on`, `blocks`, `blocked_by`, `part_of`, `contains`, `decision_for`, `related_to`).

Procedure:
1. LLM generates ~50 interconnected notes with valid frontmatter, summaries, and typed edges that form a connected graph (a seed outline pins the entities so edges are consistent).
2. For ~40 facts spread across the vault, the LLM writes a natural-language query whose answer requires specific note(s); those note ids become the **gold relevant set**. Queries span single-hop ("what does the Payments service depend on?") and multi-hop ("which decision blocks the ledger migration?").
3. Output written to `evals/dataset/` and **committed**, so `python -m evals.quality` and `python -m optimize.run` reproduce published numbers with no generation spend. Re-running `python -m evals.gen` regenerates (guarded: refuses to overwrite unless `--force`).

`meta.json` records generator model id and a hash of the seed prompt for provenance.

## 2. Note-quality eval (`evals/quality.py`) — pairwise, not absolute

Absolute 1-5 scoring saturates on decent notes (the homegpt v1 lesson). Instead:

- For each note, `evals/degrade.py` produces a **degraded twin** via deterministic transforms, each introducing >=1 defect: strip `summary`, remove one typed relationship, remove `entity_type`/`aliases`, or bloat the body with off-topic filler. Transforms are pure functions (unit-tested), seeded per-note by note id for reproducibility.
- An **independent judge model** (different family from the generator) is shown the clean note and its degraded twin and picks the better memory node against `rubric.yaml`.
- **Order-counterbalanced**: each pair judged in both A/B orders to cancel position bias.
- **Bootstrap 95% CI** on the judge's preference accuracy (fraction of pairs where it correctly prefers the clean note).

Interpretation: judge accuracy is a **validity signal**. Near 1.0 means the rubric + judge reliably detect quality; near 0.5 means the judge cannot tell clean from degraded on that dimension and is not trustworthy (the Crucible κ instinct, applied to a ground-truth pair instead of human overrides). Reported per-dimension.

`rubric.yaml` dimensions, each with anchor examples:
- **Retrievability** — does the summary/frontmatter surface the note's key facts for search?
- **Frontmatter completeness** — `entity_type`, `summary`, relationships present and sensible.
- **Atomicity** — one coherent memory, not a dump of several.
- **Relationship accuracy** — typed edges point to real, correct targets.

## 3. DSPy retrieval study (`optimize/`)

**DSPy program** (`retrieval.py`): a `dspy.Module` with signature
`query -> search_terms: str, anchor_hint: str, depth: int, relation_filters: list[str]`.
The predicted params drive the server's real retrieval primitives (`KnowledgeGraph.search` + `graph_context`, i.e. the same code path behind the `get_context` tool) over the generated vault. No server code is modified; the study imports read-only from `linked_notes_mcp.graph`.

**Metric** (`metric.py`): primary **recall@5** (fraction of a query's gold notes present in the top-5 retrieved), secondary **MRR**. Pure functions, unit-tested.

**Ladder** (`run.py`), each rung scored on a held-out dev split with **bootstrap 95% CIs**:
1. **Baseline** — raw query string → `search` (no DSPy).
2. **BootstrapFewShot** — auto-selected demos.
3. **MIPROv2 (light)** — auto-rewritten instructions + demos.

Honest headline in `results.md`: "DSPy lifted recall@5 from X to Y on a cheap student model," with CIs and the winning rung named. If no rung beats baseline beyond noise, that is reported plainly (the homegpt honesty standard).

## 4. Models & configuration (`evals/config.py`)

Resolved from env, defaults to OpenRouter (OpenAI-compatible):
- `OPENROUTER_KEY` (or `LLM_API_KEY`) + optional `LLM_BASE_URL`
- `EVAL_GEN_MODEL` — corpus generator (capable model)
- `EVAL_JUDGE_MODEL` — independent judge, **different family** from the generator
- `DSPY_STUDENT_MODEL` — cheap model with headroom (so optimization can show gains)

`litellm` and `dspy-ai` live only in the `[eval]` optional-dependency group in `pyproject.toml`. The server's runtime deps are unchanged.

## 5. Testing

Offline, LLM-mocked unit tests (mirrors homegpt's fully-offline suite):
- `test_metric.py` — recall@k and MRR on hand-built retrieval/gold fixtures.
- `test_degrade.py` — each degradation transform is deterministic and introduces the intended defect.
- `test_pairwise.py` — counterbalanced tally and bootstrap CI math on a mocked judge returning a fixed pattern.
- `test_gen_schema.py` — `dataset/queries.json` and generated notes match expected shape (runs against the committed dataset; no LLM).

One live smoke test (gated behind an API key env var, skipped in CI) confirms real generation/judge/DSPy calls work end to end.

## 6. Build order

Each stage is independently runnable and valuable, so we can stop at any point:
1. **Dataset** (`evals/gen.py` + committed `dataset/`) — unblocks both artifacts.
2. **Eval harness** (`degrade.py`, `rubric.yaml`, `quality.py`, report) — first measured result.
3. **DSPy study** (`retrieval.py`, `metric.py`, `run.py`) — second measured result.
4. **README** — "Measured results" sections + `results.md`.

## 7. Limitations (stated up front, per the homegpt standard)

- Single synthetic domain; results may not transfer to arbitrary real vaults. A "bring-your-own-vault" mode is a future add-on.
- One judge model; run-to-run judge variance is not captured (temporal repeats are a roadmap item; bootstrap captures sampling variance only).
- Gold labels are as good as the generator; a query whose answer also lives in an unlabeled note would understate recall. Generation pins gold sets explicitly to limit this.
- Degraded twins are synthetic defects, not natural bad notes; they test the judge's floor, not its ceiling.
