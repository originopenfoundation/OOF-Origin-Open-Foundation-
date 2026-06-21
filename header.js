let siteSearchIndex = null;
let siteSearchLoading = false;

function getById(id) {
  return document.getElementById(id);
}

function setDisplay(element, display) {
  if (element) element.style.display = display;
}

function isOpen(element) {
  return element && element.style.display === "block";
}

function toggleElement(id) {
  const element = getById(id);
  if (!element) return;
  element.style.display = isOpen(element) ? "none" : "block";
}

function toggleBurger() {
  toggleElement("burgerMenu");
}

function toggleBurgerSub(submenuId) {
  toggleElement(submenuId);
}

function buildMegaMenu() {
  const source = getById("burgerMenu");
  const target = getById("megaMenuContent");
  if (!source || !target || target.dataset.ready === "true") return;

  const html = source.innerHTML
    .replace(/toggleBurgerSub\('([^']+)'\)/g, "toggleMegaSub('mega-$1')")
    .replace(/id="([^"]+)"/g, 'id="mega-$1"');

  target.innerHTML = html;
  organizeMegaMenuContent(target);
  target.dataset.ready = "true";
}

function organizeMegaMenuContent(target) {
  const nodes = Array.from(target.childNodes);
  target.textContent = "";

  const sections = [];
  const directLinks = [];
  let currentBody = null;

  nodes.forEach(node => {
    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim() === "") return;
    if (node.nodeName === "BR") return;
    if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("burger-search")) return;

    if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("podstranka")) {
      Array.from(node.children).forEach(child => {
        if (child.nodeName === "A") directLinks.push(child);
      });
      return;
    }

    if (node.nodeName === "HR") {
      currentBody = null;
      return;
    }

    if (node.nodeName === "H3") {
      currentBody = document.createElement("div");
      currentBody.className = "mega-section-body";
      sections.push({
        title: node.textContent.trim(),
        body: currentBody
      });
      return;
    }

    if (!currentBody) {
      currentBody = document.createElement("div");
      currentBody.className = "mega-section-body";
      sections.push({
        title: "Navigation",
        body: currentBody
      });
    }

    currentBody.appendChild(node);
  });

  const tabs = document.createElement("div");
  const detail = document.createElement("div");
  tabs.className = "mega-menu-tabs";
  detail.className = "mega-menu-detail";

  sections.forEach((section, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mega-section-tab";
    button.textContent = section.title;
    button.addEventListener("click", () => showMegaSection(index));

    section.body.dataset.sectionIndex = String(index);
    detail.appendChild(section.body);
    tabs.appendChild(button);
  });

  directLinks.forEach(link => {
    link.className = "mega-section-tab mega-direct-link";
    tabs.appendChild(link);
  });

  target.appendChild(tabs);
  target.appendChild(detail);
  showMegaSection(0);
}

function toggleMegaMenu() {
  buildMegaMenu();
  closeSiteSearch();
  toggleElement("megaMenu");
}

function closeMegaMenu() {
  setDisplay(getById("megaMenu"), "none");
}

function toggleMegaSub(submenuId) {
  toggleElement(submenuId);
}

function showMegaSection(index) {
  const content = getById("megaMenuContent");
  if (!content) return;

  content.querySelectorAll(".mega-section-tab").forEach((button, buttonIndex) => {
    button.classList.toggle("mega-section-active", buttonIndex === index);
  });

  content.querySelectorAll(".mega-section-body").forEach(body => {
    body.style.display = body.dataset.sectionIndex === String(index) ? "block" : "none";
  });
}

function toggleSiteSearch() {
  const panel = getById("siteSearchPanel");
  const input = getById("siteSearchInput");
  if (!panel) return;

  const shouldOpen = !isOpen(panel);
  panel.style.display = shouldOpen ? "block" : "none";

  if (shouldOpen && input) {
    closeMegaMenu();
    loadSiteSearchIndex();
    setTimeout(() => input.focus(), 0);
  }
}

function closeSiteSearch() {
  setDisplay(getById("siteSearchPanel"), "none");
}

async function loadSiteSearchIndex(resultsId = "siteSearchResults") {
  if (siteSearchIndex || siteSearchLoading) return;

  siteSearchLoading = true;
  renderSearchStatus("Loading search...", resultsId);

  try {
    const response = await fetch("search-index.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Search index not found");
    siteSearchIndex = await response.json();
    renderSearchStatus("Type to search.", resultsId);
  } catch (error) {
    renderSearchStatus("Search index is not available.", resultsId);
  } finally {
    siteSearchLoading = false;
  }
}

function runSiteSearch(query, resultsId = "siteSearchResults") {
  const results = getById(resultsId);
  if (!results) return;

  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.join("").length < 2) {
    renderSearchStatus("Type at least 2 characters.", resultsId);
    return;
  }

  if (!siteSearchIndex) {
    loadSiteSearchIndex(resultsId).then(() => runSiteSearch(query, resultsId));
    return;
  }

  const matches = siteSearchIndex
    .map(page => ({ page, score: getSearchScore(page, words) }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score || a.page.title.localeCompare(b.page.title))
    .slice(0, 12);

  if (matches.length === 0) {
    renderSearchStatus("No results found.", resultsId);
    return;
  }

  results.innerHTML = matches.map(({ page }) => {
    const title = highlightSearchTerms(page.title || page.url, words);
    const excerpt = highlightSearchTerms(makeSearchExcerpt(page.text || "", words), words);
    return `<a class="site-search-result" href="${page.url}"><b>${title}</b><span>${excerpt}</span></a>`;
  }).join("");
}

function getSearchScore(page, words) {
  const title = (page.title || "").toLowerCase();
  const text = (page.text || "").toLowerCase();

  return words.reduce((score, word) => {
    if (title.includes(word)) score += 10;
    if (text.includes(word)) score += 1;
    return score;
  }, 0);
}

function renderSearchStatus(message, resultsId = "siteSearchResults") {
  const results = getById(resultsId);
  if (results) results.innerHTML = `<p class="site-search-status">${escapeHtml(message)}</p>`;
}

function makeSearchExcerpt(text, words) {
  const normalized = text.replace(/\s+/g, " ").trim();
  const lower = normalized.toLowerCase();
  const foundAt = words
    .map(word => lower.indexOf(word))
    .filter(index => index >= 0)
    .sort((a, b) => a - b)[0];
  const start = Math.max(0, (foundAt || 0) - 55);
  const excerpt = normalized.slice(start, start + 150);
  return (start > 0 ? "..." : "") + excerpt + (start + 150 < normalized.length ? "..." : "");
}

function highlightSearchTerms(value, words) {
  let highlighted = escapeHtml(value);
  const uniqueWords = Array.from(new Set(words.filter(word => word.length > 1)))
    .sort((a, b) => b.length - a.length);

  uniqueWords.forEach(word => {
    const safeWord = word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    highlighted = highlighted.replace(new RegExp(`(${safeWord})`, "gi"), '<mark class="site-search-highlight">$1</mark>');
  });

  return highlighted;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

document.addEventListener("click", event => {
  const burger = document.querySelector(".burger");
  const burgerMenu = getById("burgerMenu");
  const megaNav = document.querySelector(".desktop-mega-nav");
  const megaMenu = getById("megaMenu");
  const searchPanel = getById("siteSearchPanel");

  if (burgerMenu && burger && !burgerMenu.contains(event.target) && !burger.contains(event.target)) {
    setDisplay(burgerMenu, "none");
  }

  if (megaMenu && megaNav && !megaNav.contains(event.target)) {
    setDisplay(megaMenu, "none");
  }

  if (searchPanel && megaNav && !searchPanel.contains(event.target) && !event.target.closest(".site-search-toggle")) {
    setDisplay(searchPanel, "none");
  }
});

document.addEventListener("DOMContentLoaded", buildMegaMenu);
