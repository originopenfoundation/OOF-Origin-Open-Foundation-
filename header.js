function toggleMenu(menuId) {
  const menus = ["standardsMenu", "oofMenu", "mipMenu", "osMenu", "AccMenu", "GovernanceMenu", "burgerMenu"];

  menus.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    if (id === menuId) {
      const isOpen = el.style.display === "block";
      el.style.display = isOpen ? "none" : "block";
    } else {
      el.style.display = "none";
    }
  });
}
