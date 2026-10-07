let siteSearchIndex = null;
let siteSearchLoading = false;
const navigationStateKey = "oof-navigation-expanded";
const navigationScrollKey = "oof-navigation-scroll";

function loadCloudflareAnalytics() {
  if (location.protocol === "file:" || location.hostname === "localhost" || location.hostname === "127.0.0.1") return;
  if (document.querySelector('script[data-cf-beacon]')) return;

  const beacon = document.createElement("script");
  beacon.type = "module";
  beacon.src = "https://static.cloudflareinsights.com/beacon.min.js";
  beacon.dataset.cfBeacon = JSON.stringify({ token: "358af31e8be84a238826900e0aba2cc3" });
  document.body.appendChild(beacon);
}

function getNavigationState() {
  try {
    return JSON.parse(sessionStorage.getItem(navigationStateKey) || "{}");
  } catch (error) {
    return {};
  }
}

function getNavigationStateId(id) {
  return id.replace(/^mega-/, "");
}

function saveNavigationState(id, expanded) {
  try {
    const state = getNavigationState();
    const stateId = getNavigationStateId(id);
    if (expanded) state[stateId] = true;
    else delete state[stateId];
    sessionStorage.setItem(navigationStateKey, JSON.stringify(state));
  } catch (error) {
    return;
  }
}

function restoreNavigationState(menu) {
  const state = getNavigationState();

  menu.querySelectorAll("[aria-controls]").forEach(toggle => {
    const controlledId = toggle.getAttribute("aria-controls");
    if (!controlledId || !state[getNavigationStateId(controlledId)]) return;

    const controlled = getById(controlledId);
    if (!controlled) return;

    controlled.style.display = "block";
    toggle.setAttribute("aria-expanded", "true");
    toggle.classList.toggle("burger-main-active", toggle.classList.contains("burger-main-toggle"));
    toggle.classList.toggle("menu-toggle-open", toggle.classList.contains("burger-toggle"));
  });
}

function setupNavigationScrollPersistence(menu) {
  if (menu.dataset.scrollPersistenceReady === "true") return;
  menu.dataset.scrollPersistenceReady = "true";

  requestAnimationFrame(() => {
    const savedScroll = Number(sessionStorage.getItem(navigationScrollKey));
    if (Number.isFinite(savedScroll) && savedScroll > 0) menu.scrollTop = savedScroll;
  });

  menu.addEventListener("scroll", () => {
    try {
      sessionStorage.setItem(navigationScrollKey, String(menu.scrollTop));
    } catch (error) {
      return;
    }
  }, { passive: true });
}

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


function getSiteRootPrefix() {
  const path = window.location.pathname.replace(/\\/g, "/");
  const parts = path.split("/").filter(Boolean);
  const depth = path.endsWith("/") ? parts.length : Math.max(0, parts.length - 1);
  return "../".repeat(depth);
}

const oofLanguages = [
  { code: "en", prefix: "", label: "English" },
  { code: "de-DE", prefix: "de", label: "Deutsch" },
  { code: "zh-CN", prefix: "zh-cn", label: "简体中文（中国大陆）" },
  { code: "zh-HK", prefix: "zh-hk", label: "繁體中文（香港）" },
  { code: "ja-JP", prefix: "ja", label: "日本語" },
  { code: "es-ES", prefix: "es", label: "Español" },
  { code: "pt-PT", prefix: "pt", label: "Português" },
  { code: "fr-FR", prefix: "fr", label: "Français" },
  { code: "hi-IN", prefix: "hi", label: "हिन्दी" }
];

const oofLocalizedUi = {
  "de-DE": { language: "Sprache", home: "Startseite", search: "Suchen", menu: "Menü", index: "OOF® Seitenindex", contact: "Kontakt", back: "Zurück" },
  "zh-CN": { language: "语言", home: "首页", search: "搜索", menu: "菜单", index: "OOF® 网站索引", contact: "联系", back: "返回" },
  "zh-HK": { language: "語言", home: "首頁", search: "搜尋", menu: "選單", index: "OOF® 網站索引", contact: "聯絡", back: "返回" },
  "ja-JP": { language: "言語", home: "ホーム", search: "検索", menu: "メニュー", index: "OOF® サイト索引", contact: "お問い合わせ", back: "戻る" },
  "es-ES": { language: "Idioma", home: "Inicio", search: "Buscar", menu: "Menú", index: "Índice del sitio OOF®", contact: "Contacto", back: "Volver" },
  "pt-PT": { language: "Idioma", home: "Início", search: "Pesquisar", menu: "Menu", index: "Índice do site OOF®", contact: "Contacto", back: "Voltar" },
  "fr-FR": { language: "Langue", home: "Accueil", search: "Rechercher", menu: "Menu", index: "Index du site OOF®", contact: "Contact", back: "Retour" },
  "hi-IN": { language: "भाषा", home: "मुखपृष्ठ", search: "खोजें", menu: "मेनू", index: "OOF® साइट सूचकांक", contact: "संपर्क", back: "वापस" }
};

const oofLocalizedFooter = {
  "de-DE": ["HINWEIS ZUR NICHT AUSFÜHRENDEN FUNKTION", "OOF® — OriginOpen® Foundation ist eine nicht ausführende methodologische Autorität. Diese Website und alle Veröffentlichungen dienen ausschließlich als Referenz.", "HINWEIS ZUR KANONISCHEN SPRACHE", "UCL™ ist die kanonische Sprachebene der OOF® Veröffentlichungen. Englisch ist ihre Trägersprache.", "Bei Unklarheiten ist der veröffentlichte englische HTML-Text maßgeblich.", "RECHTE UND SCHUTZ", "© OOF® — OriginOpen® Foundation. Geschützt durch MIP® — Methodological Intellectual Property. Alle Rechte vorbehalten."],
  "zh-CN": ["非执行性声明", "OOF® — OriginOpen® Foundation 是非执行性方法论权威。本网站及所有出版物仅供参考。", "规范语言声明", "UCL™ 是 OOF® 出版物的规范语言层。英语是其承载语言。", "如有歧义，以已发布的英文 HTML 文本为准。", "权利与保护", "© OOF® — OriginOpen® Foundation。受 MIP® — Methodological Intellectual Property 保护。保留所有权利。"],
  "zh-HK": ["非執行性聲明", "OOF® — OriginOpen® Foundation 是非執行性方法論權威。本網站及所有出版物僅供參考。", "規範語言聲明", "UCL™ 是 OOF® 出版物的規範語言層。英語是其承載語言。", "如有歧義，以已發布的英文 HTML 文字為準。", "權利與保護", "© OOF® — OriginOpen® Foundation。受 MIP® — Methodological Intellectual Property 保護。保留所有權利。"],
  "ja-JP": ["非実行型に関する通知", "OOF® — OriginOpen® Foundation は非実行型の方法論的権威です。このウェブサイトとすべての出版物は参照専用です。", "正規言語に関する通知", "UCL™ は OOF® 出版物の正規言語層です。英語がその媒体言語です。", "曖昧さがある場合は、公開された英語の HTML 本文が優先されます。", "権利と保護", "© OOF® — OriginOpen® Foundation。MIP® — Methodological Intellectual Property により保護されています。無断転載を禁じます。"],
  "es-ES": ["AVISO DE CARÁCTER NO EJECUTOR", "OOF® — OriginOpen® Foundation es una autoridad metodológica no ejecutora. Este sitio web y todas las publicaciones son únicamente de referencia.", "AVISO SOBRE EL IDIOMA CANÓNICO", "UCL™ es la capa lingüística canónica de las publicaciones de OOF®. El inglés es su idioma vehicular.", "En caso de ambigüedad, prevalece el texto HTML publicado en inglés.", "DERECHOS Y PROTECCIÓN", "© OOF® — OriginOpen® Foundation. Protegido por MIP® — Methodological Intellectual Property. Todos los derechos reservados."],
  "pt-PT": ["AVISO DE CARÁTER NÃO EXECUTOR", "A OOF® — OriginOpen® Foundation é uma autoridade metodológica não executora. Este sítio e todas as publicações destinam-se apenas a referência.", "AVISO SOBRE A LÍNGUA CANÓNICA", "UCL™ é a camada linguística canónica das publicações da OOF®. O inglês é a sua língua veicular.", "Em caso de ambiguidade, prevalece o texto HTML publicado em inglês.", "DIREITOS E PROTEÇÃO", "© OOF® — OriginOpen® Foundation. Protegido por MIP® — Methodological Intellectual Property. Todos os direitos reservados."],
  "fr-FR": ["AVIS DE NON-EXÉCUTION", "OOF® — OriginOpen® Foundation est une autorité méthodologique non exécutante. Ce site et toutes ses publications sont fournis uniquement à titre de référence.", "AVIS SUR LA LANGUE CANONIQUE", "UCL™ constitue la couche linguistique canonique des publications OOF®. L’anglais en est la langue porteuse.", "En cas d’ambiguïté, le texte HTML publié en anglais prévaut.", "DROITS ET PROTECTION", "© OOF® — OriginOpen® Foundation. Protégé par MIP® — Methodological Intellectual Property. Tous droits réservés."],
  "hi-IN": ["गैर-निष्पादक सूचना", "OOF® — OriginOpen® Foundation एक गैर-निष्पादक कार्यप्रणाली प्राधिकरण है। यह वेबसाइट और सभी प्रकाशन केवल संदर्भ के लिए हैं।", "प्रामाणिक भाषा सूचना", "UCL™ OOF® प्रकाशनों की प्रामाणिक भाषा-परत है। अंग्रेज़ी इसकी वाहक भाषा है।", "किसी अस्पष्टता की स्थिति में प्रकाशित अंग्रेज़ी HTML पाठ प्रभावी होगा।", "अधिकार और संरक्षण", "© OOF® — OriginOpen® Foundation। MIP® — Methodological Intellectual Property के अंतर्गत संरक्षित। सर्वाधिकार सुरक्षित।"]
};

function getCurrentOofLanguage() {
  const firstSegment = window.location.pathname.split("/").filter(Boolean)[0] || "";
  return oofLanguages.find(language => language.prefix === firstSegment) || oofLanguages[0];
}

function getLocalizedHomeUrl(language) {
  const root = getSiteRootUrl();
  return language.prefix ? new URL(`${language.prefix}/`, root).href : root.href;
}

function applyLocalizedHeaderUi(language) {
  const labels = oofLocalizedUi[language.code];
  if (!labels) return;
  const nav = document.querySelector(".desktop-mega-nav");
  if (!nav) return;
  const links = nav.querySelectorAll(":scope > a");
  const search = nav.querySelector(".site-search-toggle");
  const menu = nav.querySelector(".mega-menu-button");
  const back = document.querySelector(".history-back-fab");
  if (search) search.textContent = `⌕ ${labels.search}`;
  if (menu) menu.textContent = `☰ ${labels.menu}`;
  if (links[0]) links[0].textContent = labels.home;
  if (links[1]) links[1].textContent = labels.index;
  if (links[2]) links[2].textContent = labels.contact;
  if (back) {
    back.setAttribute("aria-label", labels.back);
    back.title = labels.back;
  }
}

function setupLanguageSwitcher() {
  const wrapper = document.querySelector("[data-oof-language-switcher]");
  const select = getById("oofLanguageSelect");
  if (!wrapper || !select || select.dataset.ready === "true") return;
  const current = getCurrentOofLanguage();
  const labels = oofLocalizedUi[current.code];
  const label = wrapper.querySelector("label");
  if (label) label.textContent = labels ? labels.language : "Language";
  select.setAttribute("aria-label", labels ? labels.language : "Change language");
  select.innerHTML = oofLanguages.map(language =>
    `<option value="${language.code}"${language.code === current.code ? " selected" : ""}>${language.label}</option>`
  ).join("");
  select.addEventListener("change", () => {
    const target = oofLanguages.find(language => language.code === select.value) || oofLanguages[0];
    window.location.assign(getLocalizedHomeUrl(target));
  });
  select.dataset.ready = "true";
  applyLocalizedHeaderUi(current);
}

function applyLocalizedFooterUi() {
  const values = oofLocalizedFooter[getCurrentOofLanguage().code];
  const footer = document.querySelector("#footer .footer2, footer.footer2");
  if (!values || !footer || footer.dataset.localized === "true") return;
  const headings = footer.querySelectorAll(":scope > h2");
  const paragraphs = footer.querySelectorAll(":scope > p");
  if (headings[0]) headings[0].textContent = values[0];
  if (paragraphs[0]) paragraphs[0].textContent = values[1];
  if (headings[1]) headings[1].textContent = values[2];
  if (paragraphs[1]) paragraphs[1].textContent = values[3];
  if (paragraphs[2]) paragraphs[2].textContent = values[4];
  if (headings[2]) headings[2].textContent = values[5];
  if (paragraphs[3]) paragraphs[3].textContent = values[6];
  footer.dataset.localized = "true";
}

function withSiteRoot(url) {
  if (!url || /^(?:[a-z]+:|#|\/)/i.test(url)) return url;
  return getSiteRootPrefix() + url.replace(/^\.\//, "");
}

function getSiteRootUrl() {
  const headerScripts = Array.from(document.scripts).filter(script =>
    /(?:^|\/)header\.js(?:[?#].*)?$/.test(script.src)
  );
  const headerScript = headerScripts[headerScripts.length - 1];
  return headerScript ? new URL(".", headerScript.src) : new URL("./", window.location.href);
}

function getCurrentPagePdfUrl() {
  const siteRoot = getSiteRootUrl();
  const pageUrl = new URL(window.location.href);
  const rootPath = decodeURIComponent(siteRoot.pathname);
  const pagePath = decodeURIComponent(pageUrl.pathname);
  let relativePath = pagePath.startsWith(rootPath)
    ? pagePath.slice(rootPath.length)
    : pagePath.replace(/^\/+/, "");

  if (!relativePath || relativePath.endsWith("/")) relativePath += "index.html";
  relativePath = relativePath.replace(/\.html?$/i, "") + ".pdf";
  return new URL("pdf/" + relativePath, siteRoot).href;
}

function setupPagePdfDownload() {
  const footer = document.querySelector("#footer .footer2, footer.footer2");
  if (!footer) return;

  let download = footer.querySelector(".page-pdf-download");
  if (!download) {
    download = document.createElement("div");
    download.className = "page-pdf-download";
    download.innerHTML = '<a download>Download this page as PDF</a>';
    footer.insertBefore(download, footer.firstChild);
  }

  const link = download.querySelector("a");
  if (link) link.href = getCurrentPagePdfUrl();
}

function normalizePageLinks(root = document) {
  root.querySelectorAll("a[href]").forEach(link => {
    const href = link.getAttribute("href");
    const sharedNavigationLink = Boolean(link.closest("#header, #footer"));
    const siteRootPath = href && href.includes("/");
    if (href && !/^(?:[a-z]+:|#|\/|\.\.\/)/i.test(href) && (sharedNavigationLink || siteRootPath)) {
      link.setAttribute("href", withSiteRoot(href));
    }
  });
  setupPagePdfDownload();
  applyLocalizedFooterUi();
}

function toggleBurger() {
  ensureStructuredArchitectureLink();
  setupBurgerMainSections();
  toggleElement("burgerMenu");
}

function toggleBurgerSub(submenuId, toggle) {
  toggleSubmenu(submenuId, toggle);
}

function toggleSubmenu(submenuId, toggle) {
  const submenu = getById(submenuId);
  if (!submenu) return;

  const opening = !isOpen(submenu);
  submenu.style.display = opening ? "block" : "none";
  saveNavigationState(submenuId, opening);
  if (toggle) {
    toggle.classList.toggle("menu-toggle-open", opening);
    toggle.setAttribute("aria-expanded", String(opening));
  }
}

function configureMenuToggle(toggle, controlledId) {
  const controlled = getById(controlledId);
  if (!toggle || !controlled) return;

  toggle.setAttribute("role", "button");
  toggle.setAttribute("tabindex", "0");
  toggle.setAttribute("aria-controls", controlledId);
  toggle.setAttribute("aria-expanded", String(isOpen(controlled)));

  if (toggle.dataset.keyboardReady === "true") return;
  toggle.dataset.keyboardReady = "true";
  toggle.addEventListener("keydown", event => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggle.click();
  });
}

function initializeSubmenuControls(root) {
  root.querySelectorAll(".burger-toggle[onclick]").forEach(toggle => {
    const handler = toggle.getAttribute("onclick") || "";
    const match = handler.match(/toggle(?:Burger|Mega)Sub\('([^']+)'/);
    if (match) configureMenuToggle(toggle, match[1]);
  });
}

function buildMegaMenu() {
  ensureStructuredArchitectureLink();
  const source = getById("burgerMenu");
  const target = getById("megaMenuContent");
  if (!source || !target || target.dataset.ready === "true") return;

  const html = (source.dataset.originalHtml || source.innerHTML)
    .replace(/toggleBurgerSub\('([^']+)', this\)/g, "toggleMegaSub('mega-$1', this)")
    .replace(/id="([^"]+)"/g, 'id="mega-$1"');

  target.innerHTML = html;
  organizeMegaMenuContent(target);
  initializeSubmenuControls(target);
  target.dataset.ready = "true";
}

function ensureStructuredArchitectureLink() {
  const menu = getById("burgerMenu");
  if (!menu || menu.querySelector('a[href="oof-structured-architecture-index.html"]')) return;

  const standardsIndex = menu.querySelector('a[href="standardinde.html"]');
  if (!standardsIndex) return;

  const link = document.createElement("a");
  link.href = withSiteRoot("oof-structured-architecture-index.html");
  link.textContent = "OOF Structured Architecture Index";
  standardsIndex.insertAdjacentElement("afterend", link);
}

function organizeMegaMenuContent(target) {
  const nodes = Array.from(target.childNodes);
  target.textContent = "";

  const entries = [];
  const sections = [];
  let currentBody = null;

  nodes.forEach(node => {
    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim() === "") return;
    if (node.nodeName === "BR") return;
    if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("burger-search")) return;

    if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("podstranka")) {
      Array.from(node.children).forEach(child => {
        if (child.nodeName === "A") entries.push({ type: "direct", link: child });
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
      entries.push({ type: "section", index: sections.length - 1 });
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
    section.body.dataset.sectionIndex = String(index);
    detail.appendChild(section.body);
  });

  entries.forEach(entry => {
    if (entry.type === "direct") {
      entry.link.className = "mega-section-tab mega-direct-link";
      tabs.appendChild(entry.link);
      return;
    }

    const section = sections[entry.index];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mega-section-tab";
    button.textContent = section.title;
    button.addEventListener("click", () => showMegaSection(entry.index));
    tabs.appendChild(button);
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

function toggleMegaSub(submenuId, toggle) {
  toggleSubmenu(submenuId, toggle);
}

function showMegaSection(index) {
  const content = getById("megaMenuContent");
  if (!content) return;

  content.querySelectorAll("button.mega-section-tab").forEach((button, buttonIndex) => {
    button.classList.toggle("mega-section-active", buttonIndex === index);
  });

  content.querySelectorAll(".mega-section-body").forEach(body => {
    body.style.display = body.dataset.sectionIndex === String(index) ? "block" : "none";
  });
}

function setupBurgerMainSections() {
  const menu = getById("burgerMenu");
  if (!menu || menu.dataset.ready === "true") return;
  menu.dataset.originalHtml = menu.innerHTML;

  const nodes = Array.from(menu.childNodes);
  const fragment = document.createDocumentFragment();
  let currentBody = null;
  let sectionIndex = 0;

  nodes.forEach(node => {
    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim() === "") return;
    if (node.nodeName === "BR" || node.nodeName === "HR") return;

    if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("podstranka")) {
      Array.from(node.children).forEach(child => {
        if (child.nodeName === "A") fragment.appendChild(child);
      });
      currentBody = null;
      return;
    }

    if (node.nodeName === "H3") {
      const toggle = document.createElement("h3");
      toggle.className = "nadp burger-main-toggle";
      toggle.textContent = node.textContent.trim();

      const sectionBody = document.createElement("div");
      sectionBody.className = "burger-main-section";
      sectionBody.id = `burger-main-section-${sectionIndex++}`;
      currentBody = sectionBody;

      toggle.addEventListener("click", () => {
        const opening = sectionBody.style.display !== "block";
        toggle.classList.toggle("burger-main-active", opening);
        toggle.setAttribute("aria-expanded", String(opening));
        sectionBody.style.display = opening ? "block" : "none";
        saveNavigationState(sectionBody.id, opening);
      });

      fragment.appendChild(toggle);
      fragment.appendChild(sectionBody);
      return;
    }

    if (currentBody) {
      currentBody.appendChild(node);
    } else {
      fragment.appendChild(node);
    }
  });

  menu.textContent = "";
  menu.appendChild(fragment);
  menu.querySelectorAll(".burger-main-toggle").forEach(toggle => {
    const sectionBody = toggle.nextElementSibling;
    if (sectionBody?.id) configureMenuToggle(toggle, sectionBody.id);
  });
  initializeSubmenuControls(menu);
  restoreNavigationState(menu);
  setupNavigationScrollPersistence(menu);
  menu.dataset.ready = "true";
}

function createPageAnchor(heading, index) {
  if (heading.id) return heading.id;

  const base = heading.textContent
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || `section-${index + 1}`;
  let id = base;
  let suffix = 2;

  while (document.getElementById(id)) {
    id = `${base}-${suffix}`;
    suffix += 1;
  }

  heading.id = id;
  return id;
}

function setupPageContentsNavigation() {
  if (getById("pageContents")) return;

  const headings = Array.from(document.querySelectorAll(
    "body .container .oof-warning3 > h1, body .container > h1"
  )).filter(heading => !heading.closest("#header, #footer"));

  if (headings.length < 2) return;

  const aside = document.createElement("aside");
  aside.id = "pageContents";
  aside.className = "page-contents";
  aside.setAttribute("aria-label", "On this page");

  const title = document.createElement("h2");
  title.textContent = "On this page";
  aside.appendChild(title);

  const navigation = document.createElement("nav");
  headings.forEach((heading, index) => {
    const link = document.createElement("a");
    link.href = `#${createPageAnchor(heading, index)}`;
    link.textContent = heading.textContent.trim();
    navigation.appendChild(link);
  });

  aside.appendChild(navigation);
  document.body.appendChild(aside);
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
    const response = await fetch(withSiteRoot("search-index.json"), { cache: "no-store" });
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
    return `<a class="site-search-result" href="${withSiteRoot(page.url)}"><b>${title}</b><span>${excerpt}</span></a>`;
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

function initializeHeaderNavigation() {
  normalizePageLinks();
  setupLanguageSwitcher();
  buildMegaMenu();
  setupBurgerMainSections();
  setupPageContentsNavigation();
  document.body.classList.add("oof-sidebar-layout");
}

function watchHeaderNavigation() {
  const headerRoot = getById("header");
  if (!headerRoot || headerRoot.dataset.navigationWatcher === "true") return;

  headerRoot.dataset.navigationWatcher = "true";

  if (headerRoot.querySelector("header")) {
    initializeHeaderNavigation();
    return;
  }

  const observer = new MutationObserver(() => {
    if (!headerRoot.querySelector("header")) return;
    initializeHeaderNavigation();
    observer.disconnect();
  });

  observer.observe(headerRoot, { childList: true });
}

watchHeaderNavigation();
document.addEventListener("DOMContentLoaded", watchHeaderNavigation);
loadCloudflareAnalytics();
