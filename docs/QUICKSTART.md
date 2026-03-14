# Quick Start: Graph Memory for MCP Clients

Get Codex or another MCP client using graph-first memory in a few minutes.

## 1. Clone and Install

```bash
git clone https://github.com/rgodse/linked-notes-mcp
cd linked-notes-mcp
uv sync
```

## 2. Create a Memory Folder

```bash
mkdir ~/agent-brain
```

This folder is your graph memory. Notes are nodes. Links and frontmatter relationships are edges.

Build the notes for the agent first:

- keep frontmatter structured
- use `aliases`, `entity_type`, `project`, `status`, and `summary`
- use the body for supporting detail, not the primary retrieval key

## 3. Configure Codex

Edit `~/.codex/config.toml`:

```toml
[features]
rmcp_client = true

[mcp_servers.brain]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/linked-notes-mcp", "linked-notes-mcp", "/Users/YOUR_USERNAME/agent-brain"]
```

Restart Codex.

## 4. Create a First Structured Note

Create a note like this:

```md
---
title: API Gateway
tags: [architecture, backend]
aliases: [Gateway]
entity_type: service
project: graph-memory
status: active
summary: Request entry point that coordinates auth and downstream services.
depends_on:
  - Auth Service
related_to:
  - User Service
---

# API Gateway

Routes requests and coordinates auth + downstream services.
```

Then create the related notes it points to.

## 5. Use the Graph Tools

Try these prompts:

- "Get context on API Gateway"
- "List relationships for API Gateway"
- "Show graph context around API Gateway"
- "Find the path between API Gateway and User Service"

## 6. Add Session Memory Habits

Use these habits consistently:

1. Start with `get_context` or `get_graph_context`
2. Save decisions when you make them
3. Add followups for unresolved work
4. End with `save_session_summary`

## Troubleshooting

**Client doesn't see the MCP**
- restart the client
- check the configured repo path
- check the configured notes path

**Graph feels weak**
- add explicit frontmatter relationships
- add more wikilinks between related notes
- use consistent note titles and tags

**A relationship did not resolve**
- make sure the target note exists
- prefer exact note titles in frontmatter relationship lists
