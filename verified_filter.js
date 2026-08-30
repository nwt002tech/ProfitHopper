// Optional casino-floor filter: hide every game that does not currently have
// a verified, actionable PLAY condition in quick_decision.js.
(() => {
  const VERIFIED_PLAY_IDS = new Set([1, 2, 3, 18, 47]);
  let verifiedOnly = false;

  if (typeof matchesView === "function") {
    const originalMatchesView = matchesView;
    matchesView = function(game) {
      if (!originalMatchesView(game)) return false;
      if (verifiedOnly && !VERIFIED_PLAY_IDS.has(game.p)) return false;
      return true;
    };
  }

  const checkbox = document.getElementById("verifiedOnly");
  if (checkbox) {
    checkbox.checked = false;
    checkbox.addEventListener("change", () => {
      verifiedOnly = checkbox.checked;
      if (typeof selected !== "undefined") selected = null;
      if (typeof render === "function") render();
    });
  }

  if (typeof render === "function") render();
})();
