"""Tests for UI-facing graph snapshot support."""

from linked_notes_mcp.graph import KnowledgeGraph


def test_visual_graph_returns_anchor_neighborhood(tmp_path):
    (tmp_path / "project.md").write_text(
        "---\n"
        "title: Project Alpha\n"
        "entity_type: project\n"
        "summary: Main project node.\n"
        "contains: [Service Beta]\n"
        "related_to: [Decision Gamma]\n"
        "---\n"
        "Body.\n"
    )
    (tmp_path / "service-beta.md").write_text(
        "---\n"
        "title: Service Beta\n"
        "entity_type: service\n"
        "summary: Core service.\n"
        "depends_on: [Decision Gamma]\n"
        "---\n"
        "Body.\n"
    )
    (tmp_path / "decision-gamma.md").write_text(
        "---\n"
        "title: Decision Gamma\n"
        "entity_type: decision\n"
        "summary: Important decision.\n"
        "---\n"
        "Body.\n"
    )

    graph = KnowledgeGraph(tmp_path)
    snapshot = graph.visual_graph(anchor="Project Alpha", depth=2, limit=10)

    assert snapshot.anchor == "project"
    assert {node["id"] for node in snapshot.nodes} == {
        "project",
        "service-beta",
        "decision-gamma",
    }
    assert any(
        edge["source"] == "project" and edge["target"] == "service-beta"
        for edge in snapshot.edges
    )
    assert "contains" in snapshot.available_relation_types
    assert snapshot.stats["shown_nodes"] == 3


def test_visual_graph_query_picks_best_matching_anchor(tmp_path):
    (tmp_path / "capex.md").write_text(
        "---\n"
        "title: CAPEX Process\n"
        "entity_type: workstream\n"
        "summary: Capex approval workflow.\n"
        "---\n"
        "Manager approval, finance review, and procurement steps.\n"
    )
    (tmp_path / "finance.md").write_text(
        "---\n"
        "title: Finance Review\n"
        "summary: Finance validation step.\n"
        "part_of: [CAPEX Process]\n"
        "---\n"
        "Budget validation body.\n"
    )

    graph = KnowledgeGraph(tmp_path)
    snapshot = graph.visual_graph(query="capex", depth=2, limit=10)

    assert snapshot.anchor == "capex"
    assert any(node["id"] == "finance" for node in snapshot.nodes)


def test_visual_graph_demo_mode_includes_second_order_flow_notes(tmp_path):
    (tmp_path / "repo-root.md").write_text(
        "---\n"
        "title: Repo Root\n"
        "entity_type: project\n"
        "contains: [Repo Service]\n"
        "---\n"
        "Body.\n"
    )
    (tmp_path / "repo-service.md").write_text(
        "---\n"
        "title: Repo Service\n"
        "entity_type: service\n"
        "part_of: [Repo Root]\n"
        "---\n"
        "Body.\n"
    )
    (tmp_path / "repo-request-flow.md").write_text(
        "---\n"
        "title: Repo request flow\n"
        "entity_type: process\n"
        "part_of: [Repo Root]\n"
        "related_to: [Repo Service]\n"
        "---\n"
        "Flow through [[Repo Service]].\n"
    )
    (tmp_path / "repo-data-flow.md").write_text(
        "---\n"
        "title: Repo data flow\n"
        "entity_type: data-flow\n"
        "part_of: [Repo Root]\n"
        "related_to: [Repo Service]\n"
        "---\n"
        "Data through [[Repo Service]].\n"
    )

    graph = KnowledgeGraph(tmp_path)
    snapshot = graph.visual_graph(anchor="Repo Root", depth=1, limit=10, demo_mode=True)

    assert snapshot.anchor == "repo-root"
    assert {node["id"] for node in snapshot.nodes} == {
        "repo-root",
        "repo-service",
        "repo-request-flow",
        "repo-data-flow",
    }
