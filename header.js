function toggleMenu(menuId) {
  const menus = ["standardsMenu", "oofMenu", "mipMenu", "osMenu", "AccMenu", "GovernanceMenu"];

  menus.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    if (id === menuId) {
      el.style.display = (el.style.display === "block") ? "none" : "block";
    } else {
      el.style.display = "none";
    }
  });
}

function toggleBurger() {
  const menu = document.getElementById("burgerMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

document.addEventListener("click", function(e) {
  const menu = document.getElementById("burgerMenu");
  const burger = document.querySelector(".burger");

  if (!menu.contains(e.target) && !burger.contains(e.target)) {
    menu.style.display = "none";
  }
});
