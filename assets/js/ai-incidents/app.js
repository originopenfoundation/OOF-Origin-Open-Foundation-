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

enhanceDashboardLayout();
markCurrentView();
if (view === "methodology") {
  monitor.hidden = true;
  methodology.hidden = false;
} else {
  wireFilters();
  retry.addEventListener("click", start);
  start();
}

function enhanceDashboardLayout() {
  const legendLabels = ['1–5 incidents', '6–20 incidents', '21–50 incidents', '51+ incidents', 'No public incident data'];
  document.querySelectorAll('.oof-incident-map-legend span').forEach((item, index) => {
    const icon = item.querySelector('i');
    if (icon && legendLabels[index]) item.replaceChildren(icon, document.createTextNode(legendLabels[index]));
  });
  const intro = document.querySelector('.oof-incident-intro');
  if (intro) {
    const disclosure = document.createElement('details');
    disclosure.className = 'oof-dashboard-intro';
    const title = document.createElement('summary');
    title.textContent = 'About this intelligence platform';
    intro.before(disclosure);
    disclosure.append(title, intro);
    document.querySelector('.oof-incident-nav')?.after(disclosure);
  }
  const nav = document.querySelector('.oof-incident-nav');
  const overview = nav?.querySelector('a[href="/ai-incidents/"]');
  if (overview) overview.textContent = 'Overview';
  if (nav) {
    const analyses = document.createElement('a');
    analyses.href = '/ai-incidents/?lens=systems';
    analyses.textContent = 'Analyses';
    analyses.dataset.fixedTarget = 'true';
    nav.querySelector('a[href="/ai-incidents/architectures/"]')?.before(analyses);
    const sourcesLink = document.createElement('a');
    sourcesLink.href = '/ai-incidents/#dashboard-sources-title';
    sourcesLink.textContent = 'Sources';
    sourcesLink.dataset.fixedTarget = 'true';
    nav.querySelector('a[href="/ai-incidents/methodology/"]')?.before(sourcesLink);
    const mainLinks = [overview, nav.querySelector('a[href="/ai-incidents/map/"]'), nav.querySelector('a[href="/ai-incidents/latest/"]'), analyses, nav.querySelector('a[href="/ai-incidents/architectures/"]'), sourcesLink, nav.querySelector('a[href="/ai-incidents/methodology/"]')];
    const latest = mainLinks[2];
    if (latest) latest.textContent = 'Incidents';
    const more = document.createElement('details');
    more.className = 'oof-nav-more';
    const label = document.createElement('summary');
    label.textContent = 'More';
    const menu = document.createElement('div');
    [...nav.querySelectorAll('a')].filter((link) => !mainLinks.includes(link)).forEach((link) => menu.append(link));
    more.append(label, menu);
    mainLinks.filter(Boolean).forEach((link) => nav.append(link));
    nav.append(more);
  }
  const metrics = document.querySelector('.oof-incident-metrics');
  if (metrics) {
    const featured = ['totalIncidents', 'countriesAffected', 'automatedAnalyses', 'humanReviewPriorityQueue'];
    const extra = document.createElement('dl');
    extra.className = 'oof-incident-metrics';
    extra.setAttribute('aria-label', 'Additional incident dataset metrics');
    [...metrics.children].forEach((item) => {
      if (!featured.includes(item.querySelector('[data-metric]')?.dataset.metric)) extra.append(item);
    });
    featured.forEach((name) => {
      const item = metrics.querySelector(`[data-metric="${name}"]`)?.parentElement;
      if (item) metrics.append(item);
    });
    const disclosure = document.createElement('details');
    disclosure.className = 'oof-dashboard-extra-metrics';
    const title = document.createElement('summary');
    title.textContent = 'More dataset metrics';
    disclosure.append(title, extra);
    metrics.after(disclosure);
  }
  const countryTable = document.getElementById('incident-country-table');
  if (countryTable) {
    const disclosure = document.createElement('details');
    disclosure.className = 'oof-dashboard-countries';
    const title = document.createElement('summary');
    title.textContent = 'Incident counts by country';
    countryTable.before(disclosure);
    const geographySummary = document.getElementById('incident-geography-summary');
    disclosure.append(title);
    if (geographySummary) disclosure.append(geographySummary);
    disclosure.append(countryTable);
  }
  const filters = document.getElementById('incident-filters');
  if (filters) {
    const disclosure = document.createElement('details');
    disclosure.className = 'oof-dashboard-filters';
    const title = document.createElement('summary');
    title.textContent = 'Search and filters';
    filters.before(disclosure);
    disclosure.append(title, filters);
    if (params.toString()) disclosure.open = true;
  }
  const operations = document.querySelector('.oof-incident-operations');
  if (operations && listPane) {
    const disclosure = document.createElement('details');
    disclosure.className = 'oof-dashboard-operations';
    const title = document.createElement('summary');
    title.textContent = 'Operational transparency';
    operations.querySelector('h2')?.remove();
    operations.before(disclosure);
    disclosure.append(title, operations);
    document.querySelector('.oof-incident-workspace')?.after(disclosure);
  }
  if (mapPane && view === 'dashboard') {
    const sources = document.createElement('aside');
    sources.className = 'oof-dashboard-sources';
    sources.setAttribute('aria-labelledby', 'dashboard-sources-title');
    sources.innerHTML = '<h2 id="dashboard-sources-title">Sources</h2><p>Loading source information…</p><a href="/ai-incidents/methodology/#source-collection-and-verification">Source methodology</a>';
    mapPane.after(sources);
    const severity = document.createElement('aside');
    severity.className = 'oof-dashboard-severity';
    severity.innerHTML = '<h2>Incidents by Severity</h2><p>Loading severity data…</p>';
    listPane.after(severity);
    const heading = listPane.querySelector('h2');
    if (heading) heading.textContent = 'Recent Incidents';
    const all = document.createElement('a');
    all.className = 'oof-dashboard-view-all';
    all.href = '/ai-incidents/latest/';
    all.textContent = 'View all incidents →';
    listPane.querySelector('.oof-incident-section-heading')?.append(all);
  }
  const subtitle = document.querySelector('.oof-incident-header > div > p');
  if (subtitle) subtitle.textContent = 'AI Incidents · Risk Analysis · Architectures · Prevention · Verification';
  if (view !== 'methodology') {
    const trend = document.createElement('section');
    trend.className = 'oof-dashboard-trend';
    trend.innerHTML = '<h2>Incident Trend</h2><p>Loading event dates…</p>';
    metrics?.after(trend);
    if (metrics) {
      const row = document.createElement('div');
      row.className = 'oof-dashboard-kpis';
      metrics.before(row);
      row.append(metrics, trend);
    }
    const workspace = document.querySelector('.oof-incident-workspace');
    const supplementary = document.createElement('div');
    supplementary.className = 'oof-dashboard-supplementary';
    ['.oof-dashboard-intro', '.oof-dashboard-extra-metrics', '.oof-dashboard-filters', '.oof-incident-source-disclosure', '.oof-dashboard-operations'].forEach((selector) => {
      const item = document.querySelector(selector);
      if (item) supplementary.append(item);
    });
    workspace?.after(supplementary);
    const search = document.createElement('button');
    search.type = 'button';
    search.className = 'oof-dashboard-search';
    search.title = 'Search and filters';
    search.setAttribute('aria-label', 'Search and filters');
    search.addEventListener('click', () => {
      const panel = supplementary.querySelector('.oof-dashboard-filters');
      if (panel) { panel.open = true; panel.scrollIntoView({block: 'start', behavior: 'smooth'}); panel.querySelector('input[type="search"]')?.focus({preventScroll: true}); }
    });
    document.querySelector('.oof-incident-header')?.append(search);
    const dataTime = document.getElementById('incident-data-time');
    if (dataTime) supplementary.append(dataTime);
  }
}

function renderDashboardCharts(aggregations, summary) {
  const trends = (aggregations.trends || []).filter((item) => /^\d{4}-\d{2}$/.test(item.period));
  const trend = document.querySelector('.oof-dashboard-trend');
  if (trend) {
    const values = trends.slice(-6);
    const bars = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    bars.classList.add('oof-trend-line');
    bars.setAttribute('viewBox', '0 0 240 65');
    bars.setAttribute('role', 'img');
    bars.setAttribute('aria-label', values.map((item) => `${item.period}: ${item.total}`).join(', '));
    const max = Math.max(1, ...values.map((item) => item.total));
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    line.setAttribute('points', values.map((item, index) => `${values.length > 1 ? index * 240 / (values.length - 1) : 0},${60 - item.total / max * 52}`).join(' '));
    bars.append(line);
    trend.querySelector('p, .oof-trend-line')?.replaceWith(bars);
    trend.title = 'Monthly event dates in the public dataset; records without dates are excluded.';
  }
  const panel = document.querySelector('.oof-dashboard-severity');
  if (panel) {
    const values = ['critical', 'high', 'moderate', 'low'].map((key) => ({key, count: trends.reduce((sum, row) => sum + Number(row[key] || 0), 0)}));
    const classified = values.reduce((sum, item) => sum + item.count, 0);
    let offset = 0;
    const colors = ['#e9a46d', '#3172b6', '#6ea4de', '#bdd3e9'];
    const stops = values.map((item, index) => {
      const start = offset;
      offset += classified ? item.count / classified * 100 : 0;
      return `${colors[index]} ${start}% ${offset}%`;
    });
    const chart = element('div', 'oof-severity-chart');
    const donut = element('div', 'oof-severity-donut');
    donut.style.background = classified ? `conic-gradient(${stops.join(',')})` : '#aaa';
    const center = element('div', 'oof-severity-center');
    center.append(element('strong', '', String(classified)), element('span', '', 'dated records'));
    donut.append(center);
    const legend = element('ul', 'oof-severity-legend');
    values.forEach((item, index) => {
      const row = document.createElement('li');
      const swatch = document.createElement('i');
      swatch.style.backgroundColor = colors[index];
      row.append(swatch, element('span', '', item.key[0].toUpperCase() + item.key.slice(1)), element('b', '', String(item.count)));
      legend.append(row);
    });
    chart.append(donut, legend);
    panel.querySelector('p, .oof-severity-chart')?.replaceWith(chart);
    let note = panel.querySelector('.oof-chart-note');
    if (!note) { note = element('p', 'oof-chart-note'); panel.append(note); }
    note.textContent = `${classified} of ${summary.totalIncidents} public records have both an event month and a listed severity.`;
  }
}

function renderDailyTrend(items, generatedAt) {
  const panel = document.querySelector('.oof-dashboard-trend');
  const exportDate = new Date(generatedAt || '');
  if (!panel || Number.isNaN(exportDate.valueOf())) return;
  const end = Date.UTC(exportDate.getUTCFullYear(), exportDate.getUTCMonth(), exportDate.getUTCDate());
  const day = 86400000;
  const counts = Array(30).fill(0);
  items.forEach((item) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(item.occurredAt || '')) return;
    const date = Date.parse(`${item.occurredAt}T00:00:00Z`);
    const index = 29 - Math.round((end - date) / day);
    if (index >= 0 && index < 30) counts[index] += 1;
  });
  const heading = panel.querySelector('h2');
  if (heading) heading.textContent = '30-Day Trend';
  const chart = panel.querySelector('.oof-trend-line');
  const line = chart?.querySelector('polyline');
  const max = Math.max(1, ...counts);
  if (line) line.setAttribute('points', counts.map((count, index) => `${index * 240 / 29},${60 - count / max * 52}`).join(' '));
  const total = counts.reduce((sum, count) => sum + count, 0);
  const dateLabel = exportDate.toISOString().slice(0, 10);
  const disclosure = `${total} records with an event date in the 30 days ending ${dateLabel}. Event dates are not the same as publication dates; recent events may be missing.`;
  panel.title = disclosure;
  chart?.setAttribute('aria-label', disclosure);
  let note = panel.querySelector('.oof-trend-note');
  if (!note) { note = element('p', 'oof-trend-note'); panel.append(note); }
  note.textContent = `${total} dated events · through ${dateLabel}`;
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
    renderDashboardCharts(aggregations, summary);
    loadWorkflowStatus(signal);
    let result = page;
    if (requiresSearchProjection()) {
      const search = await repository.search(signal);
      result = { ...search, page: requestedPage, pageSize: 25 };
    }
    if (signal.aborted) return;
    await renderRoute(result, mapData, aggregations, architectureLinks, signal);
    if (signal.aborted) return;
    setState("success", "Public incident dataset loaded.");
    if (view === 'dashboard') {
      repository.search(signal).then((data) => {
        if (!signal.aborted) renderDailyTrend(data.items || [], summary.generatedAt);
      }).catch((error) => {
        if (error.name !== 'AbortError') console.warn('Daily trend unavailable; showing monthly trend.', error);
      });
    }
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
    if (link.dataset.fixedTarget) return;
    const target = new URL(link.href, location.origin);
    if (target.pathname === route) link.setAttribute("aria-current", "page");
    target.search = target.pathname === '/ai-incidents/' ? '' : params.toString();
    target.searchParams.delete("page");
    link.href = target.pathname + target.search;
  });
}

function requiresSearchProjection() {
  return ["critical", "stress-tests"].includes(view)
    || ["q", "severity", "eventType", "analysisStatus", "reviewStatus", "evidenceStatus", "source", "country", "architecture", "dateFrom", "dateTo", "lens", "domain", "component", "mechanism", "prevention"].some((key) => params.get(key));
}

async function renderRoute(result, mapData, aggregations, architectureLinks, signal) {
  const showMap = view === "dashboard" || view === "map";
  const aggregateViews = ["architectures", "industries", "countries", "trends"];
  mapPane.hidden = !showMap;
  analysisView.hidden = !aggregateViews.includes(view);
  listPane.hidden = aggregateViews.includes(view) && !params.get("architecture") && !params.get("country");
  let items = applyFilters(result.items || []);
  if (view === "critical") items = items.filter((item) => item.severity === "Critical");
  if (view === "stress-tests") items = items.filter((item) => item.assessment?.oofApproved === true);
  const viewAggregations = aggregateViews.includes(view) && requiresSearchProjection() ? filteredAggregations(items) : aggregations;
  if (view === "architectures") renderArchitectures(viewAggregations.architectures, architectureLinks);
  if (view === "industries") renderIndustries(viewAggregations.industries, viewAggregations.scopeNotice);
  if (view === "countries") renderCountries(viewAggregations.geography, viewAggregations.scopeNotice);
  if (view === "trends") renderTrends(viewAggregations.trends, viewAggregations.scopeNotice);
  if (showMap) {
    const geography = requiresSearchProjection() ? filteredGeography(items) : aggregations.geography;
    const visibleMap = requiresSearchProjection() ? { countries: geography.countries.map((country) => ({ ...country, incidentCount: country.count })) } : mapData;
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    await renderMap(visibleMap, signal);
    if (signal.aborted) return;
    renderGeographySummary(geography);
    renderCountryTable(geography.countries, true);
  }
  if (view === "dashboard" && params.get("lens")) {
    analysisView.hidden = false;
    renderIncidentLens(items, params.get("lens"));
  }
  const locallyPaged = requiresSearchProjection();
  renderIncidents(items, architectureLinks, {
    page: Math.max(1, Number(params.get("page")) || 1),
    pageSize: result.pageSize || 25,
    total: locallyPaged ? items.length : result.total,
    locallyPaged,
  });
}

function filteredAggregations(items) {
  const industries = new Map(), architectures = new Map(), trends = new Map();
  items.forEach((item) => {
    const industry = item.industry || "Industry not specified";
    industries.set(industry, (industries.get(industry) || 0) + 1);
    const addArchitecture = (architecture, role) => {
      if (!architecture?.architectureId) return;
      const row = architectures.get(architecture.architectureId) || { architectureId: architecture.architectureId, label: architecture.label, canonicalUrl: architecture.canonicalUrl, primary: 0, contributing: 0, methodologyReferences: "Not available" };
      row[role] += 1;
      architectures.set(architecture.architectureId, row);
    };
    addArchitecture(item.primaryArchitecture, "primary");
    (item.contributingArchitectures || []).forEach((architecture) => addArchitecture(architecture, "contributing"));
    const period = item.occurredAt ? item.occurredAt.slice(0, 7) : "Date not specified";
    const trend = trends.get(period) || { period, total: 0, critical: 0, high: 0, moderate: 0, low: 0 };
    trend.total += 1;
    const severity = String(item.severity || "").toLowerCase();
    if (["critical", "high", "moderate", "low"].includes(severity)) trend[severity] += 1;
    trends.set(period, trend);
  });
  return { geography: filteredGeography(items), industries: [...industries].map(([industry, count]) => ({industry, count})).sort((a, b) => b.count - a.count), architectures: [...architectures.values()], trends: [...trends.values()].sort((a, b) => a.period.localeCompare(b.period)), scopeNotice: "Counts describe filtered public records, not global prevalence or architecture quality." };
}

function filteredGeography(items) {
  const countries = new Map();
  items.forEach((item) => {
    if (!item.countryCode) return;
    const row = countries.get(item.countryCode) || { countryCode: item.countryCode, country: item.country || item.countryCode, count: 0, critical: 0 };
    row.count += 1;
    if (item.severity === "Critical") row.critical += 1;
    countries.set(item.countryCode, row);
  });
  const assigned = [...countries.values()].reduce((total, row) => total + row.count, 0);
  return { total: items.length, geographicallyAssigned: assigned, locationNotSpecified: items.length - assigned, countries: [...countries.values()].sort((a, b) => b.count - a.count || a.country.localeCompare(b.country)) };
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
    if (error.name === "AbortError") throw error;
    console.warn("Architecture links are temporarily unavailable.", error);
    return new Map();
  }
}

function renderSummary(summary) {
  document.querySelectorAll("[data-metric]").forEach((element) => {
    const value = summary[element.dataset.metric];
    element.textContent = Number.isFinite(Number(value)) ? Number(value).toLocaleString("en") : "—";
    if (element.dataset.metric === "architecturesExposed" && element.previousElementSibling) element.previousElementSibling.textContent = "Architectures identified for review";
    if (element.dataset.metric === "incidentsThisMonth") {
      const generated = new Date(summary.generatedAt || "");
      const now = new Date();
      if (Number.isNaN(generated.valueOf()) || generated.getUTCFullYear() !== now.getUTCFullYear() || generated.getUTCMonth() !== now.getUTCMonth()) {
        element.textContent = "Unavailable (outdated export)";
      }
      if (!Number.isNaN(generated.valueOf()) && now - generated > 36 * 3600000) element.textContent = "Unavailable (outdated export)";
      if (element.previousElementSibling) element.previousElementSibling.textContent = "Record timestamps this month (UTC)";
      element.title = "Source record timestamps in the UTC calendar month of the public export; these may reflect source updates, not incident occurrence or first publication.";
    }
  });
  const operational = summary.operationalStatus || {};
  document.getElementById("incident-data-time").textContent = operational.lastSuccessfulSourceCheck
    ? `Last successful source check ${formatTimestamp(operational.lastSuccessfulSourceCheck)} · Latest public export ${formatTimestamp(operational.latestPublicExport || summary.generatedAt)}`
    : summary.generatedAt
      ? `Public dataset updated ${formatTimestamp(summary.generatedAt)}`
      : "Public dataset synchronization time is unavailable";
  renderOperationalStatus(operational);
  const transparency = summary.sourceTransparency || {};
  const sourcePanel = document.querySelector('.oof-dashboard-sources');
  if (sourcePanel) {
    const list = document.createElement('ul');
    const publishers = transparency.publishers || [];
    publishers.forEach((publisher) => {
      const row = document.createElement('li');
      const name = element('span', 'oof-source-name', publisher);
      row.append(name);
      if (publishers.length === 1 && Number.isFinite(Number(summary.totalIncidents))) {
        const count = element('strong', 'oof-source-count', Number(summary.totalIncidents).toLocaleString('en'));
        count.title = 'Public records attributed to this publisher';
        row.append(count);
      }
      list.append(row);
    });
    if (!publishers.length) {
      const row = document.createElement('li');
      row.textContent = 'Source information unavailable';
      list.append(row);
    }
    sourcePanel.querySelector('ul, p')?.replaceWith(list);
  }
  const sourceSelect = document.querySelector('#incident-filters select[name="source"]');
  if (sourceSelect) {
    const selected = params.get("source") || "";
    sourceSelect.replaceChildren(new Option("All", ""));
    (transparency.publishers || []).forEach((publisher) => sourceSelect.add(new Option(publisher, publisher)));
    sourceSelect.value = selected;
  }
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
    ["Source freshness", formatFreshness(status.sourceFreshness, status.latestSourceSnapshot)],
    ["Newly published incidents", Number(status.newlyPublishedIncidents || 0).toLocaleString("en")],
    ["Pending candidates", Number(status.pendingCandidateCount || 0).toLocaleString("en")],
    ["Last run recorded in export", `${status.runStatus || "not recorded"} (later runs may not be reflected)`],
    ["Latest GitHub workflow run", "Checking GitHub Actions…"],
    ["Most recent unsuccessful run (last 20)", "Checking GitHub Actions…"],
  ];
  target.replaceChildren();
  rows.forEach(([label, value]) => {
    const group = document.createElement("div");
    const detail = element("dd", "", value);
    if (label === "Latest GitHub workflow run") detail.id = "incident-live-workflow";
    if (label === "Most recent unsuccessful run (last 20)") detail.id = "incident-live-failure";
    group.append(element("dt", "", label), detail);
    target.append(group);
  });
}

async function loadWorkflowStatus(signal) {
  const latestTarget = document.getElementById("incident-live-workflow");
  const failedTarget = document.getElementById("incident-live-failure");
  if (!latestTarget || !failedTarget) return;
  try {
    const url = "https://api.github.com/repos/originopenfoundation/OOF-Origin-Open-Foundation-/actions/workflows/ai-incident-daily-sync.yml/runs?branch=main1&per_page=20";
    const response = await fetch(url, { signal, headers: { Accept: "application/vnd.github+json" } });
    if (!response.ok) throw new Error(`Workflow status request failed (${response.status})`);
    const runs = (await response.json()).workflow_runs || [];
    const describe = (run) => run ? `${run.conclusion || run.status || "unknown"} · ${formatTimestamp(run.created_at)}` : "No recorded run in the latest 20";
    latestTarget.textContent = describe(runs[0]);
    failedTarget.textContent = describe(runs.find((run) => ["failure", "timed_out", "cancelled"].includes(run.conclusion)));
  } catch (error) {
    if (error.name === "AbortError") return;
    latestTarget.textContent = "Unavailable; GitHub status could not be checked";
    failedTarget.textContent = "Unavailable; GitHub status could not be checked";
  }
}

function formatFreshness(freshness, snapshotUrl) {
  if (!freshness) return "not recorded";
  const dateMatch = String(snapshotUrl || "").match(/(20\d{2})(\d{2})(\d{2})/);
  const timestamp = Date.parse(freshness.snapshotDate || (dateMatch ? `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}T00:00:00Z` : ""));
  if (Number.isFinite(timestamp)) {
    const hours = Math.max(0, Math.floor((Date.now() - timestamp) / 3600000));
    return `${hours > freshness.sloHours ? "Older than expected: " : ""}${hours} hours old (weekly snapshot; alert after ${freshness.sloHours} hours). A successful check does not guarantee a newer export exists.`;
  }
  if (Number.isFinite(freshness.snapshotAgeHours)) return `at export: ${freshness.snapshotAgeHours} hours old; current age unavailable`;
  return "snapshot date unavailable";
}

function incidentCountColor(country) {
  const count = Number(country?.incidentCount || 0);
  if (count >= 51) return "#2162a8";
  if (count >= 21) return "#4c88ce";
  if (count >= 6) return "#80aee0";
  if (count >= 1) return "#b3d0ee";
  return "#b5c0c8";
}

async function renderMap(mapData, signal) {
  const mapElement = document.getElementById("incident-map");
  mapElement?.setAttribute("aria-busy", "true");
  if (leafletMap) {
    leafletMap.invalidateSize();
    mapElement?.setAttribute("aria-busy", "false");
    return;
  }
  const map = L.map("incident-map", { minZoom: 0, maxZoom: 7, zoomSnap: 0.25, worldCopyJump: true, attributionControl: false, scrollWheelZoom: false });
  leafletMap = map;
  const resetMap = () => {
    map.invalidateSize({ pan: false });
    map.fitBounds([[-58, -170], [78, 180]], { padding: [8, 8], animate: false });
  };
  const resetControl = L.Control.extend({
    options: { position: 'topleft' },
    onAdd() {
      const container = L.DomUtil.create('div', 'leaflet-bar oof-map-reset');
      const button = L.DomUtil.create('button', '', container);
      button.type = 'button';
      button.textContent = '↺';
      button.title = 'Reset map view';
      button.setAttribute('aria-label', 'Reset map view');
      L.DomEvent.disableClickPropagation(container);
      L.DomEvent.on(button, 'click', resetMap);
      return container;
    },
  });
  map.addControl(new resetControl());
  const countryByCode = new Map(mapData.countries.map((country) => [country.countryCode, country]));
  const response = await fetch("/assets/data/ne_50m_admin_0_countries.geojson", { signal });
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
  requestAnimationFrame(resetMap);
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
    navigate(Object.fromEntries(query.entries()), false, true);
  });
  form.addEventListener("reset", (event) => {
    event.preventDefault();
    navigate({}, true, true);
  });
  window.addEventListener("popstate", () => {
    params = new URLSearchParams(location.search);
    markCurrentView();
    setFilterFormValues(form);
    start();
  });
}

function setFilterFormValues(form) {
  [...form.elements].forEach((control) => { if (control.name) control.value = params.get(control.name) || ""; });
}

function navigate(changes, replace = false, clear = false) {
  const query = new URLSearchParams(clear ? "" : location.search);
  Object.entries(changes).forEach(([key, value]) => {
    if (value === null || value === "") query.delete(key);
    else query.set(key, value);
  });
  const next = `${location.pathname}${query.toString() ? `?${query}` : ""}`;
  history[replace ? "replaceState" : "pushState"]({}, "", next);
  params = new URLSearchParams(query);
  markCurrentView();
  const form = document.getElementById("incident-filters");
  if (form) setFilterFormValues(form);
  start();
}

function applyFilters(items) {
  let result = [...items];
  const query = (params.get("q") || "").toLowerCase();
  if (query) result = result.filter((item) => {
    const text = `${item.id || ""} ${item.searchText || ""}`.toLowerCase();
    const normalizedIdQuery = query.replace(/[^a-z0-9]/g, "");
    return text.includes(query) || (normalizedIdQuery.length >= 4 && String(item.id || "").toLowerCase().replace(/[^a-z0-9]/g, "").includes(normalizedIdQuery));
  });
  if (params.get("severity")) result = result.filter((item) => item.severity === params.get("severity"));
  if (params.get("eventType")) result = result.filter((item) => item.eventType === params.get("eventType"));
  if (params.get("analysisStatus")) result = result.filter((item) => item.assessment?.analysisStatus === params.get("analysisStatus"));
  if (params.get("reviewStatus")) result = result.filter((item) => item.assessment?.reviewStatus === params.get("reviewStatus"));
  if (params.get("evidenceStatus")) result = result.filter((item) => item.assessment?.evidenceStatus === params.get("evidenceStatus"));
  if (params.get("source")) result = result.filter((item) => item.source?.publisher === params.get("source"));
  if (params.get("country")) result = result.filter((item) => item.countryCode === params.get("country"));
  if (params.get("domain")) result = result.filter((item) => (item.systemFailure?.domains || []).includes(params.get("domain")));
  if (params.get("component")) result = result.filter((item) => (item.systemFailure?.components || []).includes(params.get("component")));
  if (params.get("mechanism")) result = result.filter((item) => (item.systemFailure?.candidateMechanisms || []).includes(params.get("mechanism")));
  if (params.get("prevention")) result = result.filter((item) => Boolean(item.preventionPreview?.conditionalIdeaAvailable) === (params.get("prevention") === "conditional"));
  if (params.get("excludeDisputed") === "1") result = result.filter((item) => item.assessment?.evidenceStatus !== "Contradicted / Disputed");
  if (params.get("dateFrom")) result = result.filter((item) => item.occurredAt && item.occurredAt.slice(0, 10) >= params.get("dateFrom"));
  if (params.get("dateTo")) result = result.filter((item) => item.occurredAt && item.occurredAt.slice(0, 10) <= params.get("dateTo"));
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
  analysisView.replaceChildren(viewIntro("Incident trends", `${notice} Periods use event occurrence dates only; records without an occurrence date are excluded from this table.`));
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

function renderIncidentLens(items, lens) {
  const counts = new Map();
  const add = (key) => counts.set(key, (counts.get(key) || 0) + 1);
  if (lens === "systems") {
    items.forEach((item) => (item.systemFailure?.components || []).forEach(add));
    analysisView.replaceChildren(viewIntro("System components", "Indicators are drawn from source descriptions and are not confirmed causes."));
  } else if (lens === "patterns") {
    items.forEach((item) => {
      if (item.assessment?.evidenceStatus === "Contradicted / Disputed") return;
      (item.systemFailure?.domains || []).forEach((domain) => (item.systemFailure?.components || []).forEach((component) => (item.systemFailure?.candidateMechanisms || []).forEach((mechanism) => add(`${domain} | ${component} | ${mechanism}`))));
    });
    analysisView.replaceChildren(viewIntro("Candidate recurring contexts", "Shared domain, component and source-language mechanism are leads for review, not evidence of a recurring failure or shared root cause."));
  } else if (lens === "timeline" || lens === "yearly") {
    items.forEach((item) => add(item.occurredAt ? item.occurredAt.slice(0, lens === "yearly" ? 4 : 7) : "Event date unknown"));
    analysisView.replaceChildren(viewIntro("Event timeline", "Counts are reports in this dataset, not real-world failure rates. Unknown event dates remain separate."));
  } else if (lens === "architectures") {
    items.forEach((item) => [item.primaryArchitecture, ...(item.contributingArchitectures || [])].filter(Boolean).forEach((architecture) => add(`${architecture.architectureId} | ${architecture.label}`)));
    analysisView.replaceChildren(viewIntro("Architecture relevance", "Automated relevance is provisional and does not establish a violation or governance failure."));
  } else if (lens === "prevention") {
    items.forEach((item) => add(item.preventionPreview?.conditionalIdeaAvailable ? "Conditional idea available" : "Evidence review needed"));
    analysisView.replaceChildren(viewIntro("Prevention and verification", "Conditional ideas are not confirmed causes, approved controls, or guarantees of protection."));
  } else {
    analysisView.hidden = true;
    return;
  }
  const rows = [...counts.entries()].filter(([, count]) => lens !== "patterns" || count > 1)
    .sort((a, b) => ["timeline", "yearly"].includes(lens) ? b[0].localeCompare(a[0]) : b[1] - a[1] || a[0].localeCompare(b[0]));
  if (!rows.length) {
    analysisView.append(element("p", "", "No supported entries for the selected filters."));
    return;
  }
  const list = element("div", "oof-bar-list");
  rows.forEach(([label, count]) => {
    const row = element("div", "oof-bar-row");
    const action = element("a", "", label);
    if (lens === "patterns") {
      const [domain, component, mechanism] = label.split(" | ");
      action.href = queryLink({ domain, component, mechanism, excludeDisputed: "1", lens: null, page: null });
    } else if (lens === "systems") action.href = queryLink({ component: label, lens: null, page: null });
    else if (lens === "architectures") action.href = queryLink({ architecture: label.split(" | ")[0], lens: null, page: null });
    else if (lens === "prevention") action.href = queryLink({ prevention: label === "Conditional idea available" ? "conditional" : "pending", lens: null, page: null });
    else {
      action.textContent = label;
      if (label !== "Event date unknown") {
        if (lens === "yearly") action.href = queryLink({ dateFrom: `${label}-01-01`, dateTo: `${label}-12-31`, lens: null, page: null });
        else {
          const [year, month] = label.split("-").map(Number);
          const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
          action.href = queryLink({ dateFrom: `${label}-01`, dateTo: `${label}-${String(last).padStart(2, "0")}`, lens: null, page: null });
        }
      }
    }
    row.append(action, element("b", "", count));
    list.append(row);
  });
  analysisView.append(list);
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
  let visibleItems = options.locallyPaged ? items.slice((currentPage - 1) * options.pageSize, currentPage * options.pageSize) : items;
  const overviewPreview = view === 'dashboard' && !requiresSearchProjection() && currentPage === 1;
  if (overviewPreview) visibleItems = visibleItems.slice(0, 1);
  document.getElementById("incident-result-count").textContent = `${options.total} public record${options.total === 1 ? "" : "s"}`;
  list.replaceChildren();
  empty.hidden = options.total > 0;
  visibleItems.forEach((incident) => list.append(createIncidentCard(incident, architectureLinks)));
  if (!overviewPreview && options.total > options.pageSize) list.append(createPagination(currentPage, pageCount));
}

function createIncidentCard(incident, architectureLinks) {
  const article = element("article", "oof-incident-row");
  if (view === 'dashboard') {
    const visual = element('div', 'oof-incident-card-visual');
    visual.setAttribute('aria-hidden', 'true');
    article.append(visual);
  }
  const headingBlock = element("div", "oof-incident-card-main");
  const eyebrow = element("p", "oof-incident-card-eyebrow");
  eyebrow.append(
    element("span", "oof-incident-id", incident.id),
    element("span", "", incident.industry || "Industry not specified"),
    element("span", "", incident.country || "Location not specified"),
    element("time", "", incident.occurredAt ? `Event: ${incident.occurredAt.slice(0, 10)}` : incident.reportedAt ? `Record timestamp: ${incident.reportedAt.slice(0, 10)} (event date unknown)` : "Event date unknown"),
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
  const architecture = incident.assessment?.available ? incident.primaryArchitecture : null;
  const architectureUrl = architectureLinks.get(String(architecture?.architectureId || "").toLowerCase()) || architecture?.canonicalUrl;
  const architectureLine = element('p', 'oof-card-architecture');
  architectureLine.append(element('span', '', 'Architecture: '));
  if (architectureUrl) {
    const link = element('a', '', architecture?.label || architecture?.architectureId?.toUpperCase());
    link.href = architectureUrl;
    architectureLine.append(link);
  } else architectureLine.append(document.createTextNode('Undetermined'));
  headingBlock.append(architectureLine);
  const focusHeading = element("h4", "", "Intelligence governance focus");
  const focus = element("p", "");
  if (architectureUrl) {
    const link = element("a", "", architecture?.label || architecture?.architectureId?.toUpperCase());
    link.href = architectureUrl;
    focus.append(link);
  } else focus.textContent = "Architecture undetermined";
  const assignment = element("p", "oof-incident-card-assignment", `Assignment: ${incident.assessment?.coverage || "Review required"}`);
  const insight = element("p", "oof-incident-card-insight", incident.governanceInsight || "Available evidence does not yet support a case-specific governance conclusion.");
  const systemFailure = incident.systemFailure || {};
  const component = element("p", "oof-incident-card-component", `System component: ${systemFailure.component || "Not established"}`);
  const mechanism = element("p", "oof-incident-card-mechanism", systemFailure.mechanismStatus === "NOT_CONFIRMED" || !systemFailure.mechanismStatus
    ? "Failure mechanism not established."
    : `Failure mechanism status: ${systemFailure.mechanismStatus}`);
  intelligence.append(focusHeading, focus, assignment, component, mechanism, insight);

  const preview = incident.preventionPreview || {};
  const prevention = element("ol", "oof-incident-prevention-preview");
  const conditional = Boolean(preview.conditionalIdeaAvailable);
  [
    ["Could this happen?", preview.applicability],
    [conditional ? "Conditional control idea" : "Evidence needed before control selection", preview.control],
    [conditional ? "Conditional verification idea" : "Evidence review", preview.verification && preview.verification !== preview.control ? preview.verification : "Verification procedure not established."],
  ].forEach(([label, value]) => {
    const row = document.createElement("li");
    row.append(element("b", "", label), element("span", "", value || "Prevention analysis pending sufficient evidence."));
    prevention.append(row);
  });
  const actions = element("div", "oof-incident-card-actions");
  const makeDisclosure = (label, content) => {
    const section = element('details', 'oof-card-disclosure');
    section.append(element('summary', '', label), content);
    return section;
  };
  actions.append(makeDisclosure('Analysis', intelligence), makeDisclosure('Prevention', prevention));
  const verification = element('div', 'oof-card-verification');
  verification.append(element('p', '', preview.verification || 'Verification procedure not established.'));
  const verify = element("a", "oof-incident-secondary-action", "Help verify / Submit evidence");
  verify.href = incident.verifyUrl || `/ai-incidents/verify/?incident=${encodeURIComponent(incident.slug)}`;
  verification.append(verify);
  actions.append(makeDisclosure('Verification', verification));
  const detailAction = element("a", "oof-incident-primary-action", "Details");
  detailAction.href = incident.detailUrl;
  actions.append(detailAction);
  headingBlock.append(actions);
  article.append(headingBlock);
  return article;
}

function incidentDefinitionList(incident, architectureLinks) {
  const list = document.createElement("dl");
  [["Event date", (incident.occurredAt || "Unknown").slice(0, 10)], ["Record timestamp (may be source update)", (incident.reportedAt || "Unknown").slice(0, 10)], ["Country", incident.country || "Location not specified"], ["Severity", incident.severity || "Insufficient evidence"]].forEach(([term, value]) => {
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
