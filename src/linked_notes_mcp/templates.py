"""
Note templates for common patterns.

Templates provide consistent structure for different types of notes.
"""

from datetime import datetime
from typing import Optional


# Template definitions
TEMPLATES = {
    "initiative": {
        "name": "Initiative",
        "description": "Cross-functional initiative memory with goals, outcomes, and risks",
        "default_tags": ["initiative"],
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
"""
    },
    "stakeholder": {
        "name": "Stakeholder",
        "description": "Memory node for a person, team, or stakeholder relationship",
        "default_tags": ["stakeholder"],
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
        "structure": """## Summary
{summary}

## Repository
{repository}

## Stack
{stack}

## Key Areas
{areas}

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
        "structure": """## Summary
{summary}

## Responsibilities
{responsibilities}

## Interfaces
{interfaces}

## Dependencies
{dependencies}

## Risks
{risks}
"""
    },
    "issue": {
        "name": "Issue Node",
        "description": "Structured issue memory for bugs, incidents, or blockers",
        "default_tags": ["issue"],
        "structure": """## Summary
{summary}

## Symptoms
{symptoms}

## Impact
{impact}

## Suspected Cause
{suspected_cause}

## Next Actions
{next_actions}
"""
    },
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


def create_repo_memory(
    repo_name: str,
    summary: str,
    stack: list[str],
    areas: list[str],
    concerns: Optional[list[str]] = None,
) -> tuple[str, str, list[str]]:
    """Create a repo-oriented project memory note."""

    title = f"Project: {repo_name}"
    content = TEMPLATES["repo_project"]["structure"].format(
        summary=summary,
        repository=repo_name,
        stack="\n".join(f"- {item}" for item in stack) if stack else "- _TBD_",
        areas="\n".join(f"- {item}" for item in areas) if areas else "- _TBD_",
        concerns="\n".join(f"- {item}" for item in (concerns or [])) if concerns else "- _None_",
        notes="_TBD_",
    )
    tags = ["project", "repo", f"project-{repo_name.lower().replace(' ', '-')}"]
    return title, content, tags


def create_workstream_memory(
    name: str,
    summary: str,
    owners: list[str],
    dependencies: Optional[list[str]] = None,
    open_questions: Optional[list[str]] = None,
) -> tuple[str, str, list[str]]:
    """Create a non-technical workstream memory note."""

    title = f"Workstream: {name}"
    content = TEMPLATES["workstream"]["structure"].format(
        summary=summary,
        scope="_TBD_",
        owners="\n".join(f"- {item}" for item in owners) if owners else "- _TBD_",
        dependencies="\n".join(f"- {item}" for item in (dependencies or [])) if dependencies else "- _None_",
        open_questions="\n".join(f"- {item}" for item in (open_questions or [])) if open_questions else "- _None_",
    )
    tags = ["workstream", f"workstream-{name.lower().replace(' ', '-')}"]
    return title, content, tags
