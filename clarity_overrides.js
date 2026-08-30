// Final clarity overrides for rules where older explanatory copy could conflict
// with the casino-floor quick decision.
(() => {
  if (!Array.isArray(window.G)) return;

  const patch = (id, values) => {
    const game = window.G.find((item) => item.p === id);
    if (game) Object.assign(game, values);
  };

  patch(12, {
    s: "VERIFY",
    v: "pigs",
    l: "Rich Little Piggies has three persistent pig features, but the pigs trigger randomly rather than at a must-hit-by count. The Blue pig can build to 100 free games and still is not guaranteed to trigger.",
    a: "There is no trustworthy free public universal +EV Blue-pig entry number. Do not use 18 or 25 as an automatic play threshold. If a highly developed multi-pig state is found, photograph all three pigs and the wager for a state-specific decision.",
    n: "Pig size does not make the feature more likely to trigger. Blue 100 is a cap, not a must-hit-by."
  });

  patch(18, {
    s: "RULE",
    v: "ocean",
    l: "Wild bubbles persist and rise one row after each paid spin. Their next-spin reel and row determine the inherited value.",
    a: "Fast conservative floor rule for classic Ocean Magic: play when a bubble will be on the NEXT SPIN in reels 1, 2 or 3 and is not already at the top/exiting row. Stop when that qualifying bubble state is gone.",
    n: "Bubble Boost changes the wager/math and should not automatically use this shortcut. Do not count bubbles without checking their next-spin positions."
  });
})();
