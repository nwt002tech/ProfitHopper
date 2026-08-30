const META = {
  RULE: ["FIXED RULE", "#137a4b", "#e9f6ef"],
  SCOUT: ["STATE-BASED", "#205da8", "#eaf2fc"],
  METER: ["METER / COUNTER", "#205da8", "#eaf2fc"],
  VERIFY: ["PHOTO / VERIFY", "#a65c00", "#fff3de"],
};

const PRIORITY_ORDER = [1, 2, 37, 3, 47, 45, 4, 9, 10, 11, 12, 46];
const NEW_START_ID = 37;

let tab = "all";
let filter = "ALL";
let query = "";
let selected = null;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function favorites() {
  try {
    return new Set(JSON.parse(localStorage.getItem("coushattaFavs") || "[]"));
  } catch (error) {
    return new Set();
  }
}

function saveFavorites(set) {
  localStorage.setItem("coushattaFavs", JSON.stringify([...set]));
}

function priorityRank(game) {
  const index = PRIORITY_ORDER.indexOf(game.p);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function priorityGames() {
  return G.filter((game) => PRIORITY_ORDER.includes(game.p)).sort(
    (a, b) => priorityRank(a) - priorityRank(b)
  );
}

function matchesView(game) {
  if (tab === "route" && !PRIORITY_ORDER.includes(game.p)) return false;
  if (tab === "fav" && !favorites().has(game.p)) return false;

  if (filter === "NEW") {
    if (game.p < NEW_START_ID) return false;
  } else if (filter !== "ALL" && game.s !== filter) {
    return false;
  }

  if (query) {
    const mapText = (game.maps || []).map(([name, sid]) => `${name} ${sid}`).join(" ");
    const searchable = [game.t, game.m, game.l, game.a, game.n, mapText]
      .join(" ")
      .toLowerCase();
    if (!searchable.includes(query)) return false;
  }

  return true;
}

function visibleGames() {
  const games = G.filter(matchesView);
  if (tab === "route") {
    return games.sort((a, b) => priorityRank(a) - priorityRank(b));
  }
  return games.sort((a, b) => a.p - b.p);
}

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char]
  );
}

function svgText(x, y, text, options = {}) {
  const size = options.size || 10;
  const weight = options.weight || 700;
  const fill = options.fill || "#10243e";
  const anchor = options.anchor || "middle";
  return `<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" font-weight="${weight}" fill="${fill}">${escapeHtml(text)}</text>`;
}

function visual(type) {
  let body = "";
  let label = "";
  const top =
    '<svg viewBox="0 0 320 170" xmlns="http://www.w3.org/2000/svg">' +
    '<text x="12" y="14" font-size="9" font-weight="700" fill="#62748a">ILLUSTRATED RECOGNITION DIAGRAM</text>';
  const end = "</svg>";

  const gridTypes = [
    "scarab",
    "golden_egypt",
    "lock_spin",
    "sticky_reels",
    "frames",
    "grid",
    "prize_blocks",
    "cash_falls",
  ];

  if (gridTypes.includes(type)) {
    for (let row = 0; row < 3; row += 1) {
      for (let col = 0; col < 5; col += 1) {
        const x = 18 + col * 58;
        const y = 28 + row * 34;
        const highlighted = (col + row) % 3 === 0 || (type === "cash_falls" && col === 2);
        body +=
          `<rect x="${x}" y="${y}" width="48" height="25" rx="6" ` +
          `fill="${highlighted ? "#fff1b8" : "#fff"}" ` +
          `stroke="${highlighted ? "#c7982e" : "#d8e2ec"}" stroke-width="2"/>`;
      }
    }

    if (type === "scarab") label = "Gold frames on reels 1-3";
    else if (type === "golden_egypt") label = "Stored coin holders";
    else if (type === "cash_falls") label = "Loaded Fireballs + spins remaining";
    else label = "Persistent loaded positions + counter";
  } else if (["multiplier", "reel_multiplier"].includes(type)) {
    body =
      '<rect x="58" y="35" width="204" height="86" rx="14" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>' +
      '<text x="160" y="90" text-anchor="middle" font-size="44" font-weight="800" fill="#c7982e">12x</text>';
    label = "Stored multiplier";
  } else if (type === "reel_heights") {
    [
      [55, 5],
      [82, 6],
      [110, 7],
    ].forEach(([height, rows], index) => {
      const x = 28 + index * 94;
      const y = 128 - height;
      body +=
        `<rect x="${x}" y="${y}" width="66" height="${height}" rx="8" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>` +
        svgText(x + 33, y + height / 2 + 5, `${rows} rows`, { size: 14, fill: "#205da8" });
    });
    label = "Reels grow toward 7 rows";
  } else if (
    ["counter", "meter", "progressive", "mhb5", "gems", "three_meters", "wolf_meters"].includes(type)
  ) {
    [92, 87, 81].forEach((percent, index) => {
      const y = 34 + index * 34;
      body +=
        `<rect x="30" y="${y}" width="260" height="22" rx="8" fill="#fff" stroke="#d8e2ec"/>` +
        `<rect x="30" y="${y}" width="${2.6 * percent}" height="22" rx="8" fill="#205da8" opacity=".20"/>` +
        svgText(42, y + 15, `${percent}%`, { anchor: "start" });
    });
    label = type === "three_meters" ? "Compare all persistent meters" : "Read actual meter / counter / ceiling";
  } else if (type === "many_meters") {
    for (let row = 0; row < 3; row += 1) {
      for (let col = 0; col < 3; col += 1) {
        const x = 20 + col * 100;
        const y = 28 + row * 35;
        const pct = 70 + ((row * 3 + col) * 3) % 29;
        body += `<rect x="${x}" y="${y}" width="84" height="22" rx="6" fill="#fff" stroke="#d8e2ec"/>`;
        body += `<rect x="${x}" y="${y}" width="${0.84 * pct}" height="22" rx="6" fill="#205da8" opacity=".18"/>`;
        body += svgText(x + 42, y + 15, `${pct}%`, { size: 9 });
      }
    }
    label = "27 MHB meters: compare current value to each ceiling";
  } else if (type === "lanterns") {
    body =
      '<text x="30" y="50" font-size="18" font-weight="800" fill="#205da8">BLUE 36 / 40</text>' +
      '<text x="30" y="82" font-size="18" font-weight="800" fill="#137a4b">GREEN 55 / 60</text>' +
      '<text x="30" y="114" font-size="18" font-weight="800" fill="#a23b3b">RED 92 / 100</text>';
    label = "Use lantern numbers, not pig animation";
  } else if (["pigs", "piggy"].includes(type)) {
    [
      ["BLUE 22", "#205da8"],
      ["YELLOW", "#c7982e"],
      ["RED", "#a23b3b"],
    ].forEach(([text, color], index) => {
      const cx = 70 + index * 90;
      body += `<circle cx="${cx}" cy="80" r="30" fill="${color}"/>`;
      body += svgText(cx, 84, text, { fill: "#fff" });
    });
    label = "Persistent pig / bank state";
  } else if (["bubbles", "ocean", "spheres", "orbs"].includes(type)) {
    [
      [60, 82, 23, "$5"],
      [130, 55, 18, "$2"],
      [205, 92, 27, "$10"],
      [270, 58, 16, "$1"],
    ].forEach(([x, y, radius, text]) => {
      body += `<circle cx="${x}" cy="${y}" r="${radius}" fill="#eaf2fc" stroke="#205da8" stroke-width="2"/>`;
      body += svgText(x, y + 4, text, { fill: "#205da8" });
    });
    label = type === "orbs" ? "Orb value + row position + remaining travel" : "Persistent object value + position";
  } else if (type === "moving_wilds") {
    for (let row = 0; row < 3; row += 1) {
      for (let col = 0; col < 5; col += 1) {
        const x = 18 + col * 58;
        const y = 29 + row * 35;
        const wild = (row === 2 && col === 1) || (row === 1 && col === 3);
        body += `<rect x="${x}" y="${y}" width="48" height="26" rx="6" fill="${wild ? "#fff1b8" : "#fff"}" stroke="${wild ? "#c7982e" : "#d8e2ec"}" stroke-width="2"/>`;
        if (wild) body += svgText(x + 24, y + 17, "WILD ↑", { size: 10, fill: "#a65c00" });
      }
    }
    label = "Persistent Wilds move upward each paid spin";
  } else if (type === "sticky_wilds") {
    for (let row = 0; row < 3; row += 1) {
      for (let col = 0; col < 5; col += 1) {
        const x = 18 + col * 58;
        const y = 29 + row * 35;
        const wild = [1, 4, 6, 9, 12].includes(row * 5 + col);
        body += `<rect x="${x}" y="${y}" width="48" height="26" rx="6" fill="${wild ? "#fff1b8" : "#fff"}" stroke="${wild ? "#c7982e" : "#d8e2ec"}" stroke-width="2"/>`;
        if (wild) body += svgText(x + 24, y + 17, "WILD", { size: 10, fill: "#a65c00" });
      }
    }
    body += svgText(160, 143, "2 SPINS REMAINING", { size: 11, fill: "#205da8" });
    label = "Sticky Wild count + spins remaining";
  } else if (type === "tokens") {
    const data = [
      ["RED", "2/3", "#a23b3b"],
      ["BLUE", "2/3", "#205da8"],
      ["GREEN", "1/3", "#137a4b"],
      ["GOLD", "1/3", "#c7982e"],
      ["YELLOW", "0/3", "#8a7b2f"],
    ];
    data.forEach(([name, count, color], index) => {
      const x = 38 + index * 61;
      body += `<circle cx="${x}" cy="75" r="25" fill="${color}" opacity=".16" stroke="${color}" stroke-width="2"/>`;
      body += svgText(x, 72, name, { size: 8, fill: color });
      body += svgText(x, 88, count, { size: 11, fill: color });
    });
    label = "3 tokens activates 3 scatter-pay spins";
  } else if (type === "wonder4") {
    for (let row = 0; row < 2; row += 1) {
      for (let col = 0; col < 2; col += 1) {
        const x = 30 + col * 135;
        const y = 30 + row * 52;
        body += `<rect x="${x}" y="${y}" width="120" height="42" rx="8" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>`;
        body += svgText(x + 60, y + 25, `BASE GAME ${row * 2 + col + 1}`, { size: 9, fill: "#205da8" });
      }
    }
    label = "Evaluate the state of the specific underlying game";
  } else if (type === "pusher") {
    body += '<rect x="28" y="32" width="264" height="92" rx="12" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>';
    for (let i = 0; i < 12; i += 1) {
      const x = 48 + (i % 6) * 42;
      const y = 55 + Math.floor(i / 6) * 42 + (i % 2) * 5;
      body += `<circle cx="${x}" cy="${y}" r="13" fill="#fff1b8" stroke="#c7982e" stroke-width="2"/>`;
    }
    body += '<path d="M48 128 L272 128" stroke="#a23b3b" stroke-width="3" stroke-dasharray="6 5"/>';
    label = "Tray state: photo required before betting";
  } else if (type === "pots") {
    ["TIGER", "DRAGON", "OX"].forEach((name, index) => {
      const x = 68 + index * 92;
      body += `<ellipse cx="${x}" cy="78" rx="34" ry="42" fill="#fff1b8" stroke="#c7982e" stroke-width="2"/>`;
      body += svgText(x, 82, name, { size: 9, fill: "#8a6515" });
    });
    label = "Pot fullness alone may be perceived persistence";
  } else if (type === "bombs") {
    for (let row = 0; row < 3; row += 1) {
      for (let col = 0; col < 5; col += 1) {
        const x = 45 + col * 58;
        const y = 47 + row * 36;
        const active = [1, 2, 6, 7, 8, 12].includes(row * 5 + col);
        if (active) {
          body += `<circle cx="${x}" cy="${y}" r="13" fill="#172033"/>`;
          body += `<path d="M${x + 8} ${y - 10} q10 -12 18 0" fill="none" stroke="#a23b3b" stroke-width="3"/>`;
        } else {
          body += `<circle cx="${x}" cy="${y}" r="13" fill="#fff" stroke="#d8e2ec"/>`;
        }
      }
    }
    label = "Bomb cluster + adjacency + active fuse/countdown";
  } else if (type === "ocean_treasure") {
    body += '<rect x="68" y="42" width="184" height="82" rx="14" fill="#eaf2fc" stroke="#205da8" stroke-width="2"/>';
    body += '<path d="M68 72 H252" stroke="#205da8" stroke-width="2"/>';
    body += svgText(160, 62, "TREASURE BOX", { size: 12, fill: "#205da8" });
    body += svgText(160, 101, "PHOTO FULL STATE", { size: 16, fill: "#a65c00" });
    label = "Do not reuse classic Ocean Magic thresholds";
  } else {
    body =
      '<rect x="60" y="38" width="200" height="84" rx="14" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>' +
      '<text x="160" y="88" text-anchor="middle" font-size="28" font-weight="800" fill="#a65c00">PHOTO</text>';
    label = "Full screen + meters + wager panel";
  }

  return top + body + svgText(160, 160, label, { size: 10 }) + end;
}

function hasRealPhoto(game) {
  return Boolean(window.GAME_IMAGES && window.GAME_IMAGES[game.p]);
}

function realPhotoMarkup(game) {
  const photo = window.GAME_IMAGES && window.GAME_IMAGES[game.p];
  if (!photo) return "";

  const isState = photo.kind === "state";
  const badgeText = isState
    ? "REAL STATE / MECHANIC PHOTO"
    : "REAL GAME PHOTO - VERIFY STATE";
  const badgeClass = isState ? "photo-state" : "photo-reference";

  return (
    '<section class="real-photo-card">' +
    '<div class="photo-toolbar">' +
    `<span class="photo-badge ${badgeClass}">${badgeText}</span>` +
    `<a class="photo-source" href="${escapeHtml(photo.source)}" target="_blank" rel="noopener">Source: ${escapeHtml(photo.sourceLabel)} ↗</a>` +
    "</div>" +
    `<img id="realGameImage" src="${escapeHtml(photo.image)}" alt="Real ${escapeHtml(game.t)} slot machine reference" decoding="async">` +
    '<div class="photo-load-error" id="photoLoadError">The external photo could not load. Use the recognition diagram and source link.</div>' +
    `<div class="photo-caption">${escapeHtml(photo.caption)}</div>` +
    (isState
      ? '<div class="photo-warning">This is a real example of the game/state mechanic, but it is not automatically a PLAY. Compare the live numbers/layout with the Action Rule.</div>'
      : '<div class="photo-warning">This is a real photo of the correct game/family for recognition. It is not verified as a qualifying AP state. Use the live screen plus the Action Rule.</div>') +
    "</section>"
  );
}

function updateTabButtons() {
  $$(".tabs .pillbtn").forEach((button) => {
    button.classList.toggle("on", button.dataset.tab === tab);
  });
}

function updateFilterButtons() {
  $$(".filters .pillbtn").forEach((button) => {
    button.classList.toggle("on", button.dataset.f === filter);
  });
}

function scrollToGameCard() {
  const card = $("#card");
  const header = document.querySelector("header");
  if (!card) return;

  requestAnimationFrame(() => {
    const headerHeight = header ? header.offsetHeight : 0;
    const targetY = card.getBoundingClientRect().top + window.scrollY - headerHeight - 10;
    window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
  });
}

function scrollToPageTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderStats() {
  const allCount = $("#allCount");
  const priorityCount = $("#priorityCount");
  if (allCount) allCount.textContent = G.length;
  if (priorityCount) priorityCount.textContent = priorityGames().length;
}

function renderRouteList() {
  const list = $("#routeList");
  if (!list) return;
  list.innerHTML = priorityGames()
    .map((game) => `<li><b>${escapeHtml(game.t)}</b> <span class="route-type">${META[game.s][0]}</span></li>`)
    .join("");
}

function renderQuickJump(games) {
  const quick = $("#quick");
  quick.innerHTML = games
    .map(
      (game) =>
        `<button data-p="${game.p}"><b>${String(game.p).padStart(2, "0")}</b> · ${escapeHtml(game.t)}</button>`
    )
    .join("");

  quick.querySelectorAll("button").forEach((button) => {
    button.onclick = () => {
      selected = Number(button.dataset.p);
      $("#gameSelect").value = String(selected);
      renderCardOnly();
      scrollToGameCard();
    };
  });
}

function renderCardOnly() {
  const games = visibleGames();
  if (!games.length) {
    $("#card").innerHTML = "";
    return;
  }

  if (!selected || !games.some((game) => game.p === selected)) {
    selected = games[0].p;
  }

  const game = games.find((item) => item.p === selected);
  const gameIndex = games.findIndex((item) => item.p === selected);
  const previousGame = gameIndex > 0 ? games[gameIndex - 1] : null;
  const nextGame = gameIndex < games.length - 1 ? games[gameIndex + 1] : null;
  const [label, color, background] = META[game.s];
  const favoriteSet = favorites();
  const isFavorite = favoriteSet.has(game.p);
  const isNew = game.p >= NEW_START_ID;
  const openDiagram = hasRealPhoto(game) ? "" : " open";

  const maps = game.maps
    .map(
      ([name, sid]) =>
        `<a class="map" target="_blank" rel="noopener" href="https://www.coushattacasinoresort.com/slot-map.php?sid=${sid}">MAP · ${escapeHtml(name)} · SID ${sid}</a>`
    )
    .join("");

  $("#card").innerHTML =
    '<article class="card">' +
    '<div class="head">' +
    `<div class="num">#${String(game.p).padStart(2, "0")}</div>` +
    '<div class="hmain">' +
    `<div class="title">${escapeHtml(game.t)}</div>` +
    `<div class="maker">${escapeHtml(game.m)}</div>` +
    '<div class="badge-row">' +
    `<span class="badge" style="color:${color};background:${background}">${label}</span>` +
    (isNew ? '<span class="badge new-badge">NEW AUDIT ADDITION</span>' : "") +
    "</div>" +
    "</div>" +
    '<div class="header-actions">' +
    '<button class="top-game-btn" id="topGameBtn" type="button">Top ↑</button>' +
    `<button class="fav ${isFavorite ? "on" : ""}" id="favBtn" type="button" aria-label="Favorite">${isFavorite ? "★" : "☆"}</button>` +
    "</div>" +
    "</div>" +
    '<div class="game-nav">' +
    `<button id="prevGameBtn" type="button" ${previousGame ? "" : "disabled"}>← Previous</button>` +
    `<div class="game-position">${gameIndex + 1} of ${games.length}</div>` +
    `<button id="nextGameBtn" type="button" ${nextGame ? "" : "disabled"}>Next →</button>` +
    "</div>" +
    '<div class="body">' +
    realPhotoMarkup(game) +
    `<div class="box"><div class="lab">LOOK FOR</div>${escapeHtml(game.l)}</div>` +
    `<div class="box" style="background:${background};border-color:${color}"><div class="lab">ACTION RULE</div><b>${escapeHtml(game.a)}</b></div>` +
    `<div class="box warn"><div class="lab">DO NOT MISREAD</div>${escapeHtml(game.n)}</div>` +
    `<details class="diagram-details"${openDiagram}>` +
    '<summary>Illustrated recognition diagram</summary>' +
    `<div class="visual">${visual(game.v)}</div>` +
    '<div class="vnote">Recognition aid only. Read the actual meter, counter, symbols and wager on the live cabinet.</div>' +
    "</details>" +
    `<div class="box"><div class="lab">COUSHATTA MAP</div><div class="mapgrid">${maps}</div></div>` +
    "</div>" +
    "</article>";

  const image = $("#realGameImage");
  const imageError = $("#photoLoadError");
  if (image) {
    image.addEventListener("error", () => {
      image.style.display = "none";
      if (imageError) imageError.classList.add("show");
    });
  }

  $("#topGameBtn").onclick = scrollToPageTop;

  const previousButton = $("#prevGameBtn");
  const nextButton = $("#nextGameBtn");

  if (previousButton && previousGame) {
    previousButton.onclick = () => {
      selected = previousGame.p;
      $("#gameSelect").value = String(selected);
      renderCardOnly();
      scrollToGameCard();
    };
  }

  if (nextButton && nextGame) {
    nextButton.onclick = () => {
      selected = nextGame.p;
      $("#gameSelect").value = String(selected);
      renderCardOnly();
      scrollToGameCard();
    };
  }

  $("#favBtn").onclick = () => {
    const set = favorites();
    if (set.has(game.p)) set.delete(game.p);
    else set.add(game.p);
    saveFavorites(set);
    render();
  };
}

function render() {
  const games = visibleGames();
  renderStats();
  renderRouteList();

  $("#vc").textContent = games.length;
  $("#empty").classList.toggle("show", games.length === 0);
  $("#routeBox").classList.toggle("show", tab === "route");
  updateTabButtons();
  updateFilterButtons();

  if (!games.length) {
    $("#gameSelect").innerHTML = "";
    $("#quick").innerHTML = "";
    $("#card").innerHTML = "";
    return;
  }

  if (!selected || !games.some((game) => game.p === selected)) {
    selected = games[0].p;
  }

  $("#gameSelect").innerHTML = games
    .map(
      (game) =>
        `<option value="${game.p}" ${game.p === selected ? "selected" : ""}>${String(game.p).padStart(2, "0")} · ${escapeHtml(game.t)}</option>`
    )
    .join("");

  renderQuickJump(games);
  renderCardOnly();
}

function selectTopView(nextTab) {
  tab = nextTab;
  filter = "ALL";
  query = "";
  selected = null;
  const search = $("#q");
  if (search) search.value = "";
  render();
}

$("#tabs").onclick = (event) => {
  const button = event.target.closest("button[data-tab]");
  if (!button) return;
  selectTopView(button.dataset.tab);
};

$("#filters").onclick = (event) => {
  const button = event.target.closest("button[data-f]");
  if (!button) return;
  filter = button.dataset.f;
  selected = null;
  render();
};

$("#q").oninput = (event) => {
  query = event.target.value.trim().toLowerCase();
  selected = null;
  render();
};

$("#gameSelect").onchange = (event) => {
  selected = Number(event.target.value);
  renderCardOnly();
  scrollToGameCard();
};

$("#priorityStat").onclick = () => selectTopView("route");
$("#allGamesStat").onclick = () => selectTopView("all");

render();
