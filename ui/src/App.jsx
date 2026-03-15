import { useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const DEFAULT_QUERY = "Umami";
const STORAGE_KEY = "linked-notes-ui-state-v1";

function readStoredUiState() {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function colorForType(type) {
  const palette = {
    project: "#135f5a",
    service: "#2f5fd0",
    decision: "#cc6b2c",
    process: "#7a4bb8",
    "data-flow": "#0f8a7f",
    issue: "#b6472f",
  };
  return palette[type] || "#4d695f";
}

function typeLabel(type) {
  const labels = {
    project: "Repo Root",
    service: "Subsystem",
    process: "Process Flow",
    "data-flow": "Data Flow",
    decision: "Decision",
    issue: "Risk",
    research: "Context",
  };
  return labels[type] || type || "Note";
}

function splitPathAndLine(rawPath) {
  const cleaned = String(rawPath || "").replace(/^`|`$/g, "");
  const match = cleaned.match(/^(.*):(\d+)(?:-(\d+))?$/);
  if (!match) {
    return { path: cleaned, start: null, end: null };
  }
  return {
    path: match[1],
    start: Number(match[2]),
    end: Number(match[3] || match[2]),
  };
}

function architectureNode({ data, selected }) {
  return (
    <div
      className={`rf-card ${data.role} ${selected ? "selected" : ""}`}
      style={{ "--accent": data.color }}
    >
      <Handle type="target" position={Position.Top} className="rf-handle" />
      <div className="rf-title">{data.title}</div>
      <div className="rf-chip">{data.label}</div>
      {data.summary ? <div className="rf-summary">{data.summary}</div> : null}
      <Handle type="source" position={Position.Bottom} className="rf-handle" />
    </div>
  );
}

const nodeTypes = { architecture: architectureNode };

function enrichGraph(graph) {
  if (!graph?.anchor) return graph;
  const edgeIndex = new Map();
  for (const edge of graph.edges) {
    if (!edgeIndex.has(edge.source)) edgeIndex.set(edge.source, new Set());
    if (!edgeIndex.has(edge.target)) edgeIndex.set(edge.target, new Set());
    edgeIndex.get(edge.source).add(edge.target);
    edgeIndex.get(edge.target).add(edge.source);
  }
  const anchor = graph.nodes.find((node) => node.id === graph.anchor);
  if (!anchor) return graph;
  const primaryNodes = graph.nodes
    .filter(
      (node) =>
        node.id !== anchor.id &&
        node.entity_type === "service" &&
        edgeIndex.get(anchor.id)?.has(node.id),
    )
    .sort((a, b) => a.title.localeCompare(b.title));
  const primaryIds = new Set(primaryNodes.map((node) => node.id));
  const nodes = graph.nodes.map((node) => {
    if (node.id === anchor.id) {
      return { ...node, display_role: "anchor", cluster_id: anchor.id };
    }
    if (primaryIds.has(node.id)) {
      return { ...node, display_role: "primary", cluster_id: node.id };
    }
    const neighbors = Array.from(edgeIndex.get(node.id) || []);
    const clusterId =
      neighbors.find((neighbor) => primaryIds.has(neighbor)) || primaryNodes[0]?.id || anchor.id;
    return {
      ...node,
      display_role:
        node.entity_type === "process" || node.entity_type === "data-flow" ? "flow" : "detail",
      cluster_id: clusterId,
    };
  });
  return {
    ...graph,
    nodes,
    primary_nodes: primaryNodes.map((node) => ({ id: node.id, title: node.title })),
  };
}

function applyLens(graph, { viewMode, focusId, level }) {
  if (!graph?.anchor) return graph;
  const selectedIds = new Set([graph.anchor]);
  const primaryNodes = graph.nodes.filter((node) => node.display_role === "primary");
  const chosenPrimary = focusId
    ? primaryNodes.filter((node) => node.id === focusId)
    : primaryNodes;
  for (const node of chosenPrimary) selectedIds.add(node.id);

  for (const node of graph.nodes) {
    if (selectedIds.has(node.id) || node.id === graph.anchor) continue;
    if (focusId && node.cluster_id !== focusId) continue;
    if (level === "1") continue;
    if (level === "2") {
      if (viewMode === "flow") {
        if (node.display_role === "flow") selectedIds.add(node.id);
      } else if (node.display_role === "detail" || node.display_role === "flow") {
        selectedIds.add(node.id);
      }
      continue;
    }
    if (viewMode === "subsystem" && focusId && node.cluster_id !== focusId) continue;
    if (
      viewMode === "flow" &&
      node.display_role !== "flow" &&
      focusId &&
      node.cluster_id !== focusId
    ) {
      continue;
    }
    selectedIds.add(node.id);
  }

  const nodes = graph.nodes.filter((node) => selectedIds.has(node.id));
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter(
    (edge) =>
      nodeIds.has(edge.source) &&
      nodeIds.has(edge.target) &&
      (edge.types.includes("contains") ||
        edge.types.includes("part_of") ||
        viewMode === "flow" ||
        level === "3"),
  );

  return {
    ...graph,
    nodes,
    edges,
    stats: {
      ...graph.stats,
      shown_nodes: nodes.length,
      shown_edges: edges.length,
    },
  };
}

function layoutGraph(graph, viewMode, focusId) {
  const width = 1200;
  const height = 900;
  if (!graph?.anchor) return { nodes: [], edges: [] };
  const anchor = graph.nodes.find((node) => node.id === graph.anchor);
  const primaryNodes = graph.nodes.filter((node) => node.display_role === "primary");
  const secondaryNodes = graph.nodes.filter(
    (node) => node.id !== graph.anchor && node.display_role !== "primary",
  );
  const positions = new Map();

  if (viewMode === "flow") {
    positions.set(anchor.id, { x: 110, y: height / 2 });
    primaryNodes.forEach((node, index) => {
      positions.set(node.id, {
        x: 430,
        y: ((index + 1) * height) / (primaryNodes.length + 1),
      });
    });
    secondaryNodes.forEach((node) => {
      const siblings = secondaryNodes.filter((candidate) => candidate.cluster_id === node.cluster_id);
      const siblingIndex = siblings.findIndex((candidate) => candidate.id === node.id);
      const primaryIndex = Math.max(
        0,
        primaryNodes.findIndex((candidate) => candidate.id === node.cluster_id),
      );
      const baseY = ((primaryIndex + 1) * height) / (primaryNodes.length + 1);
      positions.set(node.id, {
        x: node.display_role === "flow" ? 700 : 930,
        y: baseY + (siblingIndex - (siblings.length - 1) / 2) * 90,
      });
    });
  } else if (viewMode === "subsystem" && focusId) {
    const focus = primaryNodes.find((node) => node.id === focusId) || primaryNodes[0];
    positions.set(anchor.id, { x: 160, y: height / 2 });
    positions.set(focus.id, { x: 500, y: height / 2 });
    const focusDetails = secondaryNodes.filter((node) => node.cluster_id === focus.id);
    focusDetails.forEach((node, index) => {
      const angle = -Math.PI / 2 + (index * Math.PI) / Math.max(1, focusDetails.length - 1 || 1);
      positions.set(node.id, {
        x: 860 + Math.cos(angle) * 120,
        y: height / 2 + Math.sin(angle) * 180,
      });
    });
    primaryNodes
      .filter((node) => node.id !== focus.id)
      .forEach((node, index) => {
        positions.set(node.id, { x: 470, y: 110 + index * 84 });
      });
  } else {
    positions.set(anchor.id, { x: width / 2, y: height / 2 });
    const ringRadius = 240;
    primaryNodes.forEach((node, index) => {
      const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(1, primaryNodes.length);
      positions.set(node.id, {
        x: width / 2 + Math.cos(angle) * ringRadius,
        y: height / 2 + Math.sin(angle) * ringRadius,
      });
    });
    secondaryNodes.forEach((node) => {
      const siblings = secondaryNodes.filter((candidate) => candidate.cluster_id === node.cluster_id);
      const siblingIndex = siblings.findIndex((candidate) => candidate.id === node.id);
      const primaryIndex = Math.max(
        0,
        primaryNodes.findIndex((candidate) => candidate.id === node.cluster_id),
      );
      const primaryAngle =
        -Math.PI / 2 + (primaryIndex * Math.PI * 2) / Math.max(1, primaryNodes.length);
      const fanStart = primaryAngle - 0.34;
      const fanStep = siblings.length > 1 ? 0.68 / (siblings.length - 1) : 0;
      const angle = fanStart + fanStep * siblingIndex;
      positions.set(node.id, {
        x: width / 2 + Math.cos(angle) * (ringRadius + 210),
        y: height / 2 + Math.sin(angle) * (ringRadius + 210),
      });
    });
  }

  const nodes = graph.nodes.map((node) => ({
    id: node.id,
    type: "architecture",
    position: positions.get(node.id) || { x: 0, y: 0 },
    data: {
      title: node.title,
      label: typeLabel(node.entity_type),
      summary:
        node.display_role === "anchor" ||
        node.display_role === "flow" ||
        node.id === graph.anchor
          ? node.summary
          : "",
      color: colorForType(node.entity_type),
      role: node.display_role,
    },
  }));

  const edges = graph.edges.map((edge) => ({
    id: `${edge.source}-${edge.target}-${edge.label}`,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    animated: false,
    style: {
      stroke:
        edge.types.includes("contains") || edge.types.includes("part_of")
          ? "rgba(19,95,90,0.34)"
          : "rgba(47,95,208,0.18)",
      strokeWidth:
        edge.types.includes("contains") || edge.types.includes("part_of") ? 2.2 : 1.4,
    },
  }));

  return { nodes, edges };
}

function AppInner() {
  const initialState = readStoredUiState();
  const [graph, setGraph] = useState(null);
  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState(initialState.query || DEFAULT_QUERY);
  const [viewMode, setViewMode] = useState(initialState.viewMode || "overview");
  const [focusId, setFocusId] = useState(initialState.focusId || "");
  const [level, setLevel] = useState(initialState.level || "2");
  const [depth, setDepth] = useState(initialState.depth || "1");
  const [limit, setLimit] = useState(initialState.limit || "80");
  const [relationFilter, setRelationFilter] = useState(initialState.relationFilter || "");
  const [demoMode, setDemoMode] = useState(
    typeof initialState.demoMode === "boolean" ? initialState.demoMode : true,
  );
  const [theme, setTheme] = useState(initialState.theme || "light");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    Boolean(initialState.sidebarCollapsed),
  );
  const [detailCollapsed, setDetailCollapsed] = useState(
    Boolean(initialState.detailCollapsed),
  );
  const [detailWidth, setDetailWidth] = useState(initialState.detailWidth || 380);
  const resizingRef = useRef(false);

  useEffect(() => {
    document.body.classList.toggle("theme-charcoal", theme === "charcoal");
    return () => {
      document.body.classList.remove("theme-charcoal");
    };
  }, [theme]);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          query,
          viewMode,
          focusId,
          level,
          depth,
          limit,
          relationFilter,
          demoMode,
          theme,
          sidebarCollapsed,
          detailCollapsed,
          detailWidth,
        }),
      );
    } catch {
      // ignore local storage write failures
    }
  }, [
    query,
    viewMode,
    focusId,
    level,
    depth,
    limit,
    relationFilter,
    demoMode,
    theme,
    sidebarCollapsed,
    detailCollapsed,
    detailWidth,
  ]);

  async function loadGraph() {
    setLoading(true);
    const params = new URLSearchParams();
    if (query) {
      params.set("anchor", query);
      params.set("query", query);
    }
    params.set("depth", depth);
    params.set("limit", limit);
    params.set("demo_mode", String(demoMode));
    if (relationFilter) params.append("relation_type", relationFilter);
    const response = await fetch(`/api/graph?${params.toString()}`);
    const raw = enrichGraph(await response.json());
    const next = applyLens(raw, { viewMode, focusId, level });
    setGraph(next);
    if (next.anchor) {
      loadNote(next.anchor);
    }
    setLoading(false);
  }

  async function loadNote(id) {
    const response = await fetch(`/api/note?id=${encodeURIComponent(id)}`);
    if (!response.ok) return;
    setNote(await response.json());
  }

  useEffect(() => {
    loadGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!graph) return;
    loadGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, level, focusId]);

  useEffect(() => {
    const onMove = (event) => {
      if (!resizingRef.current || detailCollapsed) return;
      setDetailWidth(Math.max(320, Math.min(680, window.innerWidth - event.clientX)));
    };
    const onUp = () => {
      resizingRef.current = false;
      document.body.style.cursor = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [detailCollapsed]);

  const focusOptions = graph?.primary_nodes || [];
  const flow = useMemo(() => layoutGraph(graph, viewMode, focusId), [graph, viewMode, focusId]);

  const shellStyle = {
    "--sidebar-width": sidebarCollapsed ? "72px" : "320px",
    "--detail-width": detailCollapsed ? "0px" : `${detailWidth}px`,
  };

  return (
    <div
      className={`shell ${sidebarCollapsed ? "sidebar-collapsed" : ""} ${detailCollapsed ? "detail-collapsed" : ""}`}
      style={shellStyle}
    >
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">Local Graph Workbench</div>
          <h1>linked-notes-ui</h1>
          <p>Explore your markdown memory graph without leaving localhost.</p>
        </div>
        <form
          className="controls"
          onSubmit={(event) => {
            event.preventDefault();
            loadGraph();
          }}
        >
          <div className="quick-actions">
            <button
              type="button"
              className="pill"
              onClick={() => {
                setQuery("Umami");
                setViewMode("overview");
                setFocusId("");
                setLevel("2");
                setDepth("1");
                loadGraph();
              }}
            >
              Demo: Umami
            </button>
            <button
              type="button"
              className="pill"
              onClick={() => {
                setQuery("PocketBase");
                setViewMode("overview");
                setFocusId("");
                setLevel("2");
                setDepth("1");
                loadGraph();
              }}
            >
              Demo: PocketBase
            </button>
          </div>
          <section className="panel compact">
            <div className="panel-title">Graph Lens</div>
            <label>
              <span>View</span>
              <select value={viewMode} onChange={(event) => setViewMode(event.target.value)}>
                <option value="overview">Overview</option>
                <option value="flow">Flow</option>
                <option value="subsystem">Subsystem</option>
              </select>
            </label>
            <label>
              <span>Focus Area</span>
              <select value={focusId} onChange={(event) => setFocusId(event.target.value)}>
                <option value="">All subsystems</option>
                {focusOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Detail Level</span>
              <select value={level} onChange={(event) => setLevel(event.target.value)}>
                <option value="1">L1 · Core map</option>
                <option value="2">L2 · Branches</option>
                <option value="3">L3 · Full detail</option>
              </select>
            </label>
          </section>
          <label>
            <span>Anchor or Search</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <label>
            <span>Depth</span>
            <input type="range" min="1" max="4" value={depth} onChange={(e) => setDepth(e.target.value)} />
          </label>
          <label>
            <span>Node Limit</span>
            <input type="number" min="10" max="250" value={limit} onChange={(e) => setLimit(e.target.value)} />
          </label>
          <label>
            <span>Relation Filter</span>
            <select value={relationFilter} onChange={(e) => setRelationFilter(e.target.value)}>
              <option value="">All relationships</option>
              {(graph?.available_relation_types || []).map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={demoMode} onChange={(e) => setDemoMode(e.target.checked)} />
            <span>Demo mode</span>
          </label>
          <div className="button-row">
            <button type="submit">Load Graph</button>
          </div>
        </form>
      </aside>

      <main className="workspace">
        <div className="toolbar">
          <div className="toolbar-main">
            <button type="button" className="icon-button secondary" onClick={() => setSidebarCollapsed((value) => !value)}>
              {sidebarCollapsed ? "Show Controls" : "Hide Controls"}
            </button>
            <div id="graphTitle">{graph?.anchor ? `Graph: ${graph.nodes.find((n) => n.id === graph.anchor)?.title || graph.anchor}` : "Graph"}</div>
          </div>
          <div className="toolbar-meta">
            <button
              type="button"
              className="icon-button secondary"
              onClick={() => setTheme((value) => (value === "charcoal" ? "light" : "charcoal"))}
            >
              {theme === "charcoal" ? "Light" : "Charcoal"}
            </button>
            <span className="lens-label">{`${viewMode} · L${level}${focusId ? ` · ${focusOptions.find((item) => item.id === focusId)?.title || ""}` : ""}`}</span>
            <span className="badge">{loading ? "loading" : "ready"}</span>
          </div>
        </div>
        <div className="canvas-wrap">
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.3}
            maxZoom={1.8}
            onNodeClick={(_, node) => loadNote(node.id)}
          >
            <Background color="rgba(13,108,99,0.08)" gap={40} />
            <Controls />
            <MiniMap nodeColor={(node) => colorForType(node.data?.label?.toLowerCase?.() || "")} pannable />
          </ReactFlow>
          <div className="legend">
            <span className="legend-item"><span className="legend-swatch" style={{ background: "#2f5fd0" }} />Subsystem</span>
            <span className="legend-item"><span className="legend-swatch" style={{ background: "#7a4bb8" }} />Process</span>
            <span className="legend-item"><span className="legend-swatch" style={{ background: "#0f8a7f" }} />Data Flow</span>
          </div>
        </div>
      </main>

      <div className="resize-handle" onMouseDown={() => {
        resizingRef.current = true;
        document.body.style.cursor = "col-resize";
      }} />
      <aside className="detail">
        <section className="panel">
          <div className="detail-header">
            <div className="panel-title">Selected Node</div>
            <div className="detail-tabs">
              <button type="button" className="tab active">Note</button>
              <button
                type="button"
                className="tab secondary"
                onClick={() => {
                  if (!note?.id) return;
                  window.open(`/source.html?id=${encodeURIComponent(note.id)}`, "_blank", "noopener,noreferrer");
                }}
              >
                Open Source View
              </button>
              <button type="button" className="icon-button secondary" onClick={() => setDetailCollapsed((value) => !value)}>
                {detailCollapsed ? "Show" : "Hide"}
              </button>
            </div>
          </div>
          <div className="detail-content">
            {note ? (
              <>
                <h2>{note.title}</h2>
                <p className="meta-line"><strong>Entity Type:</strong> {note.frontmatter.entity_type || "n/a"}</p>
                <p className="meta-line"><strong>Status:</strong> {note.frontmatter.status || "n/a"}</p>
                <div className="tag-list">
                  {(note.frontmatter.tags || []).map((tag) => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
                <div className="detail-section">
                  <h3>Summary</h3>
                  <p>{note.frontmatter.summary || "No summary yet."}</p>
                </div>
                {note.flow_body || note.data_path_body ? (
                  <div className="detail-section">
                    <h3>{note.flow_body ? "Flow" : "Data Path"}</h3>
                    <pre>{note.flow_body || note.data_path_body}</pre>
                  </div>
                ) : null}
                <div className="detail-section">
                  <h3>Relationships</h3>
                  <div className="edge-list">
                    {note.explicit_relationships?.length
                      ? note.explicit_relationships.map((item) => (
                          <span key={`${item.type}-${item.target}`} className="edge">
                            {item.type} -&gt; {item.target}
                          </span>
                        ))
                      : <span className="edge">No explicit relationships</span>}
                  </div>
                </div>
              </>
            ) : (
              <p>Select a node to inspect its note details.</p>
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppInner />
    </ReactFlowProvider>
  );
}
