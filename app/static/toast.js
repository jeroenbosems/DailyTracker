/** G3 — auto-dismiss celebration toasts (no modals). */
(function () {
  function arm(el) {
    if (!el || el.dataset.toastArmed) return;
    el.dataset.toastArmed = "1";
    el.classList.add("toast");
    window.setTimeout(function () {
      el.classList.add("toast-out");
      window.setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 320);
    }, 4200);
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".flash").forEach(arm);
  });
})();
