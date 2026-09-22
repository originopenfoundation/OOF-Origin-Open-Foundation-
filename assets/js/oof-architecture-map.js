(function () {
  "use strict";

  const layouts = {
    GOA: [0, 0, 25.5, 42.5, "polygon(0 0,96% 0,100% 8%,98% 94%,92% 100%,0 98%)"],
    INTEGROS: [24.5, 0, 31, 25.5, "polygon(3% 0,100% 0,98% 95%,92% 100%,0 96%,2% 8%)"],
    AIG: [54.5, 0, 23, 26, "polygon(3% 0,96% 0,100% 12%,97% 100%,0 96%,2% 11%)"],
    ORA: [76.5, 0, 23.5, 26, "polygon(2% 0,100% 0,100% 96%,5% 100%,0 90%,2% 12%)"],
    ASGA: [24.7, 24.5, 25.8, 26.5, "polygon(1% 0,94% 3%,100% 12%,97% 94%,89% 100%,0 97%,3% 12%)"],
    CLIA: [49.5, 24.5, 28, 26.5, "polygon(3% 2%,98% 0,100% 91%,94% 100%,0 96%,2% 10%)"],
    MGIA: [76.5, 24.5, 23.5, 26.5, "polygon(2% 2%,100% 0,100% 100%,6% 97%,0 89%,3% 12%)"],
    TREGA: [0, 41.5, 25.5, 31.5, "polygon(0 2%,96% 0,100% 8%,98% 92%,90% 100%,0 97%)"],
    AGA: [24.5, 50, 26, 23, "polygon(2% 0,96% 3%,100% 14%,97% 100%,1% 96%,3% 12%)"],
    OBIDENITY: [49.5, 50, 29, 23, "polygon(2% 2%,100% 0,97% 92%,90% 100%,0 97%,3% 12%)"],
    CLA: [77.5, 50, 22.5, 23, "polygon(3% 0,100% 2%,100% 100%,5% 96%,0 86%,2% 10%)"],
    SIMULOS: [0, 71.5, 27.5, 28.5, "polygon(0 3%,93% 0,100% 10%,97% 100%,0 100%)"],
    VFM: [26.5, 71.5, 26, 28.5, "polygon(3% 0,96% 3%,100% 14%,97% 100%,0 100%,2% 10%)"],
    VALIDOS: [51.5, 71.5, 25.5, 28.5, "polygon(3% 2%,100% 0,98% 100%,0 100%,2% 12%)"],
    HALIA: [76, 71.5, 24, 28.5, "polygon(3% 0,100% 3%,100% 100%,0 100%,2% 12%)"]
  };

  const fallbackLayouts = [
    [76, 71.5, 24, 28.5, "polygon(3% 0,100% 3%,100% 100%,0 100%,2% 12%)"]
  ];

  const root = document.getElementById("oof-architecture-territories");
  const status = document.getElementById("oof-map-status");
  const panel = document.getElementById("oof-selected-architecture");
  const title = document.getElementById("oof-selected-title");
  const selectedStatus = document.getElementById("oof-selected-status");
  const links = document.getElementById("oof-selected-links");
  const note = document.getElementById("oof-selected-development-note");
  const frame = document.getElementById("oof-selected-page");

  function setLayout(button, item, index) {
    const values = layouts[item.acronym] || fallbackLayouts[index % fallbackLayouts.length];
    ["--x", "--y", "--w", "--h"].forEach((name, position) => button.style.setProperty(name, values[position]));
    button.style.setProperty("--shape", values[4]);
  }

  function selectArchitecture(item, button) {
    root.querySelectorAll(".oof-map-territory").forEach((territory) => territory.setAttribute("aria-pressed", "false"));
    button.setAttribute("aria-pressed", "true");
    panel.hidden = false;
    title.textContent = item.displayName || `${item.acronym} — ${item.name}`;
    selectedStatus.textContent = item.status === "development" ? "Status: In Development" : "Status: Completed / Published Architecture";
    links.replaceChildren();

    if (item.status === "development") {
      note.hidden = false;
      frame.hidden = true;
      frame.removeAttribute("src");
    } else {
      note.hidden = true;
      const primary = item.primaryPage || item.pages[0];
      frame.src = primary.url;
      frame.hidden = false;
      item.pages.filter((page) => page.url !== primary.url).forEach((page) => {
        const anchor = document.createElement("a");
        anchor.href = page.url;
        anchor.textContent = `${page.label} →`;
        links.append(anchor);
      });
    }
    panel.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }

  function render(data) {
    const items = [...data.architectures, ...data.developmentArchitectures];
    items.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "oof-map-territory";
      button.dataset.status = item.status;
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-label", `${item.displayName || `${item.acronym} — ${item.name}`}. Status: ${item.status === "development" ? "In Development" : "Completed / Published Architecture"}.`);
      setLayout(button, item, index);
      const acronym = document.createElement("span");
      acronym.className = "oof-map-acronym";
      acronym.textContent = item.acronymLabel || item.acronym;
      const name = document.createElement("span");
      name.className = "oof-map-name";
      name.textContent = item.name;
      const state = document.createElement("span");
      state.className = "oof-map-territory-status";
      state.textContent = item.status === "development" ? "In Development" : "Completed";
      button.append(acronym, name, state);
      button.addEventListener("click", () => selectArchitecture(item, button));
      root.append(button);
    });
    root.setAttribute("aria-busy", "false");
    status.textContent = `${data.architectures.length} completed architectures from the official Architecture Index${data.developmentArchitectures.length ? ` · ${data.developmentArchitectures.length} in development` : ""}.`;
  }

  fetch("data/oof-architecture-registry.json")
    .then((response) => {
      if (!response.ok) throw new Error(`Registry request failed (${response.status})`);
      return response.json();
    })
    .then(render)
    .catch(() => {
      root.setAttribute("aria-busy", "false");
      status.textContent = "The Architecture Map could not load the official Architecture Index data.";
    });
})();
