const menus = ["oofMenu", "authMenu", "minfraMenu", "osMenu", "toolsMenu", "mappingMenu", "mapsMenu", "standardsMenu", "GovernanceMenu", "oprealMenu", "AISMenu", "mipMenu", "AccMenu"];

function closeNestedSubmenus(rootSelector) {
  document.querySelectorAll(rootSelector + " .tools-submenu").forEach(item => {
    item.style.display = "none";
  });
}

function closeToolsSubmenus() {
  closeNestedSubmenus("#toolsMenu");
}

function closeMapsSubmenus() {
  closeNestedSubmenus("#mapsMenu");
}

function toggleMenu(menuId) {
  menus.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    if (id === menuId) {
      const isOpen = el.style.display === "block";
      el.style.display = isOpen ? "none" : "block";
      if (id === "toolsMenu" && isOpen) {
        closeToolsSubmenus();
      }
      if (id === "mapsMenu" && isOpen) {
        closeMapsSubmenus();
      }
    } else {
      el.style.display = "none";
      if (menuId !== "toolsMenu") {
        closeToolsSubmenus();
      }
      if (menuId !== "mapsMenu") {
        closeMapsSubmenus();
      }
    }
  });
}

function toggleBurger() {
  const menu = document.getElementById("burgerMenu");
  if (!menu) return;

  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

function toggleBurgerSub(submenuId) {
  const submenu = document.getElementById(submenuId);
  if (!submenu) return;

  submenu.style.display = (submenu.style.display === "block") ? "none" : "block";
}

function toggleToolsSub(submenuId, event) {
  toggleNestedSub(submenuId, event);
}

function toggleNestedSub(submenuId, event) {
  if (event) event.stopPropagation();

  const submenu = document.getElementById(submenuId);
  if (!submenu) return;

  const container = submenu.parentElement?.parentElement || document.getElementById("toolsMenu");
  const siblingSubmenus = Array.from(container.children)
    .filter(item => item.classList && item.classList.contains("tools-menu-item"))
    .map(item => Array.from(item.children).find(child => child.classList && child.classList.contains("tools-submenu")))
    .filter(Boolean);

  siblingSubmenus.forEach(item => {
    if (item.id !== submenuId) {
      item.style.display = "none";
      item.querySelectorAll(".tools-submenu").forEach(child => {
        child.style.display = "none";
      });
    }
  });

  submenu.style.display = (submenu.style.display === "block") ? "none" : "block";
}

document.addEventListener("click", function(e) {
  const menu = document.getElementById("burgerMenu");
  const burger = document.querySelector(".burger");

  if (menu && burger && !menu.contains(e.target) && !burger.contains(e.target)) {
    menu.style.display = "none";
  }

  const toolsMenu = document.getElementById("toolsMenu");
  if (toolsMenu && !toolsMenu.contains(e.target) && !e.target.closest("[onclick*=\"toolsMenu\"]")) {
    closeToolsSubmenus();
  }

  const mapsMenu = document.getElementById("mapsMenu");
  if (mapsMenu && !mapsMenu.contains(e.target) && !e.target.closest("[onclick*=\"mapsMenu\"]")) {
    closeMapsSubmenus();
  }

  if (!e.target.closest(".dropdown") && !e.target.closest(".burger") && !e.target.closest(".burger-menu")) {
    menus.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = "none";
    });
    closeToolsSubmenus();
    closeMapsSubmenus();
  }
});
