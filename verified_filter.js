// Casino-floor filter: show only games with a concrete public entry point.
// UX rules:
//   • Site opens in Exact Route with exact-entry filtering ON.
//   • Tapping All Cards turns exact-entry filtering OFF so all 52 cards can appear.
//   • Tapping Exact Route turns exact-entry filtering ON.
//   • The checkbox can still be changed manually after selecting a tab.
(() => {
  const FALLBACK_EXACT_IDS = new Set([1, 2, 3, 8, 9, 10, 11, 12, 18, 35, 47]);
  let verifiedOnly = true;

  function exactIds() {
    return window.COUSATTA_EXACT_ENTRY_IDS instanceof Set
      ? window.COUSATTA_EXACT_ENTRY_IDS
      : FALLBACK_EXACT_IDS;
  }

  function exactCount() {
    return exactIds().size;
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
  const label = document.querySelector('label[for="verifiedOnly"] span');

  function updateCheckboxUI() {
    if (checkbox) checkbox.checked = verifiedOnly;
    if (label) {
      label.textContent = `Exact entry points only (${exactCount()})`;
    }
  }

  function setVerifiedOnly(value, shouldRender = true) {
    verifiedOnly = Boolean(value);
    updateCheckboxUI();
    if (typeof selected !== "undefined") selected = null;
    if (shouldRender && typeof render === "function") render();
  }

  if (checkbox) {
    checkbox.addEventListener("change", () => {
      setVerifiedOnly(checkbox.checked, true);
    });
  }

  // Synchronize the top tabs with the filter. app.js owns the tab change itself;
  // this listener runs afterward and makes the filter match the user's intent.
  const tabs = document.getElementById("tabs");
  if (tabs) {
    tabs.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-tab]");
      if (!button) return;

      if (button.dataset.tab === "all") {
        setVerifiedOnly(false, true);
      } else if (button.dataset.tab === "route") {
        setVerifiedOnly(true, true);
      }
      // Favorites preserves the user's current exact-entry preference.
    });
  }

  // The stats buttons are alternate entry points to the same views.
  const allStat = document.getElementById("allGamesStat");
  if (allStat) {
    allStat.addEventListener("click", () => setVerifiedOnly(false, true));
  }

  const routeStat = document.getElementById("priorityStat");
  if (routeStat) {
    routeStat.addEventListener("click", () => setVerifiedOnly(true, true));
  }

  // Open in casino-floor mode instead of showing an "All Cards" tab with an
  // exact-only checkbox simultaneously. All Cards remains one tap away.
  if (typeof tab !== "undefined") tab = "route";
  if (typeof filter !== "undefined") filter = "ALL";
  if (typeof query !== "undefined") query = "";
  verifiedOnly = true;
  updateCheckboxUI();
  if (typeof selected !== "undefined") selected = null;
  if (typeof render === "function") render();
})();
