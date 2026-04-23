// ─────────────────────────────────────────────────────────────
// CONFIGURATION — update RAW_URL to your own repo's raw URL
// Format: https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/funding.json
// ─────────────────────────────────────────────────────────────
const RAW_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/funding.json";

// ─── STATE ───
let allItems = [];
let filteredItems = [];
let activeTab = "all";
let activeTypes = new Set();
let activeSources = new Set();
let bookmarks = new Set(JSON.parse(localStorage.getItem("fundingBookmarks") || "[]"));

// ─── LOAD DATA ───
async function loadData() {
  showState("loading");
  try {
    const res = await fetch(RAW_URL + "?t=" + Date.now());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allItems = data.items || [];

    // update last-updated
    const d = new Date(data.last_updated);
    document.getElementById("lastUpdated").textContent =
      "Updated: " + d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });

    buildFilterPills();
    applyFilters();
    updateStats();
    showState("grid");
  } catch (e) {
    document.getElementById("errorDetail").textContent = e.message;
    showState("error");
  }
}

function showState(state) {
  document.getElementById("loadingState").style.display = state === "loading" ? "block" : "none";
  document.getElementById("errorState").style.display   = state === "error"   ? "block" : "none";
  document.getElementById("grid").style.display         = state === "grid"    ? "grid"  : "none";
  document.getElementById("emptyState").style.display   = state === "empty"   ? "block" : "none";
}

// ─── BUILD FILTER PILLS ───
function buildFilterPills() {
  const types   = [...new Set(allItems.map(i => i.type).filter(Boolean))].sort();
  const sources = [...new Set(allItems.map(i => i.source).filter(Boolean))].sort();

  renderPills("typeFilters", types, activeTypes, "type");
  renderPills("sourceFilters", sources, activeSources, "source");
}

function renderPills(containerId, values, activeSet, kind) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  values.forEach(v => {
    const btn = document.createElement("button");
    btn.className = "pill" + (activeSet.has(v) ? " active" : "");
    btn.textContent = v;
    btn.onclick = () => togglePill(v, activeSet, btn, kind);
    container.appendChild(btn);
  });
}

function togglePill(value, set, btn, kind) {
  if (set.has(value)) { set.delete(value); btn.classList.remove("active"); }
  else                 { set.add(value);    btn.classList.add("active"); }
  applyFilters();
}

// ─── FILTERS & SORT ───
function applyFilters() {
  const query     = document.getElementById("searchInput").value.toLowerCase().trim();
  const minScore  = parseInt(document.getElementById("relevanceFilter").value || "0");
  const sortBy    = document.getElementById("sortBy").value;

  let items = activeTab === "bookmarks"
    ? allItems.filter(i => bookmarks.has(i.id))
    : allItems;

  if (activeTypes.size)   items = items.filter(i => activeTypes.has(i.type));
  if (activeSources.size) items = items.filter(i => activeSources.has(i.source));
  if (minScore > 0)       items = items.filter(i => (i.relevance_score || 0) >= minScore);

  if (query) {
    items = items.filter(i =>
      (i.title       || "").toLowerCase().includes(query) ||
      (i.description || "").toLowerCase().includes(query) ||
      (i.source      || "").toLowerCase().includes(query) ||
      (i.tags        || []).some(t => t.toLowerCase().includes(query))
    );
  }

  if (sortBy === "newest") {
    items = [...items].sort((a, b) => new Date(b.posted || 0) - new Date(a.posted || 0));
  } else if (sortBy === "source") {
    items = [...items].sort((a, b) => (a.source || "").localeCompare(b.source || ""));
  } else {
    items = [...items].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
  }

  filteredItems = items;
  renderGrid();
  updateStats();
}

// ─── RENDER CARDS ───
function renderGrid() {
  const grid = document.getElementById("grid");
  if (!filteredItems.length) {
    showState("empty");
    return;
  }
  showState("grid");
  grid.innerHTML = filteredItems.map(item => cardHTML(item)).join("");
}

function cardHTML(item) {
  const isBookmarked = bookmarks.has(item.id);
  const score = item.relevance_score || 0;
  const dots = Array.from({ length: 8 }, (_, i) =>
    `<div class="relevance-dot${i < score ? " filled" : ""}"></div>`
  ).join("");

  const tags = [
    item.type   ? `<span class="tag tag-type">${esc(item.type)}</span>`   : "",
    item.source ? `<span class="tag tag-source">${esc(item.source)}</span>` : "",
    item.amount ? `<span class="tag tag-badge">💰 ${esc(item.amount)}</span>` : "",
    item.deadline ? `<span class="tag tag-badge">⏰ ${esc(item.deadline)}</span>` : "",
  ].filter(Boolean).join("");

  return `
    <div class="card" onclick="openModal('${esc(item.id)}')">
      <div class="card-header">
        <div class="card-title">${esc(item.title)}</div>
        <button class="bookmark-btn ${isBookmarked ? "bookmarked" : ""}"
          onclick="toggleBookmark(event, '${esc(item.id)}')"
          title="${isBookmarked ? "Remove bookmark" : "Bookmark"}">
          ${isBookmarked ? "★" : "☆"}
        </button>
      </div>
      <div class="card-tags">${tags}</div>
      ${item.description ? `<p class="card-desc">${esc(item.description)}</p>` : ""}
      <div class="card-footer">
        <span class="card-meta">${esc(item.source || "")}</span>
        <div class="relevance-bar" title="Relevance: ${score}/8">${dots}</div>
      </div>
    </div>`;
}

// ─── BOOKMARK ───
function toggleBookmark(e, id) {
  e.stopPropagation();
  if (bookmarks.has(id)) bookmarks.delete(id);
  else bookmarks.add(id);
  localStorage.setItem("fundingBookmarks", JSON.stringify([...bookmarks]));
  applyFilters();
}

// ─── MODAL ───
function openModal(id) {
  const item = allItems.find(i => i.id === id);
  if (!item) return;

  const tags = [
    item.type   ? `<span class="tag tag-type">${esc(item.type)}</span>` : "",
    item.source ? `<span class="tag tag-source">${esc(item.source)}</span>` : "",
    ...(item.tags || []).map(t => `<span class="tag tag-badge">${esc(t)}</span>`),
  ].filter(Boolean).join("");

  document.getElementById("modalContent").innerHTML = `
    <h2 class="modal-title">${esc(item.title)}</h2>
    <div class="modal-tags">${tags}</div>
    ${item.description ? `
      <div class="modal-section">
        <div class="modal-label">Description</div>
        <div class="modal-value">${esc(item.description)}</div>
      </div>` : ""}
    ${item.amount ? `
      <div class="modal-section">
        <div class="modal-label">Funding Amount</div>
        <div class="modal-value">${esc(item.amount)}</div>
      </div>` : ""}
    ${item.deadline ? `
      <div class="modal-section">
        <div class="modal-label">Deadline</div>
        <div class="modal-value">${esc(item.deadline)}</div>
      </div>` : ""}
    ${item.posted ? `
      <div class="modal-section">
        <div class="modal-label">Posted</div>
        <div class="modal-value">${esc(item.posted)}</div>
      </div>` : ""}
    ${item.url ? `<a class="modal-link" href="${esc(item.url)}" target="_blank" rel="noopener">→ View Opportunity</a>` : ""}
  `;

  document.getElementById("modal").style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeModal(e) {
  if (e && e.target !== document.getElementById("modal") && e.type === "click") return;
  document.getElementById("modal").style.display = "none";
  document.body.style.overflow = "";
}

document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

// ─── TABS ───
function switchTab(tab, btn) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");
  applyFilters();
}

// ─── STATS ───
function updateStats() {
  const items = activeTab === "bookmarks" ? allItems.filter(i => bookmarks.has(i.id)) : allItems;
  document.getElementById("totalCount").textContent      = filteredItems.length;
  document.getElementById("fellowshipCount").textContent = items.filter(i => i.type === "Fellowship").length;
  document.getElementById("federalCount").textContent    = items.filter(i => i.type === "Federal Grant").length;
  document.getElementById("privateCount").textContent    = items.filter(i => i.type === "Private Foundation Grant").length;
  document.getElementById("bookmarkCount").textContent   = bookmarks.size;
}

// ─── UTIL ───
function esc(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ─── INIT ───
loadData();
