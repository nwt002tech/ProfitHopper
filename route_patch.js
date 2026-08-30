// Casino-floor exact-entry route — 2026-08-29
// Every game in this route has a concrete public PLAY IF condition in floor_exact.js.

(() => {
  const revisedPriority = [
    1,  // Scarab — clearest short-cycle exact rule
    2,  // Golden Egypt — simple stored-coin rule
    3,  // Dancing Drums: Golden Drums — 4x+ stored multiplier
    18, // Ocean Magic — bubble in reels 1-3, not exiting
    8,  // Buffalo Ascension — center reel 7 + 3,360 ways
    47, // Wu Wang Zhe — inherited active scatter-pay spins
    11, // Zhao Cai Zhu — exact Blue/Green/Red entry counts
    12, // Rich Little Piggies — Blue 20+
    9,  // Buffalo Link — counter 1,600+
    10, // Phoenix Link — counter 1,500+
    35  // Wolf Run Eclipse — exact public meter entries; extreme variance
  ];

  try {
    if (typeof PRIORITY_ORDER !== "undefined" && Array.isArray(PRIORITY_ORDER)) {
      PRIORITY_ORDER.splice(0, PRIORITY_ORDER.length, ...revisedPriority);
      if (typeof selected !== "undefined") selected = null;
      if (typeof render === "function") render();
    }
  } catch (error) {
    console.warn("Coushatta exact-route patch could not be applied:", error);
  }
})();
