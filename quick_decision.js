// Casino-floor quick decisions for the Coushatta AP guide.
// The goal is deliberately conservative: if a defensible public +EV entry
// threshold is not verified, the card says DO NOT PLAY YET rather than
// inventing a number.

(() => {
  const Q = {
    1: {v:"PLAY", rule:"PLAY IF spin 1–4 has 2+ gold frames on reels 1–3, OR spin 5–9 has 3+ gold frames on reels 1–3.", skip:"Otherwise skip."},
    2: {v:"PLAY", rule:"PLAY IF at least 1 stored coin is showing on TWO of reels 1, 2 and 3, OR a wild reel is already active on reels 1–3.", skip:"Coins only on reels 4–5 = skip."},
    3: {v:"PLAY", rule:"PLAY IF the stored Golden Drums multiplier is 4x or higher. 5x+ is stronger.", skip:"2x–3x = skip."},
    4: {v:"WAIT", rule:"NO VERIFIED PUBLIC +EV COUNT. A screen with 5 locked gold scatters and spins remaining is a PHOTO/CHECK candidate, not an automatic play.", skip:"Do not auto-play 4 or fewer locked scatters from this guide."},
    5: {v:"WAIT", rule:"NO VERIFIED PUBLIC +EV THRESHOLD. Multiple 5x/6x/8x multipliers on the LEFT with 4+ spins remaining = PHOTO/CHECK.", skip:"Do not auto-play from multiplier count alone."},
    6: {v:"WAIT", rule:"NO VERIFIED PUBLIC +EV THRESHOLD. Multiple heavily loaded reels with 2–3 spins left = PHOTO/CHECK.", skip:"Do not auto-play one lightly loaded reel."},
    7: {v:"WAIT", rule:"NO VERIFIED PUBLIC +EV THRESHOLD. Photograph the locked cash symbols and every remaining-spin indicator.", skip:"Do not play just because the screen looks busy."},
    8: {v:"WAIT", rule:"NO VERIFIED PUBLIC +EV THRESHOLD. Reels 2–4 at 6–7 rows high = PHOTO/CHECK.", skip:"4/4/4 or only one reel at 5 = skip."},
    9: {v:"WAIT", rule:"COUNTER MUST HIT BEFORE 1800, but the exact profitable entry depends on bet/RTP. No public single play number is verified here.", skip:"Without a calculator/verified threshold, do not auto-play from the counter."},
    10:{v:"WAIT", rule:"COUNTER MUST HIT BEFORE 1888, but the exact profitable entry depends on bet/RTP and reset. No public single play number is verified here.", skip:"Without a calculator/verified threshold, do not auto-play from the counter."},
    11:{v:"WAIT", rule:"MHB CEILINGS: Blue 40, Green 60, Red 100. If you see 39 / 59 / 99, STOP and photograph it before playing.", skip:"Those ceilings are not the same thing as a verified +EV entry threshold."},
    12:{v:"WAIT", rule:"NO TRUSTWORTHY PUBLIC EXACT ENTRY NUMBER. The pigs trigger randomly; even Blue 100 is not guaranteed to trigger.", skip:"Do not use 18, 25, or pig 'fatness' as an automatic play rule."},
    13:{v:"WAIT", rule:"NO VERIFIED ONE-NUMBER THRESHOLD. Photograph bubble values, sizes and exact vertical positions.", skip:"Do not play from bubble count alone."},
    14:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV ENTRY. Active multiplied wild reels or several reels at 2-of-3 coins = PHOTO/CHECK.", skip:"Two ordinary coins on one reel is not an automatic play."},
    15:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV ENTRY. Two or more active Coin Catch reels with 2–3 spins left = PHOTO/CHECK.", skip:"One active reel alone = do not auto-play."},
    16:{v:"WAIT", rule:"NO VERIFIED DRAGON SPHERE ENTRY GRID. Photograph all sphere positions/values at the exact wager.", skip:"Do not copy Ocean Magic thresholds onto Dragon Sphere."},
    17:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV ENTRY. Actual jeweled/glowing BOOST bags = PHOTO/CHECK; check every bet level.", skip:"A merely large-looking bag = skip."},
    18:{v:"PLAY", rule:"CLASSIC OCEAN MAGIC: PLAY when a bubble will be on the NEXT SPIN in reels 1–3 and is not already at the top/exiting row.", skip:"No useful bubble in reels 1–3 = skip. Bubble Boost is a separate calculation."},
    19:{v:"WAIT", rule:"NO VERIFIED BUBBLE BOOST +EV GRID. The paid Boost changes the math even when the bubbles look like classic Ocean Magic.", skip:"Do not copy the classic Ocean Magic shortcut here."},
    20:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV GRID TOTAL. Photograph all 20 stored prize values; several unusually large values = PHOTO/CHECK.", skip:"Do not play based on number of lit boxes."},
    21:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV THRESHOLD. High-value/Wheel coins already on the BOTTOM row = PHOTO/CHECK.", skip:"A full grid of small values is not an automatic play."},
    22:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV COUNT. Photograph the numeric Green, Purple and Gold Money Ball counts.", skip:"Do not judge by pot animation/fullness."},
    23:{v:"WAIT", rule:"PERSISTENCE IS VERIFIED, but no public exact +EV frame count is verified. Several upgraded frames = PHOTO/CHECK.", skip:"Do not auto-play one upgraded house/frame."},
    24:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV ENTRY. If Pay Upgrade spins are visibly remaining, photograph the exact multiplier/state and wager.", skip:"Do not chase a fresh Pay Upgrade state."},
    25:{v:"WAIT", rule:"DISPLAYED RANGES: Mega 250–350, Grand 200–250, Major 150–200, Minor 100–150, Mini 75–125. No exact +EV entry combo is verified publicly.", skip:"Do not use one arbitrary percentage for all five meters."},
    26:{v:"WAIT", rule:"FIVE-METER GAME, but no verified public +EV combination is available here.", skip:"Do not auto-play because one meter looks high."},
    27:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV ENTRY. Check every bet level and photograph all gem/meter values together.", skip:"Do not use 80% as a guaranteed play threshold."},
    28:{v:"WAIT", rule:"DOCUMENTED MHB VERSION: lower $200→$500, upper $4,000→$5,000. PHOTO/CHECK near about $490 or $4,945+; those are average-hit areas, not guaranteed +EV entries.", skip:"Do not auto-play merely because a meter is halfway up."},
    29:{v:"WAIT", rule:"PROGRESSIVE OVERLAY ONLY. At 1¢ baseline Grand resets $5,000 and Major $500, but no verified public +EV jackpot amount is available here.", skip:"Above reset does not automatically mean +EV."},
    30:{v:"WAIT", rule:"NO VERIFIED EXACT THREE-METER ENTRY. A high GREEN meter with supportive Red/Blue state = PHOTO/CHECK.", skip:"Blue 99 by itself = do not auto-play."},
    31:{v:"SKIP", rule:"DO NOT PLAY FROM A PIG/BANK COUNT. The verified Lock It Link rules do not establish a pre-trigger persistent countdown for this version.", skip:"Skip unless a clearly persistent live counter can be verified on the cabinet."},
    32:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV RING COUNT. Multiple active glowing rings with most life segments remaining = PHOTO/CHECK.", skip:"Do not use a vague 'looks close' rule."},
    33:{v:"SKIP", rule:"NO VERIFIED PUBLIC PLAY THRESHOLD for this exact Luckymon Evolution configuration.", skip:"Skip unless the exact persistent mechanic is verified from the live screen."},
    34:{v:"SKIP", rule:"NO VERIFIED PUBLIC PLAY THRESHOLD for this exact Piggy Parade configuration.", skip:"Do not play from pig/progress appearance alone."},
    35:{v:"SKIP", rule:"PUBLIC SOURCES CONFLICT on whether the Eclipse meters are true MHB counters. No exact play number is trustworthy yet.", skip:"Skip unless the cabinet itself shows explicit must-hit/must-award wording and the threshold is verified."},
    36:{v:"SKIP", rule:"NO VERIFIED BUFFALO DIAMOND EXTREME ENTRY RULE. Do not import rules from other Buffalo Diamond versions.", skip:"Skip unless this exact Extreme state is verified."},
    37:{v:"WAIT", rule:"BUFFALO COLLECT MUST HIT BEFORE 1800, but no verified public profitable entry count is available here.", skip:"Do not auto-play just because the counter is high."},
    38:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV ORB LAYOUT. Multiple high-value orbs with several rows of travel left = PHOTO/CHECK.", skip:"Do not auto-play from orb count alone."},
    39:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV WILD LAYOUT. Multiple Red/Gold Wilds low on the reels with several upward moves left = PHOTO/CHECK.", skip:"Do not switch bet level after finding a state."},
    40:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV STICKY-WILD COUNT. Five active Wilds with 2 spins left = IMPORTANT PHOTO/CHECK state.", skip:"Do not treat 5 Wilds as guaranteed +EV without layout/wager verification."},
    41:{v:"WAIT", rule:"READ THE ACTUAL LIGHTNING FREE MHB METER AND ITS PRINTED CEILING. No universal entry count is verified for all 10 Year Storm configurations.", skip:"Do not use Phoenix Link's 1888 number here."},
    42:{v:"WAIT", rule:"THREE COUNTERS MUST AWARD BY 15. If Red, Green or Blue is at 14, STOP and photograph the full three-counter state and wager.", skip:"14 is a critical check point, not a universal guaranteed +EV rule."},
    43:{v:"WAIT", rule:"NO VERIFIED PUBLIC BRONZE/SILVER/GOLD ENTRY COMBINATION. Photograph all three progression values.", skip:"Do not auto-play one advanced meter."},
    44:{v:"WAIT", rule:"27 MUST-HIT-BY METERS: compare each current amount to its printed ceiling. No verified universal % entry rule is available.", skip:"Do not play because one jackpot merely looks large."},
    45:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV FIREBALL LAYOUT. Multiple loaded reels with 2–3 spins left = PHOTO/CHECK.", skip:"Do not apply this to non-Cash-Falls Ultimate Fire Link titles."},
    46:{v:"WAIT", rule:"MASTER MULTIPLIER BUILDS TO 18x, but no verified public +EV entry multiplier is available here.", skip:"Do not assume 18x is 'due' or that a lower multiplier is automatically playable."},
    47:{v:"PLAY", rule:"PLAY IF a character is ALREADY ACTIVE as a scatter-pay and inherited scatter spins remain, at the SAME wager.", skip:"No active scatter-pay spins = do not auto-play from token progress alone."},
    48:{v:"SKIP", rule:"NO VERIFIED TREASURE BOX ENTRY RULE for Dizzy/Mermaid.", skip:"Do not copy classic Ocean Magic thresholds."},
    49:{v:"WAIT", rule:"FIRST identify the exact Wonder 4 variant. Collection has red/blue Free Games meters, but no verified public +EV meter number is available here.", skip:"Do not apply Collection rules to Boost, Revolution, Buffalo or other Wonder 4 versions."},
    50:{v:"SKIP", rule:"NO VERIFIED CARRYOVER +EV TRAY THRESHOLD. A full-looking Super Push tray is not enough.", skip:"Skip unless persistent carryover and token value are verified."},
    51:{v:"SKIP", rule:"POT FULLNESS IS NOT VERIFIED PLAYER EQUITY. No exact inherited-state play threshold is established.", skip:"Do not play from Tiger/Dragon/Ox pot fullness."},
    52:{v:"WAIT", rule:"NO VERIFIED PUBLIC +EV BOMB PATTERN. Dense connected bombs plus an active favorable fuse/countdown = PHOTO/CHECK.", skip:"Do not play from bomb count alone."}
  };

  const style = document.createElement("style");
  style.textContent = `
    .quick-decision{border:3px solid #10243e;border-radius:14px;padding:12px;margin:0 0 10px;background:#fff;box-shadow:0 3px 10px rgba(16,36,62,.08)}
    .quick-decision.play{border-color:#137a4b;background:#eef9f2}
    .quick-decision.wait{border-color:#b36b00;background:#fff8e8}
    .quick-decision.skip{border-color:#a23b3b;background:#fff0f0}
    .qd-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}
    .qd-label{font-size:.67rem;font-weight:900;letter-spacing:.06em;color:#5b677a}
    .qd-verdict{border-radius:999px;padding:6px 9px;font-size:.7rem;font-weight:900;white-space:nowrap}
    .play .qd-verdict{background:#137a4b;color:#fff}.wait .qd-verdict{background:#b36b00;color:#fff}.skip .qd-verdict{background:#a23b3b;color:#fff}
    .qd-rule{font-size:1rem;line-height:1.32;font-weight:850;color:#10243e}
    .qd-skip{font-size:.79rem;line-height:1.3;color:#5b677a;margin-top:8px;padding-top:8px;border-top:1px solid rgba(16,36,62,.15)}
    .more-details{border:1px solid #d9e0e8;border-radius:12px;margin:9px 0;background:#f9fbfd;overflow:hidden}
    .more-details>summary{padding:11px;font-size:.78rem;font-weight:850;color:#10243e;cursor:pointer;list-style:none}
    .more-details>summary::-webkit-details-marker{display:none}
    .more-details>summary:after{content:"＋";float:right;color:#5b677a}.more-details[open]>summary:after{content:"−"}
    .more-details-inner{padding:0 8px 8px}
  `;
  document.head.appendChild(style);

  function verdictText(v){
    if(v === "PLAY") return "PLAY";
    if(v === "SKIP") return "SKIP";
    return "DO NOT PLAY YET";
  }

  function applyQuickDecision(){
    if(typeof selected === "undefined" || !selected) return;
    const data = Q[selected];
    const body = document.querySelector("#card .body");
    if(!body || !data) return;

    body.querySelectorAll(".quick-decision,.more-details").forEach((el)=>el.remove());

    const panel = document.createElement("section");
    panel.className = `quick-decision ${data.v.toLowerCase()}`;
    panel.innerHTML = `
      <div class="qd-top"><span class="qd-label">QUICK DECISION</span><span class="qd-verdict">${verdictText(data.v)}</span></div>
      <div class="qd-rule">${data.rule}</div>
      <div class="qd-skip">${data.skip}</div>`;
    body.prepend(panel);

    // The first three boxes are the long research explanation. Keep the floor map visible,
    // but collapse research text and the illustrated diagram so they cannot be mistaken
    // for the actual play threshold.
    const directBoxes = [...body.children].filter((el)=>el.classList && el.classList.contains("box"));
    const researchBoxes = directBoxes.slice(0, 3);
    const diagram = body.querySelector(":scope > .diagram-details");
    if(diagram) {
      diagram.removeAttribute("open");
      const summary = diagram.querySelector("summary");
      if(summary) summary.textContent = "Optional recognition diagram — NOT a play threshold";
    }

    if(researchBoxes.length || diagram){
      const details = document.createElement("details");
      details.className = "more-details";
      details.innerHTML = `<summary>More explanation / recognition help</summary><div class="more-details-inner"></div>`;
      const inner = details.querySelector(".more-details-inner");
      researchBoxes.forEach((box)=>inner.appendChild(box));
      if(diagram) inner.appendChild(diagram);

      const mapBox = [...body.children].find((el)=>el.classList && el.classList.contains("box"));
      if(mapBox) body.insertBefore(details, mapBox);
      else body.appendChild(details);
    }
  }

  if(typeof renderCardOnly === "function"){
    const originalRenderCardOnly = renderCardOnly;
    renderCardOnly = function(){
      originalRenderCardOnly();
      applyQuickDecision();
    };
  }

  if(typeof render === "function") render();
})();
