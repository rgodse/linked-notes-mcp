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
