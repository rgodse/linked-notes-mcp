"""Provider-agnostic LLM extraction for the ingestion pipeline.

Uses litellm so any supported LLM works with a single code path.
Model names follow litellm routing conventions:

  "gpt-4o-mini"                  → OpenAI
  "claude-haiku-4-5-20251001"    → Anthropic
  "gemini/gemini-1.5-flash"      → Google Gemini
  "groq/llama-3.1-8b-instant"    → Groq
  "openai/llama3"                → Ollama or any OpenAI-compatible endpoint
                                   (set base_url to your endpoint)

See https://docs.litellm.ai/docs/providers for the full list.

Configuration (highest to lowest priority):
  1. Vault config:  <vault>/.linked-notes-config.json
  2. Env vars:      LLM_MODEL / LLM_API_KEY / LLM_BASE_URL
  3. Legacy:        ANTHROPIC_API_KEY, OPENAI_API_KEY

Config file schema:
  {
    "llm": {
      "model":    "gpt-4o-mini",
      "api_key":  "YOUR_KEY_HERE",
      "base_url": null
    }
  }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "description": "Extracted memory node candidates",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Canonical name of this entity",
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "service",
                            "project",
                            "decision",
                            "issue",
                            "process",
                            "person",
                            "workstream",
                            "concept",
                        ],
                        "description": "Type of entity",
                    },
                    "summary": {
                        "type": "string",
                        "description": "1-2 sentence summary of this entity",
                    },
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Alternative names or abbreviations",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relevant tags",
                    },
                    "relationships": {
                        "type": "array",
                        "description": "Typed relationships to other entities",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "target": {"type": "string"},
                            },
                            "required": ["type", "target"],
                        },
                    },
                    "body": {
                        "type": "string",
                        "description": "Relevant body text for this entity",
                    },
                },
                "required": ["title", "entity_type", "summary"],
            },
        }
    },
    "required": ["candidates"],
}


@dataclass
class LLMConfig:
    model: str
    api_key: str
    base_url: str | None = None


def load_llm_config(vault_path: Path | None = None) -> LLMConfig | None:
    """Load LLM config from vault config file, then env var fallbacks."""
    if vault_path is not None:
        cfg = _read_config_file(vault_path / ".linked-notes-config.json")
        if cfg is not None:
            return cfg
    return _config_from_env()


def _read_config_file(path: Path) -> LLMConfig | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    llm = data.get("llm")
    if not isinstance(llm, dict):
        return None
    model = llm.get("model")
    api_key = llm.get("api_key")
    base_url = llm.get("base_url") or None
    if not model or not api_key:
        return None
    return LLMConfig(model=model, api_key=api_key, base_url=base_url)


def _config_from_env() -> LLMConfig | None:
    # Generic env vars
    api_key = os.environ.get("LLM_API_KEY")
    if api_key:
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("LLM_BASE_URL") or None
        return LLMConfig(model=model, api_key=api_key, base_url=base_url)

    # Legacy: Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
        return LLMConfig(model=model, api_key=anthropic_key)

    # Legacy: OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        return LLMConfig(model=model, api_key=openai_key)

    return None


def can_use_llm(vault_path: Path | None = None) -> bool:
    """Return True if a valid config exists and litellm is installed."""
    if load_llm_config(vault_path) is None:
        return False
    try:
        import litellm  # noqa: F401

        return True
    except ImportError:
        return False


def extract_candidates_llm(
    content: str,
    display_name: str,
    project: str | None = None,
    vault_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Extract memory node candidates from content using the configured LLM.

    Returns candidate dicts with: title, entity_type, summary, aliases,
    tags, relationships, body.
    """
    cfg = load_llm_config(vault_path)
    if cfg is None:
        return []

    import litellm

    ctx = f" for project '{project}'" if project else ""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a knowledge graph extraction assistant. "
                "Extract ALL distinct entities (services, decisions, projects, issues, "
                "people, processes, workstreams) from the provided content as separate "
                "memory node candidates. Be comprehensive — if a document describes "
                "multiple things, extract each as its own node."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Extract memory node candidates from the following document "
                f"'{display_name}'{ctx}:\n\n{content}"
            ),
        },
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_memory_nodes",
                "description": "Extract structured memory nodes from the provided content.",
                "parameters": _EXTRACTION_SCHEMA,
            },
        }
    ]

    kwargs: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "tools": tools,
        "tool_choice": {"type": "function", "function": {"name": "extract_memory_nodes"}},
        "max_tokens": 4096,
        "api_key": cfg.api_key,
    }
    if cfg.base_url:
        kwargs["api_base"] = cfg.base_url

    response = litellm.completion(**kwargs)
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        result = json.loads(tool_calls[0].function.arguments)
        return result.get("candidates", [])
    return []
