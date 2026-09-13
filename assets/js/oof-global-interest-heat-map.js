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
  if (!container || !select || !card) return;

  let globe;
  let hoveredFeature = null;
  let selectedFeature = null;
  let resizeFrame = 0;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
        const centroid = feature.properties && feature.properties.LABEL_Y != null
          ? { lat: Number(feature.properties.LABEL_Y), lng: Number(feature.properties.LABEL_X) }
          : null;
        if (centroid && Number.isFinite(centroid.lat) && Number.isFinite(centroid.lng)) {
          globe.pointOfView({ ...centroid, altitude: 1.75 }, 700);
        }
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
      .showAtmosphere(true)
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
      });

    const material = globe.globeMaterial();
    material.color.set("#656565");
    material.emissive.set("#292929");
    material.emissiveIntensity = 0.16;
    material.shininess = 0.6;
    globe.pointOfView({ lat: 20, lng: 8, altitude: 2.05 }, 0);
    globe.controls().enablePan = false;
    globe.controls().minDistance = 150;
    globe.controls().maxDistance = 420;
    globe.controls().autoRotate = !reducedMotion;
    globe.controls().autoRotateSpeed = 0.18;
    setGlobeSize();

    ["pointerdown", "touchstart", "wheel"].forEach(eventName => {
      container.addEventListener(eventName, stopRotation, { passive: true, once: true });
    });
    window.addEventListener("resize", () => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(setGlobeSize);
    });
  }).catch(error => {
    showFallback("The public map could not be loaded. The last valid dataset remains unavailable in this preview.");
    console.error("OOF Global Interest Heat Map:", error);
  });
})();
