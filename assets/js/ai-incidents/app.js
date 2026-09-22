import { IncidentRepository } from "./repository.js";

const repository = new IncidentRepository();
const params = new URLSearchParams(location.search);
const view = document.documentElement.dataset.aiIncidentsView || "dashboard";
const monitor = document.getElementById("incident-monitor-view");
const methodology = document.getElementById("incident-methodology-view");

if (view === "methodology") {
  monitor.hidden = true;
  methodology.hidden = false;
} else {
  start().catch((error) => {
    document.getElementById("incident-empty").textContent = "The public incident dataset could not be loaded.";
    console.error(error);
  });
}

async function start() {
  const [summary, mapData, page] = await Promise.all([repository.summary(), repository.map(), repository.all()]);
  renderSummary(summary);
  renderMap(mapData);
  wireFilters();
  renderIncidents(applyFilters(page.items));
}

function renderSummary(summary) {
  document.querySelectorAll("[data-metric]").forEach((element) => {
    element.textContent = Number(summary[element.dataset.metric] || 0).toLocaleString("en");
  });
  document.getElementById("incident-data-time").textContent = summary.generatedAt
    ? `Public dataset updated ${new Date(summary.generatedAt).toLocaleString("en")}`
    : "Public dataset not yet synchronized";
}

function coverageColor(country) {
  const values = country?.coverage || {};
  if (values.NO_ARCHITECTURE_IDENTIFIED) return "#9f2130";
  if (values.ARCHITECTURE_REVIEW_REQUIRED) return "#ad6c12";
  if (values.ARCHITECTURE_IDENTIFIED) return "#08704a";
  return "#777b79";
}

async function renderMap(mapData) {
  const map = L.map("incident-map", { minZoom: 1, maxZoom: 7, worldCopyJump: true, attributionControl: false }).setView([18, 8], 2);
  const countryByCode = new Map(mapData.countries.map((country) => [country.countryCode, country]));
  const response = await fetch("/assets/data/ne_50m_admin_0_countries.geojson");
  const geojson = await response.json();
  L.geoJSON(geojson, {
    style(feature) {
      const code = countryCodeForFeature(feature);
      const country = countryByCode.get(code);
      return { color: "#d6d6d6", weight: 0.55, fillColor: coverageColor(country), fillOpacity: country ? 0.92 : 0.6 };
    },
    onEachFeature(feature, layer) {
      const code = countryCodeForFeature(feature);
      const country = countryByCode.get(code);
      const name = feature.properties.NAME_EN || feature.properties.NAME || "Country";
      layer.bindTooltip(country ? `${name}: ${country.incidentCount} public incident${country.incidentCount === 1 ? "" : "s"}` : `${name}: no public incident data`, { sticky: true });
    }
  }).addTo(map);
  mapData.incidents.forEach((incident) => {
    if (!incident.coordinates) return;
    L.circleMarker([incident.coordinates.latitude, incident.coordinates.longitude], {
      radius: 5, color: "#fff", weight: 1, fillColor: coverageColor({ coverage: { [incident.architectureRelevance?.status || "NOT_ASSESSED"]: 1 } }), fillOpacity: 0.95
    }).bindTooltip(incident.title).addTo(map);
  });
}

function countryCodeForFeature(feature) {
  const properties = feature.properties || {};
  const primary = properties.ISO_A2 || properties.iso_a2;
  return primary === "-99" ? (properties.ISO_A2_EH || properties.iso_a2_eh) : primary;
}

function wireFilters() {
  const form = document.getElementById("incident-filters");
  for (const [key, value] of params.entries()) {
    if (form.elements[key]) form.elements[key].value = value;
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = new URLSearchParams();
    new FormData(form).forEach((value, key) => { if (value) query.set(key, value); });
    location.search = query.toString();
  });
  form.addEventListener("reset", () => { location.search = ""; });
}

function applyFilters(items) {
  let result = items;
  const routeFilters = {
    critical: (item) => item.severity === "Critical",
    latest: () => true,
    "stress-tests": (item) => item.assessment?.status === "Approved"
  };
  if (routeFilters[view]) result = result.filter(routeFilters[view]);
  const query = (params.get("q") || "").toLowerCase();
  if (query) result = result.filter((item) => JSON.stringify(item).toLowerCase().includes(query));
  if (params.get("severity")) result = result.filter((item) => item.severity === params.get("severity"));
  if (params.get("eventType")) result = result.filter((item) => item.eventType === params.get("eventType"));
  if (params.get("coverage")) result = result.filter((item) => item.architectureRelevance?.status === params.get("coverage"));
  return result;
}

function renderIncidents(items) {
  const list = document.getElementById("incident-list");
  const empty = document.getElementById("incident-empty");
  const pageSize = 25;
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const currentPage = Math.min(pageCount, Math.max(1, Number(params.get("page")) || 1));
  const visibleItems = items.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  document.getElementById("incident-result-count").textContent = `${items.length} public record${items.length === 1 ? "" : "s"}`;
  list.replaceChildren();
  empty.hidden = items.length > 0;
  visibleItems.forEach((incident) => {
    const article = document.createElement("article");
    article.className = "oof-incident-row";
    const coverage = incident.architectureRelevance?.status || "NOT_ASSESSED";
    article.innerHTML = `<div><span class="oof-incident-id"></span><h3></h3><p class="oof-incident-summary"></p><p class="oof-incident-source"><a target="_blank" rel="noopener noreferrer">View source record</a></p></div><dl><div><dt>Date</dt><dd></dd></div><div><dt>Country</dt><dd></dd></div><div><dt>Severity</dt><dd></dd></div><div><dt>Coverage</dt><dd></dd></div></dl>`;
    article.querySelector(".oof-incident-id").textContent = incident.id;
    article.querySelector("h3").textContent = incident.title;
    article.querySelector(".oof-incident-summary").textContent = incident.summary || "No public summary available.";
    const sourceLink = article.querySelector(".oof-incident-source a");
    const sourceUrl = incident.sources?.[0]?.url;
    if (sourceUrl) sourceLink.href = sourceUrl;
    else sourceLink.parentElement.hidden = true;
    const values = article.querySelectorAll("dd");
    values[0].textContent = (incident.occurredAt || incident.reportedAt || "Unknown").slice(0, 10);
    values[1].textContent = incident.country || "Unknown";
    values[2].textContent = incident.severity || "Unclassified";
    values[3].textContent = coverage.replaceAll("_", " ");
    list.append(article);
  });
  if (items.length > pageSize) {
    const pagination = document.createElement("nav");
    pagination.className = "oof-incident-pagination";
    pagination.setAttribute("aria-label", "Incident result pages");
    const previous = document.createElement("button");
    const status = document.createElement("span");
    const next = document.createElement("button");
    previous.type = next.type = "button";
    previous.textContent = "Previous";
    next.textContent = "Next";
    status.textContent = `Page ${currentPage} of ${pageCount}`;
    previous.disabled = currentPage === 1;
    next.disabled = currentPage === pageCount;
    previous.addEventListener("click", () => openResultPage(currentPage - 1));
    next.addEventListener("click", () => openResultPage(currentPage + 1));
    pagination.append(previous, status, next);
    list.append(pagination);
  }
}

function openResultPage(page) {
  const query = new URLSearchParams(location.search);
  query.set("page", page);
  location.search = query.toString();
}
