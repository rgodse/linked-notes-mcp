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
