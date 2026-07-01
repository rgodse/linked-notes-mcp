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
