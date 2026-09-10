/** Theme preference (BL-024) — localStorage only. */
(function () {
  var KEY = "dt-theme";

  function current() {
    try {
      var t = localStorage.getItem(KEY);
      if (t === "light" || t === "dark") return t;
    } catch (e) {}
    return document.documentElement.getAttribute("data-theme") || "dark";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch (e) {}
    document.querySelectorAll("[data-theme-label]").forEach(function (el) {
      el.textContent = theme === "light" ? "Light" : "Dark";
    });
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      btn.textContent = theme === "dark" ? "Use light theme" : "Use dark theme";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    apply(current());
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        apply(current() === "dark" ? "light" : "dark");
      });
    });
  });
})();
