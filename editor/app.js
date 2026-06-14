const state = {
  view: "filters",
  filters: [],
  labels: [],
  selectedFilter: null,
  selectedLabel: null,
  filterCreatedAt: readFilterCreatedAt(),
  filterEditMode: "basic",
  matchYamlByCriteria: {},
  previewRequest: 0,
  query: "",
};

const filterRows = document.getElementById("filter-rows");
const labelRows = document.getElementById("label-rows");
const count = document.getElementById("count");
const filterMessage = document.getElementById("filter-message");
const labelMessage = document.getElementById("label-message");
const details = document.getElementById("details");
const detailsTitle = document.getElementById("details-title");
const search = document.getElementById("search");
const reload = document.getElementById("reload");
const authForm = document.getElementById("auth-form");
const authToken = document.getElementById("auth-token");
const filtersTab = document.getElementById("filters-tab");
const labelsTab = document.getElementById("labels-tab");
const filtersPanel = document.getElementById("filters-panel");
const labelsPanel = document.getElementById("labels-panel");
const filterForm = document.getElementById("filter-form");
const basicFilterMode = document.getElementById("basic-filter-mode");
const rawFilterMode = document.getElementById("raw-filter-mode");
const basicFilterEditor = document.getElementById("basic-filter-editor");
const filterJson = document.getElementById("filter-json");
const filterQuery = document.getElementById("filter-query");
const filterLabel = document.getElementById("filter-label");
const filterSkipInbox = document.getElementById("filter-skip-inbox");
const newFilter = document.getElementById("new-filter");
const saveFilter = document.getElementById("save-filter");
const deleteFilter = document.getElementById("delete-filter");
const labelForm = document.getElementById("label-form");
const labelName = document.getElementById("label-name");
const labelListVisibility = document.getElementById("label-list-visibility");
const messageListVisibility = document.getElementById("message-list-visibility");
const labelBg = document.getElementById("label-bg");
const labelFg = document.getElementById("label-fg");
const newLabel = document.getElementById("new-label");
const saveLabel = document.getElementById("save-label");
const deleteLabel = document.getElementById("delete-label");
const busyOverlay = document.getElementById("busy-overlay");
const busyTitle = document.getElementById("busy-title");
const busyDetail = document.getElementById("busy-detail");

function summarize(value) {
  if (!value || Object.keys(value).length === 0) return "";
  return JSON.stringify(value);
}

function labelById() {
  return new Map(state.labels.map((label) => [label.id, label]));
}

function labelNameFor(id) {
  const label = labelById().get(id);
  return label ? `${label.name} (${id})` : id;
}

function summarizeAction(action) {
  if (!action || Object.keys(action).length === 0) return "";
  const copy = { ...action };
  if (copy.addLabelIds) copy.addLabelIds = copy.addLabelIds.map(labelNameFor);
  if (copy.removeLabelIds) copy.removeLabelIds = copy.removeLabelIds.map(labelNameFor);
  return JSON.stringify(copy);
}

function matches(value) {
  const text = JSON.stringify(value).toLowerCase();
  return text.includes(state.query.toLowerCase());
}

function readFilterCreatedAt() {
  try {
    return JSON.parse(localStorage.getItem("gmail-filter-editor-created-at") || "{}");
  } catch {
    return {};
  }
}

function writeFilterCreatedAt() {
  localStorage.setItem("gmail-filter-editor-created-at", JSON.stringify(state.filterCreatedAt));
}

function rememberFilterCreated(filter) {
  if (!filter || !filter.id) return;
  state.filterCreatedAt[filter.id] = new Date().toISOString();
  writeFilterCreatedAt();
}

function sortedFilters() {
  return state.filters
    .map((filter, index) => ({ filter, index, createdAt: state.filterCreatedAt[filter.id] || "" }))
    .sort((left, right) => {
      if (left.createdAt && right.createdAt) return right.createdAt.localeCompare(left.createdAt);
      if (left.createdAt) return -1;
      if (right.createdAt) return 1;
      const idOrder = String(right.filter.id || "").localeCompare(String(left.filter.id || ""));
      return idOrder || left.index - right.index;
    })
    .map((entry) => entry.filter);
}

function render() {
  renderTabs();
  renderFilters();
  renderLabels();
  renderDetails();
}

function renderTabs() {
  filtersTab.classList.toggle("active", state.view === "filters");
  labelsTab.classList.toggle("active", state.view === "labels");
  filtersPanel.classList.toggle("hidden", state.view !== "filters");
  labelsPanel.classList.toggle("hidden", state.view !== "labels");
  filterForm.classList.toggle("hidden", state.view !== "filters");
  labelForm.classList.toggle("hidden", state.view !== "labels");
  basicFilterMode.classList.toggle("active", state.filterEditMode === "basic");
  rawFilterMode.classList.toggle("active", state.filterEditMode === "raw");
  basicFilterEditor.classList.toggle("hidden", state.filterEditMode !== "basic");
  filterJson.classList.toggle("hidden", state.filterEditMode !== "raw");
}

function renderFilters() {
  const visible = sortedFilters().filter(matches);
  filterRows.innerHTML = "";
  filterMessage.textContent = visible.length ? "" : "No filters";
  if (state.view === "filters") count.textContent = `${visible.length} of ${state.filters.length}`;

  for (const filter of visible) {
    const tr = document.createElement("tr");
    if (state.selectedFilter && state.selectedFilter.id === filter.id) tr.className = "selected";
    tr.innerHTML = `
      <td class="mono">${escapeHtml(filter.id || "")}</td>
      <td class="mono">${escapeHtml(summarize(filter.criteria))}</td>
      <td class="mono">${escapeHtml(summarizeAction(filter.action))}</td>
    `;
    tr.addEventListener("click", () => selectFilter(filter));
    filterRows.appendChild(tr);
  }

  if (!state.selectedFilter && visible[0]) selectFilter(visible[0], false);
}

function renderLabels() {
  const visible = state.labels.filter(matches);
  labelRows.innerHTML = "";
  labelMessage.textContent = visible.length ? "" : "No labels";
  if (state.view === "labels") count.textContent = `${visible.length} of ${state.labels.length}`;

  for (const label of visible) {
    const tr = document.createElement("tr");
    if (state.selectedLabel && state.selectedLabel.id === label.id) tr.className = "selected";
    tr.innerHTML = `
      <td>${labelSwatch(label)}${escapeHtml(label.name || "")}</td>
      <td class="mono">${escapeHtml(label.id || "")}</td>
      <td>${escapeHtml(label.type || "")}</td>
      <td>${escapeHtml([label.labelListVisibility, label.messageListVisibility].filter(Boolean).join(" / "))}</td>
    `;
    tr.addEventListener("click", () => selectLabel(label));
    labelRows.appendChild(tr);
  }

  if (state.view === "labels" && !state.selectedLabel && visible[0]) selectLabel(visible[0], false);
}

function renderDetails() {
  if (state.view === "labels") {
    const label = state.selectedLabel || {};
    detailsTitle.textContent = label.id ? "Label JSON" : "New label";
    details.textContent = JSON.stringify(label, null, 2);
    syncLabelForm(label);
    return;
  }

  const filter = state.selectedFilter || {};
  detailsTitle.textContent = filter.id ? "Filter JSON" : "New filter";
  details.textContent = JSON.stringify(filter, null, 2);
  syncFilterForm(filter);
}

function labelSwatch(label) {
  if (!label.color || !label.color.backgroundColor) return "";
  const bg = escapeHtml(label.color.backgroundColor);
  const fg = escapeHtml(label.color.textColor || "#ffffff");
  return `<span class="swatch" style="background:${bg};color:${fg}"></span>`;
}

function syncLabelForm(label) {
  labelName.value = label.name || "";
  labelListVisibility.value = label.labelListVisibility || "";
  messageListVisibility.value = label.messageListVisibility || "";
  labelBg.value = label.color && label.color.backgroundColor ? label.color.backgroundColor : "";
  labelFg.value = label.color && label.color.textColor ? label.color.textColor : "";
  const isSystem = label.type === "system";
  saveLabel.disabled = isSystem;
  deleteLabel.disabled = isSystem || !label.id;
}

function syncFilterForm(filter) {
  syncFilterLabelOptions(filter);
  syncBasicFilterForm(filter);
  filterJson.value = JSON.stringify(filter, null, 2);
  if (state.filterEditMode === "basic") syncStructuredFilterPreview();
  deleteFilter.disabled = !filter.id;
}

function syncFilterLabelOptions(filter) {
  const selected = firstValue(filter.action && filter.action.addLabelIds) || "";
  const options = ['<option value="">No label</option>'];
  for (const label of state.labels) {
    options.push(`<option value="${escapeHtml(label.id)}">${escapeHtml(label.name || label.id)}</option>`);
  }
  filterLabel.innerHTML = options.join("");
  filterLabel.value = selected;
}

function syncBasicFilterForm(filter) {
  const criteria = filter.criteria || {};
  const criteriaKey = JSON.stringify(criteria);
  filterQuery.value = state.matchYamlByCriteria[criteriaKey] || fallbackCriteriaYaml(criteria);
  if (Object.keys(criteria).length) loadCriteriaYaml(criteria).catch(showError);
  filterSkipInbox.checked = includesValue(filter.action && filter.action.removeLabelIds, "INBOX");
}

function selectFilter(filter, rerender = true) {
  state.selectedFilter = filter;
  if (rerender) render();
}

function selectLabel(label, rerender = true) {
  state.selectedLabel = label;
  if (rerender) render();
}

function switchView(view) {
  state.view = view;
  if (view === "labels" && !state.selectedLabel && state.labels[0]) state.selectedLabel = state.labels[0];
  if (view === "filters" && !state.selectedFilter && state.filters[0]) state.selectedFilter = state.filters[0];
  render();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function firstValue(value) {
  return Array.isArray(value) && value.length ? value[0] : "";
}

function includesValue(value, item) {
  return Array.isArray(value) && value.includes(item);
}

function showBusy(title, detail = "") {
  busyTitle.textContent = title;
  busyDetail.textContent = detail;
  busyOverlay.classList.remove("hidden");
}

function hideBusy() {
  busyOverlay.classList.add("hidden");
  busyTitle.textContent = "Working";
  busyDetail.textContent = "";
}

async function withBusy(title, detail, operation) {
  showBusy(title, detail);
  try {
    return await operation();
  } finally {
    hideBusy();
  }
}

async function loadAuthToken() {
  const response = await fetch("/api/auth/token", { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Token request failed");
  authToken.value = data.token || "";
}

async function saveAuthToken(event) {
  event.preventDefault();
  const token = authToken.value.trim();
  if (!token) throw new Error("Token is required");
  return withBusy("Updating token", "Saving token for this editor session", async () => {
    const response = await fetch("/api/auth/token", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Token update failed");
    await loadAll();
  });
}

async function loadMatchYaml(query) {
  return loadCriteriaYaml({ query });
}

async function loadCriteriaYaml(criteria) {
  const criteriaKey = JSON.stringify(criteria || {});
  if (state.matchYamlByCriteria[criteriaKey]) return state.matchYamlByCriteria[criteriaKey];
  const response = await fetch("/api/match/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ criteria }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Criteria parse failed");
  state.matchYamlByCriteria[criteriaKey] = data.yaml;
  if (
    state.filterEditMode === "basic"
    && state.selectedFilter
    && JSON.stringify(state.selectedFilter.criteria || {}) === criteriaKey
  ) {
    filterQuery.value = data.yaml.trimEnd();
    syncStructuredFilterPreview();
  }
  return data.yaml;
}

function fallbackCriteriaYaml(criteria) {
  if (!criteria || !Object.keys(criteria).length) return "";
  if (criteria.query) return `raw: ${criteria.query}`;
  if (criteria.from) return `from: ${criteria.from}`;
  if (criteria.to) return `to: ${criteria.to}`;
  if (criteria.subject) return `subject: ${criteria.subject}`;
  return `raw: ${JSON.stringify(criteria)}`;
}

async function renderMatchYaml(matchYaml) {
  if (!matchYaml) return "";
  const response = await fetch("/api/match/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml: matchYaml }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Criteria render failed");
  return data;
}

async function loadAll() {
  return withBusy("Loading Gmail data", "Fetching filters and labels", async () => {
    filterMessage.textContent = "Loading";
    labelMessage.textContent = "Loading";
    filterRows.innerHTML = "";
    labelRows.innerHTML = "";
    const [filtersResponse, labelsResponse] = await Promise.all([
      fetch("/api/filters", { cache: "no-store" }),
      fetch("/api/labels", { cache: "no-store" }),
    ]);
    const filtersData = await filtersResponse.json();
    const labelsData = await labelsResponse.json();
    if (!filtersResponse.ok) throw new Error(filtersData.error || "Filter request failed");
    if (!labelsResponse.ok) throw new Error(labelsData.error || "Label request failed");
    state.filters = filtersData.filter || [];
    state.labels = labelsData.labels || [];
    state.selectedFilter = null;
    state.selectedLabel = null;
    render();
  });
}

function labelPayload() {
  const payload = { name: labelName.value.trim() };
  if (labelListVisibility.value) payload.labelListVisibility = labelListVisibility.value;
  if (messageListVisibility.value) payload.messageListVisibility = messageListVisibility.value;
  if (labelBg.value.trim() || labelFg.value.trim()) {
    payload.color = {};
    if (labelBg.value.trim()) payload.color.backgroundColor = labelBg.value.trim();
    if (labelFg.value.trim()) payload.color.textColor = labelFg.value.trim();
  }
  return payload;
}

async function filterPayload() {
  if (state.filterEditMode === "basic") {
    return await structuredFilterPayload();
  }
  const payload = JSON.parse(filterJson.value || "{}");
  if (!payload.criteria || !payload.action) {
    throw new Error("Filter JSON must include criteria and action");
  }
  return payload;
}

async function structuredFilterPayload() {
  const rendered = await renderMatchYaml(filterQuery.value.trim());
  const criteria = rendered.criteria || {};
  const labelId = filterLabel.value;
  const action = {};
  if (!Object.keys(criteria).length) throw new Error("Criteria is required");
  if (labelId) action.addLabelIds = [labelId];
  if (filterSkipInbox.checked) action.removeLabelIds = ["INBOX"];
  if (Object.keys(action).length === 0) throw new Error("Choose a label or skip inbox");
  const payload = {
    criteria,
    action,
  };
  filterJson.value = JSON.stringify(payload, null, 2);
  details.textContent = filterJson.value;
  return payload;
}

function syncStructuredFilterPreview() {
  if (state.filterEditMode !== "basic") return;
  const requestId = ++state.previewRequest;
  renderMatchYaml(filterQuery.value.trim()).then((rendered) => {
    if (requestId !== state.previewRequest || state.filterEditMode !== "basic") return;
    const criteria = rendered.criteria || {};
    const labelId = filterLabel.value;
    const action = {};
    if (labelId) action.addLabelIds = [labelId];
    if (filterSkipInbox.checked) action.removeLabelIds = ["INBOX"];
    const payload = {
      criteria,
      action,
    };
    filterJson.value = JSON.stringify(payload, null, 2);
    details.textContent = filterJson.value;
  }).catch(() => {
    if (requestId === state.previewRequest) details.textContent = filterJson.value;
  });
}

function switchFilterEditMode(mode) {
  if (mode === "basic") {
    try {
      syncBasicFilterForm(JSON.parse(filterJson.value || "{}"));
    } catch {
      syncBasicFilterForm({});
    }
  } else {
    syncStructuredFilterPreview();
  }
  state.filterEditMode = mode;
  renderTabs();
}

async function saveSelectedFilter(event) {
  event.preventDefault();
  const payload = await filterPayload();
  const selected = state.selectedFilter;
  return withBusy(
    selected && selected.id ? "Replacing filter" : "Creating filter",
    selected && selected.id ? `Creating replacement, then deleting ${selected.id}` : "Posting new filter JSON",
    async () => {
      const response = await fetch(selected && selected.id ? `/api/filters/${encodeURIComponent(selected.id)}` : "/api/filters", {
        method: selected && selected.id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Filter save failed");
      rememberFilterCreated(data);
      await loadAll();
      state.view = "filters";
      state.selectedFilter = state.filters.find((filter) => filter.id === data.id) || data;
      render();
    },
  );
}

async function deleteSelectedFilter() {
  const selected = state.selectedFilter;
  if (!selected || !selected.id) return;
  return withBusy("Deleting filter", selected.id, async () => {
    const response = await fetch(`/api/filters/${encodeURIComponent(selected.id)}`, { method: "DELETE" });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "Filter delete failed");
    }
    await loadAll();
    state.view = "filters";
    render();
  });
}

async function saveSelectedLabel(event) {
  event.preventDefault();
  const payload = labelPayload();
  if (!payload.name) return;
  const selected = state.selectedLabel;
  return withBusy(
    selected && selected.id ? "Saving label" : "Creating label",
    payload.name,
    async () => {
      const response = await fetch(selected && selected.id ? `/api/labels/${encodeURIComponent(selected.id)}` : "/api/labels", {
        method: selected && selected.id ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Label save failed");
      await loadAll();
      state.view = "labels";
      state.selectedLabel = state.labels.find((label) => label.id === data.id) || data;
      render();
    },
  );
}

async function deleteSelectedLabel() {
  const selected = state.selectedLabel;
  if (!selected || !selected.id || selected.type === "system") return;
  return withBusy("Deleting label", selected.name || selected.id, async () => {
    const response = await fetch(`/api/labels/${encodeURIComponent(selected.id)}`, { method: "DELETE" });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "Label delete failed");
    }
    await loadAll();
    state.view = "labels";
    render();
  });
}

function showError(error) {
  filterRows.innerHTML = "";
  labelRows.innerHTML = "";
  filterMessage.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  labelMessage.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  count.textContent = "";
  details.textContent = "{}";
}

search.addEventListener("input", () => {
  state.query = search.value;
  render();
});

reload.addEventListener("click", () => {
  loadAll().catch(showError);
});

authForm.addEventListener("submit", (event) => {
  saveAuthToken(event).catch(showError);
});

filtersTab.addEventListener("click", () => switchView("filters"));
labelsTab.addEventListener("click", () => switchView("labels"));

newLabel.addEventListener("click", () => {
  state.selectedLabel = {};
  switchView("labels");
});

newFilter.addEventListener("click", () => {
  state.selectedFilter = {
    criteria: {
      query: "",
    },
    action: {
      addLabelIds: [],
    },
  };
  switchView("filters");
});

basicFilterMode.addEventListener("click", () => switchFilterEditMode("basic"));
rawFilterMode.addEventListener("click", () => switchFilterEditMode("raw"));

for (const input of [filterQuery, filterLabel, filterSkipInbox]) {
  input.addEventListener("input", syncStructuredFilterPreview);
  input.addEventListener("change", syncStructuredFilterPreview);
}

filterJson.addEventListener("input", () => {
  if (state.filterEditMode === "raw") details.textContent = filterJson.value;
});

filterForm.addEventListener("submit", (event) => {
  saveSelectedFilter(event).catch(showError);
});

deleteFilter.addEventListener("click", () => {
  deleteSelectedFilter().catch(showError);
});

labelForm.addEventListener("submit", (event) => {
  saveSelectedLabel(event).catch(showError);
});

deleteLabel.addEventListener("click", () => {
  deleteSelectedLabel().catch(showError);
});

loadAuthToken().catch(showError);
loadAll().catch(showError);
