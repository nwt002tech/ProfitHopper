// Casino-floor filter: show only games with a concrete public entry point.
// Exact-entry mode is ON by default so the first view is immediately usable
// while walking the casino floor.
(() => {
  const FALLBACK_EXACT_IDS = new Set([1, 2, 3, 8, 9, 10, 11, 12, 18, 35, 47]);
  let verifiedOnly = true;

  function exactIds() {
    return window.COUSATTA_EXACT_ENTRY_IDS instanceof Set
      ? window.COUSATTA_EXACT_ENTRY_IDS
      : FALLBACK_EXACT_IDS;
  }

  if (typeof matchesView === "function") {
    const originalMatchesView = matchesView;
    matchesView = function(game) {
      if (!originalMatchesView(game)) return false;
      if (verifiedOnly && !exactIds().has(game.p)) return false;
      return true;
    };
  }

  const checkbox = document.getElementById("verifiedOnly");
  if (checkbox) {
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      verifiedOnly = checkbox.checked;
      if (typeof selected !== "undefined") selected = null;
      if (typeof render === "function") render();
    });
  }

  const label = document.querySelector('label[for="verifiedOnly"] span');
  if (label) label.textContent = "Exact entry points only";

  if (typeof selected !== "undefined") selected = null;
  if (typeof render === "function") render();
})();
