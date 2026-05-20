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

function toggleBurger() {
  const menu = document.getElementById("burgerMenu");
  if (!menu) return;

  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

document.addEventListener("click", function(e) {
  const menu = document.getElementById("burgerMenu");
  const burger = document.querySelector(".burger");

  if (menu && burger && !menu.contains(e.target) && !burger.contains(e.target)) {
    menu.style.display = "none";
  }
});
