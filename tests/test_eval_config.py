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
