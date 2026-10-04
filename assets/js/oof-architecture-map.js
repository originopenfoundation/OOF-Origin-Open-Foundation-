(function () {
  "use strict";

  const architectureOrder = [
    "GOA", "ASGA", "INTEGROS", "AIG", "ORA",
    "CLIA", "MGIA", "PGA", "CLA", "TREGA",
    "AGA", "OBIDENITY", "SIMULOS", "VFM", "VALIDOS",
    "LIGA"
  ];

  const iconLabels = {
    GOA: "GO",
    ASGA: "AS",
    INTEGROS: "IN",
    AIG: "AI",
    ORA: "OR",
    CLIA: "CI",
    MGIA: "MG",
    PGA: "PG",
    CLA: "CL",
    TREGA: "TR",
    AGA: "AG",
    OBIDENITY: "ID",
    SIMULOS: "SI",
    VFM: "VF",
    VALIDOS: "VA",
    LIGA: "LI"
  };

  const root = document.getElementById("oof-architecture-territories");
  const status = document.getElementById("oof-map-status");
  const panel = document.getElementById("oof-selected-architecture");
  const title = document.getElementById("oof-selected-title");
  const selectedStatus = document.getElementById("oof-selected-status");
  const links = document.getElementById("oof-selected-links");
  const note = document.getElementById("oof-selected-development-note");
  const frame = document.getElementById("oof-selected-page");

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
    const positions = new Map(architectureOrder.map((acronym, index) => [acronym, index]));
    const items = [...data.architectures, ...data.developmentArchitectures]
      .sort((left, right) => (positions.get(left.acronym) ?? 999) - (positions.get(right.acronym) ?? 999));
    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "oof-map-territory";
      button.dataset.status = item.status;
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-label", `${item.displayName || `${item.acronym} — ${item.name}`}. Status: ${item.status === "development" ? "In Development" : "Completed / Published Architecture"}.`);
      const icon = document.createElement("span");
      icon.className = "oof-map-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = iconLabels[item.acronym] || item.acronym.slice(0, 2);
      const copy = document.createElement("span");
      copy.className = "oof-map-copy";
      const acronym = document.createElement("span");
      acronym.className = "oof-map-acronym";
      acronym.textContent = item.acronymLabel || item.acronym;
      const name = document.createElement("span");
      name.className = "oof-map-name";
      name.textContent = item.name;
      copy.append(acronym, name);
      button.append(icon, copy);
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
      status.textContent = "The Governance Space Map could not load the official Architecture Index data.";
    });
})();
