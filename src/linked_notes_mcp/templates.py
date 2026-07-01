"""
Note templates for common patterns.

Templates provide consistent structure for different types of notes.
"""

from datetime import datetime
from typing import Optional

from .parser import RELATIONSHIP_FIELDS


DEFAULT_IMPORTANCE = "medium"
DEFAULT_CONFIDENCE = 0.7


def _relationship_prompt(label: str) -> str:
    return f"- _None yet. Add note titles for `{label}` relationships._"


# Template definitions
TEMPLATES = {
    "initiative": {
        "name": "Initiative",
        "description": "Cross-functional initiative memory with goals, outcomes, and risks",
        "default_tags": ["initiative"],
        "entity_type": "project",
        "default_status": "active",
        "default_importance": "high",
        "default_confidence": 0.75,
        "body_fields": ["summary", "outcomes", "status", "risks", "next_moves"],
        "relationship_fields": ["depends_on", "related_to"],
        "structure": """## Summary
{summary}

## Desired Outcomes
{outcomes}

## Current Status
{status}

## Risks
{risks}

## Next Moves
{next_moves}
"""
    },
    "workstream": {
        "name": "Workstream",
        "description": "Ongoing stream of work within a larger program or initiative",
        "default_tags": ["workstream"],
        "entity_type": "workstream",
        "default_status": "active",
        "default_importance": "high",
        "default_confidence": 0.8,
        "body_fields": [
            "summary",
            "scope",
            "owners",
            "dependencies",
            "open_questions",
            "next_actions",
        ],
        "relationship_fields": ["part_of", "depends_on", "blocks", "related_to"],
        "structure": """## Summary
{summary}

## Scope
{scope}

## Owners
{owners}

## Dependencies
{dependencies}

## Open Questions
{open_questions}

## Next Actions
{next_actions}
"""
    },
    "stakeholder": {
        "name": "Stakeholder",
        "description": "Memory node for a person, team, or stakeholder relationship",
        "default_tags": ["stakeholder"],
        "entity_type": "person",
        "default_status": "active",
        "default_importance": "medium",
        "default_confidence": 0.75,
        "body_fields": ["summary", "role", "interests", "concerns", "notes"],
        "relationship_fields": ["related_to"],
        "structure": """## Summary
{summary}

## Role
{role}

## Interests
{interests}

## Concerns
{concerns}

## Working Notes
{notes}
"""
    },
    "research": {
        "name": "Research Note",
        "description": "Structured research memory with question, findings, evidence, and next steps",
        "default_tags": ["research"],
        "entity_type": "concept",
        "default_status": "active",
        "default_importance": "medium",
        "default_confidence": 0.6,
        "body_fields": ["question", "summary", "findings", "evidence", "next_steps"],
        "relationship_fields": ["related_to", "decision_for"],
        "structure": """## Question
{question}

## Summary
{summary}

## Findings
{findings}

## Evidence
{evidence}

## Next Steps
{next_steps}
"""
    },
    "repo_project": {
        "name": "Repo Project",
        "description": "Project memory node for a software repository with goals, stack, and active concerns",
        "default_tags": ["project", "repo"],
        "entity_type": "project",
        "default_status": "active",
        "default_importance": "high",
        "default_confidence": 0.8,
        "body_fields": [
            "summary",
            "repository",
            "stack",
            "areas",
            "owners",
            "concerns",
            "notes",
        ],
        "relationship_fields": ["contains", "depends_on", "related_to", "decided_by"],
        "structure": """## Summary
{summary}

## Repository
{repository}

## Stack
{stack}

## Key Areas
{areas}

## Owners
{owners}

## Active Concerns
{concerns}

## Notes
{notes}
"""
    },
    "service": {
        "name": "Service Node",
        "description": "Structured memory node for a service or subsystem",
        "default_tags": ["service"],
        "entity_type": "service",
        "default_status": "active",
        "default_importance": "high",
        "default_confidence": 0.8,
        "body_fields": [
            "summary",
            "responsibilities",
            "interfaces",
            "dependencies",
            "owners",
            "risks",
            "runbook",
        ],
        "relationship_fields": ["part_of", "depends_on", "blocks", "related_to", "decided_by"],
        "structure": """## Summary
{summary}

## Responsibilities
{responsibilities}

## Interfaces
{interfaces}

## Dependencies
{dependencies}

## Owners
{owners}

## Risks
{risks}

## Runbook / Ops Notes
{runbook}
"""
    },
    "issue": {
        "name": "Issue Node",
        "description": "Structured issue memory for bugs, incidents, or blockers",
        "default_tags": ["issue"],
        "entity_type": "issue",
        "default_status": "open",
        "default_importance": "high",
        "default_confidence": 0.7,
        "body_fields": [
            "summary",
            "symptoms",
            "impact",
            "suspected_cause",
            "scope",
            "next_actions",
        ],
        "relationship_fields": ["blocked_by", "blocks", "part_of", "related_to", "decided_by"],
        "structure": """## Summary
{summary}

## Symptoms
{symptoms}

## Impact
{impact}

## Suspected Cause
{suspected_cause}

## Scope
{scope}

## Next Actions
{next_actions}
"""
    },
    "session": {
        "name": "Session Summary",
        "description": "End-of-session summary capturing accomplishments, decisions, and next steps",
        "default_tags": ["session"],
        "entity_type": "session",
        "default_status": "done",
        "default_importance": "medium",
        "default_confidence": 0.8,
        "body_fields": ["summary", "accomplished", "decisions", "open_items", "next_session"],
        "relationship_fields": ["related_to"],
        "structure": """## Summary
{summary}

## Accomplished
{accomplished}

## Decisions Made
{decisions}

## Open Items
{open_items}

## Next Session
{next_session}
"""
    },
    "decision": {
        "name": "Decision Log",
        "description": "Record a decision with context, options considered, and reasoning",
        "default_tags": ["decision"],
        "entity_type": "decision",
        "default_status": "decided",
        "default_importance": "high",
        "default_confidence": 0.9,
        "body_fields": ["context", "options", "decision", "reasoning", "implications"],
        "relationship_fields": ["decision_for", "supersedes", "related_to"],
        "structure": """## Context
{context}

## Options Considered
{options}

## Decision
{decision}

## Reasoning
{reasoning}

## Implications
{implications}
"""
    },
    "project": {
        "name": "Project Context",
        "description": "Overview of a project including goals, status, and key information",
        "default_tags": ["project", "context"],
        "entity_type": "project",
        "default_status": "active",
        "default_importance": "high",
        "default_confidence": 0.75,
        "body_fields": [
            "overview",
            "goals",
            "status",
            "stakeholders",
            "links",
            "notes",
            "next_actions",
        ],
        "relationship_fields": ["depends_on", "contains", "related_to", "decided_by"],
        "structure": """## Overview
{overview}

## Goals
{goals}

## Current Status
{status}

## Key Stakeholders
{stakeholders}

## Important Links
{links}

## Notes
{notes}

## Next Actions
{next_actions}
"""
    },
    "meeting": {
        "name": "Meeting Notes",
        "description": "Capture meeting discussions, decisions, and action items",
        "default_tags": ["meeting"],
        "entity_type": "process",
        "default_status": "done",
        "default_importance": "medium",
        "default_confidence": 0.8,
        "body_fields": ["attendees", "agenda", "discussion", "decisions", "action_items"],
        "relationship_fields": ["related_to", "decision_for"],
        "structure": """## Attendees
{attendees}

## Agenda
{agenda}

## Discussion
{discussion}

## Decisions
{decisions}

## Action Items
{action_items}
"""
    },
    "idea": {
        "name": "Idea / Brainstorm",
        "description": "Capture an idea with potential benefits, challenges, and next steps",
        "default_tags": ["idea"],
        "entity_type": "concept",
        "default_status": "draft",
        "default_importance": "low",
        "default_confidence": 0.4,
        "body_fields": ["idea", "problem", "benefits", "challenges", "next_steps"],
        "relationship_fields": ["related_to"],
        "structure": """## The Idea
{idea}

## Problem It Solves
{problem}

## Potential Benefits
{benefits}

## Challenges / Risks
{challenges}

## Next Steps to Explore
{next_steps}
"""
    },
    "bug": {
        "name": "Bug / Issue",
        "description": "Document a bug with symptoms, investigation, and resolution",
        "default_tags": ["bug"],
        "entity_type": "issue",
        "default_status": "open",
        "default_importance": "high",
        "default_confidence": 0.75,
        "body_fields": [
            "symptoms",
            "steps",
            "investigation",
            "root_cause",
            "resolution",
            "prevention",
        ],
        "relationship_fields": ["blocked_by", "blocks", "part_of", "related_to"],
        "structure": """## Symptoms
{symptoms}

## Steps to Reproduce
{steps}

## Investigation
{investigation}

## Root Cause
{root_cause}

## Resolution
{resolution}

## Prevention
{prevention}
"""
    },
    "learning": {
        "name": "Learning / TIL",
        "description": "Document something learned for future reference",
        "default_tags": ["learning", "til"],
        "entity_type": "concept",
        "default_status": "active",
        "default_importance": "low",
        "default_confidence": 0.7,
        "body_fields": ["learning", "context", "takeaways", "related", "resources"],
        "relationship_fields": ["related_to"],
        "structure": """## What I Learned
{learning}

## Context
{context}

## Key Takeaways
{takeaways}

## Related Topics
{related}

## Resources
{resources}
"""
    }
}


def get_template(template_name: str) -> Optional[dict]:
    """Get a template by name."""
    return TEMPLATES.get(template_name.lower())


def list_templates() -> list[dict]:
    """List all available templates."""
    return [
        {
            "id": tid,
            "name": t["name"],
            "description": t["description"],
            "default_tags": t["default_tags"],
            "entity_type": t.get("entity_type"),
            "default_status": t.get("default_status"),
            "default_importance": t.get("default_importance", DEFAULT_IMPORTANCE),
            "default_confidence": t.get("default_confidence", DEFAULT_CONFIDENCE),
            "body_fields": t.get("body_fields", []),
            "relationship_fields": t.get("relationship_fields", []),
        }
        for tid, t in TEMPLATES.items()
    ]


def _format_field_value(field_name: str, field_value: object) -> str:
    if isinstance(field_value, list):
        return "\n".join(f"- {item}" for item in field_value) if field_value else "- _None_"
    if field_value in (None, ""):
        if field_name in RELATIONSHIP_FIELDS:
            return _relationship_prompt(field_name)
        return "_TBD_"
    return str(field_value)


def build_template_frontmatter(
    template_name: str,
    title: str,
    fields: dict[str, object],
    extra_tags: Optional[list[str]] = None,
) -> tuple[dict, list[str]]:
    """Build structured frontmatter and tags for a template note."""

    template = get_template(template_name)
    if not template:
        raise ValueError(f"Template not found: {template_name}")

    tags = template["default_tags"].copy()
    if extra_tags:
        tags.extend([t.lower() for t in extra_tags])
    tags = list(dict.fromkeys(tags))

    frontmatter: dict[str, object] = {
        "entity_type": template.get("entity_type", "concept"),
        "summary": fields.get("summary")
        or fields.get("overview")
        or fields.get("decision")
        or "_TBD_",
        "status": fields.get("status") or template.get("default_status", "draft"),
        "importance": fields.get("importance")
        or template.get("default_importance", DEFAULT_IMPORTANCE),
        "confidence": fields.get("confidence", template.get("default_confidence", DEFAULT_CONFIDENCE)),
        "last_reviewed": fields.get("last_reviewed") or datetime.now().isoformat(),
        "tags": tags,
    }

    aliases = fields.get("aliases")
    if aliases:
        frontmatter["aliases"] = aliases if isinstance(aliases, list) else [str(aliases)]

    project = fields.get("project")
    if not project and template_name == "repo_project":
        project = fields.get("repository")
    if project:
        frontmatter["project"] = str(project)

    for relation_type in template.get("relationship_fields", []):
        value = fields.get(relation_type)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            frontmatter[relation_type] = [str(item) for item in value if str(item).strip()]
        else:
            frontmatter[relation_type] = [part.strip() for part in str(value).split(",") if part.strip()]

    return frontmatter, tags


def render_template(
    template_name: str,
    fields: dict[str, object],
    title: Optional[str] = None,
    extra_tags: Optional[list[str]] = None
) -> tuple[str, str, list[str]]:
    """Render a template with provided fields.

    Args:
        template_name: Name of the template to use
        fields: Dict of field_name -> content
        title: Optional title override
        extra_tags: Additional tags to add

    Returns:
        Tuple of (title, content, tags)

    Raises:
        ValueError: If template not found
    """
    template = get_template(template_name)
    if not template:
        raise ValueError(f"Template not found: {template_name}")

    # Build title
    if not title:
        date_str = datetime.now().strftime("%Y-%m-%d")
        title = f"{template['name']} - {date_str}"

    # Render content - fill in provided fields, leave placeholders for missing ones
    content = template["structure"]
    rendered_fields = {
        field_name: _format_field_value(field_name, fields.get(field_name))
        for field_name in template.get("body_fields", [])
    }
    for field_name, field_value in {**rendered_fields, **fields}.items():
        placeholder = "{" + field_name + "}"
        if placeholder in content:
            content = content.replace(placeholder, _format_field_value(field_name, field_value))

    # Replace any remaining placeholders with "TBD"
    import re
    content = re.sub(r'\{[a-z_]+\}', '_TBD_', content)

    _, tags = build_template_frontmatter(template_name, title, fields, extra_tags)

    return title, content, tags


def create_session_summary(
    summary: str,
    accomplished: list[str],
    decisions: Optional[list[str]] = None,
    open_items: Optional[list[str]] = None,
    next_session: Optional[str] = None,
    project_tag: Optional[str] = None,
    topic: Optional[str] = None
) -> tuple[str, str, list[str]]:
    """Create a session summary note.

    Convenience function for the most common template.

    Returns:
        Tuple of (title, content, tags)
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Build title
    if topic:
        title = f"Session - {date_str} - {topic}"
    else:
        title = f"Session Summary - {date_str}"

    fields = {
        "summary": summary,
        "accomplished": "\n".join(f"- {item}" for item in accomplished) if accomplished else "- _None_",
        "decisions": "\n".join(f"- {item}" for item in (decisions or [])) if decisions else "- _None_",
        "open_items": "\n".join(f"- [ ] {item}" for item in (open_items or [])) if open_items else "- _None_",
        "next_session": next_session or "_TBD_"
    }

    content = TEMPLATES["session"]["structure"]
    for field_name, field_value in fields.items():
        content = content.replace("{" + field_name + "}", field_value)

    tags = ["session"]
    if project_tag:
        tags.append(f"project-{project_tag.lower()}")

    return title, content, tags


def create_decision_log(
    decision_title: str,
    context: str,
    options: list[str],
    decision: str,
    reasoning: str,
    implications: Optional[str] = None,
    project_tag: Optional[str] = None
) -> tuple[str, str, list[str]]:
    """Create a decision log note.

    Convenience function for decision tracking.

    Returns:
        Tuple of (title, content, tags)
    """
    title = f"Decision: {decision_title}"

    fields = {
        "context": context,
        "options": "\n".join(f"- **{opt}**" for opt in options),
        "decision": decision,
        "reasoning": reasoning,
        "implications": implications or "_To be determined_"
    }

    content = TEMPLATES["decision"]["structure"]
    for field_name, field_value in fields.items():
        content = content.replace("{" + field_name + "}", field_value)

    tags = ["decision"]
    if project_tag:
        tags.append(f"project-{project_tag.lower()}")

    return title, content, tags
