(function () {
  "use strict";

  const COLORS = {
    high: "#167a45",
    moderate: "#2468b4",
    emerging: "#d6a51f",
    insufficient: "#a3a3a3",
    hover: "#f2f2f2"
  };
  const STATUS_LABELS = {
    high: "High Interest",
    moderate: "Moderate Interest",
    emerging: "Emerging Interest",
    insufficient: "Insufficient Signal"
  };
  const MOMENTUM_LABELS = {
    "rapidly-rising": "↑ Rapidly Rising",
    rising: "↗ Rising",
    stable: "→ Stable",
    declining: "↘ Declining"
  };

  const container = document.getElementById("global-interest-globe");
  const fallback = document.getElementById("global-interest-fallback");
  const select = document.getElementById("global-interest-country-select");
  const card = document.getElementById("global-interest-country-card");
  const countryName = document.getElementById("global-interest-country-name");
  const countryStatus = document.getElementById("global-interest-country-status");
  const countryMomentum = document.getElementById("global-interest-country-momentum");
  const viewControls = document.querySelector(".oof-global-interest-view-controls");
  if (!container || !select || !card) return;

  let globe;
  let hoveredFeature = null;
  let selectedFeature = null;
  let resizeFrame = 0;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mobileViewport = window.matchMedia("(max-width: 959px)");
  const precisePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const INITIAL_VIEW = { lat: 20, lng: 8, altitude: 2.05 };
  const MOBILE_INITIAL_VIEW = { lat: 20, lng: 8, altitude: 2.3 };

  function countryCode(feature) {
    const properties = feature && feature.properties ? feature.properties : {};
    const candidates = [properties.ISO_A2_EH, properties.ISO_A2, properties.WB_A2, properties.POSTAL];
    return String(candidates.find(code => code && code !== "-99") || "").toUpperCase();
  }

  function countryLabel(feature) {
    const properties = feature && feature.properties ? feature.properties : {};
    return properties.ADMIN || properties.NAME_LONG || properties.NAME || "Unknown country";
  }

  function flagFor(iso) {
    if (!/^[A-Z]{2}$/.test(iso)) return "";
    return String.fromCodePoint(...iso.split("").map(letter => 127397 + letter.charCodeAt(0)));
  }

  function supportsWebGL() {
    try {
      const canvas = document.createElement("canvas");
      return Boolean(window.WebGLRenderingContext && (canvas.getContext("webgl2") || canvas.getContext("webgl")));
    } catch (_) {
      return false;
    }
  }

  function publicState(feature) {
    return feature.__oofInterest || { status: "insufficient" };
  }

  function showCountry(feature) {
    if (!feature) {
      countryName.textContent = "Select a country";
      countryStatus.textContent = "Interest classification will appear here.";
      countryMomentum.hidden = true;
      return;
    }
    const iso = countryCode(feature);
    const state = publicState(feature);
    const flag = flagFor(iso);
    countryName.textContent = `${flag ? flag + " " : ""}${countryLabel(feature)}`;
    countryStatus.textContent = `Interest: ${STATUS_LABELS[state.status] || STATUS_LABELS.insufficient}`;
    if (state.momentum && MOMENTUM_LABELS[state.momentum]) {
      countryMomentum.textContent = `Momentum: ${MOMENTUM_LABELS[state.momentum]}`;
      countryMomentum.hidden = false;
    } else {
      countryMomentum.hidden = true;
    }
  }

  function stopRotation() {
    if (globe && globe.controls()) globe.controls().autoRotate = false;
  }

  function initialView() {
    return mobileViewport.matches ? MOBILE_INITIAL_VIEW : INITIAL_VIEW;
  }

  function featureView(feature) {
    const properties = feature && feature.properties ? feature.properties : {};
    const lat = Number(properties.LABEL_Y);
    const lng = Number(properties.LABEL_X);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
    return { lat, lng, altitude: mobileViewport.matches ? 1.95 : 1.75 };
  }

  function focusFeature(feature) {
    const view = featureView(feature);
    if (globe && view) globe.pointOfView(view, reducedMotion ? 0 : 650);
  }

  function changeZoom(delta) {
    if (!globe) return;
    const current = globe.pointOfView();
    const altitude = Math.min(3.5, Math.max(0.72, Number(current.altitude || initialView().altitude) + delta));
    globe.pointOfView({ lat: current.lat, lng: current.lng, altitude }, reducedMotion ? 0 : 260);
    stopRotation();
  }

  function populateCountrySelector(features) {
    const sorted = [...features].sort((a, b) => countryLabel(a).localeCompare(countryLabel(b), "en"));
    const fragment = document.createDocumentFragment();
    sorted.forEach(feature => {
      const option = document.createElement("option");
      option.value = countryCode(feature);
      option.textContent = countryLabel(feature);
      option.__feature = feature;
      fragment.appendChild(option);
    });
    select.appendChild(fragment);
    select.addEventListener("change", () => {
      const option = select.options[select.selectedIndex];
      const feature = option && option.__feature;
      if (!feature) return showCountry(null);
      selectedFeature = feature;
      showCountry(feature);
      stopRotation();
      if (globe) {
        focusFeature(feature);
        globe.polygonCapColor(globe.polygonCapColor());
      }
    });
  }

  function setGlobeSize() {
    if (!globe) return;
    globe.width(container.clientWidth).height(container.clientHeight);
  }

  function showFallback(message) {
    container.classList.add("is-fallback");
    container.innerHTML = `<p>${message}</p>`;
    if (viewControls) viewControls.hidden = true;
    if (fallback) fallback.hidden = false;
  }

  Promise.all([
    fetch("assets/data/ne_110m_admin_0_countries.geojson", { cache: "force-cache" }).then(response => {
      if (!response.ok) throw new Error("Country geometry unavailable");
      return response.json();
    }),
    fetch("data/oof-global-interest-heat-map.json", { cache: "no-cache" }).then(response => {
      if (!response.ok) throw new Error("Public interest dataset unavailable");
      return response.json();
    })
  ]).then(([world, dataset]) => {
    const publicCountries = new Map((dataset.countries || []).map(item => [String(item.iso || "").toUpperCase(), item]));
    const features = (world.features || []).filter(feature => countryCode(feature));
    features.forEach(feature => {
      const state = publicCountries.get(countryCode(feature));
      feature.__oofInterest = state && STATUS_LABELS[state.status] ? state : { status: "insufficient" };
    });
    populateCountrySelector(features);

    if (!supportsWebGL() || typeof window.Globe !== "function") {
      showFallback("The 3D globe is unavailable in this browser. Use the country selector below.");
      return;
    }

    container.innerHTML = "";
    globe = window.Globe({ animateIn: !reducedMotion })(container)
      .backgroundColor("rgba(0,0,0,0)")
      .showAtmosphere(!mobileViewport.matches)
      .atmosphereColor("#f5f5f5")
      .atmosphereAltitude(0.08)
      .showGraticules(false)
      .polygonsData(features)
      .polygonCapColor(feature => {
        if (feature === hoveredFeature) return COLORS.hover;
        const status = publicState(feature).status;
        return COLORS[status] || COLORS.insufficient;
      })
      .polygonSideColor(() => "rgba(60,60,60,0.58)")
      .polygonStrokeColor(() => "rgba(255,255,255,0.48)")
      .polygonAltitude(feature => feature === selectedFeature ? 0.018 : feature === hoveredFeature ? 0.012 : 0.006)
      .polygonLabel(() => "")
      .onPolygonHover(feature => {
        if (!precisePointer) return;
        hoveredFeature = feature || null;
        if (feature) showCountry(feature);
        else if (selectedFeature) showCountry(selectedFeature);
        globe.polygonCapColor(globe.polygonCapColor()).polygonAltitude(globe.polygonAltitude());
      })
      .onPolygonClick(feature => {
        selectedFeature = feature;
        showCountry(feature);
        select.value = countryCode(feature);
        stopRotation();
        focusFeature(feature);
      });

    const material = globe.globeMaterial();
    material.color.set("#656565");
    material.emissive.set("#292929");
    material.emissiveIntensity = 0.16;
    material.shininess = 0.6;
    const controls = globe.controls();
    const renderer = globe.renderer && globe.renderer();
    if (renderer && renderer.setPixelRatio) {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobileViewport.matches ? 1.35 : 2));
    }
    globe.pointOfView(initialView(), 0);
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.dampingFactor = mobileViewport.matches ? 0.09 : 0.06;
    controls.rotateSpeed = mobileViewport.matches ? 0.62 : 0.8;
    controls.zoomSpeed = mobileViewport.matches ? 0.72 : 1;
    controls.minDistance = 130;
    controls.maxDistance = 460;
    controls.autoRotate = !reducedMotion && !mobileViewport.matches;
    controls.autoRotateSpeed = 0.18;
    setGlobeSize();

    if (viewControls) {
      viewControls.addEventListener("click", event => {
        const button = event.target.closest("button[data-globe-action]");
        if (!button) return;
        const action = button.dataset.globeAction;
        if (action === "zoom-in") changeZoom(-0.28);
        if (action === "zoom-out") changeZoom(0.28);
        if (action === "reset") {
          selectedFeature = null;
          hoveredFeature = null;
          select.value = "";
          showCountry(null);
          stopRotation();
          globe.pointOfView(initialView(), reducedMotion ? 0 : 550);
          globe.polygonCapColor(globe.polygonCapColor()).polygonAltitude(globe.polygonAltitude());
        }
      });
    }

    ["pointerdown", "touchstart", "wheel"].forEach(eventName => {
      container.addEventListener(eventName, stopRotation, { passive: true, once: true });
    });
    window.addEventListener("resize", () => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(setGlobeSize);
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden && globe.pauseAnimation) globe.pauseAnimation();
      if (!document.hidden && globe.resumeAnimation) globe.resumeAnimation();
    });
  }).catch(error => {
    showFallback("The public map could not be loaded. The last valid dataset remains unavailable in this preview.");
    console.error("OOF Global Interest Heat Map:", error);
  });
})();
