# Eval + DSPy Optimization Artifacts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two dev-only, reproducible studies beside the lean MCP server — a pairwise G-Eval note-quality harness (`evals/`) and a DSPy retrieval-optimization study (`optimize/`) — fed by a committed synthetic vault.

**Architecture:** Both live in top-level packages (`evals/`, `optimize/`) that import read-only from `linked_notes_mcp.graph` and are never imported by the server. Deterministic logic (metrics, degradation, CI, config) is pure and unit-tested offline; LLM calls go through `litellm` and are mocked in tests. A generated corpus in `evals/dataset/` is committed so published numbers reproduce without spend.

**Tech Stack:** Python 3.10+, `litellm` (LLM calls), `dspy-ai` (optimization), `pyyaml`, `pytest`. `litellm`/`dspy-ai` live only in the `[eval]` optional-dependency group.

## Global Constraints

- Python `>=3.10` (matches existing `requires-python`).
- Server runtime deps unchanged: `mcp`, `networkx`, `pyyaml`, `watchdog`. **No LLM dep may enter server runtime deps.**
- `litellm>=1.0.0` and `dspy-ai>=2.5` go **only** in `[project.optional-dependencies] eval`.
- `evals/` and `optimize/` must never be imported by any module under `src/linked_notes_mcp/`.
- All new unit tests run fully offline (LLM calls mocked). Live runs are gated behind `OPENROUTER_KEY`/`LLM_API_KEY` and skipped when absent.
- Primary retrieval metric is **recall@5**; secondary is **MRR**.
- Judge model must be a **different provider family** than the generator model (independence).
- Determinism: any randomness (bootstrap, degradation choice) is seeded; degradation is seeded by note id via `hashlib.sha256`, not Python's salted `hash()`.

---

### Task 1: Package scaffolding + `[eval]` dependency group

**Files:**
- Create: `evals/__init__.py` (empty), `optimize/__init__.py` (empty)
- Modify: `pyproject.toml` (add `[eval]` optional-dependency group)
- Test: `tests/test_eval_isolation.py`

**Interfaces:**
- Produces: importable `evals` and `optimize` packages; `pyproject.toml` `[project.optional-dependencies].eval == ["litellm>=1.0.0", "dspy-ai>=2.5"]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_isolation.py
import ast, pathlib

SRC = pathlib.Path("src/linked_notes_mcp")

def test_server_never_imports_eval_or_optimize():
    offenders = []
    for py in SRC.rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            if any(m.split(".")[0] in {"evals", "optimize"} for m in mods):
                offenders.append(str(py))
    assert offenders == [], f"server imports dev-only packages: {offenders}"

def test_eval_optional_dep_group_present():
    import tomllib
    data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
    eval_deps = data["project"]["optional-dependencies"]["eval"]
    assert any(d.startswith("litellm") for d in eval_deps)
    assert any(d.startswith("dspy-ai") for d in eval_deps)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_eval_isolation.py -v`
Expected: FAIL (`eval` group missing / KeyError).

- [ ] **Step 3: Create packages and add the dependency group**

```bash
mkdir -p evals optimize
printf '' > evals/__init__.py
printf '' > optimize/__init__.py
```

In `pyproject.toml`, under `[project.optional-dependencies]`, add:

```toml
eval = ["litellm>=1.0.0", "dspy-ai>=2.5"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_eval_isolation.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add evals/__init__.py optimize/__init__.py pyproject.toml tests/test_eval_isolation.py
git commit -m "feat(eval): scaffold evals/ + optimize/ packages and [eval] dep group"
```

---

### Task 2: `evals/config.py` — model + endpoint resolution

**Files:**
- Create: `evals/config.py`
- Test: `tests/test_eval_config.py`

**Interfaces:**
- Produces: `EvalConfig` dataclass with fields `api_key, base_url, gen_model, judge_model, student_model: str`; `load_config() -> EvalConfig`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_config.py
from evals.config import load_config

def test_defaults(monkeypatch):
    for v in ["OPENROUTER_KEY","LLM_API_KEY","LLM_BASE_URL","EVAL_GEN_MODEL","EVAL_JUDGE_MODEL","DSPY_STUDENT_MODEL"]:
        monkeypatch.delenv(v, raising=False)
    c = load_config()
    assert c.base_url == "https://openrouter.ai/api/v1"
    assert c.gen_model and c.judge_model and c.student_model
    assert c.gen_model.split("/")[0] != c.judge_model.split("/")[0]  # independent families

def test_env_override(monkeypatch):
    monkeypatch.setenv("OPENROUTER_KEY", "sk-test")
    monkeypatch.setenv("EVAL_JUDGE_MODEL", "x/y")
    c = load_config()
    assert c.api_key == "sk-test"
    assert c.judge_model == "x/y"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_eval_config.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.config`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/config.py
"""Resolve models + endpoint for the dev-only eval/optimize studies."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass
class EvalConfig:
    api_key: str
    base_url: str
    gen_model: str
    judge_model: str
    student_model: str


def load_config() -> EvalConfig:
    return EvalConfig(
        api_key=os.environ.get("OPENROUTER_KEY") or os.environ.get("LLM_API_KEY", ""),
        base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        gen_model=os.environ.get("EVAL_GEN_MODEL", "anthropic/claude-sonnet-4-6"),
        judge_model=os.environ.get("EVAL_JUDGE_MODEL", "openai/gpt-4o"),
        student_model=os.environ.get("DSPY_STUDENT_MODEL", "meta-llama/llama-3.1-8b-instruct"),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_eval_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/config.py tests/test_eval_config.py
git commit -m "feat(eval): config resolution for models and endpoint"
```

---

### Task 3: `optimize/metric.py` — recall@k and MRR

**Files:**
- Create: `optimize/metric.py`
- Test: `tests/test_metric.py`

**Interfaces:**
- Produces: `recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float`; `mrr(retrieved: list[str], gold: list[str]) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metric.py
from optimize.metric import recall_at_k, mrr

def test_recall_at_k():
    assert recall_at_k(["a","b","c"], ["a","c"], 5) == 1.0
    assert recall_at_k(["a","x","y"], ["a","c"], 5) == 0.5
    assert recall_at_k(["x","y","z","a"], ["a"], 3) == 0.0   # a is outside top-3
    assert recall_at_k(["a"], [], 5) == 1.0                   # empty gold => trivially satisfied

def test_mrr():
    assert mrr(["a","b"], ["a"]) == 1.0
    assert mrr(["x","a"], ["a"]) == 0.5
    assert mrr(["x","y"], ["a"]) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_metric.py -v`
Expected: FAIL (`ModuleNotFoundError: optimize.metric`).

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/metric.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_metric.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/metric.py tests/test_metric.py
git commit -m "feat(optimize): recall@k and MRR metrics"
```

---

### Task 4: `evals/stats.py` — bootstrap confidence interval

**Files:**
- Create: `evals/stats.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Produces: `bootstrap_ci(values: list[float], n_resamples: int = 2000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stats.py
from evals.stats import bootstrap_ci

def test_ci_brackets_mean_and_is_deterministic():
    vals = [1.0] * 50 + [0.0] * 50   # mean 0.5
    lo, hi = bootstrap_ci(vals, n_resamples=500, seed=1)
    assert lo <= 0.5 <= hi
    assert (lo, hi) == bootstrap_ci(vals, n_resamples=500, seed=1)  # deterministic

def test_ci_all_same_is_degenerate():
    lo, hi = bootstrap_ci([1.0, 1.0, 1.0], n_resamples=200, seed=0)
    assert lo == 1.0 and hi == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stats.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.stats`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/stats.py
"""Bootstrap confidence interval. Seeded for reproducibility."""
from __future__ import annotations
import random


def bootstrap_ci(values: list[float], n_resamples: int = 2000,
                 alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        total = 0.0
        for _ in range(n):
            total += values[rng.randrange(n)]
        means.append(total / n)
    means.sort()
    lo = means[int((alpha / 2) * n_resamples)]
    hi = means[min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))]
    return (lo, hi)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_stats.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/stats.py tests/test_stats.py
git commit -m "feat(eval): seeded bootstrap confidence interval"
```

---

### Task 5: `evals/degrade.py` — deterministic degradation transforms

**Files:**
- Create: `evals/degrade.py`
- Test: `tests/test_degrade.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `RELATIONSHIP_FIELDS: tuple[str,...]`; `degrade(note_id: str, frontmatter: dict, body: str) -> tuple[dict, str, str]` returning `(new_frontmatter, new_body, defect_name)`. Deterministic per `note_id`. Picks, from transforms whose precondition holds, one seeded by `sha256(note_id)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_degrade.py
from evals.degrade import degrade

FM = {"entity_type": "service", "summary": "Handles billing.",
      "aliases": ["Billing"], "depends_on": ["Auth Service"]}

def test_degrade_is_deterministic_per_id():
    a = degrade("note-1", dict(FM), "body text")
    b = degrade("note-1", dict(FM), "body text")
    assert a == b

def test_degrade_introduces_a_defect():
    fm, body, defect = degrade("note-1", dict(FM), "body text")
    assert defect in {"strip_summary", "remove_relationship", "remove_entity_type", "bloat_body"}
    if defect == "strip_summary":
        assert "summary" not in fm
    if defect == "remove_relationship":
        assert fm.get("depends_on") != FM["depends_on"]
    if defect == "remove_entity_type":
        assert "entity_type" not in fm
    if defect == "bloat_body":
        assert len(body) > len("body text")

def test_precondition_respected():
    # note with no relationships/summary/entity_type can only be bloated
    fm, body, defect = degrade("x", {"title": "T"}, "hi")
    assert defect == "bloat_body"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_degrade.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.degrade`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/degrade.py
"""Deterministic degradation of a note into a worse memory-node twin."""
from __future__ import annotations
import hashlib

RELATIONSHIP_FIELDS = ("depends_on", "blocks", "blocked_by", "part_of",
                       "contains", "decision_for", "related_to")

_FILLER = (" Additionally there are many unrelated considerations to note here "
           "that do not pertain to the subject and merely add length without value.") * 3


def _seed(note_id: str) -> int:
    return int(hashlib.sha256(note_id.encode()).hexdigest(), 16)


def degrade(note_id: str, frontmatter: dict, body: str) -> tuple[dict, str, str]:
    fm = dict(frontmatter)
    options = []
    if fm.get("summary"):
        options.append("strip_summary")
    if any(fm.get(f) for f in RELATIONSHIP_FIELDS):
        options.append("remove_relationship")
    if fm.get("entity_type"):
        options.append("remove_entity_type")
    options.append("bloat_body")  # always available

    defect = options[_seed(note_id) % len(options)]

    if defect == "strip_summary":
        fm.pop("summary", None)
    elif defect == "remove_relationship":
        for f in RELATIONSHIP_FIELDS:
            if fm.get(f):
                fm[f] = fm[f][:-1] if len(fm[f]) > 1 else []
                break
    elif defect == "remove_entity_type":
        fm.pop("entity_type", None)
    else:  # bloat_body
        body = body + _FILLER

    return fm, body, defect
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_degrade.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/degrade.py tests/test_degrade.py
git commit -m "feat(eval): deterministic note degradation transforms"
```

---

### Task 6: `evals/pairwise.py` — counterbalanced tally

**Files:**
- Create: `evals/pairwise.py`
- Test: `tests/test_pairwise.py`

**Interfaces:**
- Consumes: `evals.stats.bootstrap_ci`.
- Produces: `Judgment` TypedDict-like dict `{"dimension": str, "order": "clean_first"|"degraded_first", "picked": "A"|"B"}`; `accuracy(judgments: list[dict]) -> float`; `accuracy_by_dimension(judgments: list[dict]) -> dict[str, tuple[float, tuple[float,float]]]` returning per-dimension (accuracy, CI).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pairwise.py
from evals.pairwise import accuracy, accuracy_by_dimension

def _j(dim, order, picked):
    return {"dimension": dim, "order": order, "picked": picked}

def test_accuracy_counts_clean_pick_regardless_of_position():
    js = [
        _j("retrievability", "clean_first", "A"),      # clean=A, correct
        _j("retrievability", "degraded_first", "B"),   # clean=B, correct
        _j("retrievability", "clean_first", "B"),      # clean=A, wrong
    ]
    assert abs(accuracy(js) - 2/3) < 1e-9

def test_accuracy_by_dimension_returns_ci():
    js = [_j("atomicity", "clean_first", "A")] * 10
    out = accuracy_by_dimension(js)
    acc, (lo, hi) = out["atomicity"]
    assert acc == 1.0 and lo <= 1.0 <= hi
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pairwise.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.pairwise`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/pairwise.py
"""Score order-counterbalanced pairwise judgments (clean vs degraded)."""
from __future__ import annotations
from collections import defaultdict
from evals.stats import bootstrap_ci


def _is_correct(j: dict) -> int:
    clean_pos = "A" if j["order"] == "clean_first" else "B"
    return 1 if j["picked"] == clean_pos else 0


def accuracy(judgments: list[dict]) -> float:
    if not judgments:
        return 0.0
    return sum(_is_correct(j) for j in judgments) / len(judgments)


def accuracy_by_dimension(judgments: list[dict]) -> dict[str, tuple[float, tuple[float, float]]]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for j in judgments:
        buckets[j["dimension"]].append(float(_is_correct(j)))
    out = {}
    for dim, vals in buckets.items():
        acc = sum(vals) / len(vals)
        out[dim] = (acc, bootstrap_ci(vals, seed=0))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pairwise.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/pairwise.py tests/test_pairwise.py
git commit -m "feat(eval): counterbalanced pairwise accuracy with CIs"
```

---

### Task 7: `evals/llm.py` — thin litellm wrapper (mockable)

**Files:**
- Create: `evals/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `evals.config.EvalConfig`.
- Produces: `chat(model: str, messages: list[dict], cfg, **kw) -> str` returning message content. Isolated so all higher layers mock `evals.llm.chat`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm.py
from evals import llm
from evals.config import EvalConfig

def test_chat_calls_litellm_and_returns_content(monkeypatch):
    captured = {}
    def fake_completion(**kw):
        captured.update(kw)
        class M: pass
        m = M(); m.choices = [type("C", (), {"message": type("Msg", (), {"content": "hello"})})]
        return m
    monkeypatch.setattr(llm, "_completion", fake_completion)
    cfg = EvalConfig("k", "http://base", "g/x", "j/y", "s/z")
    out = llm.chat("g/x", [{"role": "user", "content": "hi"}], cfg)
    assert out == "hello"
    assert captured["model"] == "g/x"
    assert captured["api_base"] == "http://base"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_llm.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.llm`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/llm.py
"""Thin, mockable litellm chat wrapper for the eval studies."""
from __future__ import annotations
from evals.config import EvalConfig


def _completion(**kwargs):
    import litellm  # imported lazily so importing this module never requires litellm
    return litellm.completion(**kwargs)


def chat(model: str, messages: list[dict], cfg: EvalConfig, **kw) -> str:
    resp = _completion(model=model, messages=messages,
                       api_key=cfg.api_key, api_base=cfg.base_url, **kw)
    return resp.choices[0].message.content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_llm.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/llm.py tests/test_llm.py
git commit -m "feat(eval): mockable litellm chat wrapper"
```

---

### Task 8: `evals/gen.py` — synthesize + persist the dataset

**Files:**
- Create: `evals/gen.py`, `evals/dataset/.gitkeep`
- Test: `tests/test_gen.py`

**Interfaces:**
- Consumes: `evals.llm.chat`, `evals.config.load_config`.
- Produces: `generate(out_dir: str, cfg, chat_fn=llm.chat, force: bool=False) -> dict` writing `<out_dir>/vault/*.md`, `<out_dir>/queries.json` (`[{"id","query","gold_note_ids"}]`), `<out_dir>/meta.json`; returns counts `{"notes": int, "queries": int}`. Refuses to overwrite an existing non-empty `queries.json` unless `force`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen.py
import json, pathlib
from evals import gen
from evals.config import EvalConfig

CFG = EvalConfig("k", "b", "gen/x", "judge/y", "s/z")

def _fake_chat_factory():
    # first call returns notes JSON, second returns queries JSON
    notes = {"notes": [
        {"id": "auth-service", "frontmatter": {"title": "Auth Service", "entity_type": "service",
         "summary": "Issues tokens.", "depends_on": []}, "body": "Handles auth."},
        {"id": "api-gateway", "frontmatter": {"title": "API Gateway", "entity_type": "service",
         "summary": "Entry point.", "depends_on": ["Auth Service"]}, "body": "Routes requests."},
    ]}
    queries = {"queries": [{"query": "what does the gateway depend on?", "gold_note_ids": ["auth-service"]}]}
    calls = iter([json.dumps(notes), json.dumps(queries)])
    def fake_chat(model, messages, cfg, **kw):
        return next(calls)
    return fake_chat

def test_generate_writes_vault_and_queries(tmp_path):
    counts = gen.generate(str(tmp_path), CFG, chat_fn=_fake_chat_factory())
    assert counts == {"notes": 2, "queries": 1}
    assert (tmp_path / "vault" / "auth-service.md").exists()
    q = json.loads((tmp_path / "queries.json").read_text())
    assert q[0]["gold_note_ids"] == ["auth-service"]
    assert q[0]["id"]  # ids assigned
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["gen_model"] == "gen/x"

def test_generate_refuses_overwrite(tmp_path):
    gen.generate(str(tmp_path), CFG, chat_fn=_fake_chat_factory())
    import pytest
    with pytest.raises(FileExistsError):
        gen.generate(str(tmp_path), CFG, chat_fn=_fake_chat_factory())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_gen.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.gen`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/gen.py
"""Synthesize a reproducible software-domain vault + query->gold dataset."""
from __future__ import annotations
import json
from pathlib import Path
import yaml
from evals import llm
from evals.config import EvalConfig, load_config

NOTES_PROMPT = (
    "Generate a connected knowledge vault for a software system as JSON: "
    '{"notes":[{"id":"kebab-id","frontmatter":{"title","entity_type","summary",'
    '"depends_on":[...],"blocks":[...],"part_of":[...]},"body":"markdown"}]}. '
    "Use entity_type in {service,decision,issue,project,workstream,concept}. "
    "Relationship values are note titles. Produce ~50 interconnected notes. JSON only."
)
QUERIES_PROMPT = (
    "Given these notes (id + title + summary), write natural-language questions whose "
    "answers require specific notes. JSON: {\"queries\":[{\"query\":\"...\","
    "\"gold_note_ids\":[\"id\",...]}]}. ~40 queries, mix single- and multi-hop. JSON only.\n\n"
)


def _write_note(vault: Path, note: dict) -> None:
    fm = yaml.safe_dump(note["frontmatter"], sort_keys=False).strip()
    (vault / f"{note['id']}.md").write_text(f"---\n{fm}\n---\n\n{note['body']}\n")


def generate(out_dir: str, cfg: EvalConfig | None = None,
             chat_fn=llm.chat, force: bool = False) -> dict:
    cfg = cfg or load_config()
    out = Path(out_dir)
    queries_path = out / "queries.json"
    if queries_path.exists() and queries_path.read_text().strip() and not force:
        raise FileExistsError(f"{queries_path} exists; pass force=True to regenerate")

    vault = out / "vault"
    vault.mkdir(parents=True, exist_ok=True)

    notes = json.loads(chat_fn(cfg.gen_model, [{"role": "user", "content": NOTES_PROMPT}], cfg))["notes"]
    for note in notes:
        _write_note(vault, note)

    catalog = "\n".join(f'{n["id"]}: {n["frontmatter"].get("title","")} — '
                        f'{n["frontmatter"].get("summary","")}' for n in notes)
    raw_q = json.loads(chat_fn(cfg.gen_model,
                               [{"role": "user", "content": QUERIES_PROMPT + catalog}], cfg))["queries"]
    queries = [{"id": f"q{i:03d}", **q} for i, q in enumerate(raw_q)]
    queries_path.write_text(json.dumps(queries, indent=2))
    (out / "meta.json").write_text(json.dumps(
        {"gen_model": cfg.gen_model, "notes": len(notes), "queries": len(queries)}, indent=2))
    return {"notes": len(notes), "queries": len(queries)}


if __name__ == "__main__":  # pragma: no cover
    import sys
    force = "--force" in sys.argv
    counts = generate("evals/dataset", force=force)
    print(f"generated {counts}")
```

```bash
mkdir -p evals/dataset && printf '' > evals/dataset/.gitkeep
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_gen.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/gen.py evals/dataset/.gitkeep tests/test_gen.py
git commit -m "feat(eval): synthetic vault + query dataset generator"
```

---

### Task 9: Generate + commit the real dataset (live, manual)

**Files:**
- Create: `evals/dataset/vault/*.md`, `evals/dataset/queries.json`, `evals/dataset/meta.json` (committed)

**Interfaces:**
- Consumes: `evals.gen.generate` with real `chat`.
- Produces: the committed corpus every later study reads.

- [ ] **Step 1: Run generation live (requires key)**

Run:
```bash
OPENROUTER_KEY=sk-or-... uv run python -m evals.gen
```
Expected: prints `generated {'notes': ~50, 'queries': ~40}`.

- [ ] **Step 2: Sanity-check the corpus**

Run:
```bash
uv run python - <<'PY'
import json, pathlib
q = json.loads(pathlib.Path("evals/dataset/queries.json").read_text())
ids = {p.stem for p in pathlib.Path("evals/dataset/vault").glob("*.md")}
missing = [x for row in q for x in row["gold_note_ids"] if x not in ids]
print("queries:", len(q), "notes:", len(ids), "dangling gold refs:", missing[:5])
assert not missing, "gold ids must reference real notes"
PY
```
Expected: `dangling gold refs: []`.

- [ ] **Step 3: Commit the dataset**

```bash
git add evals/dataset/vault evals/dataset/queries.json evals/dataset/meta.json
git commit -m "data(eval): committed synthetic vault + query dataset"
```

---

### Task 10: `evals/rubric.yaml` + `evals/quality.py` — pairwise judge run

**Files:**
- Create: `evals/rubric.yaml`, `evals/quality.py`
- Test: `tests/test_quality.py`

**Interfaces:**
- Consumes: `evals.degrade.degrade`, `evals.pairwise.accuracy_by_dimension`, `evals.llm.chat`, `linked_notes_mcp.parser` (to read a note's frontmatter+body).
- Produces: `load_rubric(path="evals/rubric.yaml") -> dict`; `build_pairwise_prompt(dimension, desc, note_a, note_b) -> list[dict]`; `run_quality(vault_dir, cfg, chat_fn=llm.chat, rubric=None) -> list[dict]` producing judgment records `{"dimension","order","picked"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quality.py
from evals import quality
from evals.config import EvalConfig

CFG = EvalConfig("k","b","gen/x","judge/y","s/z")

def test_run_quality_tallies_mocked_judge(tmp_path):
    (tmp_path / "n1.md").write_text("---\nentity_type: service\nsummary: Does X.\n"
                                    "depends_on:\n  - Other\n---\n\nBody.\n")
    # judge always picks the note in position A
    def fake_chat(model, messages, cfg, **kw):
        return "A"
    rubric = {"retrievability": "is it findable"}
    records = quality.run_quality(str(tmp_path), CFG, chat_fn=fake_chat, rubric=rubric)
    # one note x one dimension x two orders (counterbalanced) => 2 records
    assert len(records) == 2
    assert {r["order"] for r in records} == {"clean_first", "degraded_first"}
    assert all(r["dimension"] == "retrievability" for r in records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_quality.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.quality`).

- [ ] **Step 3: Write rubric + implementation**

```yaml
# evals/rubric.yaml
retrievability: "Which note's summary and frontmatter make its key facts easier to find via search?"
frontmatter_completeness: "Which note has more complete, sensible frontmatter (entity_type, summary, relationships)?"
atomicity: "Which note is a single coherent memory rather than a bloated dump?"
relationship_accuracy: "Which note's typed relationships are more complete and correct?"
```

```python
# evals/quality.py
"""Pairwise clean-vs-degraded note-quality judging."""
from __future__ import annotations
from pathlib import Path
import yaml
from linked_notes_mcp.parser import parse_frontmatter
from evals import llm
from evals.config import EvalConfig
from evals.degrade import degrade


def load_rubric(path: str = "evals/rubric.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


def _render(frontmatter: dict, body: str) -> str:
    fm = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    return f"---\n{fm}\n---\n\n{body}"


def build_pairwise_prompt(dimension: str, desc: str, note_a: str, note_b: str) -> list[dict]:
    return [{"role": "user", "content":
             f"Criterion ({dimension}): {desc}\n\n"
             f"NOTE A:\n{note_a}\n\nNOTE B:\n{note_b}\n\n"
             "Reply with exactly one character: A or B."}]


def run_quality(vault_dir: str, cfg: EvalConfig, chat_fn=llm.chat, rubric: dict | None = None) -> list[dict]:
    rubric = rubric or load_rubric()
    records: list[dict] = []
    for md in sorted(Path(vault_dir).glob("*.md")):
        fm, body = parse_frontmatter(md.read_text())
        clean = _render(fm, body)
        d_fm, d_body, _defect = degrade(md.stem, fm, body)
        degraded = _render(d_fm, d_body)
        for dimension, desc in rubric.items():
            for order, a, b in (("clean_first", clean, degraded),
                                ("degraded_first", degraded, clean)):
                picked = chat_fn(cfg.judge_model,
                                 build_pairwise_prompt(dimension, desc, a, b), cfg).strip()[:1].upper()
                records.append({"dimension": dimension, "order": order, "picked": picked})
    return records


if __name__ == "__main__":  # pragma: no cover
    from evals.config import load_config
    from evals.pairwise import accuracy_by_dimension
    from evals.report import render_quality
    recs = run_quality("evals/dataset/vault", load_config())
    print(render_quality(accuracy_by_dimension(recs)))
```

Note: confirm `parse_frontmatter` returns `(frontmatter_dict, body_str)`; if its signature differs, adapt this call and the test to the real signature found in `src/linked_notes_mcp/parser.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_quality.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/rubric.yaml evals/quality.py tests/test_quality.py
git commit -m "feat(eval): pairwise note-quality judge run"
```

---

### Task 11: `evals/report.py` — quality report table

**Files:**
- Create: `evals/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: output of `evals.pairwise.accuracy_by_dimension`.
- Produces: `render_quality(by_dim: dict[str, tuple[float, tuple[float,float]]]) -> str` markdown table.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
from evals.report import render_quality

def test_render_quality_markdown():
    md = render_quality({"retrievability": (0.9, (0.8, 0.97))})
    assert "retrievability" in md
    assert "0.90" in md
    assert "0.80" in md and "0.97" in md
    assert md.count("|") >= 6  # a table
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_report.py -v`
Expected: FAIL (`ModuleNotFoundError: evals.report`).

- [ ] **Step 3: Write minimal implementation**

```python
# evals/report.py
"""Render study results as markdown tables."""
from __future__ import annotations


def render_quality(by_dim: dict[str, tuple[float, tuple[float, float]]]) -> str:
    lines = ["| Dimension | Judge accuracy | 95% CI |", "|---|---|---|"]
    for dim, (acc, (lo, hi)) in sorted(by_dim.items()):
        lines.append(f"| {dim} | {acc:.2f} | {lo:.2f}–{hi:.2f} |")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add evals/report.py tests/test_report.py
git commit -m "feat(eval): markdown quality report"
```

---

### Task 12: `optimize/retrieval.py` — DSPy program + graph execution

**Files:**
- Create: `optimize/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `linked_notes_mcp.graph.KnowledgeGraph` (read-only), `optimize.metric`.
- Produces: `retrieve(graph, params: dict, k: int = 5) -> list[str]` (pure: runs search+graph expansion for given params, returns ranked note ids); `RetrievalProgram` (dspy.Module) whose `forward(query)` predicts params then calls `retrieve`. Params shape: `{"search_terms": str, "depth": int}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retrieval.py
from pathlib import Path
from linked_notes_mcp.graph import KnowledgeGraph
from optimize.retrieval import retrieve

def _vault(tmp_path):
    (tmp_path / "auth.md").write_text("---\ntitle: Auth\nsummary: issues tokens\n---\n\nauthentication tokens\n")
    (tmp_path / "gw.md").write_text("---\ntitle: Gateway\nsummary: entry point\ndepends_on:\n  - Auth\n---\n\nrouting\n")
    g = KnowledgeGraph(tmp_path); g.rebuild(); return g

def test_retrieve_returns_ranked_ids(tmp_path):
    g = _vault(tmp_path)
    ids = retrieve(g, {"search_terms": "tokens", "depth": 1}, k=5)
    assert "auth" in ids
    assert isinstance(ids, list) and all(isinstance(x, str) for x in ids)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_retrieval.py -v`
Expected: FAIL (`ModuleNotFoundError: optimize.retrieval`).

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/retrieval.py
"""DSPy retrieval program over the linked-notes graph (read-only)."""
from __future__ import annotations


def retrieve(graph, params: dict, k: int = 5) -> list[str]:
    """Run text search then bounded graph expansion; return ranked note ids."""
    terms = params.get("search_terms", "")
    depth = int(params.get("depth", 1))
    hits = graph.search(terms, limit=k)
    ordered: list[str] = []
    for note in hits:
        if note.id not in ordered:
            ordered.append(note.id)
        ctx = graph.graph_context(note.id, depth=depth, limit=k)
        for nb in ctx.get("nodes", []):
            nid = nb["id"] if isinstance(nb, dict) else nb
            if nid not in ordered:
                ordered.append(nid)
    return ordered[:max(k, 1) * 3]


def build_program():
    """Construct the DSPy module. Imported lazily so tests don't require dspy."""
    import dspy

    class RetrievalSig(dspy.Signature):
        """Produce search parameters for a knowledge-vault question."""
        query = dspy.InputField()
        search_terms = dspy.OutputField(desc="space-separated keywords")
        depth = dspy.OutputField(desc="graph expansion depth, 1-3")

    class RetrievalProgram(dspy.Module):
        def __init__(self, graph, k: int = 5):
            super().__init__()
            self.graph = graph
            self.k = k
            self.predict = dspy.Predict(RetrievalSig)

        def forward(self, query: str):
            pred = self.predict(query=query)
            try:
                depth = max(1, min(3, int(pred.depth)))
            except (ValueError, TypeError):
                depth = 1
            ids = retrieve(self.graph, {"search_terms": pred.search_terms, "depth": depth}, k=self.k)
            return dspy.Prediction(note_ids=ids)

    return RetrievalProgram


# Note: confirm KnowledgeGraph.graph_context returns {"nodes":[...]} and that Note has .id;
# adjust the `retrieve` accessors to the real shapes in src/linked_notes_mcp/graph.py.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_retrieval.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/retrieval.py tests/test_retrieval.py
git commit -m "feat(optimize): DSPy retrieval program + graph execution"
```

---

### Task 13: `optimize/run.py` — baseline→bootstrap→MIPRO ladder

**Files:**
- Create: `optimize/run.py`
- Test: `tests/test_run.py`

**Interfaces:**
- Consumes: `optimize.metric.recall_at_k`, `optimize.metric.mrr`, `evals.stats.bootstrap_ci`, `optimize.retrieval.retrieve`.
- Produces: `evaluate(predict_params_fn, graph, dataset: list[dict], k: int = 5) -> dict` returning `{"recall@5": float, "mrr": float, "recall_ci": (lo,hi)}` where `predict_params_fn(query) -> dict` yields retrieval params; `load_dataset(path) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run.py
from pathlib import Path
from linked_notes_mcp.graph import KnowledgeGraph
from optimize.run import evaluate

def _vault(tmp_path):
    (tmp_path / "auth.md").write_text("---\ntitle: Auth\nsummary: tokens\n---\n\ntokens\n")
    (tmp_path / "gw.md").write_text("---\ntitle: Gateway\nsummary: routing\n---\n\nrouting\n")
    g = KnowledgeGraph(tmp_path); g.rebuild(); return g

def test_evaluate_scores_baseline(tmp_path):
    g = _vault(tmp_path)
    dataset = [{"id": "q1", "query": "tokens", "gold_note_ids": ["auth"]}]
    # baseline params fn: just use the raw query as search terms, depth 1
    res = evaluate(lambda q: {"search_terms": q, "depth": 1}, g, dataset, k=5)
    assert res["recall@5"] == 1.0
    assert 0.0 <= res["mrr"] <= 1.0
    assert res["recall_ci"][0] <= res["recall@5"] <= res["recall_ci"][1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py -v`
Expected: FAIL (`ModuleNotFoundError: optimize.run`).

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/run.py
"""Retrieval optimization ladder: baseline -> BootstrapFewShot -> MIPROv2."""
from __future__ import annotations
import json
from pathlib import Path
from optimize.metric import recall_at_k, mrr
from optimize.retrieval import retrieve
from evals.stats import bootstrap_ci


def load_dataset(path: str) -> list[dict]:
    return json.loads(Path(path).read_text())


def evaluate(predict_params_fn, graph, dataset: list[dict], k: int = 5) -> dict:
    recalls, rrs = [], []
    for row in dataset:
        ids = retrieve(graph, predict_params_fn(row["query"]), k=k)
        recalls.append(recall_at_k(ids, row["gold_note_ids"], k))
        rrs.append(mrr(ids, row["gold_note_ids"]))
    return {
        "recall@5": sum(recalls) / len(recalls),
        "mrr": sum(rrs) / len(rrs),
        "recall_ci": bootstrap_ci(recalls, seed=0),
    }


def run_ladder(graph, dataset: list[dict], cfg, k: int = 5) -> dict:  # pragma: no cover
    """Live ladder. Requires dspy + a key. Not unit-tested (needs real LM)."""
    import dspy
    from optimize.retrieval import build_program
    dspy.configure(lm=dspy.LM(f"openrouter/{cfg.student_model}",
                              api_key=cfg.api_key, api_base=cfg.base_url))
    Program = build_program()

    def params_from_program(program):
        return lambda q: _program_params(program, q)

    def _program_params(program, q):
        pred = program.predict(query=q)
        try:
            depth = max(1, min(3, int(pred.depth)))
        except (ValueError, TypeError):
            depth = 1
        return {"search_terms": pred.search_terms, "depth": depth}

    trainset = [dspy.Example(query=r["query"], gold=r["gold_note_ids"]).with_inputs("query")
                for r in dataset]

    def dspy_metric(example, pred, trace=None):
        return recall_at_k(pred.note_ids, example.gold, k)

    results = {"baseline": evaluate(lambda q: {"search_terms": q, "depth": 1}, graph, dataset, k)}

    base = Program(graph, k=k)
    bfs = dspy.BootstrapFewShot(metric=dspy_metric).compile(base, trainset=trainset)
    results["bootstrap_fewshot"] = evaluate(params_from_program(bfs), graph, dataset, k)

    mipro = dspy.MIPROv2(metric=dspy_metric, auto="light").compile(
        Program(graph, k=k), trainset=trainset)
    results["miprov2"] = evaluate(params_from_program(mipro), graph, dataset, k)
    return results


if __name__ == "__main__":  # pragma: no cover
    from evals.config import load_config
    from linked_notes_mcp.graph import KnowledgeGraph
    g = KnowledgeGraph(Path("evals/dataset/vault")); g.rebuild()
    ds = load_dataset("evals/dataset/queries.json")
    out = run_ladder(g, ds, load_config())
    print(json.dumps(out, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_run.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimize/run.py tests/test_run.py
git commit -m "feat(optimize): retrieval evaluation + DSPy ladder"
```

---

### Task 14: `results.md` + README "Measured results" sections

**Files:**
- Create: `results.md`
- Modify: `README.md` (add two short "Measured results" subsections linking `results.md`, `evals/`, `optimize/`)

**Interfaces:**
- Consumes: live outputs of `python -m evals.quality` and `python -m optimize.run`.
- Produces: documented, reproducible result tables.

- [ ] **Step 1: Run both studies live and capture output (requires key)**

Run:
```bash
OPENROUTER_KEY=sk-or-... uv run python -m evals.quality > /tmp/quality.txt
OPENROUTER_KEY=sk-or-... uv run python -m optimize.run > /tmp/ladder.json
```
Expected: a quality markdown table and a ladder JSON with `baseline`/`bootstrap_fewshot`/`miprov2`.

- [ ] **Step 2: Write `results.md`**

Paste the captured quality table and a recall@5 table built from the ladder JSON (baseline vs each rung, with CIs). State the honest headline (which rung won, or "no rung beat baseline beyond noise"). Include the reproduce commands and the model ids from `evals/dataset/meta.json`.

- [ ] **Step 3: Add README subsections**

Under a new "## Evaluation & optimization (dev studies)" section in `README.md`, add:
- one paragraph on the pairwise note-quality harness (independent judge, counterbalanced, bootstrap CIs) linking `evals/` and `results.md`;
- one paragraph on the DSPy retrieval study (recall@5 ladder) linking `optimize/` and `results.md`;
- the reproduce commands and the `[eval]` install line (`uv sync --extra eval`).

- [ ] **Step 4: Verify the full offline suite still passes**

Run: `uv run pytest -q`
Expected: all prior tests + the new eval/optimize tests PASS (offline).

- [ ] **Step 5: Commit**

```bash
git add results.md README.md
git commit -m "docs(eval): measured results + README study sections"
```

---

## Self-Review

**Spec coverage:**
- Layout (`evals/`, `optimize/`, `dataset/`, `results.md`) → Tasks 1, 8, 14. ✓
- Dataset generation + committed corpus → Tasks 8, 9. ✓
- Pairwise note-quality eval (degrade, independent judge, counterbalanced, bootstrap CI, per-dimension validity) → Tasks 4, 5, 6, 10, 11. ✓
- DSPy retrieval study (query→params program, recall@5/MRR, baseline→BootstrapFewShot→MIPROv2, CIs) → Tasks 3, 12, 13. ✓
- Models/config from env, independent judge family, `[eval]` optional dep, server keeps zero LLM deps → Tasks 1, 2, 7; enforced by `test_eval_isolation.py`. ✓
- Offline mocked tests + gated live runs → every task's tests are offline; live runs isolated to Tasks 9, 14. ✓
- Limitations → carried in `results.md` (Task 14) from the spec. ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"write tests for the above" — every code step shows code. Two explicit *verification notes* (parser signature in Task 10, graph_context/Note shapes in Task 12) instruct the implementer to confirm real signatures against `src/`; these are correctness guards, not placeholders.

**Type consistency:** `retrieve(graph, params, k)` params `{"search_terms","depth"}` consistent across Tasks 12–13; `accuracy_by_dimension` return `dict[str,(float,(float,float))]` consumed identically in Tasks 6, 11; judgment record `{"dimension","order","picked"}` consistent Tasks 6, 10; `EvalConfig` field order consistent Tasks 2, 7, 10, 13.
