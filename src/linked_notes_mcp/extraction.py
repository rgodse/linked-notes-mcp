"""Provider-agnostic LLM extraction for the ingestion pipeline.

Supports any OpenAI-compatible API (OpenAI, Gemini, Codex, Groq, Ollama, ...)
as well as the native Anthropic SDK.

Configuration is loaded in this order (highest to lowest priority):
  1. Vault-local config: <vault>/.linked-notes-config.json
  2. Global config:      ~/.config/linked-notes-mcp/config.json
  3. Env vars:           LLM_PROVIDER / LLM_MODEL / LLM_API_KEY / LLM_BASE_URL
  4. Legacy env vars:    ANTHROPIC_API_KEY, OPENAI_API_KEY

Config file schema (.linked-notes-config.json):
  {
    "llm": {
      "provider": "openai",          // "openai" | "anthropic" | "openai_compatible"
      "model":    "gpt-4o-mini",     // any model string your provider accepts
      "api_key":  "YOUR_KEY_HERE",
      "base_url": null               // set for custom endpoints (Gemini, Ollama, etc.)
    }
  }

Provider notes:
  - "openai"           → OpenAI API (api.openai.com)
  - "openai_compatible" → any OpenAI-compatible endpoint; set base_url accordingly
      Gemini:  https://generativelanguage.googleapis.com/v1beta/openai/
      Groq:    https://api.groq.com/openai/v1
      Ollama:  http://localhost:11434/v1
  - "anthropic"        → Anthropic API via the anthropic SDK
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# JSON schema shared by both provider adapters
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
    provider: str  # "openai" | "openai_compatible" | "anthropic"
    model: str
    api_key: str
    base_url: str | None = None


def load_llm_config(vault_path: Path | None = None) -> LLMConfig | None:
    """Load LLM config from config files then env var fallbacks."""
    if vault_path is not None:
        cfg = _read_config_file(vault_path / ".linked-notes-config.json")
        if cfg is not None:
            return cfg

    global_path = Path.home() / ".config" / "linked-notes-mcp" / "config.json"
    cfg = _read_config_file(global_path)
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
    provider = llm.get("provider", "openai")
    model = llm.get("model")
    api_key = llm.get("api_key")
    base_url = llm.get("base_url") or None
    if not model or not api_key:
        return None
    return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)


def _config_from_env() -> LLMConfig | None:
    # Generic LLM env vars (highest priority among env vars)
    api_key = os.environ.get("LLM_API_KEY")
    if api_key:
        provider = os.environ.get("LLM_PROVIDER", "openai_compatible")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("LLM_BASE_URL") or None
        return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)

    # Legacy: Anthropic env var
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
        return LLMConfig(provider="anthropic", model=model, api_key=anthropic_key)

    # Legacy: OpenAI env var
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        return LLMConfig(provider="openai", model=model, api_key=openai_key)

    return None


def can_use_llm(vault_path: Path | None = None) -> bool:
    """Return True if a valid LLM config exists and the required SDK is installed."""
    cfg = load_llm_config(vault_path)
    if cfg is None:
        return False
    if cfg.provider == "anthropic":
        try:
            import anthropic  # noqa: F401

            return True
        except ImportError:
            return False
    else:
        try:
            import openai  # noqa: F401

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
    if cfg.provider == "anthropic":
        return _extract_anthropic(content, display_name, project, cfg)
    else:
        return _extract_openai_compat(content, display_name, project, cfg)


# ---------------------------------------------------------------------------
# Shared prompt helpers
# ---------------------------------------------------------------------------

def _system_prompt() -> str:
    return (
        "You are a knowledge graph extraction assistant. "
        "Extract ALL distinct entities (services, decisions, projects, issues, "
        "people, processes, workstreams) from the provided content as separate "
        "memory node candidates. Be comprehensive — if a document describes "
        "multiple things, extract each as its own node."
    )


def _user_message(content: str, display_name: str, project: str | None) -> str:
    ctx = f" for project '{project}'" if project else ""
    return (
        f"Extract memory node candidates from the following document "
        f"'{display_name}'{ctx}:\n\n{content}"
    )


# ---------------------------------------------------------------------------
# Anthropic adapter (native tool_use)
# ---------------------------------------------------------------------------

def _extract_anthropic(
    content: str,
    display_name: str,
    project: str | None,
    cfg: LLMConfig,
) -> list[dict[str, Any]]:
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.api_key)
    tools = [
        {
            "name": "extract_memory_nodes",
            "description": "Extract structured memory nodes from the provided content.",
            "input_schema": _EXTRACTION_SCHEMA,
        }
    ]
    response = client.messages.create(
        model=cfg.model,
        max_tokens=4096,
        system=_system_prompt(),
        tools=tools,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": _user_message(content, display_name, project)}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_memory_nodes":
            return block.input.get("candidates", [])
    return []


# ---------------------------------------------------------------------------
# OpenAI-compatible adapter (works with OpenAI, Gemini, Groq, Ollama, ...)
# ---------------------------------------------------------------------------

def _extract_openai_compat(
    content: str,
    display_name: str,
    project: str | None,
    cfg: LLMConfig,
) -> list[dict[str, Any]]:
    import openai as openai_sdk

    kwargs: dict[str, Any] = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    client = openai_sdk.OpenAI(**kwargs)

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
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_message(content, display_name, project)},
        ],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "extract_memory_nodes"}},
    )
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        result = json.loads(tool_calls[0].function.arguments)
        return result.get("candidates", [])
    return []
