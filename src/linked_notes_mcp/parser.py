"""
Parser for markdown files with wikilinks and frontmatter.

Extracts:
- YAML frontmatter (title, tags, etc.)
- Wikilinks: [[Target]] or [[Target|Display Text]]
- Standard markdown links: [text](path.md)
- Typed graph relationships from frontmatter
- Full text content for search
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


RELATIONSHIP_FIELDS = {
    "depends_on",
    "blocks",
    "blocked_by",
    "related_to",
    "part_of",
    "contains",
    "decision_for",
    "decided_by",
    "supersedes",
    "superseded_by",
}


@dataclass
class Link:
    """A link from one note to another."""

    target: str
    display_text: Optional[str] = None
    link_type: str = "wikilink"
    line_number: int = 0


@dataclass
class Relationship:
    """A typed relationship declared in frontmatter."""

    target: str
    relation_type: str
    source_field: str
    raw_target: str


@dataclass
class Note:
    """A parsed markdown note."""

    path: Path
    id: str
    title: str
    content: str
    frontmatter: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    outgoing_links: list[Link] = field(default_factory=list)
    explicit_relationships: list[Relationship] = field(default_factory=list)

    @property
    def body(self) -> str:
        """Content without frontmatter."""
        if self.content.startswith("---"):
            parts = self.content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return self.content


WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from content."""

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        frontmatter = {}

    remaining = content[match.end() :]
    return frontmatter, remaining


def normalize_id(value: str) -> str:
    """Normalize a note identifier or title to a note ID."""

    value = Path(value).stem
    normalized = value.lower().strip()
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"[^a-z0-9\-_]", "", normalized)
    return normalized


def extract_wikilinks(content: str) -> list[Link]:
    """Extract wikilinks from markdown content."""

    links = []
    for match in WIKILINK_PATTERN.finditer(content):
        target = normalize_id(match.group(1))
        display_text = match.group(2)
        line_number = content[: match.start()].count("\n") + 1
        links.append(
            Link(
                target=target,
                display_text=display_text,
                link_type="wikilink",
                line_number=line_number,
            )
        )
    return links


def extract_markdown_links(content: str) -> list[Link]:
    """Extract markdown links to local markdown files."""

    links = []
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        text = match.group(1)
        target = normalize_id(match.group(2))
        line_number = content[: match.start()].count("\n") + 1
        links.append(
            Link(
                target=target,
                display_text=text,
                link_type="markdown",
                line_number=line_number,
            )
        )
    return links


def extract_title(content: str, frontmatter: dict, filename: str) -> str:
    """Extract title from frontmatter, first heading, or filename."""

    if frontmatter.get("title"):
        return frontmatter["title"]

    match = HEADING_PATTERN.search(content)
    if match:
        return match.group(1).strip()

    return filename.replace("-", " ").replace("_", " ").title()


def extract_tags(frontmatter: dict) -> list[str]:
    """Extract tags from frontmatter."""

    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    elif isinstance(tags, list):
        tags = [str(t).strip() for t in tags]
    else:
        tags = []

    return [t.lower() for t in tags if t]


def extract_relationships(frontmatter: dict) -> list[Relationship]:
    """Extract typed graph relationships from frontmatter."""

    relationships: list[Relationship] = []
    for field, value in frontmatter.items():
        if field not in RELATIONSHIP_FIELDS:
            continue

        if isinstance(value, str):
            targets = [value]
        elif isinstance(value, list):
            targets = [str(item) for item in value]
        else:
            continue

        for target in targets:
            normalized_target = normalize_id(target)
            if not normalized_target:
                continue
            relationships.append(
                Relationship(
                    target=normalized_target,
                    relation_type=field,
                    source_field=field,
                    raw_target=target,
                )
            )
    return relationships


def parse_note(path: Path) -> Note:
    """Parse a markdown file into a Note object."""

    content = path.read_text(encoding="utf-8")
    frontmatter, _body = parse_frontmatter(content)
    note_id = normalize_id(path.stem)
    title = extract_title(content, frontmatter, path.stem)
    tags = extract_tags(frontmatter)
    wikilinks = extract_wikilinks(content)
    md_links = extract_markdown_links(content)
    relationships = extract_relationships(frontmatter)

    return Note(
        path=path,
        id=note_id,
        title=title,
        content=content,
        frontmatter=frontmatter,
        tags=tags,
        outgoing_links=wikilinks + md_links,
        explicit_relationships=relationships,
    )


def is_markdown_file(path: Path) -> bool:
    """Check if a path is a markdown file we should process."""

    if not path.is_file():
        return False
    if path.name.startswith("."):
        return False
    return path.suffix.lower() in (".md", ".markdown")
