// Casino-floor exact entry overrides.
// Loaded after quick_decision.js. Only rules with a concrete public entry point
// belong here. Games not listed remain hidden when Exact Entry Points Only is on.

(() => {
  const EXACT_ENTRY = {
    1: {
      rule: "PLAY IF spins 1–4 show 2+ gold frames on reels 1–3, OR spins 5–9 show 3+ gold frames on reels 1–3.",
      stop: "Stop/recheck after spin 10 resets the cycle."
    },
    2: {
      rule: "PLAY IF at least 1 stored coin is showing on TWO of reels 1–3, OR a wild reel is already active on reels 1–3.",
      stop: "Coins only on reels 4–5 = SKIP. Stay on the same bet/state while it qualifies."
    },
    3: {
      rule: "PLAY IF the Golden Drums stored multiplier is 4x or higher. 5x+ is stronger.",
      stop: "2x–3x = SKIP. Stop/recheck when the multiplier is used/reset."
    },
    8: {
      rule: "PLAY ONLY IF the CENTER / 3rd reel is at level 7 AND the display shows at least 3,360 ways.",
      stop: "If either condition is missing, SKIP. Recheck after the feature/reset changes the reel heights."
    },
    9: {
      rule: "PLAY IF the Buffalo free-feature counter is 1,600 or higher.",
      stop: "Must hit before 1,800. Play the qualifying wager until the feature triggers/resets, then stop and recheck."
    },
    10: {
      rule: "PLAY IF the Phoenix feature counter is 1,500 or higher.",
      stop: "Must hit before 1,888. Play the qualifying wager until the feature triggers/resets, then stop and recheck."
    },
    11: {
      rule: "PLAY IF Blue ≥ 28, Green ≥ 41, Red ≥ 87, OR Blue + Green combined ≥ 60.",
      stop: "Check all three lantern numbers before betting. Recheck after any meter awards/resets."
    },
    12: {
      rule: "PLAY IF the BLUE pig shows 20+ free games at the SAME bet level.",
      stop: "Below 20 = SKIP. Continue only while that same Blue-pig state remains; stop/recheck after it triggers/resets."
    },
    18: {
      rule: "PLAY IF at least one persistent bubble is in reels/columns 1–3 AND it is not already on the top/exiting row.",
      stop: "No useful bubble in reels 1–3 = SKIP. Recheck after each spin as bubbles move upward."
    },
    35: {
      rule: "PLAY IF Mini (blue) ≥ 30, Minor (purple) ≥ 40, OR Major (orange) ≥ 65. NEVER chase the Mega/green meter.",
      stop: "If none of Mini/Minor/Major meet those numbers, SKIP. Recheck after a meter awards/resets."
    },
    47: {
      rule: "PLAY IF a character is ALREADY ACTIVE as a scatter-pay and inherited scatter spins remain at the SAME wager.",
      stop: "No active scatter-pay spins = SKIP. Stop/recheck when the inherited active spins end."
    }
  };

  window.COUSATTA_EXACT_ENTRY_IDS = new Set(
    Object.keys(EXACT_ENTRY).map((id) => Number(id))
  );

  function applyExactEntry() {
    if (typeof selected === "undefined" || !selected) return;
    const data = EXACT_ENTRY[selected];
    if (!data) return;

    const panel = document.querySelector("#card .quick-decision");
    if (!panel) return;

    panel.classList.remove("wait", "skip");
    panel.classList.add("play");

    const verdict = panel.querySelector(".qd-verdict");
    const rule = panel.querySelector(".qd-rule");
    const skip = panel.querySelector(".qd-skip");

    if (verdict) verdict.textContent = "PLAY";
    if (rule) rule.textContent = data.rule;
    if (skip) skip.textContent = data.stop;
  }

  if (typeof renderCardOnly === "function") {
    const originalRenderCardOnly = renderCardOnly;
    renderCardOnly = function() {
      originalRenderCardOnly();
      applyExactEntry();
    };
  }

  if (typeof render === "function") {
    const originalRender = render;
    render = function() {
      originalRender();
      applyExactEntry();
    };
  }

  applyExactEntry();
})();
