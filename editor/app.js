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
  sortKey: "id",
  sortDirection: "desc",
  filterChip: "all",
  selectedFilterId: null,
  selectedLabelIds: [],
  undoStack: readUndoStack(),
  query: "",
  criteriaValid: false,
  actionValid: false,
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
const authStatus = document.getElementById("auth-status");
const filtersTab = document.getElementById("filters-tab");
const labelsTab = document.getElementById("labels-tab");
const filtersPanel = document.getElementById("filters-panel");
const labelsPanel = document.getElementById("labels-panel");
const filterForm = document.getElementById("filter-form");
const basicFilterMode = document.getElementById("basic-filter-mode");
const rawFilterMode = document.getElementById("raw-filter-mode");
const basicFilterEditor = document.getElementById("basic-filter-editor");
const filterJson = document.getElementById("filter-json");
const jsonStatus = document.getElementById("json-status");
const filterQuery = document.getElementById("filter-query");
const criteriaStatus = document.getElementById("criteria-status");
const renderedQuery = document.getElementById("rendered-query");
const filterLabelSelect = document.getElementById("filter-label-select");
const filterLabelTrigger = document.getElementById("filter-label-trigger");
const filterLabelSummary = document.getElementById("filter-label-summary");
const filterLabelOptions = document.getElementById("filter-label-options");
const filterSkipInbox = document.getElementById("filter-skip-inbox");
const actionStatus = document.getElementById("action-status");
const newFilter = document.getElementById("new-filter");
const saveFilter = document.getElementById("save-filter");
const discardFilter = document.getElementById("discard-filter");
const deleteFilter = document.getElementById("delete-filter");
const undoFilter = document.getElementById("undo-filter");
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
const filterChips = Array.from(document.querySelectorAll("[data-filter-chip]"));
const sortButtons = Array.from(document.querySelectorAll("[data-sort-key]"));

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

function labelDisplayNameFor(id) {
  const label = labelById().get(id);
  return label ? label.name : id;
}

function isUserLabel(label) {
  return label && label.type === "user";
}

function summarizeAction(action) {
  if (!action || Object.keys(action).length === 0) return "";
  const copy = { ...action };
  if (copy.addLabelIds) copy.addLabelIds = copy.addLabelIds.map(labelNameFor);
  if (copy.removeLabelIds) copy.removeLabelIds = copy.removeLabelIds.map(labelNameFor);
  return JSON.stringify(copy);
}

function actionChips(action) {
  if (!action || Object.keys(action).length === 0) return "";
  const chips = [];
  for (const id of action.removeLabelIds || []) {
    chips.push({ text: id === "INBOX" ? "Skip inbox" : `Remove ${labelNameFor(id)}`, kind: id === "INBOX" ? "skip" : "remove" });
  }
  if (action.forward) chips.push({ text: `Forward ${action.forward}`, kind: "forward" });
  for (const [key, value] of Object.entries(action)) {
    if (["addLabelIds", "removeLabelIds", "forward"].includes(key)) continue;
    chips.push({ text: `${key}: ${Array.isArray(value) ? value.join(", ") : value}`, kind: "other" });
  }
  return chips.map(actionChipHtml).join("");
}

function labelActionChips(action) {
  if (!action || !Array.isArray(action.addLabelIds)) return "";
  return action.addLabelIds
    .map((id) => actionChipHtml({ text: labelDisplayNameFor(id), title: id, kind: "label", label: labelById().get(id) }))
    .join("");
}

function labelActionText(action) {
  if (!action || !Array.isArray(action.addLabelIds)) return "";
  return action.addLabelIds.map(labelNameFor).join(" ");
}

function actionChipHtml(chip) {
  const title = chip.title ? ` title="${escapeHtml(chip.title)}"` : "";
  if (chip.label && chip.label.color && chip.label.color.backgroundColor) {
    const bg = escapeHtml(chip.label.color.backgroundColor);
    const fg = escapeHtml(chip.label.color.textColor || "#ffffff");
    return `<span class="action-chip ${chip.kind}"${title} style="background:${bg};border-color:${bg};color:${fg}">${escapeHtml(chip.text)}</span>`;
  }
  return `<span class="action-chip ${chip.kind}"${title}>${escapeHtml(chip.text)}</span>`;
}

function labelColorStyle(label) {
  if (!label.color || !label.color.backgroundColor) return "";
  const bg = escapeHtml(label.color.backgroundColor);
  const fg = escapeHtml(label.color.textColor || "#ffffff");
  return ` style="--label-bg:${bg};--label-fg:${fg}"`;
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

function readUndoStack() {
  try {
    return JSON.parse(localStorage.getItem("gmail-filter-editor-undo") || "[]");
  } catch {
    return [];
  }
}

function writeUndoStack() {
  localStorage.setItem("gmail-filter-editor-undo", JSON.stringify(state.undoStack.slice(-10)));
}

function rememberUndo(kind, filter) {
  if (!filter) return;
  state.undoStack.push({ kind, filter, at: new Date().toISOString() });
  state.undoStack = state.undoStack.slice(-10);
  writeUndoStack();
  updateUndoState();
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
  const base = state.filters
    .map((filter, index) => ({ filter, index, createdAt: state.filterCreatedAt[filter.id] || "" }))
    .sort((left, right) => {
      let result;
      if (state.sortKey === "criteria") {
        result = summarize(left.filter.criteria).localeCompare(summarize(right.filter.criteria));
      } else if (state.sortKey === "label") {
        result = labelActionText(left.filter.action).localeCompare(labelActionText(right.filter.action));
      } else if (state.sortKey === "action") {
        result = summarizeAction(left.filter.action).localeCompare(summarizeAction(right.filter.action));
      } else {
        if (left.createdAt && right.createdAt) result = left.createdAt.localeCompare(right.createdAt);
        else if (left.createdAt) result = 1;
        else if (right.createdAt) result = -1;
        else result = String(left.filter.id || "").localeCompare(String(right.filter.id || ""));
      }
      return (state.sortDirection === "desc" ? -result : result) || left.index - right.index;
    })
    .map((entry) => entry.filter);
  return base;
}

function render() {
  renderTabs();
  renderFilterChips();
  renderFilters();
  renderLabels();
  renderDetails();
  updateUndoState();
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
  jsonStatus.classList.toggle("hidden", state.filterEditMode !== "raw");
  updateSaveState();
}

function renderFilters() {
  const visible = sortedFilters().filter(matches).filter(matchesFilterChip);
  filterRows.innerHTML = "";
  filterMessage.textContent = visible.length ? "" : "No filters";
  if (state.view === "filters") count.textContent = `${visible.length} of ${state.filters.length}`;

  for (const filter of visible) {
    const tr = document.createElement("tr");
    if (state.selectedFilter && state.selectedFilter.id === filter.id) tr.className = "selected";
    tr.innerHTML = `
      <td class="mono">${escapeHtml(filter.id || "")}</td>
      <td class="mono">${escapeHtml(summarize(filter.criteria))}</td>
      <td>${labelActionChips(filter.action)}</td>
      <td>${actionChips(filter.action)}</td>
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

function renderFilterChips() {
  for (const chip of filterChips) {
    chip.classList.toggle("active", chip.dataset.filterChip === state.filterChip);
  }
}

function matchesFilterChip(filter) {
  if (state.filterChip === "skip-inbox") return includesValue(filter.action && filter.action.removeLabelIds, "INBOX");
  if (state.filterChip === "has-label") return Array.isArray(filter.action && filter.action.addLabelIds) && filter.action.addLabelIds.length > 0;
  if (state.filterChip === "no-label") return !Array.isArray(filter.action && filter.action.addLabelIds) || filter.action.addLabelIds.length === 0;
  if (state.filterChip === "raw-query") return !!(filter.criteria && filter.criteria.query);
  return true;
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
  if (state.filterEditMode === "raw") validateRawFilterJson();
  deleteFilter.disabled = !filter.id;
  updateSaveState();
}

function syncFilterLabelOptions(filter) {
  state.selectedLabelIds = Array.isArray(filter.action && filter.action.addLabelIds) ? filter.action.addLabelIds.slice() : [];
  renderFilterLabelOptions();
}

function renderFilterLabelOptions() {
  const selectedLabels = state.selectedLabelIds.map(labelDisplayNameFor);
  filterLabelSummary.textContent = selectedLabels.length ? selectedLabels.join(", ") : "No labels selected";
  filterLabelOptions.innerHTML = state.labels
    .filter(isUserLabel)
    .map((label) => {
      const selected = state.selectedLabelIds.includes(label.id);
      const name = label.name || label.id;
      return `
        <button class="custom-select-option ${selected ? "selected" : ""}" type="button" role="option" aria-selected="${selected}" data-label-id="${escapeHtml(label.id)}" title="${escapeHtml(label.id)}"${labelColorStyle(label)}>
          <span class="custom-check">${selected ? "✓" : ""}</span>
          <span class="custom-label-swatch"></span>
          <span>${escapeHtml(name)}</span>
        </button>
      `;
    })
    .join("") || '<div class="empty">No labels</div>';
  for (const option of filterLabelOptions.querySelectorAll("[data-label-id]")) {
    option.addEventListener("click", () => {
      const labelId = option.dataset.labelId;
      if (state.selectedLabelIds.includes(labelId)) {
        state.selectedLabelIds = state.selectedLabelIds.filter((id) => id !== labelId);
      } else {
        state.selectedLabelIds.push(labelId);
      }
      renderFilterLabelOptions();
      syncStructuredFilterPreview();
    });
  }
}

function setLabelDropdownOpen(open) {
  filterLabelOptions.classList.toggle("hidden", !open);
  filterLabelTrigger.setAttribute("aria-expanded", String(open));
}

function syncBasicFilterForm(filter) {
  const criteria = filter.criteria || {};
  const criteriaKey = JSON.stringify(criteria);
  filterQuery.value = state.matchYamlByCriteria[criteriaKey] || fallbackCriteriaYaml(criteria);
  if (Object.keys(criteria).length) loadCriteriaYaml(criteria).catch(showError);
  filterSkipInbox.checked = includesValue(filter.action && filter.action.removeLabelIds, "INBOX");
}

function confirmDiscardFilterChanges() {
  return !hasFilterChanges() || confirm("Discard unsaved filter changes?");
}

function selectFilter(filter, rerender = true) {
  if (rerender && state.selectedFilter !== filter && !confirmDiscardFilterChanges()) return;
  state.selectedFilter = filter;
  state.selectedFilterId = filter && filter.id ? filter.id : null;
  if (rerender) render();
}

function selectLabel(label, rerender = true) {
  state.selectedLabel = label;
  if (rerender) render();
}

function switchView(view) {
  if (view !== state.view && state.view === "filters" && !confirmDiscardFilterChanges()) return;
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
    setAuthStatus("Token updated", "ok");
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
  if (!matchYaml) return { query: "", criteria: {} };
  const response = await fetch("/api/match/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml: matchYaml }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Criteria render failed");
  return data;
}

function criteriaDisplay(rendered) {
  if (rendered.query) return rendered.query;
  const criteria = rendered.criteria || {};
  return Object.entries(criteria)
    .map(([key, value]) => `${key}:${Array.isArray(value) || typeof value === "object" ? JSON.stringify(value) : value}`)
    .join(" ");
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
    if (!filtersResponse.ok) throw apiError(filtersData.error || "Filter request failed", filtersResponse.status);
    if (!labelsResponse.ok) throw apiError(labelsData.error || "Label request failed", labelsResponse.status);
    state.filters = filtersData.filter || [];
    state.labels = labelsData.labels || [];
    state.selectedFilter = state.filters.find((filter) => filter.id === state.selectedFilterId) || null;
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
  const action = {};
  if (!Object.keys(criteria).length) throw new Error("Criteria is required");
  if (state.selectedLabelIds.length) action.addLabelIds = state.selectedLabelIds.slice();
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

function setCriteriaStatus(message, className = "") {
  criteriaStatus.textContent = message;
  criteriaStatus.className = `validation-status ${className}`.trim();
}

function setActionStatus(message, className = "") {
  actionStatus.textContent = message;
  actionStatus.className = `validation-status ${className}`.trim();
}

function setJsonStatus(message, className = "") {
  jsonStatus.textContent = message;
  jsonStatus.className = `validation-status ${className}`.trim();
  jsonStatus.classList.toggle("hidden", state.filterEditMode !== "raw");
}

function hasActionConfigured() {
  return state.selectedLabelIds.length > 0 || filterSkipInbox.checked;
}

function updateActionValidation() {
  state.actionValid = hasActionConfigured();
  if (state.actionValid) {
    setActionStatus("Action valid", "ok");
  } else {
    setActionStatus("Choose a label or skip inbox", "error");
  }
  updateSaveState();
}

function updateSaveState() {
  if (state.view !== "filters") return;
  const dirty = hasFilterChanges();
  if (state.filterEditMode === "basic") {
    saveFilter.disabled = !dirty || !state.criteriaValid || !state.actionValid;
  } else {
    saveFilter.disabled = !dirty || !validateRawFilterJson(false);
  }
  discardFilter.disabled = !dirty;
}

function hasFilterChanges() {
  if (state.view !== "filters") return false;
  const selected = normalizeFilterForDirty(state.selectedFilter || {});
  try {
    return stableJson(normalizeFilterForDirty(JSON.parse(filterJson.value || "{}"))) !== stableJson(selected);
  } catch {
    return filterJson.value.trim() !== JSON.stringify(state.selectedFilter || {}, null, 2).trim();
  }
}

function normalizeFilterForDirty(filter) {
  const copy = { ...filter };
  delete copy.id;
  return copy;
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function validateRawFilterJson(updateStatus = true) {
  try {
    const payload = JSON.parse(filterJson.value || "{}");
    if (!payload.criteria) {
      if (updateStatus) setJsonStatus("JSON must include criteria", "error");
      return false;
    }
    if (!payload.action) {
      if (updateStatus) setJsonStatus("JSON must include action", "error");
      return false;
    }
    if (updateStatus) setJsonStatus("JSON valid", "ok");
    return true;
  } catch (error) {
    if (updateStatus) setJsonStatus(error.message, "error");
    return false;
  }
}

function syncStructuredFilterPreview() {
  if (state.filterEditMode !== "basic") return;
  const requestId = ++state.previewRequest;
  state.criteriaValid = false;
  updateActionValidation();
  setCriteriaStatus("Validating criteria", "");
  renderedQuery.textContent = "";
  updateSaveState();
  renderMatchYaml(filterQuery.value.trim()).then((rendered) => {
    if (requestId !== state.previewRequest || state.filterEditMode !== "basic") return;
    const criteria = rendered.criteria || {};
    state.criteriaValid = Object.keys(criteria).length > 0;
    if (state.criteriaValid) {
      setCriteriaStatus("Criteria valid", "ok");
      renderedQuery.textContent = criteriaDisplay(rendered);
    } else {
      setCriteriaStatus("Criteria is required", "error");
      renderedQuery.textContent = "";
    }
    const action = {};
    if (state.selectedLabelIds.length) action.addLabelIds = state.selectedLabelIds.slice();
    if (filterSkipInbox.checked) action.removeLabelIds = ["INBOX"];
    const payload = {
      criteria,
      action,
    };
    filterJson.value = JSON.stringify(payload, null, 2);
    details.textContent = filterJson.value;
    updateSaveState();
  }).catch(() => {
    if (requestId === state.previewRequest) {
      state.criteriaValid = false;
      setCriteriaStatus("Criteria YAML is invalid", "error");
      renderedQuery.textContent = "";
      details.textContent = filterJson.value;
      updateSaveState();
    }
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
    validateRawFilterJson();
  }
  state.filterEditMode = mode;
  renderTabs();
}

async function saveSelectedFilter(event) {
  event.preventDefault();
  const payload = await filterPayload();
  const selected = state.selectedFilter;
  if (selected && selected.id && !confirm("Replace this filter? Gmail will create a new filter and then delete the old one.")) return;
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
      if (!response.ok) throw apiError(data.error || "Filter save failed", response.status);
      if (selected && selected.id) rememberUndo("replace", selected);
      rememberFilterCreated(data);
      state.selectedFilterId = data.id || null;
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
  if (!confirm("Delete this filter? It can only be restored by recreating it.")) return;
  return withBusy("Deleting filter", selected.id, async () => {
    const response = await fetch(`/api/filters/${encodeURIComponent(selected.id)}`, { method: "DELETE" });
    if (!response.ok) {
      const data = await response.json();
      throw apiError(data.error || "Filter delete failed", response.status);
    }
    rememberUndo("delete", selected);
    state.selectedFilterId = null;
    await loadAll();
    state.view = "filters";
    render();
  });
}

function discardSelectedFilterChanges() {
  setLabelDropdownOpen(false);
  renderDetails();
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
  if (error && error.status === 401) setAuthStatus("Auth failed", "error");
  filterRows.innerHTML = "";
  labelRows.innerHTML = "";
  filterMessage.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  labelMessage.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  count.textContent = "";
  details.textContent = "{}";
}

function apiError(message, status) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function setAuthStatus(message, className = "") {
  authStatus.textContent = message;
  authStatus.className = `auth-status ${className}`.trim();
}

function updateUndoState() {
  undoFilter.disabled = state.undoStack.length === 0;
}

async function undoLastFilterChange() {
  const entry = state.undoStack.pop();
  if (!entry) return;
  writeUndoStack();
  updateUndoState();
  return withBusy("Restoring filter", entry.filter.id || "previous filter", async () => {
    const response = await fetch("/api/filters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entry.filter),
    });
    const data = await response.json();
    if (!response.ok) throw apiError(data.error || "Filter restore failed", response.status);
    rememberFilterCreated(data);
    state.selectedFilterId = data.id || null;
    await loadAll();
  });
}

search.addEventListener("input", () => {
  state.query = search.value;
  render();
});

reload.addEventListener("click", () => {
  if (!confirmDiscardFilterChanges()) return;
  loadAll().catch(showError);
});

for (const chip of filterChips) {
  chip.addEventListener("click", () => {
    state.filterChip = chip.dataset.filterChip;
    render();
  });
}

for (const button of sortButtons) {
  button.addEventListener("click", () => {
    if (state.sortKey === button.dataset.sortKey) {
      state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = button.dataset.sortKey;
      state.sortDirection = "asc";
    }
    render();
  });
}

authForm.addEventListener("submit", (event) => {
  saveAuthToken(event).catch(showError);
});

filtersTab.addEventListener("click", () => switchView("filters"));
labelsTab.addEventListener("click", () => switchView("labels"));

newLabel.addEventListener("click", () => {
  if (state.view === "filters" && !confirmDiscardFilterChanges()) return;
  state.selectedLabel = {};
  switchView("labels");
});

newFilter.addEventListener("click", () => {
  if (!confirmDiscardFilterChanges()) return;
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

filterLabelTrigger.addEventListener("click", () => {
  setLabelDropdownOpen(filterLabelOptions.classList.contains("hidden"));
});

document.addEventListener("click", (event) => {
  if (!filterLabelSelect.contains(event.target)) setLabelDropdownOpen(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setLabelDropdownOpen(false);
});

for (const input of [filterQuery, filterSkipInbox]) {
  input.addEventListener("input", syncStructuredFilterPreview);
  input.addEventListener("change", syncStructuredFilterPreview);
}

filterJson.addEventListener("input", () => {
  if (state.filterEditMode === "raw") {
    details.textContent = filterJson.value;
    validateRawFilterJson();
    updateSaveState();
  }
});

filterForm.addEventListener("submit", (event) => {
  saveSelectedFilter(event).catch(showError);
});

discardFilter.addEventListener("click", discardSelectedFilterChanges);

deleteFilter.addEventListener("click", () => {
  deleteSelectedFilter().catch(showError);
});

undoFilter.addEventListener("click", () => {
  undoLastFilterChange().catch(showError);
});

labelForm.addEventListener("submit", (event) => {
  saveSelectedLabel(event).catch(showError);
});

deleteLabel.addEventListener("click", () => {
  deleteSelectedLabel().catch(showError);
});

loadAuthToken().catch(showError);
loadAll().catch(showError);
