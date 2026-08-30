// Priority-route refresh — 2026-08-29
// Run after app.js so the existing route array can be reordered without
// duplicating the full rendering code.

(() => {
  const revisedPriority = [
    1,  // Scarab — fixed 10-spin cycle / clear screen rule
    2,  // Golden Egypt — clear stored-coin rule
    3,  // Dancing Drums: Golden Drums — published multiplier floor
    15, // Coin Catch Cove — short inherited 3-spin windows; 2+ active reels preferred
    47, // Wu Wang Zhe — active inherited scatter-pay spins are immediately actionable
    11, // Zhao Cai Zhu — three visible must-hit-by lantern meters
    42, // Legend of the 3x2x Phoenix — three must-hit-by-15 counters
    37, // Buffalo Cash — visible Buffalo Collect counter approaching 1,800
    9,  // Buffalo Link — visible free-feature counter approaching ~1,800
    10, // Phoenix Link — visible counter approaching ~1,888
    18, // Ocean Magic — short-lived persistent bubbles with a public position rule
    12  // Rich Little Piggies — Blue 18+ public screening territory
  ];

  try {
    if (typeof PRIORITY_ORDER !== "undefined" && Array.isArray(PRIORITY_ORDER)) {
      PRIORITY_ORDER.splice(0, PRIORITY_ORDER.length, ...revisedPriority);
      if (typeof selected !== "undefined") selected = null;
      if (typeof render === "function") render();
    }
  } catch (error) {
    console.warn("Coushatta priority-route patch could not be applied:", error);
  }
})();
