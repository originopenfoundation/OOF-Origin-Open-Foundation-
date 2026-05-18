function toggleMenu(menuId) {
  const menus = ["standardsMenu", "oofMenu", "mipMenu", "osMenu", "AccMenu", "GovernanceMenu", "burgerMenu"];

  menus.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    el.style.display = (id === menuId && el.style.display !== "block") 
      ? "block" 
      : "none";
  });
}
