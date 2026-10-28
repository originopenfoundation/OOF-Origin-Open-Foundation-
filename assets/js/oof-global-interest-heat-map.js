(function () {
  "use strict";

  const COLORS = { "very-high": "#167a45", high: "#167a45", moderate: "#2468b4", emerging: "#d6a51f", insufficient: "#a3a3a3" };
  const STATUS_LABELS = { "very-high": "High Interest", high: "High Interest", moderate: "Moderate Interest", emerging: "Emerging Interest", insufficient: "Insufficient Signal" };
  const MOMENTUM_LABELS = { "rapidly-rising": "Rapidly rising", rising: "Rising", stable: "Stable", declining: "Declining" };
  const PUBLIC_STATUS_ORDER = { "very-high": 0, high: 1, moderate: 2, emerging: 3, insufficient: 4 };
  const WORLD_BOUNDS = [[-58, -180], [84, 180]];
  const STALE_AFTER_MS = 36 * 60 * 60 * 1000;
  const SHORT_COUNTRY_NAMES = { CN: "China", US: "USA" };
  const regionNames = typeof Intl.DisplayNames === "function" ? new Intl.DisplayNames(["en"], { type: "region" }) : null;

  const container = document.getElementById("global-interest-globe");
  const fallback = document.getElementById("global-interest-fallback");
  const select = document.getElementById("global-interest-country-select");
  const countryList = document.getElementById("global-interest-country-list");
  const card = document.getElementById("global-interest-country-card");
  const countryName = document.getElementById("global-interest-country-name");
  const countryStatus = document.getElementById("global-interest-country-status");
  const countryMomentum = document.getElementById("global-interest-country-momentum");
  const viewControls = document.querySelector(".oof-global-interest-view-controls");
  const dataModeControls = document.querySelector(".oof-global-interest-data-mode");
  const mapTitle = document.getElementById("global-interest-map-title");
  const viewNotice = document.getElementById("global-interest-view-notice");
  const updated = document.getElementById("global-interest-updated");
  const dataWindow = document.getElementById("global-interest-window");
  const dataSource = document.getElementById("global-interest-source");
  const staleWarning = document.getElementById("global-interest-stale-warning");
  if (!container || !select || !card) return;

  let map;
  let selectedEntry = null;
  let selectedFeature = null;
  let hoveredFeature = null;
  let countryLayers = [];
  let labelLayers = [];
  let catalog = new Map();
  let activeDataset = null;
  let activeWorld = null;
  let interestView = "raw";
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const precisePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  function countryCode(feature) {
    const properties = feature && feature.properties ? feature.properties : {};
    const candidates = [properties.ISO_A2_EH, properties.ISO_A2];
    return String(candidates.find(code => code && code !== "-99") || "").toUpperCase();
  }

  function countryLabel(feature) {
    const properties = feature && feature.properties ? feature.properties : {};
    return properties.NAME_EN || properties.ADMIN || properties.NAME_LONG || properties.NAME || "Unknown country";
  }

  function shortCountryLabel(name, iso) { return SHORT_COUNTRY_NAMES[iso] || name; }

  function labelForIso(iso) {
    try { return SHORT_COUNTRY_NAMES[iso] || (regionNames && regionNames.of(iso)) || iso; }
    catch (_) { return SHORT_COUNTRY_NAMES[iso] || iso; }
  }

  function featureCenter(feature) {
    const properties = feature && feature.properties ? feature.properties : {};
    const lat = Number(properties.LABEL_Y);
    const lng = Number(properties.LABEL_X);
    return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null;
  }

  function isTinyFeature(feature) { return Number((feature && feature.properties ? feature.properties : {}).TINY) > 0; }

  function flagFor(iso) {
    if (!/^[A-Z]{2}$/.test(iso)) return "";
    return String.fromCodePoint(...iso.split("").map(letter => 127397 + letter.charCodeAt(0)));
  }

  function stateForFeature(feature) { return feature.__oofInterest || { status: "insufficient" }; }

  function viewDefinition(dataset = activeDataset) {
    return dataset && dataset.trafficViews ? dataset.trafficViews[interestView] : null;
  }

  function countriesForView(dataset) {
    const definition = viewDefinition(dataset);
    return interestView === "raw" && definition && definition.countryData === "countries" ? dataset.countries || [] : definition && Array.isArray(definition.countries) ? definition.countries : [];
  }

  function applyViewPresentation() {
    const definition = viewDefinition();
    const available = definition && definition.status === "available";
    if (mapTitle) mapTitle.textContent = `OOF® Global Interest Heat Map™ — ${definition ? definition.label : "Traffic Map"}`;
    if (viewNotice) viewNotice.textContent = available
      ? definition.description
      : definition && definition.reason ? definition.reason : "This traffic quality view is unavailable.";
    if (dataModeControls) dataModeControls.querySelectorAll("button[data-interest-view]").forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.interestView === interestView));
    });
  }

  function escapeHtml(value) {
    const span = document.createElement("span");
    span.textContent = value;
    return span.innerHTML;
  }

  function showCountry(entry) {
    if (!entry) {
      countryName.textContent = "Select a country";
      countryStatus.textContent = "Interest classification will appear here.";
      countryMomentum.hidden = true;
      return;
    }
    const flag = flagFor(entry.iso);
    countryName.textContent = `${flag ? `${flag} ` : ""}${entry.name}`;
    if (viewDefinition() && viewDefinition().status !== "available") {
      countryStatus.textContent = "Quality-adjusted classification is unavailable pending sufficient documented evidence.";
      countryMomentum.hidden = true;
      return;
    }
    countryStatus.textContent = `Interest: ${STATUS_LABELS[entry.state.status] || STATUS_LABELS.insufficient}`;
    if (entry.state.momentum && MOMENTUM_LABELS[entry.state.momentum]) {
      countryMomentum.textContent = `Momentum: ${MOMENTUM_LABELS[entry.state.momentum]}`;
      countryMomentum.hidden = false;
    } else {
      countryMomentum.hidden = true;
    }
  }

  function countryStyle(feature) {
    const state = stateForFeature(feature);
    const highlighted = feature === selectedFeature || feature === hoveredFeature;
    const activeTiny = isTinyFeature(feature) && state.status !== "insufficient";
    return { color: highlighted ? "#ffffff" : "rgba(255,255,255,0.68)", weight: feature === selectedFeature ? 3.4 : highlighted ? 2.4 : activeTiny ? 3 : 0.7, opacity: 1, fillColor: COLORS[state.status] || COLORS.insufficient, fillOpacity: state.status === "insufficient" ? 0.7 : 0.92 };
  }

  function validDate(value) {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function readableDate(value) {
    const parsed = validDate(value);
    return parsed ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(parsed) + " UTC" : "Unavailable";
  }

  function applyFreshness(dataset) {
    const retrieved = validDate(dataset.lastSuccessfulCloudflareRetrievalAt || dataset.lastCheckedAt);
    if (updated) { updated.dateTime = retrieved ? retrieved.toISOString() : ""; updated.textContent = readableDate(retrieved); }
    const start = validDate(dataset.windowStart);
    const end = validDate(dataset.windowEnd);
    if (dataWindow) {
      const formatter = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" });
      dataWindow.textContent = start && end ? `Rolling 14 days: ${formatter.format(start)} to ${formatter.format(end)}` : "Rolling 14 days";
    }
    if (dataSource) dataSource.textContent = dataset.source || "Cloudflare Web Analytics";
    if (staleWarning) staleWarning.hidden = !retrieved || Date.now() - retrieved.getTime() <= STALE_AFTER_MS;
  }

  function refreshHighlights() { countryLayers.forEach(({ feature, layer }) => layer.setStyle(countryStyle(feature))); }

  function selectCountry(entry, focus) {
    selectedEntry = entry;
    selectedFeature = entry && entry.feature ? entry.feature : null;
    showCountry(entry);
    select.value = entry ? entry.iso : "";
    if (countryList) countryList.querySelectorAll(".oof-global-interest-country-option").forEach(button => button.setAttribute("aria-pressed", String(Boolean(entry) && button.dataset.countryIso === entry.iso)));
    refreshHighlights();
    if (!map || !entry || !entry.feature || !focus) return;
    const center = featureCenter(entry.feature);
    if (center) map.flyTo(center, Math.max(map.getZoom(), isTinyFeature(entry.feature) ? 8 : 4), { animate: !reducedMotion, duration: reducedMotion ? 0 : 0.55 });
  }

  function minimumLabelZoom(feature) {
    if (isTinyFeature(feature) && stateForFeature(feature).status !== "insufficient") return 1;
    const properties = feature.properties || {};
    const sourceZoom = Number(properties.MIN_LABEL);
    const rank = Number(properties.LABELRANK);
    const suggested = Number.isFinite(sourceZoom) && sourceZoom > 0 ? sourceZoom : rank;
    return Math.max(3, Math.min(6, Number.isFinite(suggested) ? suggested : 5));
  }

  function createLabel(feature, minimumZoom, maximumZoom, callout) {
    const center = featureCenter(feature);
    if (!center) return;
    const iso = countryCode(feature);
    const state = stateForFeature(feature);
    const icon = L.divIcon({
      className: `oof-country-label-marker${callout ? ` is-tiny-callout is-${state.status}` : ""}`,
      html: `<span>${escapeHtml(shortCountryLabel(countryLabel(feature), iso))}</span>`,
      iconSize: callout ? [140, 32] : null,
      iconAnchor: callout ? [0, 16] : undefined
    });
    const marker = L.marker(center, { icon, interactive: Boolean(callout), keyboard: Boolean(callout), title: callout ? `Show ${countryLabel(feature)}` : undefined });
    if (callout) marker.on("click", () => selectCountry(catalog.get(iso), true));
    labelLayers.push({ minimumZoom, maximumZoom, layer: marker });
  }

  function updateLabels() {
    if (!map) return;
    const zoom = map.getZoom();
    labelLayers.forEach(item => {
      const shouldShow = zoom >= item.minimumZoom && (!item.maximumZoom || zoom < item.maximumZoom);
      if (shouldShow && !map.hasLayer(item.layer)) item.layer.addTo(map);
      if (!shouldShow && map.hasLayer(item.layer)) item.layer.removeFrom(map);
    });
  }

  function buildCatalog(dataset, features) {
    const publicCountries = new Map(countriesForView(dataset).map(item => [String(item.iso || "").toUpperCase(), item]));
    const entries = new Map();
    (features || []).forEach(feature => {
      const iso = countryCode(feature);
      if (!iso || iso === "AQ") return;
      const state = publicCountries.get(iso) || { status: "insufficient" };
      feature.__oofInterest = state;
      entries.set(iso, { iso, name: shortCountryLabel(countryLabel(feature), iso), state, feature });
    });
    publicCountries.forEach((state, iso) => {
      if (!entries.has(iso)) entries.set(iso, { iso, name: labelForIso(iso), state, feature: null });
    });
    catalog = entries;
  }

  function sortedCatalog(includeInsufficient) {
    return [...catalog.values()].filter(entry => includeInsufficient || entry.state.status !== "insufficient").sort((a, b) => a.name.localeCompare(b.name, "en"));
  }

  function sortedPublicCatalog() {
    return sortedCatalog(false).sort((a, b) => {
      const statusDifference = (PUBLIC_STATUS_ORDER[a.state.status] ?? Number.MAX_SAFE_INTEGER) - (PUBLIC_STATUS_ORDER[b.state.status] ?? Number.MAX_SAFE_INTEGER);
      return statusDifference || a.name.localeCompare(b.name, "en");
    });
  }

  function populateCountrySelector() {
    select.replaceChildren(new Option("Select a country", ""));
    const fragment = document.createDocumentFragment();
    sortedCatalog(true).forEach(entry => fragment.appendChild(new Option(entry.name, entry.iso)));
    select.appendChild(fragment);
    select.onchange = () => selectCountry(catalog.get(select.value) || null, true);
  }

  function populateCountryList() {
    if (!countryList) return;
    const countries = sortedPublicCatalog();
    const fragment = document.createDocumentFragment();
    countries.forEach(entry => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      const swatch = document.createElement("span");
      const name = document.createElement("span");
      button.type = "button";
      button.className = "oof-global-interest-country-option";
      button.dataset.countryIso = entry.iso;
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-label", `${entry.name}: ${STATUS_LABELS[entry.state.status] || STATUS_LABELS.insufficient}. Select country.`);
      swatch.className = `oof-global-interest-country-swatch is-${entry.state.status}`;
      swatch.setAttribute("aria-hidden", "true");
      name.className = "oof-global-interest-country-option-name";
      name.textContent = entry.name;
      button.append(swatch, name);
      button.addEventListener("click", () => selectCountry(entry, true));
      item.appendChild(button);
      fragment.appendChild(item);
    });
    countryList.replaceChildren(fragment);
    countryList.setAttribute("aria-busy", "false");
    if (!countries.length) {
      const empty = document.createElement("li");
      empty.className = "oof-global-interest-country-list-empty";
      empty.textContent = "No countries have a sufficient public signal in this data window.";
      countryList.appendChild(empty);
    }
  }

  function prepareDataset(dataset) { buildCatalog(dataset, []); populateCountrySelector(); populateCountryList(); applyFreshness(dataset); }

  function showFallback(message) {
    container.classList.add("is-fallback");
    container.innerHTML = `<p>${escapeHtml(message)}</p>`;
    if (viewControls) viewControls.hidden = true;
    if (fallback) fallback.hidden = false;
  }

  function initializeMap(world, dataset) {
    if (typeof window.L !== "object") throw new Error("2D map library unavailable");
    const features = (world.features || []).filter(feature => { const iso = countryCode(feature); return iso && iso !== "AQ"; });
    buildCatalog(dataset, features);
    populateCountrySelector();
    populateCountryList();
    container.classList.remove("is-fallback");
    container.innerHTML = "";
    map = L.map(container, { attributionControl: true, zoomControl: false, minZoom: 1, maxZoom: 9, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 90, maxBounds: [[-85, -190], [85, 190]], maxBoundsViscosity: 1, worldCopyJump: false, preferCanvas: true });
    map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
    map.attributionControl.addAttribution('<a href="https://www.naturalearthdata.com" target="_blank" rel="noopener">Natural Earth</a>');
    map.fitBounds(WORLD_BOUNDS, { padding: [8, 8], animate: false });
    L.geoJSON(features, {
      style: countryStyle,
      onEachFeature(feature, layer) {
        countryLayers.push({ feature, layer });
        layer.on({
          click: () => selectCountry(catalog.get(countryCode(feature)), false),
          mouseover: () => { if (!precisePointer) return; hoveredFeature = feature; showCountry(catalog.get(countryCode(feature))); refreshHighlights(); layer.bringToFront(); },
          mouseout: () => { if (!precisePointer) return; hoveredFeature = null; showCountry(selectedEntry); refreshHighlights(); }
        });
        const hasPublicSignal = stateForFeature(feature).status !== "insufficient";
        if (isTinyFeature(feature) && hasPublicSignal) {
          createLabel(feature, 1, 4, true);
          createLabel(feature, 4);
        } else if (hasPublicSignal) {
          // Publicly classified countries remain identifiable in the overview.
          createLabel(feature, 1);
        } else {
          createLabel(feature, minimumLabelZoom(feature));
        }
      }
    }).addTo(map);
    updateLabels();
    map.on("zoomend", () => { updateLabels(); refreshHighlights(); });
    if ("ResizeObserver" in window) new ResizeObserver(() => map.invalidateSize({ pan: false })).observe(container);
    else window.addEventListener("resize", () => map.invalidateSize({ pan: false }));
  }

  function rebuildMap() {
    selectedEntry = null;
    selectedFeature = null;
    hoveredFeature = null;
    if (map) map.remove();
    map = null;
    countryLayers = [];
    labelLayers = [];
    applyViewPresentation();
    if (activeWorld) initializeMap(activeWorld, activeDataset);
    else if (activeDataset) prepareDataset(activeDataset);
    showCountry(null);
  }

  if (viewControls) viewControls.addEventListener("click", event => {
    const button = event.target.closest("button[data-map-action]");
    if (!button || !map) return;
    if (button.dataset.mapAction === "zoom-in") map.zoomIn(0.5);
    if (button.dataset.mapAction === "zoom-out") map.zoomOut(0.5);
    if (button.dataset.mapAction === "reset") { selectedEntry = null; selectedFeature = null; hoveredFeature = null; selectCountry(null, false); map.fitBounds(WORLD_BOUNDS, { padding: [8, 8], animate: !reducedMotion }); }
  });

  if (dataModeControls) dataModeControls.addEventListener("click", event => {
    const button = event.target.closest("button[data-interest-view]");
    if (!button || button.dataset.interestView === interestView) return;
    interestView = button.dataset.interestView;
    rebuildMap();
  });

  fetch("data/oof-global-interest-heat-map.json", { cache: "no-store" })
    .then(response => { if (!response.ok) throw new Error("Public interest dataset unavailable"); return response.json(); })
    .then(dataset => {
      if (!dataset || dataset.schemaVersion !== "1.3" || dataset.algorithmVersion !== "3.2" || !Array.isArray(dataset.countries) || !dataset.trafficViews) throw new Error("Public Global Interest Heat Map dataset is invalid");
      activeDataset = dataset;
      applyViewPresentation();
      prepareDataset(dataset);
      return fetch("assets/data/ne_50m_admin_0_countries.geojson", { cache: "force-cache" })
        .then(response => { if (!response.ok) throw new Error("Country geometry unavailable"); return response.json(); })
        .then(world => { activeWorld = world; initializeMap(world, dataset); })
        .catch(error => { showFallback("The interactive map is temporarily unavailable. Available country classifications remain accessible below."); console.warn("OOF Global Interest Heat Map fallback:", error); });
    })
    .catch(error => { showFallback("The public map and its classification dataset could not be loaded."); console.error("OOF Global Interest Heat Map:", error); });
})();
