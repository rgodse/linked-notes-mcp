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


def _loads(text: str) -> dict:
    """Parse JSON that may be wrapped in ```json fences or surrounded by prose."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end != -1:
            return json.loads(t[start:end + 1])
        raise


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

    notes = _loads(chat_fn(cfg.gen_model, [{"role": "user", "content": NOTES_PROMPT}], cfg))["notes"]
    for note in notes:
        _write_note(vault, note)

    catalog = "\n".join(f'{n["id"]}: {n["frontmatter"].get("title","")} — '
                        f'{n["frontmatter"].get("summary","")}' for n in notes)
    raw_q = _loads(chat_fn(cfg.gen_model,
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
