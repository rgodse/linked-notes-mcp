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
