const state = {
  graph: null,
  fullGraph: null,
  nodePositions: new Map(),
  hoveredNodeId: null,
  selectedNodeId: null,
  dragNodeId: null,
  lensLabel: "Focused Demo",
  detailTab: "note",
};

const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");
const emptyState = document.getElementById("emptyState");
const detailContent = document.getElementById("detailContent");
const statsEl = document.getElementById("stats");
const statusBadge = document.getElementById("statusBadge");
const graphTitle = document.getElementById("graphTitle");
const relationFilter = document.getElementById("relationFilter");
const controls = document.getElementById("controls");
const depthInput = document.getElementById("depthInput");
const depthValue = document.getElementById("depthValue");
const resetButton = document.getElementById("resetButton");
const pathButton = document.getElementById("pathButton");
const pathResult = document.getElementById("pathResult");
const pathStart = document.getElementById("pathStart");
const pathEnd = document.getElementById("pathEnd");
const demoUmami = document.getElementById("demoUmami");
const demoPocketBase = document.getElementById("demoPocketBase");
const demoMode = document.getElementById("demoMode");
const viewMode = document.getElementById("viewMode");
const serviceFilter = document.getElementById("serviceFilter");
const levelFilter = document.getElementById("levelFilter");
const lensLabel = document.getElementById("lensLabel");
const noteTab = document.getElementById("noteTab");
const openSourceView = document.getElementById("openSourceView");
const sidebarToggle = document.getElementById("sidebarToggle");
const detailToggle = document.getElementById("detailToggle");
const shell = document.querySelector(".shell");
const resizeHandle = document.getElementById("detailResizeHandle");

function setStatus(text) {
  statusBadge.textContent = text;
}

function syncPanelState() {
  sidebarToggle.textContent = shell.classList.contains("sidebar-collapsed")
    ? "Show Controls"
    : "Hide Controls";
  detailToggle.textContent = shell.classList.contains("detail-collapsed")
    ? "Show"
    : "Hide";
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * window.devicePixelRatio;
  canvas.height = rect.height * window.devicePixelRatio;
  ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
}

function colorForNode(node) {
  const key = (node.entity_type || node.status || "note").toLowerCase();
  const palette = {
    project: "#135f5a",
    service: "#2f5fd0",
    decision: "#cc6b2c",
    process: "#7a4bb8",
    "data-flow": "#0f8a7f",
    issue: "#b6472f",
    session: "#8260d7",
    idea: "#a04f9b",
  };
  return palette[key] || "#4d695f";
}

function typeLabel(node) {
  const labels = {
    project: "Repo Root",
    service: "Subsystem",
    process: "Process Flow",
    "data-flow": "Data Flow",
    decision: "Decision",
    issue: "Risk",
    research: "Context",
  };
  return labels[node.entity_type] || node.entity_type || (node.tags[0] || "Note");
}

function wrapLines(text, maxChars = 28, maxLines = 2) {
  const words = text.split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxChars || !current) {
      current = next;
      continue;
    }
    lines.push(current);
    current = word;
    if (lines.length === maxLines - 1) {
      break;
    }
  }
  if (lines.length < maxLines && current) {
    lines.push(current);
  }
  if (lines.length > maxLines) {
    return lines.slice(0, maxLines);
  }
  if (words.join(" ").length > lines.join(" ").length && lines.length) {
    lines[lines.length - 1] = `${lines[lines.length - 1].slice(0, maxChars - 1)}...`;
  }
  return lines;
}

function ensurePositions(graph) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  for (const node of graph.nodes) {
    if (!state.nodePositions.has(node.id)) {
      state.nodePositions.set(node.id, {
        x: Math.random() * width * 0.8 + width * 0.1,
        y: Math.random() * height * 0.8 + height * 0.1,
        vx: 0,
        vy: 0,
      });
    }
  }
}

function buildEdgeIndex(graph) {
  const edgeIndex = new Map();
  for (const edge of graph.edges) {
    if (!edgeIndex.has(edge.source)) {
      edgeIndex.set(edge.source, new Set());
    }
    if (!edgeIndex.has(edge.target)) {
      edgeIndex.set(edge.target, new Set());
    }
    edgeIndex.get(edge.source).add(edge.target);
    edgeIndex.get(edge.target).add(edge.source);
  }
  return edgeIndex;
}

function enrichGraph(graph) {
  const next = {
    ...graph,
    nodes: graph.nodes.map((node) => ({ ...node })),
    edges: graph.edges.map((edge) => ({ ...edge })),
  };
  if (!next.anchor) {
    return next;
  }

  const edgeIndex = buildEdgeIndex(next);
  const anchor = next.nodes.find((node) => node.id === next.anchor);
  if (!anchor) {
    return next;
  }

  const primaryNodes = next.nodes
    .filter(
      (node) =>
        node.id !== anchor.id &&
        node.entity_type === "service" &&
        edgeIndex.get(anchor.id)?.has(node.id),
    )
    .sort((a, b) => a.title.localeCompare(b.title));
  const primaryIds = new Set(primaryNodes.map((node) => node.id));

  for (const node of next.nodes) {
    if (node.id === anchor.id) {
      node.display_role = "anchor";
      node.cluster_id = anchor.id;
      continue;
    }
    if (primaryIds.has(node.id)) {
      node.display_role = "primary";
      node.cluster_id = node.id;
      continue;
    }
    const neighbors = Array.from(edgeIndex.get(node.id) || []);
    const clusterId = neighbors.find((neighbor) => primaryIds.has(neighbor)) || primaryNodes[0]?.id || anchor.id;
    node.display_role = node.entity_type === "process" || node.entity_type === "data-flow"
      ? "flow"
      : "detail";
    node.cluster_id = clusterId;
  }

  next.primary_nodes = primaryNodes.map((node) => ({
    id: node.id,
    title: node.title,
  }));
  return next;
}

function populateFocusOptions(graph) {
  const currentValue = serviceFilter.value;
  serviceFilter.innerHTML = '<option value="">All subsystems</option>';
  for (const node of graph.primary_nodes || []) {
    const option = document.createElement("option");
    option.value = node.id;
    option.textContent = node.title;
    serviceFilter.appendChild(option);
  }
  if ([...serviceFilter.options].some((option) => option.value === currentValue)) {
    serviceFilter.value = currentValue;
  }
}

function applyGraphLens(graph) {
  if (!graph?.anchor) {
    return graph;
  }

  const focusId = serviceFilter.value;
  const level = Number(levelFilter.value || "2");
  const mode = viewMode.value;
  const selectedIds = new Set([graph.anchor]);

  const primaryNodes = graph.nodes.filter((node) => node.display_role === "primary");
  const chosenPrimary = focusId
    ? primaryNodes.filter((node) => node.id === focusId)
    : primaryNodes;

  for (const node of chosenPrimary) {
    selectedIds.add(node.id);
  }

  const candidateNodes = graph.nodes.filter((node) => {
    if (node.id === graph.anchor || selectedIds.has(node.id)) {
      return false;
    }
    if (focusId && node.cluster_id !== focusId) {
      return false;
    }
    if (level === 1) {
      return false;
    }
    if (level === 2) {
      if (mode === "flow") {
        return node.display_role === "flow";
      }
      return node.display_role === "detail" || node.display_role === "flow";
    }
    if (mode === "flow") {
      return node.display_role === "flow" || node.cluster_id === focusId || !focusId;
    }
    if (mode === "subsystem" && focusId) {
      return node.cluster_id === focusId;
    }
    return true;
  });

  for (const node of candidateNodes) {
    selectedIds.add(node.id);
  }

  if (mode === "flow") {
    for (const node of graph.nodes) {
      if (
        (node.entity_type === "process" || node.entity_type === "data-flow") &&
        (!focusId || node.cluster_id === focusId)
      ) {
        selectedIds.add(node.id);
        if (node.cluster_id) {
          selectedIds.add(node.cluster_id);
        }
      }
    }
  }

  const filteredNodes = graph.nodes.filter((node) => selectedIds.has(node.id));
  const filteredIds = new Set(filteredNodes.map((node) => node.id));
  const filteredEdges = graph.edges.filter(
    (edge) => filteredIds.has(edge.source) && filteredIds.has(edge.target),
  );

  const lensText = `${viewMode.options[viewMode.selectedIndex].text} · ${levelFilter.options[levelFilter.selectedIndex - 1 + 1].text.split("·")[0].trim()}${focusId ? ` · ${serviceFilter.options[serviceFilter.selectedIndex].text}` : ""}`;
  state.lensLabel = lensText;
  lensLabel.textContent = lensText;

  return {
    ...graph,
    nodes: filteredNodes,
    edges: filteredEdges,
    stats: {
      ...graph.stats,
      shown_nodes: filteredNodes.length,
      shown_edges: filteredEdges.length,
      orphan_nodes_shown: filteredNodes.filter(
        (node) => !filteredEdges.some((edge) => edge.source === node.id || edge.target === node.id),
      ).length,
    },
  };
}

function estimateNodeBox(node) {
  const titleLength = Math.max(12, node.title.length);
  const isFlow = node.entity_type === "process" || node.entity_type === "data-flow";
  const width = node.is_anchor
    ? Math.min(360, Math.max(230, titleLength * 8.6))
    : isFlow
      ? Math.min(280, Math.max(190, titleLength * 7.6))
      : Math.min(250, Math.max(170, titleLength * 7.3));
  const height = node.is_anchor ? 112 : isFlow ? 94 : 82;
  return { width, height };
}

function layoutGraph(graph) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const positions = state.nodePositions;
  ensurePositions(graph);

  if (graph.demo_mode && graph.anchor) {
    const anchor = graph.nodes.find((node) => node.id === graph.anchor);
    if (!anchor) {
      return;
    }
    const edgeIndex = buildEdgeIndex(graph);
    const primaryNodes = graph.nodes.filter((node) => node.display_role === "primary");
    const primarySet = new Set(primaryNodes.map((node) => node.id));
    const secondaryNodes = graph.nodes.filter(
      (node) => node.id !== anchor.id && !primarySet.has(node.id),
    );

    positions.set(anchor.id, {
      x: viewMode.value === "flow" ? width * 0.18 : width / 2,
      y: height / 2,
      vx: 0,
      vy: 0,
    });

    if (viewMode.value === "flow") {
      const laneX = width * 0.48;
      const detailX = width * 0.76;
      primaryNodes.forEach((node, index) => {
        const y = height * (index + 1) / (primaryNodes.length + 1);
        positions.set(node.id, { x: laneX, y, vx: 0, vy: 0 });
      });

      secondaryNodes.forEach((node) => {
        const clusterIndex = Math.max(
          0,
          primaryNodes.findIndex((candidate) => candidate.id === node.cluster_id),
        );
        const siblings = secondaryNodes.filter((candidate) => candidate.cluster_id === node.cluster_id);
        const siblingIndex = Math.max(
          0,
          siblings.findIndex((candidate) => candidate.id === node.id),
        );
        const baseY = height * (clusterIndex + 1) / (primaryNodes.length + 1);
        const offset = (siblingIndex - (siblings.length - 1) / 2) * 84;
        positions.set(node.id, {
          x: node.display_role === "flow" ? width * 0.64 : detailX,
          y: baseY + offset,
          vx: 0,
          vy: 0,
        });
      });
      return;
    }

    if (viewMode.value === "subsystem" && serviceFilter.value) {
      const focus = primaryNodes.find((node) => node.id === serviceFilter.value) || primaryNodes[0];
      positions.set(anchor.id, { x: width * 0.22, y: height / 2, vx: 0, vy: 0 });
      positions.set(focus.id, { x: width * 0.48, y: height / 2, vx: 0, vy: 0 });
      const focusDetails = secondaryNodes.filter((node) => node.cluster_id === focus.id);
      focusDetails.forEach((node, index) => {
        const angle = -Math.PI / 2 + (index * Math.PI) / Math.max(1, focusDetails.length - 1 || 1);
        positions.set(node.id, {
          x: width * 0.74 + Math.cos(angle) * 110,
          y: height / 2 + Math.sin(angle) * 150,
          vx: 0,
          vy: 0,
        });
      });
      primaryNodes
        .filter((node) => node.id !== focus.id)
        .forEach((node, index) => {
          positions.set(node.id, {
            x: width * 0.46,
            y: 120 + index * 74,
            vx: 0,
            vy: 0,
          });
        });
      return;
    }

    const ringRadius = Math.min(width, height) * 0.3;
    primaryNodes.forEach((node, index) => {
      const angle =
        -Math.PI / 2 + (index * (Math.PI * 2)) / Math.max(1, primaryNodes.length);
      positions.set(node.id, {
        x: width / 2 + Math.cos(angle) * ringRadius,
        y: height / 2 + Math.sin(angle) * ringRadius,
        vx: 0,
        vy: 0,
      });
    });

    secondaryNodes.forEach((node) => {
      const neighbors = Array.from(edgeIndex.get(node.id) || []);
      const primaryNeighborId =
        node.cluster_id ||
        neighbors.find((neighbor) => primarySet.has(neighbor)) ||
        primaryNodes[0]?.id;
      const primaryIndex = Math.max(
        0,
        primaryNodes.findIndex((candidate) => candidate.id === primaryNeighborId),
      );
      const siblings = secondaryNodes
        .filter((candidate) => {
          const related = Array.from(edgeIndex.get(candidate.id) || []);
          return (
            related.find((neighbor) => primarySet.has(neighbor)) || primaryNodes[0]?.id
          ) === primaryNeighborId;
        })
        .sort((a, b) => a.title.localeCompare(b.title));
      const siblingIndex = Math.max(
        0,
        siblings.findIndex((candidate) => candidate.id === node.id),
      );
      const primaryAngle =
        -Math.PI / 2 + (primaryIndex * (Math.PI * 2)) / Math.max(1, primaryNodes.length);
      const fanStart = primaryAngle - 0.34;
      const fanStep = siblings.length > 1 ? 0.68 / (siblings.length - 1) : 0;
      const angle = fanStart + fanStep * siblingIndex;
      const outerRadius = ringRadius + 160;

      positions.set(node.id, {
        x: width / 2 + Math.cos(angle) * outerRadius,
        y: height / 2 + Math.sin(angle) * outerRadius,
        vx: 0,
        vy: 0,
      });
    });
    return;
  }

  const columns = Math.max(2, Math.ceil(Math.sqrt(graph.nodes.length)));
  const xGap = width / (columns + 1);
  const yGap = height / (Math.ceil(graph.nodes.length / columns) + 1);
  graph.nodes.forEach((node, index) => {
    const col = index % columns;
    const row = Math.floor(index / columns);
    positions.set(node.id, {
      x: xGap * (col + 1),
      y: yGap * (row + 1),
      vx: 0,
      vy: 0,
    });
  });
}

function roundedRect(x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

function drawEdge(source, target, highlighted = false) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const mx = (source.x + target.x) / 2;
  const my = (source.y + target.y) / 2;
  const curve = Math.min(90, Math.max(18, (Math.abs(dx) + Math.abs(dy)) * 0.05));
  ctx.beginPath();
  ctx.strokeStyle = highlighted ? "rgba(13, 108, 99, 0.50)" : "rgba(31, 28, 24, 0.14)";
  ctx.lineWidth = highlighted ? 2.4 : 1.15;
  ctx.moveTo(source.x, source.y);
  ctx.quadraticCurveTo(mx, my - curve, target.x, target.y);
  ctx.stroke();
}

function shouldDrawEdge(edge) {
  return edge.types.some((type) => type === "contains" || type === "part_of");
}

function clusterColor(node) {
  if (node.entity_type === "process") {
    return "rgba(122, 75, 184, 0.08)";
  }
  if (node.entity_type === "data-flow") {
    return "rgba(15, 138, 127, 0.08)";
  }
  return "rgba(47, 95, 208, 0.06)";
}

function renderClusterLabel(text, x, y) {
  ctx.save();
  ctx.font = "600 11px sans-serif";
  const width = Math.max(82, ctx.measureText(text).width + 18);
  roundedRect(x - width / 2, y - 14, width, 24, 12);
  ctx.fillStyle = "rgba(255,252,247,0.92)";
  ctx.fill();
  ctx.strokeStyle = "rgba(35,33,29,0.08)";
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.fillStyle = "rgba(100,93,84,0.92)";
  ctx.fillText(text, x - width / 2 + 10, y + 2);
  ctx.restore();
}

function drawGraph() {
  const graph = state.graph;
  ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
  if (!graph) {
    return;
  }

  const positions = state.nodePositions;
  const anchor = graph.anchor ? graph.nodes.find((node) => node.id === graph.anchor) : null;
  const primaryNodes = graph.nodes.filter((node) => node.display_role === "primary");

  for (const node of primaryNodes) {
    const pos = positions.get(node.id);
    if (!pos) {
      continue;
    }
    ctx.beginPath();
    ctx.fillStyle = clusterColor(node);
    ctx.arc(pos.x, pos.y, viewMode.value === "flow" ? 118 : 150, 0, Math.PI * 2);
    ctx.fill();
    renderClusterLabel(node.title.replace(/^Umami\s+|^PocketBase\s+/i, ""), pos.x, pos.y - 116);
  }

  for (const edge of graph.edges) {
    const isActiveEdge =
      edge.source === state.selectedNodeId ||
      edge.target === state.selectedNodeId ||
      edge.source === state.hoveredNodeId ||
      edge.target === state.hoveredNodeId;
    if (!shouldDrawEdge(edge) && !isActiveEdge) {
      continue;
    }
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) {
      continue;
    }
    const highlighted =
      edge.source === state.selectedNodeId ||
      edge.target === state.selectedNodeId ||
      edge.source === state.hoveredNodeId ||
      edge.target === state.hoveredNodeId;
    drawEdge(source, target, highlighted);
  }

  for (const node of graph.nodes) {
    const pos = positions.get(node.id);
    const { width, height } = estimateNodeBox(node);
    const x = pos.x - width / 2;
    const y = pos.y - height / 2;
    const isFlow = node.entity_type === "process" || node.entity_type === "data-flow";
    const isSelected = node.id === state.selectedNodeId;
    const isHovered = node.id === state.hoveredNodeId;
    const fill = node.is_anchor
      ? colorForNode(node)
      : isFlow
        ? "rgba(244, 249, 248, 0.99)"
        : "rgba(255, 252, 247, 0.96)";
    const border =
      isSelected || isHovered ? colorForNode(node) : "rgba(31, 28, 24, 0.14)";

    ctx.save();
    ctx.shadowColor = node.is_anchor
      ? "rgba(19, 95, 90, 0.20)"
      : isFlow
        ? "rgba(47, 95, 208, 0.11)"
        : "rgba(30, 23, 15, 0.10)";
    ctx.shadowBlur = node.is_anchor ? 30 : isSelected ? 24 : 16;
    ctx.shadowOffsetY = node.is_anchor ? 14 : 8;
    roundedRect(x, y, width, height, 18);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.restore();

    roundedRect(x, y, width, height, 18);
    ctx.strokeStyle = border;
    ctx.lineWidth = node.id === state.selectedNodeId ? 2.4 : 1.1;
    ctx.stroke();

    ctx.fillStyle = node.is_anchor ? "#fffdf8" : colorForNode(node);
    ctx.font = node.is_anchor ? "700 14px sans-serif" : "600 12px sans-serif";
    const titleLines = wrapLines(node.title, node.is_anchor ? 30 : 24, 2);
    titleLines.forEach((line, index) => {
      ctx.fillText(line, x + 14, y + 28 + index * 16);
    });

    const subtitle = typeLabel(node);
    const chipWidth = Math.max(60, subtitle.length * 6.7 + 18);
    const chipY = y + (node.is_anchor ? 58 : 54);
    roundedRect(x + 14, chipY, chipWidth, 22, 11);
    ctx.fillStyle = node.is_anchor
      ? "rgba(255,253,248,0.18)"
      : isFlow
        ? "rgba(47,95,208,0.09)"
        : "rgba(13,108,99,0.10)";
    ctx.fill();
    ctx.fillStyle = node.is_anchor ? "rgba(255,253,248,0.86)" : "rgba(31,28,24,0.64)";
    ctx.font = "11px sans-serif";
    ctx.fillText(subtitle, x + 24, chipY + 15);

    if ((node.is_anchor || isFlow || isSelected) && node.summary) {
      ctx.fillStyle = "rgba(255,253,248,0.86)";
      if (!node.is_anchor) {
        ctx.fillStyle = "rgba(31,28,24,0.62)";
      }
      ctx.font = "11px sans-serif";
      const maxLength = node.is_anchor ? 46 : 40;
      const summary =
        node.summary.length > maxLength
          ? `${node.summary.slice(0, maxLength)}...`
          : node.summary;
      ctx.fillText(summary, x + 14, y + (node.is_anchor ? 96 : 78));
    }
  }
}

function renderStats(graph) {
  statsEl.innerHTML = "";
  const entries = [
    ["Shown Nodes", graph.stats.shown_nodes],
    ["Shown Edges", graph.stats.shown_edges],
    ["Vault Notes", graph.stats.total_notes],
    ["Orphans", graph.stats.orphan_nodes_shown],
  ];
  for (const [label, value] of entries) {
    const stat = document.createElement("div");
    stat.className = "stat";
    stat.innerHTML = `<strong>${value}</strong><br>${label}`;
    statsEl.appendChild(stat);
  }
}

async function loadNote(id) {
  const response = await fetch(`/api/note?id=${encodeURIComponent(id)}`);
  if (!response.ok) {
    detailContent.innerHTML = "<p>Failed to load note details.</p>";
    return;
  }
  const note = await response.json();
  const tags = (note.frontmatter.tags || []).map(
    (tag) => `<span class="tag">${tag}</span>`,
  );
  const relationships = note.explicit_relationships.map(
    (relationship) =>
      `<span class="edge">${relationship.type} -> ${relationship.target}</span>`,
  );
  const sourcePreviews = note.repo_evidence?.length
    ? await fetchSourcePreviews(note.id, note.repo_evidence)
    : [];
  const noteHtml = `
    <h2>${note.title}</h2>
    <p class="meta-line"><strong>Entity Type:</strong> ${note.frontmatter.entity_type || "n/a"}</p>
    <p class="meta-line"><strong>Status:</strong> ${note.frontmatter.status || "n/a"}</p>
    <div class="tag-list">${tags.join("") || "<span class='tag'>no tags</span>"}</div>
    <div class="detail-section">
      <h3>Summary</h3>
      <p>${note.frontmatter.summary || "No summary yet."}</p>
    </div>
    ${
      note.flow_body || note.data_path_body
        ? `<div class="detail-section">
            <h3>${note.flow_body ? "Flow" : "Data Path"}</h3>
            <pre>${escapeHtml(note.flow_body || note.data_path_body)}</pre>
          </div>`
        : ""
    }
    <div class="detail-section">
      <h3>Relationships</h3>
      <div class="edge-list">${relationships.join("") || "<span class='edge'>No explicit relationships</span>"}</div>
    </div>
    <div class="detail-section">
      <h3>Body Preview</h3>
      <pre>${escapeHtml(note.content.slice(0, 1200))}</pre>
    </div>
  `;
  const sourceHtml = `
    <h2>${note.title}</h2>
    <p class="meta-line"><strong>Note Path:</strong> ${note.path}</p>
    <div class="detail-section">
      <h3>Repo Evidence</h3>
      ${
        note.repo_evidence?.length
          ? `<ul class="evidence-list">${note.repo_evidence
              .map((item) => `<li><code>${escapeHtml(item)}</code></li>`)
              .join("")}</ul>`
          : "<p>No repo evidence captured in this note yet.</p>"
      }
    </div>
    <div class="detail-section">
      <h3>Local Source Preview</h3>
      ${
        sourcePreviews.length
          ? sourcePreviews
              .map((preview) => {
                if (preview.kind === "directory") {
                  return `<p><code>${escapeHtml(preview.path)}</code> is a directory.</p>`;
                }
                const lines = (preview.preview_lines || [])
                  .map(
                    (line) =>
                      `<div><span style="display:inline-block;width:48px;color:#8b8478;">${line.line_number}</span>${escapeHtml(line.text)}</div>`,
                  )
                  .join("");
                return `
                  <p class="meta-line"><strong>${escapeHtml(preview.path)}</strong></p>
                  <pre>${lines}</pre>
                `;
              })
              .join("")
          : "<p>No local source preview available yet.</p>"
      }
    </div>
    <div class="detail-section">
      <h3>Outgoing Links</h3>
      <div class="edge-list">${
        note.outgoing_links?.length
          ? note.outgoing_links
              .map((link) => `<span class="edge">${link.type} -> ${link.target}</span>`)
              .join("")
          : "<span class='edge'>No outgoing links</span>"
      }</div>
    </div>
  `;
  detailContent.innerHTML = state.detailTab === "source" ? sourceHtml : noteHtml;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function fetchSourcePreviews(noteId, evidencePaths) {
  const previews = [];
  for (const path of evidencePaths.slice(0, 2)) {
    const response = await fetch(
      `/api/source-preview?id=${encodeURIComponent(noteId)}&path=${encodeURIComponent(path)}`,
    );
    if (!response.ok) {
      continue;
    }
    previews.push(await response.json());
  }
  return previews;
}

async function loadGraph() {
  setStatus("loading");
  const anchorOrQuery = document.getElementById("anchorInput").value.trim();
  const params = new URLSearchParams();
  if (anchorOrQuery) {
    params.set("anchor", anchorOrQuery);
    params.set("query", anchorOrQuery);
  }
  params.set("depth", depthInput.value);
  params.set("limit", document.getElementById("limitInput").value);
  params.set("demo_mode", demoMode.checked ? "true" : "false");
  if (relationFilter.value) {
    params.append("relation_type", relationFilter.value);
  }
  const response = await fetch(`/api/graph?${params.toString()}`);
  const graph = enrichGraph(await response.json());
  state.fullGraph = graph;
  populateFocusOptions(graph);
  state.graph = applyGraphLens(graph);
  state.selectedNodeId = state.graph.anchor;
  state.nodePositions.clear();
  graphTitle.textContent = state.graph.anchor
    ? `Graph: ${state.graph.nodes.find((node) => node.id === state.graph.anchor)?.title || state.graph.anchor}`
    : "Graph: Vault Overview";
  emptyState.classList.toggle("hidden", state.graph.nodes.length > 0);
  relationFilter.innerHTML = '<option value="">All relationships</option>';
  for (const type of state.graph.available_relation_types) {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = type;
    relationFilter.appendChild(option);
  }
  renderStats(state.graph);
  layoutGraph(state.graph);
  drawGraph();
  if (state.graph.anchor) {
    await loadNote(state.graph.anchor);
  }
  setStatus("ready");
}

function refreshLens() {
  if (!state.fullGraph) {
    return;
  }
  state.graph = applyGraphLens(state.fullGraph);
  state.selectedNodeId = state.graph.anchor;
  state.nodePositions.clear();
  graphTitle.textContent = state.graph.anchor
    ? `Graph: ${state.graph.nodes.find((node) => node.id === state.graph.anchor)?.title || state.graph.anchor}`
    : "Graph: Vault Overview";
  renderStats(state.graph);
  layoutGraph(state.graph);
  drawGraph();
}

function setDetailTab(tab) {
  state.detailTab = tab;
  noteTab.classList.toggle("active", tab === "note");
  noteTab.classList.toggle("secondary", tab !== "note");
  if (state.selectedNodeId) {
    loadNote(state.selectedNodeId);
  }
}

function openSourceWindow() {
  if (!state.selectedNodeId) {
    return;
  }
  window.open(
    `/source.html?id=${encodeURIComponent(state.selectedNodeId)}`,
    "_blank",
    "noopener,noreferrer",
  );
}

function hitTest(x, y) {
  if (!state.graph) {
    return null;
  }
  for (const node of [...state.graph.nodes].reverse()) {
    const pos = state.nodePositions.get(node.id);
    const box = estimateNodeBox(node);
    const left = pos.x - box.width / 2;
    const top = pos.y - box.height / 2;
    if (x >= left && x <= left + box.width && y >= top && y <= top + box.height) {
      return node;
    }
  }
  return null;
}

canvas.addEventListener("mousemove", (event) => {
  const rect = canvas.getBoundingClientRect();
  const node = hitTest(event.clientX - rect.left, event.clientY - rect.top);
  state.hoveredNodeId = node?.id || null;
  drawGraph();
});

canvas.addEventListener("mousedown", (event) => {
  const rect = canvas.getBoundingClientRect();
  const node = hitTest(event.clientX - rect.left, event.clientY - rect.top);
  state.dragNodeId = node?.id || null;
});

canvas.addEventListener("mouseup", async (event) => {
  const rect = canvas.getBoundingClientRect();
  const node = hitTest(event.clientX - rect.left, event.clientY - rect.top);
  if (node) {
    state.selectedNodeId = node.id;
    pathStart.value = node.id;
    await loadNote(node.id);
  }
  state.dragNodeId = null;
  drawGraph();
});

canvas.addEventListener("mouseleave", () => {
  state.hoveredNodeId = null;
  state.dragNodeId = null;
  drawGraph();
});

canvas.addEventListener("mousemove", (event) => {
  if (!state.dragNodeId) {
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const pos = state.nodePositions.get(state.dragNodeId);
  pos.x = event.clientX - rect.left;
  pos.y = event.clientY - rect.top;
  drawGraph();
});

controls.addEventListener("submit", async (event) => {
  event.preventDefault();
  await loadGraph();
});

resetButton.addEventListener("click", async () => {
  document.getElementById("anchorInput").value = "Umami";
  relationFilter.value = "";
  demoMode.checked = true;
  depthInput.value = "1";
  depthValue.textContent = depthInput.value;
  await loadGraph();
});

demoUmami.addEventListener("click", async () => {
  document.getElementById("anchorInput").value = "Umami";
  depthInput.value = "1";
  depthValue.textContent = depthInput.value;
  demoMode.checked = true;
  serviceFilter.value = "";
  viewMode.value = "overview";
  levelFilter.value = "2";
  await loadGraph();
});

demoPocketBase.addEventListener("click", async () => {
  document.getElementById("anchorInput").value = "PocketBase";
  depthInput.value = "1";
  depthValue.textContent = depthInput.value;
  demoMode.checked = true;
  serviceFilter.value = "";
  viewMode.value = "overview";
  levelFilter.value = "2";
  await loadGraph();
});

depthInput.addEventListener("input", () => {
  depthValue.textContent = depthInput.value;
});

viewMode.addEventListener("change", refreshLens);
serviceFilter.addEventListener("change", refreshLens);
levelFilter.addEventListener("change", refreshLens);
noteTab.addEventListener("click", () => setDetailTab("note"));
openSourceView.addEventListener("click", openSourceWindow);
sidebarToggle.addEventListener("click", () => {
  shell.classList.toggle("sidebar-collapsed");
  resizeCanvas();
  if (state.graph) {
    layoutGraph(state.graph);
    drawGraph();
  }
  syncPanelState();
});
detailToggle.addEventListener("click", () => {
  shell.classList.toggle("detail-collapsed");
  resizeCanvas();
  if (state.graph) {
    layoutGraph(state.graph);
    drawGraph();
  }
  syncPanelState();
});

let resizingDetail = false;
resizeHandle.addEventListener("mousedown", () => {
  resizingDetail = true;
  document.body.style.cursor = "col-resize";
});

window.addEventListener("mousemove", (event) => {
  if (!resizingDetail || shell.classList.contains("detail-collapsed")) {
    return;
  }
  const width = Math.max(300, Math.min(620, window.innerWidth - event.clientX));
  shell.style.setProperty("--detail-width", `${width}px`);
  resizeCanvas();
  if (state.graph) {
    layoutGraph(state.graph);
    drawGraph();
  }
});

window.addEventListener("mouseup", () => {
  resizingDetail = false;
  document.body.style.cursor = "";
});

pathButton.addEventListener("click", async () => {
  const start = pathStart.value.trim();
  const end = pathEnd.value.trim();
  if (!start || !end) {
    pathResult.textContent = "Provide both start and end note IDs.";
    return;
  }
  const response = await fetch(
    `/api/path?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
  );
  const payload = await response.json();
  if (!payload.path) {
    pathResult.textContent = payload.message || "No path found.";
    return;
  }
  pathResult.textContent = payload.path
    .map((step) => {
      const rel = step.to_next?.map((item) => item.type).join(", ") || "";
      return rel ? `${step.id} --${rel}-->` : step.id;
    })
    .join("\n");
});

window.addEventListener("resize", () => {
  resizeCanvas();
  if (state.graph) {
    drawGraph();
  }
});

async function init() {
  resizeCanvas();
  document.getElementById("anchorInput").value = "Umami";
  depthInput.value = "1";
  depthValue.textContent = depthInput.value;
  demoMode.checked = true;
  viewMode.value = "overview";
  levelFilter.value = "2";
  serviceFilter.value = "";
  syncPanelState();
  await loadGraph();
}

init();
