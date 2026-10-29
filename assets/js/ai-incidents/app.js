import { IncidentRepository } from "./repository.js";

const repository = new IncidentRepository();
let params = new URLSearchParams(location.search);
const view = document.documentElement.dataset.aiIncidentsView || "dashboard";
const monitor = document.getElementById("incident-monitor-view");
const methodology = document.getElementById("incident-methodology-view");
const state = document.getElementById("incident-state");
const stateMessage = document.getElementById("incident-state-message");
const retry = document.getElementById("incident-retry");
const analysisView = document.getElementById("incident-analysis-view");
const mapPane = document.querySelector(".oof-incident-map-pane");
const listPane = document.querySelector(".oof-incident-list-pane");
let leafletMap = null;
let filtersWired = false;
let activeRequest = null;

markCurrentView();
if (view === "methodology") {
  monitor.hidden = true;
  methodology.hidden = false;
} else {
  wireFilters();
  retry.addEventListener("click", start);
  start();
}

async function start() {
  activeRequest?.abort();
  activeRequest = new AbortController();
  const { signal } = activeRequest;
  setState("loading", "Loading the public incident dataset…");
  try {
    const requestedPage = Math.max(1, Number(params.get("page")) || 1);
    const [summary, mapData, page, aggregations, architectureLinks] = await Promise.all([
      repository.summary(signal), repository.map(signal), repository.page(requestedPage, signal),
      repository.aggregations(signal), loadArchitectureLinks(signal),
    ]);
    renderSummary(summary);
    let result = page;
    if (requiresSearchProjection()) {
      const search = await repository.search(signal);
      result = { ...search, page: requestedPage, pageSize: 25 };
    }
    await renderRoute(result, mapData, aggregations, architectureLinks);
    setState("success", "Public incident dataset loaded.");
  } catch (error) {
    if (error.name === "AbortError") return;
    document.getElementById("incident-map")?.setAttribute("aria-busy", "false");
    setState("error", "The public incident dataset could not be loaded. Your filters have been preserved.");
    console.error(error);
  }
}

function setState(kind, message) {
  state.dataset.state = kind;
  stateMessage.textContent = message;
  retry.hidden = kind !== "error";
  state.hidden = kind === "success";
}

function markCurrentView() {
  const route = view === "dashboard" ? "/ai-incidents/" : `/ai-incidents/${view}/`;
  document.querySelectorAll(".oof-incident-nav a").forEach((link) => {
    if (new URL(link.href, location.origin).pathname === route) link.setAttribute("aria-current", "page");
  });
}

function requiresSearchProjection() {
  return ["critical", "stress-tests"].includes(view)
    || ["q", "severity", "eventType", "analysisStatus", "reviewStatus", "evidenceStatus", "country", "architecture"].some((key) => params.get(key));
}

async function renderRoute(result, mapData, aggregations, architectureLinks) {
  const showMap = view === "dashboard" || view === "map";
  const aggregateViews = ["architectures", "industries", "countries", "trends"];
  mapPane.hidden = !showMap;
  analysisView.hidden = !aggregateViews.includes(view);
  listPane.hidden = aggregateViews.includes(view) && !params.get("architecture") && !params.get("country");
  if (showMap) {
    await renderMap(mapData);
    renderGeographySummary(aggregations.geography);
    renderCountryTable(aggregations.geography.countries, true);
  }
  if (view === "architectures") renderArchitectures(aggregations.architectures, architectureLinks);
  if (view === "industries") renderIndustries(aggregations.industries, aggregations.scopeNotice);
  if (view === "countries") renderCountries(aggregations.geography, aggregations.scopeNotice);
  if (view === "trends") renderTrends(aggregations.trends, aggregations.scopeNotice);
  let items = applyFilters(result.items || []);
  if (view === "critical") items = items.filter((item) => item.severity === "Critical");
  if (view === "stress-tests") items = items.filter((item) => item.assessment?.oofApproved === true);
  const locallyPaged = requiresSearchProjection();
  renderIncidents(items, architectureLinks, {
    page: Math.max(1, Number(params.get("page")) || 1),
    pageSize: result.pageSize || 25,
    total: locallyPaged ? items.length : result.total,
    locallyPaged,
  });
}

async function loadArchitectureLinks(signal) {
  try {
    const response = await fetch("/data/oof-architecture-registry.json", { headers: { Accept: "application/json" }, signal });
    if (!response.ok) throw new Error(`Architecture registry request failed (${response.status})`);
    const registry = await response.json();
    return new Map((registry.architectures || []).map((architecture) => [
      String(architecture.id || "").toLowerCase(),
      architecture.primaryPage?.url ? `/${architecture.primaryPage.url.replace(/^\/+/, "")}` : null,
    ]));
  } catch (error) {
    console.warn("Architecture links are temporarily unavailable.", error);
    return new Map();
  }
}

function renderSummary(summary) {
  document.querySelectorAll("[data-metric]").forEach((element) => {
    const value = summary[element.dataset.metric];
    element.textContent = Number.isFinite(Number(value)) ? Number(value).toLocaleString("en") : "—";
  });
  const operational = summary.operationalStatus || {};
  document.getElementById("incident-data-time").textContent = operational.lastSuccessfulSourceCheck
    ? `Last successful source check ${formatTimestamp(operational.lastSuccessfulSourceCheck)} · Latest public export ${formatTimestamp(operational.latestPublicExport || summary.generatedAt)}`
    : summary.generatedAt
      ? `Public dataset updated ${formatTimestamp(summary.generatedAt)}`
      : "Public dataset synchronization time is unavailable";
  renderOperationalStatus(operational);
  const transparency = summary.sourceTransparency || {};
  const disclosure = document.getElementById("incident-source-disclosure");
  if (disclosure) disclosure.textContent = transparency.disclosure || "Source and review states are shown for each public record.";
}

function formatTimestamp(value) {
  const parsed = new Date(value || "");
  return Number.isNaN(parsed.valueOf()) ? "not recorded" : parsed.toLocaleString("en");
}

function renderOperationalStatus(status) {
  const target = document.getElementById("incident-operational-status");
  if (!target) return;
  const rows = [
    ["Last successful source check", formatTimestamp(status.lastSuccessfulSourceCheck)],
    ["Last incident update", formatTimestamp(status.lastSuccessfulIncidentUpdate)],
    ["Latest public export", formatTimestamp(status.latestPublicExport)],
    ["Source freshness", formatFreshness(status.sourceFreshness)],
    ["Newly published incidents", Number(status.newlyPublishedIncidents || 0).toLocaleString("en")],
    ["Pending candidates", Number(status.pendingCandidateCount || 0).toLocaleString("en")],
    ["Last run status", status.runStatus || "not recorded"],
  ];
  target.replaceChildren();
  rows.forEach(([label, value]) => {
    const group = document.createElement("div");
    group.append(element("dt", "", label), element("dd", "", value));
    target.append(group);
  });
}

function formatFreshness(freshness) {
  if (!freshness) return "not recorded";
  if (freshness.status === "STALE") return `stale: ${freshness.snapshotAgeHours} hours old (SLO ${freshness.sloHours} hours)`;
  if (freshness.status === "CURRENT") return `${freshness.snapshotAgeHours} hours old (SLO ${freshness.sloHours} hours)`;
  return "snapshot date unavailable";
}

function incidentCountColor(country) {
  const count = Number(country?.incidentCount || 0);
  if (count >= 15) return "#a52a35";
  if (count >= 6) return "#c56b21";
  if (count >= 3) return "#d1a928";
  if (count >= 1) return "#0b6e4f";
  return "#777b79";
}

async function renderMap(mapData) {
  const mapElement = document.getElementById("incident-map");
  mapElement?.setAttribute("aria-busy", "true");
  if (leafletMap) {
    leafletMap.invalidateSize();
    mapElement?.setAttribute("aria-busy", "false");
    return;
  }
  const map = L.map("incident-map", { minZoom: 1, maxZoom: 7, worldCopyJump: true, attributionControl: false }).setView([18, 8], 2);
  leafletMap = map;
  const countryByCode = new Map(mapData.countries.map((country) => [country.countryCode, country]));
  const response = await fetch("/assets/data/ne_50m_admin_0_countries.geojson");
  if (!response.ok) throw new Error(`Map geometry request failed (${response.status})`);
  const geojson = await response.json();
  let selectedLayer = null;
  const styleForFeature = (feature) => {
    const country = canonicalCountryForFeature(feature, countryByCode);
    return { color: "#e7e7e7", weight: 0.65, fillColor: incidentCountColor(country), fillOpacity: country ? 0.94 : 0.55 };
  };
  const countriesLayer = L.geoJSON(geojson, {
    filter: (feature) => (feature.properties?.NAME_EN || feature.properties?.NAME) !== "Antarctica",
    style: styleForFeature,
    onEachFeature(feature, layer) {
      const code = countryCodeForFeature(feature);
      const country = canonicalCountryForFeature(feature, countryByCode);
      const name = feature.properties.NAME_EN || feature.properties.NAME || "Country";
      const count = country?.incidentCount || 0;
      const label = `${name}: ${count ? `${count} public incident${count === 1 ? "" : "s"}` : "no public incident data"}`;
      layer.bindTooltip(label, { sticky: true });
      layer.bindPopup(`<strong>${escapeHtml(name)}</strong><br>${count ? `${count} public incident${count === 1 ? "" : "s"}<br><small>Open filtered incidents</small>` : "No public incident data"}`);
      const selectLayer = () => {
        if (selectedLayer && selectedLayer !== layer) countriesLayer.resetStyle(selectedLayer);
        selectedLayer = layer;
        layer.setStyle({ color: "#ffffff", weight: 2.2, fillOpacity: 1 });
        layer.bringToFront();
      };
      layer.on("click", () => {
        selectLayer();
        if (country?.countryCode) navigate({ country: country.countryCode, page: null });
      });
      layer.on("popupclose", () => {
        if (selectedLayer === layer) {
          countriesLayer.resetStyle(layer);
          selectedLayer = null;
        }
      });
      layer.on("add", () => {
        const path = layer.getElement();
        if (!path) return;
        path.setAttribute("tabindex", "0");
        path.setAttribute("role", "button");
        path.setAttribute("aria-label", label);
        path.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          selectLayer();
          if (country?.countryCode) navigate({ country: country.countryCode, page: null });
        });
      });
    },
  }).addTo(map);
  requestAnimationFrame(() => map.invalidateSize({ pan: false }));
  mapElement?.setAttribute("aria-busy", "false");
}

function canonicalCountryForFeature(feature, countryByCode) {
  const country = countryByCode.get(countryCodeForFeature(feature));
  if (!country) return null;
  const featureName = feature.properties?.NAME_EN || feature.properties?.NAME || "";
  return featureName === country.country ? country : null;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function countryCodeForFeature(feature) {
  const properties = feature.properties || {};
  const primary = properties.ISO_A2 || properties.iso_a2;
  const extended = properties.ISO_A2_EH || properties.iso_a2_eh;
  const code = primary === "-99" ? extended : primary;
  return code && code !== "-99" ? String(code).toUpperCase() : null;
}

function wireFilters() {
  if (filtersWired) return;
  filtersWired = true;
  const form = document.getElementById("incident-filters");
  setFilterFormValues(form);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = new URLSearchParams();
    new FormData(form).forEach((value, key) => { if (value) query.set(key, value); });
    navigate(Object.fromEntries(query.entries()));
  });
  form.addEventListener("reset", (event) => {
    event.preventDefault();
    navigate({}, true);
  });
  window.addEventListener("popstate", () => {
    params = new URLSearchParams(location.search);
    setFilterFormValues(form);
    start();
  });
}

function setFilterFormValues(form) {
  [...form.elements].forEach((control) => { if (control.name) control.value = params.get(control.name) || ""; });
}

function navigate(changes, replace = false) {
  const query = new URLSearchParams(location.search);
  Object.entries(changes).forEach(([key, value]) => {
    if (value === null || value === "") query.delete(key);
    else query.set(key, value);
  });
  const next = `${location.pathname}${query.toString() ? `?${query}` : ""}`;
  history[replace ? "replaceState" : "pushState"]({}, "", next);
  params = new URLSearchParams(query);
  const form = document.getElementById("incident-filters");
  if (form) setFilterFormValues(form);
  start();
}

function applyFilters(items) {
  let result = [...items];
  const query = (params.get("q") || "").toLowerCase();
  if (query) result = result.filter((item) => (item.searchText || "").includes(query));
  if (params.get("severity")) result = result.filter((item) => item.severity === params.get("severity"));
  if (params.get("eventType")) result = result.filter((item) => item.eventType === params.get("eventType"));
  if (params.get("analysisStatus")) result = result.filter((item) => item.assessment?.analysisStatus === params.get("analysisStatus"));
  if (params.get("reviewStatus")) result = result.filter((item) => item.assessment?.reviewStatus === params.get("reviewStatus"));
  if (params.get("evidenceStatus")) result = result.filter((item) => item.assessment?.evidenceStatus === params.get("evidenceStatus"));
  if (params.get("country")) result = result.filter((item) => item.countryCode === params.get("country"));
  if (params.get("architecture")) result = result.filter((item) => {
    const ids = [item.primaryArchitecture, ...(item.contributingArchitectures || [])].map((entry) => entry?.architectureId);
    return ids.includes(params.get("architecture"));
  });
  return result.sort((left, right) => {
    const leftDate = Date.parse(left.occurredAt || left.reportedAt || "") || 0;
    const rightDate = Date.parse(right.occurredAt || right.reportedAt || "") || 0;
    return rightDate - leftDate || String(left.id || "").localeCompare(String(right.id || ""));
  });
}

function renderGeographySummary(geography) {
  const container = document.getElementById("incident-geography-summary");
  container.replaceChildren(metric("Public records", geography.total), metric("Geographically assigned", geography.geographicallyAssigned), metric("Location not specified", geography.locationNotSpecified));
}

function metric(label, value) {
  const item = document.createElement("div");
  item.append(element("b", "", Number(value || 0).toLocaleString("en")), element("span", "", label));
  return item;
}

function renderCountryTable(countries, compact = false) {
  const target = compact ? document.getElementById("incident-country-table") : analysisView;
  const wrapper = element("div", "oof-country-table-wrap");
  const table = document.createElement("table");
  table.className = "oof-data-table";
  table.innerHTML = "<thead><tr><th>Country</th><th>Public records</th><th>Critical</th><th>View</th></tr></thead>";
  const body = document.createElement("tbody");
  (compact ? countries.slice(0, 12) : countries).forEach((country) => {
    const row = document.createElement("tr");
    row.append(element("td", "", country.country), element("td", "", country.count), element("td", "", country.critical));
    const action = document.createElement("td");
    const link = element("a", "oof-table-action", "Filter incidents");
    link.href = queryLink({ country: country.countryCode, page: null });
    action.append(link);
    row.append(action);
    body.append(row);
  });
  table.append(body);
  wrapper.append(table);
  if (compact) target.replaceChildren(wrapper);
  else target.append(wrapper);
}

function renderArchitectures(architectures, architectureLinks) {
  analysisView.replaceChildren(viewIntro("Architecture distribution", "Primary and contributing assignments are shown separately. Relevance does not establish architecture failure."));
  const grid = element("div", "oof-aggregate-grid");
  architectures.forEach((item) => {
    const card = element("article", "oof-aggregate-card");
    const title = element("h2", "", item.label || item.architectureId.toUpperCase());
    const canonical = architectureLinks.get(item.architectureId) || item.canonicalUrl;
    if (canonical) {
      const link = element("a", "", title.textContent);
      link.href = canonical;
      title.replaceChildren(link);
    }
    const counts = element("dl", "oof-aggregate-counts");
    [["Primary", item.primary], ["Contributing", item.contributing], ["Methodology references", item.methodologyReferences]].forEach(([label, value]) => {
      const group = document.createElement("div");
      group.append(element("dt", "", label), element("dd", "", value));
      counts.append(group);
    });
    const incidents = element("a", "oof-view-link", "View associated incidents");
    incidents.href = queryLink({ architecture: item.architectureId, page: null });
    card.append(title, counts, incidents);
    grid.append(card);
  });
  analysisView.append(grid);
}

function renderIndustries(industries, notice) {
  analysisView.replaceChildren(viewIntro("Industry distribution", notice), barList(industries, "industry", "count"));
}

function renderCountries(geography, notice) {
  analysisView.replaceChildren(viewIntro("Country coverage", notice));
  const summary = element("div", "oof-geography-summary");
  summary.append(metric("Public records", geography.total), metric("Geographically assigned", geography.geographicallyAssigned), metric("Location not specified", geography.locationNotSpecified));
  analysisView.append(summary);
  renderCountryTable(geography.countries, false);
}

function renderTrends(trends, notice) {
  analysisView.replaceChildren(viewIntro("Incident trends", `${notice} Event dates reflect the best date available in each source record.`));
  const recent = trends.filter((item) => item.period !== "Date not specified").slice(-24).reverse();
  const wrapper = element("div", "oof-country-table-wrap");
  const table = document.createElement("table");
  table.className = "oof-data-table";
  table.innerHTML = "<thead><tr><th>Period</th><th>Total</th><th>Critical</th><th>High</th><th>Moderate</th><th>Low</th></tr></thead>";
  const body = document.createElement("tbody");
  recent.forEach((item) => {
    const row = document.createElement("tr");
    [item.period, item.total, item.critical, item.high, item.moderate, item.low].forEach((value) => row.append(element("td", "", value)));
    body.append(row);
  });
  table.append(body);
  wrapper.append(table);
  analysisView.append(wrapper);
}

function viewIntro(title, copy) {
  const header = element("header", "oof-view-intro");
  header.append(element("h2", "", title), element("p", "", copy));
  return header;
}

function barList(items, labelKey, valueKey) {
  const list = element("div", "oof-bar-list");
  const maximum = Math.max(1, ...items.map((item) => item[valueKey]));
  items.forEach((item) => {
    const row = element("div", "oof-bar-row");
    row.append(element("span", "", item[labelKey]), element("b", "", item[valueKey]));
    const bar = element("i", "");
    bar.style.setProperty("--bar-size", `${Math.max(2, item[valueKey] / maximum * 100)}%`);
    row.append(bar);
    list.append(row);
  });
  return list;
}

function renderIncidents(items, architectureLinks, options) {
  const list = document.getElementById("incident-list");
  const empty = document.getElementById("incident-empty");
  const pageCount = Math.max(1, Math.ceil(options.total / options.pageSize));
  const currentPage = Math.min(pageCount, options.page);
  const visibleItems = options.locallyPaged ? items.slice((currentPage - 1) * options.pageSize, currentPage * options.pageSize) : items;
  document.getElementById("incident-result-count").textContent = `${options.total} public record${options.total === 1 ? "" : "s"}`;
  list.replaceChildren();
  empty.hidden = options.total > 0;
  visibleItems.forEach((incident) => list.append(createIncidentCard(incident, architectureLinks)));
  if (options.total > options.pageSize) list.append(createPagination(currentPage, pageCount));
}

function createIncidentCard(incident, architectureLinks) {
  const article = element("article", "oof-incident-row");
  const headingBlock = element("div", "oof-incident-card-main");
  const eyebrow = element("p", "oof-incident-card-eyebrow");
  eyebrow.append(
    element("span", "oof-incident-id", incident.id),
    element("span", "", incident.industry || "Industry not specified"),
    element("span", "", incident.country || "Location not specified"),
    element("time", "", (incident.occurredAt || incident.reportedAt || "Date not specified").slice(0, 10)),
  );
  headingBlock.append(eyebrow);
  const heading = element("h3", "");
  const detailLink = element("a", "", incident.title);
  detailLink.href = incident.detailUrl;
  heading.append(detailLink);
  headingBlock.append(heading);

  const status = element("dl", "oof-incident-card-status");
  [
    ["Evidence", incident.assessment?.evidenceStatus || "Evidence Insufficient"],
    ["Source", incident.source?.publisher || "Source not identified"],
    ["Severity", incident.severity || "Insufficient Evidence"],
    ["Review", incident.assessment?.reviewStatus || "Not performed"],
  ].forEach(([term, value]) => {
    const group = document.createElement("div");
    group.append(element("dt", "", term), element("dd", "", value));
    status.append(group);
  });
  headingBlock.append(status);

  const intelligence = element("div", "oof-incident-card-intelligence");
  const architecture = incident.primaryArchitecture;
  const architectureUrl = architectureLinks.get(String(architecture?.architectureId || "").toLowerCase()) || architecture?.canonicalUrl;
  const focusHeading = element("h4", "", "Intelligence governance focus");
  const focus = element("p", "");
  if (architectureUrl) {
    const link = element("a", "", architecture?.label || architecture?.architectureId?.toUpperCase());
    link.href = architectureUrl;
    focus.append(link);
  } else focus.textContent = "Governed space unresolved";
  const assignment = element("p", "oof-incident-card-assignment", `Assignment: ${incident.assessment?.coverage || "Review required"}`);
  const insight = element("p", "oof-incident-card-insight", incident.governanceInsight || "Available evidence does not yet support a case-specific governance conclusion.");
  intelligence.append(focusHeading, focus, assignment, insight);
  headingBlock.append(intelligence);

  const actions = element("div", "oof-incident-card-actions");
  const view = element("a", "oof-incident-primary-action", "View incident");
  view.href = incident.detailUrl;
  const verify = element("a", "oof-incident-secondary-action", "Help verify / Submit evidence");
  verify.href = incident.verifyUrl || `/ai-incidents/verify/?incident=${encodeURIComponent(incident.slug)}`;
  actions.append(view, verify);
  headingBlock.append(actions);
  article.append(headingBlock);
  return article;
}

function incidentDefinitionList(incident, architectureLinks) {
  const list = document.createElement("dl");
  [["Date", (incident.occurredAt || incident.reportedAt || "Unknown").slice(0, 10)], ["Country", incident.country || "Location not specified"], ["Severity", incident.severity || "Insufficient evidence"]].forEach(([term, value]) => {
    const group = document.createElement("div");
    group.append(element("dt", "", term), element("dd", "", value));
    list.append(group);
  });
  const coverageGroup = document.createElement("div");
  const coverage = incident.primaryArchitecture;
  coverageGroup.append(element("dt", "", "Coverage"));
  const value = element("dd", "");
  const architectureUrl = architectureLinks.get(String(coverage?.architectureId || "").toLowerCase()) || coverage?.canonicalUrl;
  if (architectureUrl) {
    const link = element("a", "oof-incident-architecture-link", coverage.label || coverage.architectureId.toUpperCase());
    link.href = architectureUrl;
    value.append(link);
  } else value.textContent = coverage?.label || "Insufficient evidence";
  coverageGroup.append(value);
  list.append(coverageGroup);
  return list;
}

function createLazyAnalysisPanel(incident, architectureLinks) {
  const details = element("details", "oof-incident-analysis");
  details.append(element("summary", "", `View ${incident.assessment.label || "Automated Preliminary Governance Assessment"} v${incident.assessment.analysisVersion || ""}`.trim()));
  const body = element("div", "oof-incident-analysis-body", "Assessment details load when opened.");
  details.append(body);
  let loaded = false;
  details.addEventListener("toggle", async () => {
    if (!details.open || loaded) return;
    loaded = true;
    body.textContent = "Loading assessment details…";
    try {
      const record = await repository.detail(incident.slug);
      body.replaceChildren();
      appendAnalysis(body, record.automatedAnalysis, architectureLinks);
    } catch (error) {
      loaded = false;
      body.textContent = "Assessment details could not be loaded. Close and reopen this section to retry.";
    }
  });
  return details;
}

function appendAnalysis(body, analysis, architectureLinks) {
  if (!analysis) {
    body.textContent = "No automated assessment is available for this record.";
    return;
  }
  const confidence = analysis.confidenceDimensions || {};
  appendDefinitionList(body, [
    ["Source corroboration", confidence.sourceCorroboration?.level || analysis.evidenceSnapshot?.corroboration?.status || "Insufficient evidence"],
    ["Extraction completeness", confidence.extractionCompleteness?.level || "Not assessed"],
    ["Methodological assignment", confidence.methodologicalAssignment?.level || analysis.assessmentConfidence || "Evidence Insufficient"],
    ["OOF Approved", analysis.oofApproved ? "Yes" : "No"],
    ["Severity", analysis.severityAssessment?.level || "Insufficient Evidence"],
  ]);
  appendAnalysisText(body, "Assessment disclosure", analysis.assessmentDisclosure, "oof-analysis-disclosure");
  const evidence = analysis.incidentEvidence || {};
  appendAnalysisList(body, "Known facts from the incident record", evidence.knownFacts, (row, item) => { row.textContent = item; });
  appendAnalysisList(body, "Reported claims", evidence.reportedClaims, (row, item) => { row.textContent = item; });
  appendAnalysisList(body, "Material unknowns", evidence.materialUnknowns, (row, item) => { row.textContent = item; });
  appendAnalysisText(body, "Primary governance problem", analysis.primaryGovernanceProblem);
  appendArchitectureCards(body, [analysis.architectureAnalysis?.primaryArchitecture, ...(analysis.architectureAnalysis?.contributingArchitectures || [])].filter(Boolean), architectureLinks);
  appendAnalysisText(body, "Incident governance insight", analysis.incidentGovernanceInsight, "oof-governance-insight");
  appendAnalysisList(body, "Preliminary findings", analysis.governanceFindings, (row, item) => { row.textContent = `${item.finding || item.statement} [${item.status || "Unresolved"}] ${item.limitation || ""}`.trim(); });
  appendAnalysisList(body, "Key governance questions", analysis.governanceQuestions, (row, item) => { row.textContent = item; });
  appendAnalysisList(body, "Evidence gaps", analysis.evidenceGaps || analysis.uncertainties, (row, item) => { row.textContent = item; });
}

function appendDefinitionList(container, entries) {
  const list = element("dl", "oof-analysis-status");
  entries.forEach(([term, value]) => {
    const group = document.createElement("div");
    group.append(element("dt", "", term), element("dd", "", value));
    list.append(group);
  });
  container.append(list);
}

function appendAnalysisList(container, heading, items, renderItem) {
  if (!items?.length) return;
  container.append(element("h5", "", heading));
  const list = document.createElement("ul");
  items.forEach((item) => {
    const row = document.createElement("li");
    renderItem(row, item);
    list.append(row);
  });
  container.append(list);
}

function appendAnalysisText(container, heading, value, className = "") {
  if (value) container.append(element("h5", "", heading), element("p", className, value));
}

function appendArchitectureCards(container, items, architectureLinks) {
  if (!items.length) return;
  container.append(element("h5", "", "Architecture intelligence"));
  const cards = element("div", "oof-architecture-intelligence");
  items.forEach((item) => {
    const card = element("section", "oof-architecture-intelligence-card");
    const heading = element("h6", "");
    const href = architectureLinks.get(String(item.architectureId || "").toLowerCase()) || item.canonicalUrl;
    if (href) {
      const link = element("a", "", item.label || item.architectureId?.toUpperCase());
      link.href = href;
      heading.append(link);
    } else heading.textContent = item.label || item.architectureId?.toUpperCase() || "Architecture not identified";
    card.append(heading, element("span", "", item.role === "Primary" ? "Primary Architecture" : "Contributing Architecture"));
    if (item.whyItMattersHere || item.reasonForRelevance) card.append(element("b", "", "Why it matters here"), element("p", "", item.whyItMattersHere || item.reasonForRelevance));
    if (item.governanceFocus) card.append(element("b", "", "Governance focus"), element("p", "", item.governanceFocus));
    const references = item.relevantStandardsModules || [];
    if (references.length) {
      card.append(element("b", "", `Canonical methodology (${item.methodologyDepth || references.at(-1)?.artifactType || "verified"})`));
      const list = document.createElement("ul");
      references.forEach((reference) => {
        const row = document.createElement("li");
        const label = `${reference.artifactType === "ParentStandard" ? "Parent Standard" : "Core Module"}: ${reference.name}`;
        if (reference.canonicalUrl) {
          const link = element("a", "", label);
          link.href = reference.canonicalUrl;
          row.append(link);
        } else row.textContent = label;
        list.append(row);
      });
      card.append(list);
    } else if (item.methodologyDepth === "Architecture") {
      card.append(element("p", "oof-methodology-withheld", "Deeper methodology is withheld because the available evidence does not justify a Parent Standard or Core Module."));
    }
    cards.append(card);
  });
  container.append(cards);
}

function createPagination(currentPage, pageCount) {
  const pagination = element("nav", "oof-incident-pagination");
  pagination.setAttribute("aria-label", "Incident result pages");
  const previous = element("a", "", "Previous");
  const next = element("a", "", "Next");
  if (currentPage > 1) previous.href = queryLink({ page: currentPage - 1 });
  else previous.setAttribute("aria-disabled", "true");
  if (currentPage < pageCount) next.href = queryLink({ page: currentPage + 1 });
  else next.setAttribute("aria-disabled", "true");
  pagination.append(previous, element("span", "", `Page ${currentPage} of ${pageCount}`), next);
  return pagination;
}

function queryLink(changes) {
  const query = new URLSearchParams(location.search);
  Object.entries(changes).forEach(([key, value]) => {
    if (value === null || value === "") query.delete(key);
    else query.set(key, value);
  });
  return `${location.pathname}${query.toString() ? `?${query}` : ""}`;
}

function element(tag, className = "", text = null) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== null && text !== undefined) node.textContent = text;
  return node;
}
