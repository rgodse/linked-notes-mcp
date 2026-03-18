"""Tests for the templates module."""

import pytest
from datetime import datetime

from linked_notes_mcp.templates import (
    TEMPLATES,
    build_template_frontmatter,
    get_template,
    list_templates,
    render_template,
    create_session_summary,
    create_decision_log,
    create_repo_memory,
    create_workstream_memory,
)


class TestTemplateBasics:
    def test_list_templates_returns_all(self):
        templates = list_templates()
        assert len(templates) == len(TEMPLATES)

        # Check structure
        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t
            assert "default_tags" in t
            assert "entity_type" in t
            assert "default_status" in t
            assert "default_importance" in t
            assert "default_confidence" in t
            assert "body_fields" in t
            assert "relationship_fields" in t

    def test_get_template_exists(self):
        template = get_template("session")
        assert template is not None
        assert template["name"] == "Session Summary"

    def test_get_template_not_found(self):
        template = get_template("nonexistent")
        assert template is None

    def test_get_template_case_insensitive(self):
        template = get_template("SESSION")
        assert template is not None


class TestRenderTemplate:
    def test_render_with_all_fields(self):
        title, content, tags = render_template(
            template_name="decision",
            fields={
                "context": "We need to choose a database",
                "options": "PostgreSQL, MySQL, MongoDB",
                "decision": "PostgreSQL",
                "reasoning": "Best for our use case",
                "implications": "Need to set up replication"
            },
            title="Database Choice"
        )

        assert title == "Database Choice"
        assert "We need to choose a database" in content
        assert "PostgreSQL" in content
        assert "decision" in tags

    def test_render_with_missing_fields(self):
        title, content, tags = render_template(
            template_name="decision",
            fields={
                "context": "Some context",
                "decision": "The decision"
            }
        )

        # Missing fields should be replaced with TBD
        assert "_TBD_" in content

    def test_render_auto_generates_title(self):
        title, content, tags = render_template(
            template_name="session",
            fields={"summary": "Test session"}
        )

        today = datetime.now().strftime("%Y-%m-%d")
        assert today in title
        assert "Session Summary" in title

    def test_render_with_extra_tags(self):
        title, content, tags = render_template(
            template_name="session",
            fields={"summary": "Test"},
            extra_tags=["project-foo", "important"]
        )

        assert "session" in tags
        assert "project-foo" in tags
        assert "important" in tags

    def test_render_unknown_template(self):
        with pytest.raises(ValueError, match="Template not found"):
            render_template("nonexistent", {})

    def test_render_initiative_template(self):
        title, content, tags = render_template(
            template_name="initiative",
            fields={
                "summary": "Improve internal operations",
                "outcomes": ["Reduce turnaround", "Clarify ownership"],
            },
            title="Ops Initiative"
        )

        assert title == "Ops Initiative"
        assert "Improve internal operations" in content
        assert "initiative" in tags

    def test_render_service_template_adds_relationship_prompts(self):
        title, content, tags = render_template(
            template_name="service",
            fields={"summary": "Handles billing workflows."},
            title="Payments Service",
        )

        assert title == "Payments Service"
        assert "Runbook / Ops Notes" in content
        assert "_TBD_" in content
        assert "service" in tags


class TestTemplateFrontmatter:
    def test_service_frontmatter_uses_template_specific_defaults(self):
        frontmatter, tags = build_template_frontmatter(
            template_name="service",
            title="Payments Service",
            fields={"summary": "Handles billing."},
        )

        assert frontmatter["entity_type"] == "service"
        assert frontmatter["status"] == "active"
        assert frontmatter["importance"] == "high"
        assert frontmatter["confidence"] == 0.8
        assert "service" in tags

    def test_repo_project_frontmatter_derives_project_from_repository(self):
        frontmatter, _ = build_template_frontmatter(
            template_name="repo_project",
            title="Project: linked-notes-mcp",
            fields={"summary": "Graph memory MCP server.", "repository": "linked-notes-mcp"},
        )

        assert frontmatter["project"] == "linked-notes-mcp"


class TestSessionSummary:
    def test_basic_session_summary(self):
        title, content, tags = create_session_summary(
            summary="Worked on authentication",
            accomplished=["Added login endpoint", "Fixed password hashing"]
        )

        today = datetime.now().strftime("%Y-%m-%d")
        assert today in title
        assert "Worked on authentication" in content
        assert "Added login endpoint" in content
        assert "Fixed password hashing" in content
        assert "session" in tags

    def test_session_summary_with_all_fields(self):
        title, content, tags = create_session_summary(
            summary="Major progress on auth",
            accomplished=["Login done", "Logout done"],
            decisions=["Use JWT tokens", "1 hour expiry"],
            open_items=["Add refresh tokens", "Add rate limiting"],
            next_session="Implement refresh token rotation",
            project_tag="webapp",
            topic="Authentication"
        )

        assert "Authentication" in title
        assert "Use JWT tokens" in content
        assert "[ ] Add refresh tokens" in content
        assert "Implement refresh token rotation" in content
        assert "project-webapp" in tags

    def test_session_summary_empty_lists(self):
        title, content, tags = create_session_summary(
            summary="Quick check-in",
            accomplished=[]
        )

        assert "_None_" in content


class TestDecisionLog:
    def test_basic_decision(self):
        title, content, tags = create_decision_log(
            decision_title="JWT vs Sessions",
            context="Need to implement authentication",
            options=["JWT tokens", "Server sessions", "OAuth only"],
            decision="JWT tokens",
            reasoning="Stateless, scales better"
        )

        assert title == "Decision: JWT vs Sessions"
        assert "Need to implement authentication" in content
        assert "JWT tokens" in content
        assert "Stateless, scales better" in content
        assert "decision" in tags

    def test_decision_with_project(self):
        title, content, tags = create_decision_log(
            decision_title="Database Choice",
            context="Choosing a database",
            options=["PostgreSQL", "MySQL"],
            decision="PostgreSQL",
            reasoning="Better JSON support",
            project_tag="api"
        )

        assert "project-api" in tags

    def test_decision_with_implications(self):
        title, content, tags = create_decision_log(
            decision_title="Cloud Provider",
            context="Choosing cloud",
            options=["AWS", "GCP"],
            decision="AWS",
            reasoning="Team experience",
            implications="Need to train on AWS services"
        )

        assert "Need to train on AWS services" in content


class TestMemoryHelpers:
    def test_create_repo_memory(self):
        title, content, tags = create_repo_memory(
            repo_name="linked-notes-mcp",
            summary="Graph memory MCP server",
            stack=["Python", "MCP"],
            areas=["retrieval", "graph maintenance"]
        )

        assert title == "Project: linked-notes-mcp"
        assert "Graph memory MCP server" in content
        assert "project-linked-notes-mcp" in tags

    def test_create_workstream_memory(self):
        title, content, tags = create_workstream_memory(
            name="Quarterly Planning",
            summary="Coordinate planning across teams",
            owners=["Ops", "Product"],
            dependencies=["Budget approval"]
        )

        assert title == "Workstream: Quarterly Planning"
        assert "Coordinate planning across teams" in content
        assert "workstream-quarterly-planning" in tags
