"use strict";

const HN_API = "https://hacker-news.firebaseio.com/v0";
const LOCAL_API = ""; 
const LIMIT = 15;
const FEED_LABELS = {
  topstories: "Top", newstories: "New", beststories: "Best",
  askstories: "Ask", showstories: "Show"
};

const currentFeed = { name: "topstories" };
let loadedStories = [];
let currentMode = "keyword"; 
let currentSourceFilter = ""; 
const commentCache = new Map(); 
const visited = new Set(
  JSON.parse(localStorage.getItem("hn_visited") || "[]")
);

const listContainer = document.getElementById("list");
const updatedEl     = document.getElementById("updated");
const statusEl      = document.getElementById("backend-status");
const searchInput   = document.getElementById("search");
const searchContainer = document.getElementById("search-container");
const feedButtons   = document.querySelectorAll(".toolbar button[data-feed]");
const sourceFilterButtons = document.querySelectorAll("#source-filters button");
const reloadBtn     = document.getElementById("reload");
const digestBtn     = document.getElementById("digest");
const btnKeyword    = document.getElementById("mode-keyword");
const btnSemantic   = document.getElementById("mode-semantic");
const btnAsk        = document.getElementById("mode-ask");
const btnAnalytics  = document.getElementById("mode-analytics");
const shortcutsEl   = document.getElementById("shortcuts");

// ---------- Helpers ----------
function el(tag, attrs = {}, text = "") {
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (v !== undefined && v !== null) e.setAttribute(k, v);
  });
  if (text) e.textContent = text;
  return e;
}

function getDomain(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch { return ""; }
}

function timeAgo(unixSeconds) {
  if (!unixSeconds) return "";
  const diff = Math.floor(Date.now() / 1000) - unixSeconds;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(unixSeconds * 1000).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric"
  });
}

function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }

function htmlToText(html) {
  const tmp = document.createElement("div");
  tmp.innerHTML = html;
  return (tmp.textContent || "").replace(/\s+/g, " ").trim();
}

function markVisited(id) {
  if (!id) return;
  visited.add(id);
  localStorage.setItem("hn_visited", JSON.stringify([...visited]));
}

// ---------- URL persistence ----------
function syncURL() {
  const params = new URLSearchParams(location.search);
  params.set("feed", currentFeed.name);
  params.set("mode", currentMode);
  if (currentSourceFilter) params.set("source", currentSourceFilter);
  else params.delete("source");
  history.replaceState(null, "", "?" + params.toString());
}

function readURL() {
  const params = new URLSearchParams(location.search);
  const feed = params.get("feed");
  const mode = params.get("mode");
  const source = params.get("source");
  
  if (feed && FEED_LABELS[feed]) currentFeed.name = feed;
  if (mode && ["keyword", "semantic", "ask", "analytics"].includes(mode)) currentMode = mode;
  if (source) currentSourceFilter = source;
}

// ---------- Backend health ----------
async function checkBackend() {
  try {
    const res = await fetch(`${LOCAL_API}/health`);
    if (!res.ok) throw new Error();
    const h = await res.json();
    statusEl.textContent = `Backend ok · ${h.story_rows} stories · ${h.llm_model}`;
    statusEl.style.color = "var(--muted)";
    return true;
  } catch (err) {
    console.error("Health check failed:", err);
    statusEl.textContent = "Backend offline — check console";
    statusEl.style.color = "var(--error-text)";
    return false;
  }
}

// ---------- Rendering ----------
function renderSkeleton() {
  listContainer.innerHTML = "";
  listContainer.setAttribute("aria-busy", "true");
  for (let i = 0; i < 5; i++) {
    const row = el("div", { class: "story", "aria-hidden": "true" });
    const title = el("div", { class: "skeleton" });
    title.style.width = `${50 + Math.random() * 40}%`;
    const meta = el("div", { class: "skeleton" });
    meta.style.width = "35%"; meta.style.marginTop = "10px";
    row.appendChild(title); row.appendChild(meta);
    listContainer.appendChild(row);
  }
}

function renderLoading(msg) {
  listContainer.innerHTML = "";
  listContainer.setAttribute("aria-busy", "true");
  const wrap = el("div", { class: "loading-state" });
  wrap.appendChild(el("div", { class: "spinner", "aria-hidden": "true" }));
  wrap.appendChild(el("span", {}, msg));
  listContainer.appendChild(wrap);
}

function renderError(message, isAi = false) {
  listContainer.innerHTML = "";
  listContainer.setAttribute("aria-busy", "false");
  const box = el("div", { class: "error", role: "alert" });
  box.appendChild(el("p", { style: "margin:0;font-weight:600" },
    isAi ? "AI Backend Error" : "Could not load stories"));
  box.appendChild(el("p", { style: "margin:6px 0 0;font-size:0.9rem" }, message));
  if (isAi) {
    box.appendChild(el("p",
      { style: "margin:8px 0 0;font-size:0.8rem;color:var(--muted)" },
      "Is the Uvicorn server running on port 8000?"));
  } else {
    const retry = el("button", {}, "Try again");
    retry.addEventListener("click", () => loadStories(currentFeed.name));
    box.appendChild(retry);
  }
  listContainer.appendChild(box);
}

function attachCommentPreview(wrap, story) {
  if (!story.kids || story.kids.length === 0) return;

  if (commentCache.has(story.id)) {
    const cached = commentCache.get(story.id);
    if (cached) renderPreview(wrap, cached.by, cached.text);
    return;
  }

  const preview = el("div", { class: "comment-preview" }, "Loading top comment…");
  wrap.appendChild(preview);

  fetch(`${HN_API}/item/${story.kids[0]}.json`, { cache: "no-store" })
    .then(res => res.ok ? res.json() : null)
    .then(comment => {
      preview.remove();
      if (!comment || !comment.text || comment.deleted || comment.dead) {
        commentCache.set(story.id, null);
        return;
      }
      const text = htmlToText(comment.text);
      if (!text) { commentCache.set(story.id, null); return; }
      const entry = { by: comment.by || "anonymous", text };
      commentCache.set(story.id, entry);
      renderPreview(wrap, entry.by, entry.text);
    })
    .catch(() => preview.remove());
}

function renderPreview(wrap, by, text) {
  const clipped = text.length > 180 ? text.slice(0, 180).trim() + "…" : text;
  const preview = el("div", { class: "comment-preview" });
  preview.appendChild(el("span", { class: "preview-author" }, `💬 ${by}`));
  preview.appendChild(document.createTextNode(clipped));
  wrap.appendChild(preview);
}

function renderStory(story, rank) {
  const wrap = el("article", { class: "story" });
  if (visited.has(story.id)) wrap.classList.add("visited");

  const titleRow = el("div", { class: "title-row" });
  if (rank) titleRow.appendChild(el("span",
    { class: "rank", "aria-hidden": "true" }, `${rank}.`));

  if (story.similarity !== undefined && story.similarity !== null) {
    const badge = el("span", { class: "sim-badge", title: "Retrieval score" });
    badge.textContent = story.similarity.toFixed(2);
    titleRow.appendChild(badge);
  }

  if (story.source) {
    const sourceNames = { hn: "📰 HN", lobsters: "🦞 Lobsters" };
    const badge = el("span", { 
      class: `source-badge ${story.source}`, 
      title: `Source: ${story.source}` 
    }, sourceNames[story.source] || story.source);
    titleRow.appendChild(badge);
  }

  const url = story.url || `https://news.ycombinator.com/item?id=${story.id}`;
  const titleLink = el("a",
    { class: "title", href: url, target: "_blank", rel: "noopener noreferrer" });
  titleLink.textContent = story.title;
  titleLink.addEventListener("click", () => markVisited(story.id));
  titleRow.appendChild(titleLink);

  if (story.url) {
    const domain = getDomain(story.url);
    if (domain) titleRow.appendChild(el("span", { class: "domain" }, `(${domain})`));
  }
  wrap.appendChild(titleRow);

  const meta = el("div", { class: "meta" });
  if (story.score !== undefined) {
    meta.appendChild(el("span", { class: "score" }, plural(story.score ?? 0, "point")));
    meta.appendChild(el("span", { class: "dot" }, "·"));
  }
  meta.appendChild(el("span", {}, `by ${story.by || "unknown"}`));

  if (story.descendants !== undefined && story.descendants !== null) {
    meta.appendChild(el("span", { class: "dot" }, "·"));
    const commentLink = el("a", {
      href: `https://news.ycombinator.com/item?id=${story.id}`,
      target: "_blank", rel: "noopener noreferrer",
      style: "color:inherit;text-decoration:none"
    });
    commentLink.textContent = plural(story.descendants, "comment");
    meta.appendChild(commentLink);
  }
  if (story.time) {
    meta.appendChild(el("span", { class: "dot" }, "·"));
    meta.appendChild(el("span", {}, timeAgo(story.time)));
  }
  wrap.appendChild(meta);

  if (story.text) {
    const snip = el("div", { class: "snippet" });
    snip.appendChild(el("span", { class: "label" }, "Self-text: "));
    const body = story.text.length > 200
      ? story.text.slice(0, 200).trim() + "…"
      : story.text;
    snip.appendChild(document.createTextNode(body));
    wrap.appendChild(snip);
  }
  if (story.comments && story.comments.length) {
    const c = story.comments[0];
    const snip = el("div", { class: "snippet" });
    snip.appendChild(el("span", { class: "label" }, `💬 ${c.by}: `));
    const body = c.text.length > 200 ? c.text.slice(0, 200).trim() + "…" : c.text;
    snip.appendChild(document.createTextNode(body));
    wrap.appendChild(snip);
  }

  if (story.kids) attachCommentPreview(wrap, story);

  return wrap;
}

function renderStories(stories, opts = {}) {
  const filtered = currentSourceFilter 
    ? stories.filter(s => (s.source || "hn") === currentSourceFilter)
    : stories;

  listContainer.innerHTML = "";
  listContainer.setAttribute("aria-busy", "false");
  
  if (!filtered.length && !opts.silentEmpty) {
    const empty = el("div",
      { style: "padding:40px;text-align:center;color:var(--muted)" },
      "No stories match the current source filter.");
    listContainer.appendChild(empty);
    return;
  }
  
  const frag = document.createDocumentFragment();
  filtered.forEach((story, i) => frag.appendChild(renderStory(story, i + 1)));
  listContainer.appendChild(frag);
  updatedEl.textContent =
    `Updated ${new Date().toLocaleTimeString()} · ${FEED_LABELS[currentFeed.name] || currentFeed.name}`;
}

async function runAskStreaming(query) {
  renderLoading("Thinking locally…");
  const answerBox = el("div", { class: "ai-answer" });
  const answerBody = el("div", {});
  answerBody.style.whiteSpace = "pre-wrap";
  const cursor = el("span", { class: "cursor", "aria-hidden": "true" });
  answerBody.appendChild(cursor);
  answerBox.appendChild(el("strong", {}, "🤖 AI Answer"));
  answerBox.appendChild(answerBody);

  listContainer.innerHTML = "";
  listContainer.setAttribute("aria-busy", "false");
  listContainer.appendChild(answerBox);

  let sources = [];
  try {
    const res = await fetch(`${LOCAL_API}/ask/stream?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        let evt;
        try { evt = JSON.parse(line); } catch { continue; }
        if (evt.type === "sources") {
          sources = evt.data;
        } else if (evt.type === "token") {
          fullText += evt.data;
          cursor.remove();
          answerBody.textContent = fullText;
          answerBody.appendChild(cursor);
        } else if (evt.type === "error") {
          throw new Error(evt.data);
        }
      }
    }
    cursor.remove();
    answerBody.textContent = fullText || "(empty response)";
  } catch (err) {
    cursor.remove();
    answerBody.textContent = `Error: ${err.message}`;
    answerBody.style.color = "var(--error-text)";
  }

  if (sources.length) {
    listContainer.appendChild(el("h3", {
      style: "font-size:0.95rem;margin:16px 0 8px;color:var(--muted)"
    }, `Sources (${sources.length}):`));
    sources.forEach((s, i) => listContainer.appendChild(renderStory(s, i + 1)));
  }
  updatedEl.textContent = `AI generated at ${new Date().toLocaleTimeString()}`;
}

function applyFilter() {
  const q = searchInput.value.toLowerCase().trim();
  const filtered = q
    ? loadedStories.filter(s =>
        (s.title || "").toLowerCase().includes(q) ||
        (s.by || "").toLowerCase().includes(q))
    : loadedStories;

  if (filtered.length === 0) {
    listContainer.innerHTML = "";
    const empty = el("div",
      { style: "padding:40px;text-align:center;color:var(--muted)" });
    empty.textContent = `No stories match "${searchInput.value}".`;
    listContainer.appendChild(empty);
    return;
  }
  renderStories(filtered, { silentEmpty: true });
}

async function runSemantic(q) {
  renderLoading("Searching by meaning…");
  try {
    const res = await fetch(`${LOCAL_API}/search?q=${encodeURIComponent(q)}&k=10`);
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const hits = await res.json();
    if (!hits.length) {
      listContainer.innerHTML = "";
      listContainer.appendChild(el("div",
        { style: "padding:40px;text-align:center;color:var(--muted)" },
        "No matches in the local index. Run ingest.py to add more stories."));
      return;
    }
    renderStories(hits);
    updatedEl.textContent = `Semantic search · ${hits.length} results`;
  } catch (err) {
    renderError(err.message, true);
  }
}

// ---------- Analytics Mode ----------
async function loadAnalytics() {
  renderLoading("Loading Analytics...");
  
  try {
    const res = await fetch(`${LOCAL_API}/analytics`);
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const data = await res.json();
    
    listContainer.innerHTML = `
      <div style="padding: 20px;">
        <h2 style="margin-bottom: 20px;">📊 Data Warehouse Insights</h2>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div style="background: var(--card-bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
            <h3 style="font-size: 1rem; margin-bottom: 15px;">Stories by Source</h3>
            <canvas id="sourceChart"></canvas>
          </div>
          
          <div style="background: var(--card-bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border);">
            <h3 style="font-size: 1rem; margin-bottom: 15px;">Top Authors by Score</h3>
            <canvas id="authorChart"></canvas>
          </div>
        </div>
      </div>
    `;

    // Render Chart.js
    new Chart(document.getElementById('sourceChart'), {
      type: 'doughnut',
      data: {
        labels: data.sources.map(s => s.source_name.toUpperCase()),
        datasets: [{
          data: data.sources.map(s => s.count),
          backgroundColor: ['#ff6600', '#d33636', '#3b82f6']
        }]
      }
    });

    new Chart(document.getElementById('authorChart'), {
      type: 'bar',
      data: {
        labels: data.top_authors.map(a => a.username),
        datasets: [{
          label: 'Total Score',
          data: data.top_authors.map(a => a.total_score),
          backgroundColor: '#3b82f6'
        }]
      },
      options: { indexAxis: 'y' }
    });

  } catch (err) {
    renderError(err.message, true);
  }
}

// ---------- Modes ----------
function setMode(mode) {
  currentMode = mode;
  syncURL();
  
  btnKeyword.setAttribute("aria-pressed", mode === "keyword" ? "true" : "false");
  btnSemantic.setAttribute("aria-pressed", mode === "semantic" ? "true" : "false");
  btnAsk.setAttribute("aria-pressed", mode === "ask" ? "true" : "false");
  btnAnalytics.setAttribute("aria-pressed", mode === "analytics" ? "true" : "false");

  if (mode === "analytics") {
    searchContainer.style.display = "none"; // Hide search bar for dashboard
    loadAnalytics();
  } else {
    searchContainer.style.display = "flex"; // Show search bar for other modes
    
    if (mode === "keyword") {
      searchInput.placeholder = "Filter loaded stories by title or author…";
      renderStories(loadedStories, { silentEmpty: true });
    } else if (mode === "semantic") {
      searchInput.placeholder = "Search by meaning (e.g. \"vector databases\")…";
      listContainer.innerHTML = "";
      listContainer.appendChild(el("div",
        { style: "padding:40px;text-align:center;color:var(--muted)" },
        "Type a query and press Enter to search the local index."));
    } else {
      searchInput.placeholder = "Ask a question about the ingested stories…";
      listContainer.innerHTML = "";
      listContainer.appendChild(el("div",
        { style: "padding:40px;text-align:center;color:var(--muted)" },
        "Type a question and press Enter."));
    }
    searchInput.focus();
  }
}

async function loadStories(feed) {
  if (currentMode === "analytics") setMode("keyword");
  
  currentFeed.name = feed;
  syncURL();
  feedButtons.forEach(b =>
    b.setAttribute("aria-pressed", b.dataset.feed === feed ? "true" : "false"));
  renderSkeleton();

  try {
    const res = await fetch(`${HN_API}/${feed}.json`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ids = await res.json();
    if (!Array.isArray(ids) || ids.length === 0) throw new Error("Feed returned no IDs.");

    const results = await Promise.allSettled(
      ids.slice(0, LIMIT).map(id =>
        fetch(`${HN_API}/item/${id}.json`).then(r => r.json()))
    );
    const stories = results
      .filter(r => r.status === "fulfilled" && r.value &&
                   r.value.title && !r.value.deleted && !r.value.dead)
      .map(r => r.value);

    loadedStories = stories;

    if (currentMode === "keyword") {
      setMode("keyword");
    } else {
      setMode(currentMode);
    }
  } catch (err) {
    renderError(err.message);
  }
}

function runDigest() {
  setMode("ask");
  searchInput.value =
    "Summarize the most important themes in these stories in 3 short bullet points.";
  runAskStreaming(searchInput.value);
}

// ---------- Wiring ----------
feedButtons.forEach(btn =>
  btn.addEventListener("click", () => loadStories(btn.dataset.feed)));
  
sourceFilterButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    currentSourceFilter = btn.dataset.source;
    sourceFilterButtons.forEach(b => 
      b.setAttribute("aria-pressed", b.dataset.source === currentSourceFilter ? "true" : "false"));
    syncURL();
    
    if (currentMode === "semantic" && searchInput.value.trim()) {
      runSemantic(searchInput.value.trim());
    } else if (currentMode === "keyword") {
      applyFilter();
    }
  });
});

reloadBtn.addEventListener("click", () => loadStories(currentFeed.name));
digestBtn.addEventListener("click", runDigest);
btnKeyword.addEventListener("click", () => setMode("keyword"));
btnSemantic.addEventListener("click", () => setMode("semantic"));
btnAsk.addEventListener("click", () => setMode("ask"));
btnAnalytics.addEventListener("click", () => setMode("analytics"));

let debounce;
searchInput.addEventListener("input", () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    if (currentMode === "keyword") applyFilter();
  }, 200);
});

searchInput.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !searchInput.value.trim()) return;
  const q = searchInput.value.trim();
  if (currentMode === "semantic") runSemantic(q);
  else if (currentMode === "ask") runAskStreaming(q);
});

function toggleShortcuts(force) {
  const open = force !== undefined ? force : !shortcutsEl.classList.contains("open");
  shortcutsEl.classList.toggle("open", open);
}
shortcutsEl.addEventListener("click", (e) => {
  if (e.target === shortcutsEl) toggleShortcuts(false);
});

document.addEventListener("keydown", e => {
  const tag = document.activeElement?.tagName;
  const inField = tag === "INPUT" || tag === "TEXTAREA" || document.activeElement?.isContentEditable;

  if (e.key === "Escape") {
    if (shortcutsEl.classList.contains("open")) { toggleShortcuts(false); return; }
    if (document.activeElement === searchInput) {
      searchInput.value = "";
      if (currentMode === "keyword") applyFilter();
    }
    return;
  }
  if (e.key === "?" && !inField) {
    e.preventDefault(); toggleShortcuts(); return;
  }
  if (inField) return;

  if (e.key === "r" && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    loadStories(currentFeed.name);
  } else if (e.key === "/") {
    e.preventDefault(); searchInput.focus();
  } else if (e.key === "m") {
    const order = ["keyword", "semantic", "ask", "analytics"];
    setMode(order[(order.indexOf(currentMode) + 1) % order.length]);
  } else if (e.key === "d") {
    runDigest();
  } else if (["1","2","3","4","5"].includes(e.key)) {
    const feeds = ["topstories","newstories","beststories","askstories","showstories"];
    loadStories(feeds[parseInt(e.key, 10) - 1]);
  }
});

// ---------- Init ----------
readURL();
renderSkeleton();
checkBackend();

sourceFilterButtons.forEach(b => 
  b.setAttribute("aria-pressed", b.dataset.source === currentSourceFilter ? "true" : "false"));
btnKeyword.setAttribute("aria-pressed", currentMode === "keyword" ? "true" : "false");
btnSemantic.setAttribute("aria-pressed", currentMode === "semantic" ? "true" : "false");
btnAsk.setAttribute("aria-pressed", currentMode === "ask" ? "true" : "false");
btnAnalytics.setAttribute("aria-pressed", currentMode === "analytics" ? "true" : "false");

if (currentMode === "analytics") {
  setMode("analytics");
} else {
  loadStories(currentFeed.name);
}