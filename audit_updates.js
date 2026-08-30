// Coushatta AP audit refinements — 2026-08-29
// Loaded after games.js/images.js so verified research can refine individual cards
// without duplicating the full inventory file.

(() => {
  const updates = {
    13: {
      s: "SCOUT",
      v: "bubbles",
      l: "Bubble Mania uses true persistent cash/jackpot bubbles. Bubbles remain for the next player and rise one row on every paid spin until they leave the top of the screen; matching the GEM trigger to a bubble awards that bubble's credit or jackpot prize.",
      a: "Prioritize higher-value bubbles that still have useful vertical life and favorable positions. Multiple valuable bubbles with several rows left are much stronger than one small bubble about to exit. There is no safe one-number entry rule.",
      n: "Do not count bubbles alone. Prize value, size/coverage, vertical position and remaining life all matter; a top-row low-value bubble can be a weak state."
    },
    14: {
      s: "SCOUT",
      v: "coins",
      l: "Reels 2, 3 and 4 each store collected 1x, 2x and 3x coins. Collecting three coins above a reel turns that entire reel Wild for the next three base games played with the same bet option; multiplier coins create multiplied Wild spins.",
      a: "Best inherited states are active Wild-reel spins, especially 2x/3x, or several middle reels already at 2 of 3 with multiplier coins stored. Evaluate reels 2-4 together and stay on the same bet option.",
      n: "Two ordinary coins above a reel can be a trap because the third coin may be harder to collect. Coin/Wild states are saved separately for each bet option."
    },
    15: {
      s: "SCOUT",
      v: "coin_counters",
      l: "A blue gem activates its reel for a three-spin Coin Catch window. The frame spans all four positions on that reel; Cash-on-Reels symbols landing inside are collected, and another blue gem refreshes that reel's three-spin window.",
      a: "A single active reel is marginal. Prioritize two or more simultaneously active reels, especially with 2-3 spins/diamonds remaining. More active reels and more remaining spins create the stronger inherited state.",
      n: "An active reel can still go three spins without catching a coin. Read how many reels are active and how many spins remain instead of chasing a decorative treasure screen."
    },
    16: {
      s: "VERIFY",
      v: "spheres",
      l: "IGT describes Dragon Sphere as a derivative of Ocean Magic with waterfall-style play, which supports an inherited moving-object mechanic. Public free documentation does not establish that this Coushatta Free Games version uses the exact same position values or entry squares as classic Ocean Magic.",
      a: "Check every wager for persistent spheres and photograph the complete reel state. Favor lower/longer-lived valuable spheres, but keep this title verify-first until the exact Coushatta rules are confirmed.",
      n: "Do not copy Ocean Magic's reel/column thresholds onto Dragon Sphere merely because IGT calls it a derivative."
    },
    17: {
      s: "SCOUT",
      v: "boost",
      l: "Only the BOOST Peacock/Tiger versions carry the useful persistent state. Each of the three bags can reach a visible jeweled/glowing BOOST state stored by bet level; a boosted bag materially improves its associated bonus.",
      a: "One bag visibly in BOOST is the minimum serious candidate. Two boosted bags create a stronger combined/Super setup; all three boosted bags create the strongest Mega-style setup. Check every denomination and bet level.",
      n: "A bag merely looking large does not make its bonus closer to triggering. Look for the actual jeweled/glowing BOOST state, and do not apply this to ordinary Dragon/Panda versions."
    },
    18: {
      s: "RULE",
      v: "ocean",
      l: "Wild bubbles persist between players and rise one row after each spin until they leave the top. Ocean Magic pays left-to-right, so bubbles farther left and lower on the screen generally carry more inherited value and more remaining life.",
      a: "Fast public screen rule: useful bubbles on reels 1-3 are playable territory; reel 4 is borderline and reel 5 is usually poor. Check every bet level and both normal/Bubble Boost states because each can store a different screen.",
      n: "Do not use bubble count alone. A bubble's reel, row and remaining life matter. Bubble Boost costs more and should be evaluated as its own stored state."
    },
    21: {
      s: "SCOUT",
      v: "grid",
      l: "The 5x7 prize-coin grid is persistent. Stored coins range from about 0.625x to 200x the bet plus Wheel symbols; coins leave only through the Coin Collect feature, which awards from the bottom row and shifts that column downward.",
      a: "Prioritize grids with large values or Wheel symbols already in the bottom row, plus valuable coins stacked immediately above them. Bottom-position value is more actionable than the same value stranded high in the grid.",
      n: "A nearly full grid is not automatically good if it is loaded with small values. Read the actual multipliers, Wheel symbols and how far the best prizes are from the bottom."
    },
    22: {
      s: "SCOUT",
      v: "treasure",
      l: "Green, Purple and Gold Money Ball counts persist in separate pots. When a matching Money Ball lands it can trigger that pot; otherwise the stored count increases. Triggered lower pots can also cascade upward into higher pots.",
      a: "Higher stored counts are stronger, especially when two or three pots are simultaneously elevated. The public game data shows counts can build into the 40s, but no trustworthy universal +EV start number is public, so compare the complete three-pot state.",
      n: "Do not judge by animated pot fullness alone. Read the numeric Money Ball counts and remember this Gold version is substantially more volatile than original Magic Treasures."
    },
    23: {
      s: "SCOUT",
      v: "frames",
      l: "Light & Wonder explicitly identifies a Persistence Feature: collect hard hats to upgrade persistent house frames, then the wolf can blow down upgraded houses for prizes, jackpots or feature-wheel entries.",
      a: "Prioritize boards with several visibly upgraded frames and meaningful hard-hat progress, especially when multiple houses are advanced at once. Exact +EV entry is tier/layout-specific, so use the complete frame board rather than one isolated upgrade.",
      n: "Do not apply We've Had Enuff frame rules to every Huff N' Puff title. The family has multiple versions with different persistence mechanics and thresholds."
    },
    28: {
      s: "METER",
      v: "meter",
      l: "River Dragons has two AGS mystery Must-Hit-By progressives. A documented configuration resets the lower meter at $200 and must hit by $500; the upper resets at $4,000 and must hit by $5,000. Use the cabinet's printed reset/ceiling if Coushatta's configuration differs.",
      a: "Treat this as a near-ceiling play, not a generic rising progressive. Published PAR-sheet math for the $4,000/$5,000 version puts the average upper hit near $4,945 and the lower near $490, so only very high meters deserve serious attention.",
      n: "AGS River Dragons meters are not well modeled by assuming an even chance throughout the range. They are documented to hit heavily near the ceiling; halfway up is not automatically attractive."
    },
    29: {
      s: "METER",
      v: "progressive",
      l: "Buffalo Instant Hit's AP value is in its two stand-alone progressives, not in a persistent Buffalo collection screen. At the 1¢ baseline, the Grand resets at $5,000 and the Major at $500; the wheel is the only path to either progressive.",
      a: "Record both live progressive values and compare them with their resets. More growth above reset adds EV, but there is no trustworthy public universal play number because the Instant Hit/wheel trigger rates and wheel jackpot probabilities are not displayed.",
      n: "Do not call a meter +EV merely because it is above reset, and do not confuse this with Buffalo Link/Buffalo Cash counters. This is progressive-overlay math, not a must-hit-by counter."
    },
    30: {
      s: "SCOUT",
      v: "three_meters",
      l: "Fire Light Eruption has three persistent colored meters—Blue, Green and Red. Blue can cap at 99 and remain there for a long time; the combination of all three meters is the inherited state.",
      a: "Best free public read: prioritize a high Green meter with supportive Red/Blue state. A high Green while Red/Blue are relatively low is specifically identified as a stronger configuration than simply chasing the highest Blue number.",
      n: "Blue at 99 by itself is a known trap and can sit there for many spins. Do not play from one meter in isolation."
    },
    32: {
      s: "SCOUT",
      v: "frames",
      l: "The current Jackpot Catcher mechanic uses persistent glowing Catcher/ring positions. Rings remain for a limited number of spins; their internal segments show remaining life, and a credit symbol landing inside a ring awards that value. Jackpot Catcher Spins can seed many rings at once.",
      a: "Favor multiple active rings with all or most life segments remaining, especially dense states left after a Jackpot Catcher Spin. More live rings + more remaining spins = stronger inherited opportunity.",
      n: "Do not use progressive-meter advice from older games that share the Jackpot Catcher name. On this state, read the actual glowing rings and their remaining segments."
    },
    35: {
      s: "VERIFY",
      v: "wolf_meters",
      l: "Wolf Run Eclipse has multiple persistent free-game meters, but current public AP sources conflict on whether those meters are true must-hit-by counters or randomly triggered accumulating free-game values.",
      a: "Read the live cabinet itself. Photograph all meter values plus any printed 'must hit by,' 'must award by,' reset, or trigger wording before treating a high meter as a forced-trigger play.",
      n: "Do not label a high Eclipse meter 'due' unless the cabinet explicitly verifies a ceiling. Conflicting public documentation makes a conservative verify-first rule safer here."
    },
    49: {
      s: "VERIFY",
      v: "wonder4",
      l: "Wonder 4 Collection specifically gives each individual game one Free Games meter and one Super Free Games meter; Collection symbols increase those meters. Other Wonder 4 variants—including Boost Gold, Revolution and newer Buffalo combinations—use different mechanics.",
      a: "First identify the exact Wonder 4 version. If it is a Collection cabinet with visible red/blue Free Games meters, evaluate those stored meters for each selectable base game. If it is another Wonder 4 variant, do not use the Collection rule.",
      n: "The words 'Wonder 4' do not define one AP mechanic. This grouped Coushatta card covers several variants, so variant identification must come before any state decision."
    },
    50: {
      s: "VERIFY",
      v: "pusher",
      l: "Super Push: Firebird Festival is a true coin-pusher-style slot presentation with a tray of coins/special tokens and a Super Push bonus that adds extra pushes. Public game descriptions verify the tray mechanics, but not a dependable inherited-state +EV threshold.",
      a: "Photograph the complete tray, special tokens, any visible prize progress and the wager before playing. Only promote this to a state-based rule if the live machine clearly preserves the tray for the next player and a defensible value threshold can be established.",
      n: "A crowded tray is not proof of positive EV. Without verified carryover behavior and token/push valuation, keep this as photo/verify."
    },
    51: {
      s: "VERIFY",
      v: "pots",
      l: "Triple Treasure Pot uses three collection pots tied to Tiger, Dragon and Ox bonuses, but manufacturer/trade coverage describes the presentation as perceived persistence rather than confirmed stored player equity.",
      a: "Use the pots for game recognition only unless the live cabinet exposes an actual numeric counter or other persistent variable that survives player change. Photograph any such state before wagering.",
      n: "Do not convert pot fullness into a play threshold. A visually fuller pot can be presentation rather than an inherited advantage."
    }
  };

  if (Array.isArray(window.G)) {
    Object.entries(updates).forEach(([id, patch]) => {
      const game = window.G.find((item) => item.p === Number(id));
      if (game) Object.assign(game, patch);
    });
  }

  // Improve photo labeling where the existing image is useful for recognition
  // but is not itself proof of a qualifying pre-play state.
  if (window.GAME_IMAGES) {
    Object.assign(window.GAME_IMAGES, {
      13: {
        image: "https://i.ytimg.com/vi/LqcPVf3sRqQ/hqdefault.jpg",
        source: "https://www.playags.com/directory/games/potion-pays",
        sourceLabel: "AGS / TheBigPayback",
        kind: "reference",
        caption: "Real Potion Pays screen for recognition. On the live machine, the AP read is each persistent bubble's credit/jackpot value, position and remaining upward travel."
      },
      17: {
        image: "https://www-knowyourslots-com.exactdn.com/wp-content/uploads/2021/06/IMG_0245-e1624814894568-1024x556.jpeg?lossy=1&ssl=1&strip=all",
        source: "https://www.knowyourslots.com/fu-dai-lian-lian-boost-peacock-a-slot-machine-with-a-chance-at-more/",
        sourceLabel: "Know Your Slots",
        kind: "reference",
        caption: "Real Fu Dai Lian Lian BOOST Peacock screen. For a pre-play AP state, inspect the bet-pad bags for the actual jeweled/glowing BOOST condition; bag size alone is not the signal."
      },
      18: {
        image: "https://www-knowyourslots-com.exactdn.com/wp-content/uploads/2019/07/ocean-magic-free-games-1024x577.jpg?strip=all",
        source: "https://www.knowyourslots.com/ocean-magic-by-igt-bubbles-for-big-wins/",
        sourceLabel: "Know Your Slots",
        kind: "reference",
        caption: "Real Ocean Magic screen showing the bubble mechanic. On a live abandoned state, bubbles farther left and lower on the screen generally retain more usable value."
      },
      23: {
        image: "https://pbs.twimg.com/media/GzZAhZyXUAA-6G6.jpg",
        source: "https://gaming.lnw.com/games/Light-And-Wonder/class3/premium-games/Huff-N%27-Puff-We%27ve-Had-Enuff-20321",
        sourceLabel: "Light & Wonder",
        kind: "reference",
        caption: "Real We've Had Enuff cabinets for recognition. Light & Wonder confirms the persistent hard-hat/frame-upgrade mechanic; inspect the lower game screen for the actual inherited frame state."
      },
      29: {
        image: "https://www.indiangaming.com/wp-content/uploads/2021/07/Aristocrat-Gaming-Buffalo-Instant-Hit.jpg",
        source: "https://www.indiangaming.com/aristocrat-gaming-buffalo-instant-hit/",
        sourceLabel: "Indian Gaming / Aristocrat",
        kind: "reference",
        caption: "Real Buffalo Instant Hit cabinet. The relevant AP read is the live Grand and Major progressive amounts relative to their resets, not a persistent Buffalo collection state."
      },
      35: {
        image: "https://eidk95seyu2.exactdn.com/en/blog/wp-content/uploads/2024/10/wolf-run-eclipse-base-game.jpg?strip=all",
        source: "https://eidk95seyu2.exactdn.com/en/blog/wp-content/uploads/2024/10/wolf-run-eclipse-base-game.jpg?strip=all",
        sourceLabel: "Game reference",
        kind: "reference",
        caption: "Real Wolf Run Eclipse base-game screen showing the feature meters. Because public sources conflict on their trigger structure, verify any printed must-hit/reset wording on the actual Coushatta cabinet."
      },
      49: {
        image: "https://www.machinepro.club/content-assets/public/eyJhbGciOiJIUzI1NiJ9.eyJvYmplY3Rfa2V5Ijoic3dmcWp6Z3cyYzZpeDg3ZnYxaHV4ZTAzMmkxZiIsImRvbWFpbiI6Ind3dy5tYWNoaW5lcHJvLmNsdWIifQ.yb9yuxSHV2KVTk0ScVB0-6smQimknAu-XjPUIBidKs0",
        source: "https://www.aristocratgaming.com/latam/games/latam-wonder-4-collection",
        sourceLabel: "Aristocrat Gaming",
        kind: "state",
        caption: "Real Wonder 4 Collection meter example. Aristocrat confirms each individual game has a Free Games meter and a Super Free Games meter; do not apply this Collection mechanic to other Wonder 4 variants."
      }
    });
  }
})();
