"""
Note templates for common patterns.

Templates provide consistent structure for different types of notes.
"""

from datetime import datetime
from typing import Optional


# Template definitions
TEMPLATES = {
    "session": {
        "name": "Session Summary",
        "description": "End-of-session summary capturing accomplishments, decisions, and next steps",
        "default_tags": ["session"],
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
"""
    },
    "meeting": {
        "name": "Meeting Notes",
        "description": "Capture meeting discussions, decisions, and action items",
        "default_tags": ["meeting"],
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
            "default_tags": t["default_tags"]
        }
        for tid, t in TEMPLATES.items()
    ]


def render_template(
    template_name: str,
    fields: dict[str, str],
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
    for field_name, field_value in fields.items():
        placeholder = "{" + field_name + "}"
        if placeholder in content:
            # Format lists as bullet points if they're lists
            if isinstance(field_value, list):
                field_value = "\n".join(f"- {item}" for item in field_value)
            content = content.replace(placeholder, field_value)

    # Replace any remaining placeholders with "TBD"
    import re
    content = re.sub(r'\{[a-z_]+\}', '_TBD_', content)

    # Build tags
    tags = template["default_tags"].copy()
    if extra_tags:
        tags.extend([t.lower() for t in extra_tags])

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
