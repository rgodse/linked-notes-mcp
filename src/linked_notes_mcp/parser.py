"""
Parser for markdown files with wikilinks and frontmatter.

Extracts:
- YAML frontmatter (title, tags, etc.)
- Wikilinks: [[Target]] or [[Target|Display Text]]
- Standard markdown links: [text](path.md)
- Full text content for search
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Link:
    """A link from one note to another."""
    target: str  # The target note identifier
    display_text: Optional[str] = None  # Optional display text
    link_type: str = "wikilink"  # "wikilink" or "markdown"
    line_number: int = 0


@dataclass
class Note:
    """A parsed markdown note."""
    path: Path
    id: str  # Derived from filename (stem)
    title: str  # From frontmatter or first heading or filename
    content: str  # Full markdown content
    frontmatter: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    outgoing_links: list[Link] = field(default_factory=list)
    
    @property
    def body(self) -> str:
        """Content without frontmatter."""
        if self.content.startswith("---"):
            parts = self.content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return self.content


# Regex patterns
WIKILINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
HEADING_PATTERN = re.compile(r'^#\s+(.+)$', re.MULTILINE)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from content.
    
    Returns:
        Tuple of (frontmatter_dict, remaining_content)
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content
    
    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        frontmatter = {}
    
    remaining = content[match.end():]
    return frontmatter, remaining


def extract_wikilinks(content: str) -> list[Link]:
    """Extract all wikilinks from content."""
    links = []
    for line_num, line in enumerate(content.split('\n'), 1):
        for match in WIKILINK_PATTERN.finditer(line):
            target = match.group(1).strip()
            display = match.group(2).strip() if match.group(2) else None
            links.append(Link(
                target=normalize_id(target),
                display_text=display,
                link_type="wikilink",
                line_number=line_num
            ))
    return links


def extract_markdown_links(content: str) -> list[Link]:
    """Extract markdown links that point to .md files."""
    links = []
    for line_num, line in enumerate(content.split('\n'), 1):
        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            display = match.group(1).strip()
            target = match.group(2).strip()
            # Convert path to id (remove .md, normalize)
            target_id = normalize_id(Path(target).stem)
            links.append(Link(
                target=target_id,
                display_text=display,
                link_type="markdown",
                line_number=line_num
            ))
    return links


def normalize_id(name: str) -> str:
    """Normalize a note name to an ID.
    
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters
    """
    # Handle paths - just take the stem
    if '/' in name or '\\' in name:
        name = Path(name).stem
    
    # Lowercase and replace spaces
    normalized = name.lower().strip()
    normalized = re.sub(r'\s+', '-', normalized)
    
    # Remove anything that's not alphanumeric, hyphen, or underscore
    normalized = re.sub(r'[^a-z0-9\-_]', '', normalized)
    
    return normalized


def extract_title(content: str, frontmatter: dict, filename: str) -> str:
    """Extract title from frontmatter, first heading, or filename."""
    # Try frontmatter first
    if frontmatter.get('title'):
        return frontmatter['title']
    
    # Try first heading
    match = HEADING_PATTERN.search(content)
    if match:
        return match.group(1).strip()
    
    # Fall back to filename
    return filename.replace('-', ' ').replace('_', ' ').title()


def extract_tags(frontmatter: dict) -> list[str]:
    """Extract tags from frontmatter."""
    tags = frontmatter.get('tags', [])
    if isinstance(tags, str):
        # Handle comma-separated string
        tags = [t.strip() for t in tags.split(',')]
    elif isinstance(tags, list):
        tags = [str(t).strip() for t in tags]
    else:
        tags = []
    
    # Normalize tags
    return [t.lower() for t in tags if t]


def parse_note(path: Path) -> Note:
    """Parse a markdown file into a Note object."""
    content = path.read_text(encoding='utf-8')
    
    # Extract frontmatter
    frontmatter, body = parse_frontmatter(content)
    
    # Extract metadata
    note_id = normalize_id(path.stem)
    title = extract_title(content, frontmatter, path.stem)
    tags = extract_tags(frontmatter)
    
    # Extract links
    wikilinks = extract_wikilinks(content)
    md_links = extract_markdown_links(content)
    all_links = wikilinks + md_links
    
    return Note(
        path=path,
        id=note_id,
        title=title,
        content=content,
        frontmatter=frontmatter,
        tags=tags,
        outgoing_links=all_links
    )


def is_markdown_file(path: Path) -> bool:
    """Check if a path is a markdown file we should process."""
    if not path.is_file():
        return False
    if path.name.startswith('.'):
        return False
    return path.suffix.lower() in ('.md', '.markdown')
