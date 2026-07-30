"use strict";

// side navigation bar
function toggleSidebar() {
  var sideNav = document.getElementById("side-nav");
  var main = document.getElementById("main");
  var topNavbar = document.getElementById("top-navbar");

  // On tablet/mobile the navigation is an overlay.  The old desktop class
  // keeps it off-screen there, so use the dedicated mobile state instead.
  if (window.matchMedia("(max-width: 1024px)").matches) {
    sideNav.classList.remove("toggle-active");
    main.classList.remove("toggle-active");
    topNavbar.classList.remove("toggle-active");
    sideNav.classList.toggle("sidebar-open");
    return;
  }

  sideNav.classList.remove("sidebar-open");
  sideNav.classList.toggle("toggle-active");
  main.classList.toggle("toggle-active");
  topNavbar.classList.toggle("toggle-active");
  // .manage-wrap is hidden in new design; skip it if not present
  var mw = document.querySelector(".manage-wrap");
  if (mw) mw.classList.toggle("toggle-active");
}

function closeMobileSidebar() {
  if (window.matchMedia("(max-width: 1024px)").matches) {
    document.getElementById("side-nav").classList.remove("sidebar-open");
  }
}

document.addEventListener("click", function (event) {
  var sideNav = document.getElementById("side-nav");
  var toggle = document.querySelector(".navbar-toggle-btn");
  if (!sideNav || !toggle || !sideNav.classList.contains("sidebar-open")) return;
  if (!sideNav.contains(event.target) && !toggle.contains(event.target)) closeMobileSidebar();
});

document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") closeMobileSidebar();
});

// #################################
// popup

var c = 0;
function pop() {
  if (c == 0) {
    document.getElementById("popup-box").style.display = "block";
    c = 1;
  } else {
    document.getElementById("popup-box").style.display = "none";
    c = 0;
  }
}

// const popupMessagesButtons = document.querySelectorAll('popup-btn-messages')

// popupMessagesButtons.forEach(button, () => {
//     button.addEventListener('click', () => {
//         document.getElementById('popup-box-messages').style.display = 'none';
//     })
// })

// const popupMessagesButtom = document.getElementById('popup-btn-messages')
// popupMessagesButtom.addEventListener('click', () => {
//     document.getElementById('popup-box-messages').style.display = 'none';
// })
// ##################################

// Example starter JavaScript for disabling form submissions if there are invalid fields
// Fetch all the forms we want to apply custom Bootstrap validation styles to
var forms = document.getElementsByClassName("needs-validation");

// Loop over them and prevent submission
Array.prototype.filter.call(forms, function (form) {
  form.addEventListener(
    "submit",
    function (event) {
      if (form.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    },
    false
  );
});
// ##################################

// extend and collapse
function showCourses(btn) {
  var btn = $(btn);

  if (collapsed) {
    btn.html('Collapse <i class="fas fa-angle-up"></i>');
    $(".hide").css("max-height", "unset");
    $(".white-shadow").css({ background: "unset", "z-index": "0" });
  } else {
    btn.html('Expand <i class="fas fa-angle-down"></i>');
    $(".hide").css("max-height", "150");
    $(".white-shadow").css({
      background: "linear-gradient(transparent 50%, rgba(255,255,255,.8) 80%)",
      "z-index": "2",
    });
  }
  collapsed = !collapsed;
}

$(document).ready(function () {
  $("#primary-search").focus(function () {
    $("#top-navbar").attr("class", "dim");
    $("#side-nav").css("pointer-events", "none");
    $("#main-content").css("pointer-events", "none");
  });
  $("#primary-search").focusout(function () {
    $("#top-navbar").removeAttr("class");
    $("#side-nav").css("pointer-events", "auto");
    $("#main-content").css("pointer-events", "auto");
  });
});
