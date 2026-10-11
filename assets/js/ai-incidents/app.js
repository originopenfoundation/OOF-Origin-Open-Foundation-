import { IncidentRepository } from "./repository.js";

const repository = new IncidentRepository();
const params = new URLSearchParams(location.search);
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
  setState("loading", "Loading the public incident dataset…");
  try {
    const requestedPage = Math.max(1, Number(params.get("page")) || 1);
    const [summary, mapData, page, aggregations, architectureLinks] = await Promise.all([
      repository.summary(), repository.map(), repository.page(requestedPage),
      repository.aggregations(), loadArchitectureLinks(),
    ]);
    renderSummary(summary);
    let result = page;
    if (requiresIndex()) {
      const index = await repository.index();
      result = { ...index, page: requestedPage, pageSize: 25 };
    }
    await renderRoute(result, mapData, aggregations, architectureLinks);
    setState("success", "Public incident dataset loaded.");
  } catch (error) {
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

function requiresIndex() {
  return ["critical", "stress-tests"].includes(view)
    || ["q", "severity", "eventType", "coverage", "country", "architecture"].some((key) => params.get(key));
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
  const locallyPaged = requiresIndex();
  renderIncidents(items, architectureLinks, {
    page: Math.max(1, Number(params.get("page")) || 1),
    pageSize: result.pageSize || 25,
    total: locallyPaged ? items.length : result.total,
    locallyPaged,
  });
}

async function loadArchitectureLinks() {
  try {
    const response = await fetch("/data/oof-architecture-registry.json", { headers: { Accept: "application/json" } });
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
  document.getElementById("incident-data-time").textContent = summary.generatedAt
    ? `Public dataset updated ${new Date(summary.generatedAt).toLocaleString("en")}`
    : "Public dataset synchronization time is unavailable";
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
  if (leafletMap) {
    leafletMap.invalidateSize();
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
    const country = countryByCode.get(countryCodeForFeature(feature));
    return { color: "#e7e7e7", weight: 0.65, fillColor: incidentCountColor(country), fillOpacity: country ? 0.94 : 0.55 };
  };
  const countriesLayer = L.geoJSON(geojson, {
    filter: (feature) => (feature.properties?.NAME_EN || feature.properties?.NAME) !== "Antarctica",
    style: styleForFeature,
    onEachFeature(feature, layer) {
      const code = countryCodeForFeature(feature);
      const country = countryByCode.get(code);
      const name = feature.properties.NAME_EN || feature.properties.NAME || "Country";
      const count = country?.incidentCount || 0;
      const label = `${name}: ${count ? `${count} public incident${count === 1 ? "" : "s"}` : "no public incident data"}`;
      layer.bindTooltip(label, { sticky: true });
      layer.bindPopup(`<strong>${escapeHtml(name)}</strong><br>${count ? `${count} public incident${count === 1 ? "" : "s"}` : "No public incident data"}`);
      const selectLayer = () => {
        if (selectedLayer && selectedLayer !== layer) countriesLayer.resetStyle(selectedLayer);
        selectedLayer = layer;
        layer.setStyle({ color: "#ffffff", weight: 2.2, fillOpacity: 1 });
        layer.bringToFront();
      };
      layer.on("click", selectLayer);
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
          layer.openPopup();
        });
      });
    },
  }).addTo(map);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function countryCodeForFeature(feature) {
  const properties = feature.properties || {};
  const primary = properties.ISO_A2 || properties.iso_a2;
  return primary === "-99" ? null : primary;
}

function wireFilters() {
  if (filtersWired) return;
  filtersWired = true;
  const form = document.getElementById("incident-filters");
  for (const [key, value] of params.entries()) if (form.elements[key]) form.elements[key].value = value;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = new URLSearchParams();
    new FormData(form).forEach((value, key) => { if (value) query.set(key, value); });
    location.search = query.toString();
  });
  form.addEventListener("reset", () => { location.search = ""; });
}

function applyFilters(items) {
  let result = [...items];
  const query = (params.get("q") || "").toLowerCase();
  if (query) result = result.filter((item) => JSON.stringify(item).toLowerCase().includes(query));
  if (params.get("severity")) result = result.filter((item) => item.severity === params.get("severity"));
  if (params.get("eventType")) result = result.filter((item) => item.eventType === params.get("eventType"));
  if (params.get("coverage")) result = result.filter((item) => item.assessment?.coverage === params.get("coverage"));
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
  const headingBlock = document.createElement("div");
  headingBlock.append(element("span", "oof-incident-id", incident.id));
  const heading = element("h3", "");
  const detailLink = element("a", "", incident.title);
  detailLink.href = incident.detailUrl;
  heading.append(detailLink);
  const summary = element("p", "oof-incident-summary", incident.summary || "No public summary available.");
  headingBlock.append(heading, summary);
  if ((incident.summary || "").length > 220) {
    const toggle = element("button", "oof-incident-summary-toggle", "Show full summary");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    toggle.addEventListener("click", () => {
      const expanded = summary.classList.toggle("is-expanded");
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.textContent = expanded ? "Show less" : "Show full summary";
    });
    headingBlock.append(toggle);
  }
  if (incident.source?.url) {
    const source = element("p", "oof-incident-source");
    const sourceLink = element("a", "", "View source record");
    sourceLink.href = incident.source.url;
    sourceLink.target = "_blank";
    sourceLink.rel = "noopener noreferrer";
    source.append(sourceLink);
    headingBlock.append(source);
  }
  article.append(headingBlock, incidentDefinitionList(incident, architectureLinks));
  if (incident.assessment?.available) article.append(createLazyAnalysisPanel(incident, architectureLinks));
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
  appendDefinitionList(body, [["Assessment confidence", analysis.assessmentConfidence || "Evidence Insufficient"], ["OOF Approved", analysis.oofApproved ? "Yes" : "No"], ["Evidence", analysis.evidenceSnapshot?.corroboration?.status || "Insufficient evidence"], ["Severity", analysis.severityAssessment?.level || "Insufficient Evidence"]]);
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
