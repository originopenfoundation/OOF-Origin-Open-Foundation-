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
  let renderIdleTimer = 0;
  let globeInViewport = true;
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

  function pauseGlobe() {
    clearTimeout(renderIdleTimer);
    renderIdleTimer = 0;
    if (globe && globe.pauseAnimation) globe.pauseAnimation();
  }

  function scheduleMobilePause(delay = 750) {
    if (!mobileViewport.matches || !globe || !globe.pauseAnimation) return;
    clearTimeout(renderIdleTimer);
    renderIdleTimer = window.setTimeout(() => {
      if (!document.hidden && globeInViewport) globe.pauseAnimation();
      renderIdleTimer = 0;
    }, delay);
  }

  function wakeGlobe(idleDelay = 0) {
    if (!globe || document.hidden || !globeInViewport) return;
    clearTimeout(renderIdleTimer);
    renderIdleTimer = 0;
    if (globe.resumeAnimation) globe.resumeAnimation();
    if (idleDelay) scheduleMobilePause(idleDelay);
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
    if (globe && view) {
      wakeGlobe(reducedMotion ? 100 : 850);
      globe.pointOfView(view, reducedMotion ? 0 : 650);
    }
  }

  function changeZoom(delta) {
    if (!globe) return;
    wakeGlobe(reducedMotion ? 100 : 500);
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
        refreshHighlights();
      }
    });
  }

  function setGlobeSize() {
    if (!globe) return;
    globe.width(container.clientWidth).height(container.clientHeight);
  }

  function refreshHighlights() {
    if (!globe) return;
    globe
      .polygonCapColor(globe.polygonCapColor())
      .polygonAltitude(globe.polygonAltitude())
      .pointColor(globe.pointColor())
      .pointRadius(globe.pointRadius());
  }

  function showFallback(message) {
    clearTimeout(renderIdleTimer);
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
    }),
    fetch("assets/data/ne_110m_missing_country_centers.json", { cache: "force-cache" }).then(response => {
      if (!response.ok) throw new Error("Small-country coordinates unavailable");
      return response.json();
    })
  ]).then(([world, dataset, countryCenters]) => {
    const publicCountries = new Map((dataset.countries || []).map(item => [String(item.iso || "").toUpperCase(), item]));
    const features = (world.features || []).filter(feature => countryCode(feature));
    features.forEach(feature => {
      const state = publicCountries.get(countryCode(feature));
      feature.__oofInterest = state && STATUS_LABELS[state.status] ? state : { status: "insufficient" };
    });
    const featureCodes = new Set(features.map(countryCode));
    const missingFeatures = (countryCenters.countries || [])
      .filter(country => publicCountries.has(String(country.iso || "").toUpperCase()) && !featureCodes.has(String(country.iso || "").toUpperCase()))
      .map(country => ({
        properties: {
          ADMIN: country.name,
          ISO_A2_EH: String(country.iso || "").toUpperCase(),
          LABEL_X: Number(country.lng),
          LABEL_Y: Number(country.lat)
        },
        __oofInterest: publicCountries.get(String(country.iso || "").toUpperCase())
      }));
    populateCountrySelector([...features, ...missingFeatures]);

    if (!supportsWebGL() || typeof window.Globe !== "function") {
      showFallback("The 3D globe is unavailable in this browser. Use the country selector below.");
      return;
    }

    container.innerHTML = "";
    globe = window.Globe({
      animateIn: !reducedMotion && !mobileViewport.matches,
      rendererConfig: {
        alpha: true,
        antialias: !mobileViewport.matches,
        powerPreference: "high-performance"
      }
    })(container)
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
      .polygonAltitude(feature => {
        if (mobileViewport.matches) return feature === selectedFeature ? 0.008 : 0.001;
        return feature === selectedFeature ? 0.018 : feature === hoveredFeature ? 0.012 : 0.006;
      })
      .polygonLabel(() => "")
      .onPolygonHover(feature => {
        if (!precisePointer) return;
        hoveredFeature = feature || null;
        if (feature) showCountry(feature);
        else if (selectedFeature) showCountry(selectedFeature);
        refreshHighlights();
      })
      .onPolygonClick(feature => {
        selectedFeature = feature;
        showCountry(feature);
        select.value = countryCode(feature);
        stopRotation();
        focusFeature(feature);
        refreshHighlights();
      })
      .pointsData(missingFeatures)
      .pointLat(feature => Number(feature.properties.LABEL_Y))
      .pointLng(feature => Number(feature.properties.LABEL_X))
      .pointColor(feature => feature === hoveredFeature ? COLORS.hover : COLORS[publicState(feature).status])
      .pointAltitude(0.02)
      .pointRadius(feature => feature === selectedFeature ? 0.7 : feature === hoveredFeature ? 0.58 : 0.48)
      .pointResolution(mobileViewport.matches ? 8 : 12)
      .pointLabel(() => "")
      .onPointHover(feature => {
        if (!precisePointer) return;
        hoveredFeature = feature || null;
        if (feature) showCountry(feature);
        else if (selectedFeature) showCountry(selectedFeature);
        refreshHighlights();
      })
      .onPointClick(feature => {
        selectedFeature = feature;
        showCountry(feature);
        select.value = countryCode(feature);
        stopRotation();
        focusFeature(feature);
        refreshHighlights();
      });

    const material = globe.globeMaterial();
    material.color.set("#656565");
    material.emissive.set("#292929");
    material.emissiveIntensity = 0.16;
    material.shininess = 0.6;
    const controls = globe.controls();
    const renderer = globe.renderer && globe.renderer();
    if (renderer && renderer.setPixelRatio) {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobileViewport.matches ? 1.1 : 2));
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
    if (controls.addEventListener) {
      controls.addEventListener("start", () => wakeGlobe());
      controls.addEventListener("end", () => scheduleMobilePause(700));
    }
    setGlobeSize();
    scheduleMobilePause(900);

    if (viewControls) {
      viewControls.addEventListener("click", event => {
        const button = event.target.closest("button[data-globe-action]");
        if (!button) return;
        const action = button.dataset.globeAction;
        if (action === "zoom-in") changeZoom(-0.28);
        if (action === "zoom-out") changeZoom(0.28);
        if (action === "reset") {
          wakeGlobe(reducedMotion ? 100 : 750);
          selectedFeature = null;
          hoveredFeature = null;
          select.value = "";
          showCountry(null);
          stopRotation();
          globe.pointOfView(initialView(), reducedMotion ? 0 : 550);
          refreshHighlights();
        }
      });
    }

    container.addEventListener("pointerdown", () => {
      stopRotation();
      wakeGlobe();
    }, { capture: true, passive: true });
    container.addEventListener("pointerup", () => scheduleMobilePause(700), { passive: true });
    container.addEventListener("pointercancel", () => scheduleMobilePause(200), { passive: true });
    container.addEventListener("wheel", () => {
      stopRotation();
      wakeGlobe(500);
    }, { passive: true });
    window.addEventListener("resize", () => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => {
        wakeGlobe(300);
        setGlobeSize();
      });
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) pauseGlobe();
      else wakeGlobe(500);
    });
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(entries => {
        globeInViewport = Boolean(entries[0] && entries[0].isIntersecting);
        if (globeInViewport) wakeGlobe(500);
        else pauseGlobe();
      }, { rootMargin: "80px 0px" });
      observer.observe(container);
    }
  }).catch(error => {
    showFallback("The public map could not be loaded. The last valid dataset remains unavailable in this preview.");
    console.error("OOF Global Interest Heat Map:", error);
  });
})();
