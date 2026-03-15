const params = new URLSearchParams(window.location.search);
const noteId = params.get("id");
const titleEl = document.getElementById("sourceTitle");
const metaEl = document.getElementById("sourceMeta");
const previewEl = document.getElementById("sourcePreview");
const themeToggle = document.getElementById("themeToggle");
const STORAGE_KEY = "linked-notes-ui-state-v1";

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function init() {
  applyThemeFromStorage();
  if (!noteId) {
    titleEl.textContent = "No note selected";
    metaEl.innerHTML = "<p>Missing note id.</p>";
    return;
  }

  const note = await fetchJson(`/api/note?id=${encodeURIComponent(noteId)}`);
  titleEl.textContent = note.title;
  metaEl.innerHTML = `
    <p class="meta-line"><strong>Entity Type:</strong> ${note.frontmatter.entity_type || "n/a"}</p>
    <p class="meta-line"><strong>Note Path:</strong> ${note.path}</p>
    <div class="tag-list">${
      (note.repo_evidence || []).map((item) => `<span class="edge">${escapeHtml(item)}</span>`).join("") ||
      "<span class='edge'>No repo evidence</span>"
    }</div>
  `;

  if (!note.repo_evidence?.length) {
    previewEl.innerHTML = "<p>No repo evidence captured in this note yet.</p>";
    return;
  }

  const previews = await Promise.all(
    note.repo_evidence.slice(0, 3).map((item) =>
      fetchJson(`/api/source-preview?id=${encodeURIComponent(noteId)}&path=${encodeURIComponent(item)}`),
    ),
  );
  previewEl.innerHTML = previews
    .map((preview) => {
      if (preview.kind === "directory") {
        return `<div class="detail-section"><h3>${escapeHtml(preview.path)}</h3><p>Directory</p></div>`;
      }
      const lines = (preview.preview_lines || [])
        .map(
          (line) =>
            `<div><span style="display:inline-block;width:48px;color:#8b8478;">${line.line_number}</span>${escapeHtml(line.text)}</div>`,
        )
        .join("");
      return `
        <div class="detail-section">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
            <h3>${escapeHtml(preview.path)}</h3>
            <button type="button" class="secondary open-file-button" data-open-path="${escapeHtml(preview.path)}">Open File</button>
          </div>
          <pre>${lines}</pre>
        </div>
      `;
    })
    .join("");

  document.querySelectorAll(".open-file-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const path = button.getAttribute("data-open-path");
      if (!path) return;
      await fetch(`/api/open-file?id=${encodeURIComponent(noteId)}&path=${encodeURIComponent(path)}`);
    });
  });
}

function applyThemeFromStorage() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const saved = raw ? JSON.parse(raw) : {};
    const charcoal = saved?.theme === "charcoal";
    document.body.classList.toggle("theme-charcoal", charcoal);
    if (themeToggle) {
      themeToggle.textContent = charcoal ? "Light" : "Charcoal";
    }
  } catch {
    // ignore theme persistence issues
  }
}

themeToggle?.addEventListener("click", () => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const saved = raw ? JSON.parse(raw) : {};
    saved.theme = saved.theme === "charcoal" ? "light" : "charcoal";
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
  } catch {
    // ignore persistence issues
  }
  applyThemeFromStorage();
});

init().catch((error) => {
  titleEl.textContent = "Source unavailable";
  metaEl.innerHTML = `<p>${escapeHtml(String(error.message || error))}</p>`;
});
