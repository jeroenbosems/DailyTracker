/** Today keyboard shortcuts (BL-023). Ignored while focus is in a form field. */
(function () {
  function typingTarget(el) {
    if (!el || el === document.body) return false;
    const tag = (el.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    if (el.isContentEditable) return true;
    return false;
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.defaultPrevented || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (typingTarget(ev.target)) return;

    const key = ev.key;
    if (key === "c" || key === "C") {
      const form = document.getElementById("shortcut-complete-next-step");
      if (!form) return;
      ev.preventDefault();
      form.requestSubmit ? form.requestSubmit() : form.submit();
      return;
    }
    if (key === "r" || key === "R") {
      ev.preventDefault();
      window.location.href = "/review";
    }
  });
})();
