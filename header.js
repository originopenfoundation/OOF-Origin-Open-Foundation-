function toggleStandards(){
var menu = document.getElementById("standardsMenu");

if(menu.style.display === "block"){
menu.style.display = "none";
}else{
menu.style.display = "block";
}
}

function toggleOOF(){
var menu = document.getElementById("oofMenu");

if(menu.style.display === "block"){
menu.style.display = "none";
}else{
menu.style.display = "block";
}
}
function toggleMIP(){
  var menu = document.getElementById("mipMenu");

  if(menu.style.display === "block"){
    menu.style.display = "none";
  }else{
    menu.style.display = "block";
  }
}
function toggleOS(){
  var menu = document.getElementById("osMenu");

  if(menu.style.display === "block"){
    menu.style.display = "none";
  }else{
    menu.style.display = "block";
  }
}
function toggleAcc(){
  var menu = document.getElementById("AccMenu");

  if(menu.style.display === "block"){
    menu.style.display = "none";
  }else{
    menu.style.display = "block";
  }
}
function toggleMenu(menuId) {
  const menus = ["standardsMenu", "oofMenu", "mipMenu", "osMenu", "AccMenu"];

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
