const META = {
  RULE: ["FIXED RULE", "#137a4b", "#e9f6ef"],
  SCOUT: ["STATE-BASED", "#205da8", "#eaf2fc"],
  METER: ["METER / COUNTER", "#205da8", "#eaf2fc"],
  VERIFY: ["PHOTO / VERIFY", "#a65c00", "#fff3de"],
};

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

function isVisible(game) {
  if (tab === "route" && game.p > 12) return false;
  if (tab === "fav" && !favorites().has(game.p)) return false;
  if (filter !== "ALL" && game.s !== filter) return false;

  if (query) {
    const searchable = [game.t, game.m, game.l, game.a, game.n]
      .join(" ")
      .toLowerCase();
    if (!searchable.includes(query)) return false;
  }

  return true;
}

function visibleGames() {
  return G.filter(isVisible);
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

function visual(type) {
  let body = "";
  let label = "";
  const top =
    '<svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg">' +
    '<text x="12" y="14" font-size="9" font-weight="700" fill="#62748a">' +
    "ILLUSTRATED RECOGNITION DIAGRAM" +
    "</text>";
  const end = "</svg>";

  if (
    [
      "scarab",
      "golden_egypt",
      "lock_spin",
      "sticky_reels",
      "frames",
      "grid",
      "prize_blocks",
    ].includes(type)
  ) {
    for (let row = 0; row < 3; row += 1) {
      for (let col = 0; col < 5; col += 1) {
        const x = 18 + col * 58;
        const y = 28 + row * 34;
        const highlighted = (col + row) % 3 === 0;
        body +=
          `<rect x="${x}" y="${y}" width="48" height="25" rx="6" ` +
          `fill="${highlighted ? "#fff1b8" : "#fff"}" ` +
          `stroke="${highlighted ? "#c7982e" : "#d8e2ec"}" stroke-width="2"/>`;
      }
    }

    if (type === "scarab") label = "Gold frames on reels 1-3";
    else if (type === "golden_egypt") label = "Stored coin holders";
    else label = "Persistent loaded positions + counter";
  } else if (["multiplier", "reel_multiplier"].includes(type)) {
    body =
      '<rect x="58" y="35" width="204" height="80" rx="14" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>' +
      '<text x="160" y="85" text-anchor="middle" font-size="44" font-weight="800" fill="#c7982e">5x</text>';
    label = "Stored multiplier";
  } else if (type === "reel_heights") {
    [
      [55, 5],
      [82, 6],
      [110, 7],
    ].forEach(([height, rows], index) => {
      const x = 28 + index * 94;
      const y = 122 - height;
      body +=
        `<rect x="${x}" y="${y}" width="66" height="${height}" rx="8" ` +
        'fill="#fff" stroke="#d8e2ec" stroke-width="2"/>' +
        `<text x="${x + 33}" y="${y + height / 2 + 5}" text-anchor="middle" ` +
        `font-size="14" font-weight="800" fill="#205da8">${rows} rows</text>`;
    });
    label = "Reels grow toward 7 rows";
  } else if (
    [
      "counter",
      "meter",
      "progressive",
      "mhb5",
      "gems",
      "three_meters",
      "wolf_meters",
    ].includes(type)
  ) {
    [
      [92, "#205da8"],
      [87, "#137a4b"],
      [81, "#a23b3b"],
    ].forEach(([percent, color], index) => {
      const y = 34 + index * 34;
      body +=
        `<rect x="30" y="${y}" width="260" height="22" rx="8" fill="#fff" stroke="#d8e2ec"/>` +
        `<rect x="30" y="${y}" width="${2.6 * percent}" height="22" rx="8" fill="${color}" opacity=".24"/>` +
        `<text x="42" y="${y + 15}" font-size="10" font-weight="700" fill="#10243e">${percent}%</text>`;
    });
    label = "Read actual meter / counter / ceiling";
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
      body +=
        `<circle cx="${cx}" cy="78" r="30" fill="${color}"/>` +
        `<text x="${cx}" y="82" text-anchor="middle" font-size="10" font-weight="800" fill="#fff">${text}</text>`;
    });
    label = "Persistent pig / bank state";
  } else if (["bubbles", "ocean", "spheres"].includes(type)) {
    [
      [60, 74, 23, "$5"],
      [130, 52, 18, "$2"],
      [205, 84, 27, "$10"],
      [270, 55, 16, "$1"],
    ].forEach(([x, y, radius, text]) => {
      body +=
        `<circle cx="${x}" cy="${y}" r="${radius}" fill="#eaf2fc" stroke="#205da8" stroke-width="2"/>` +
        `<text x="${x}" y="${y + 4}" text-anchor="middle" font-size="10" font-weight="700" fill="#205da8">${text}</text>`;
    });
    label = "Persistent object value + position";
  } else {
    body =
      '<rect x="60" y="35" width="200" height="80" rx="14" fill="#fff" stroke="#d8e2ec" stroke-width="2"/>' +
      '<text x="160" y="81" text-anchor="middle" font-size="28" font-weight="800" fill="#a65c00">PHOTO</text>';
    label = "Full screen + meters + wager panel";
  }

  return (
    top +
    body +
    `<text x="160" y="148" text-anchor="middle" font-size="11" font-weight="700" fill="#10243e">${label}</text>` +
    end
  );
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
    '<div class="photo-load-error" id="photoLoadError">The external photo could not load. Use the recognition diagram and source link below.</div>' +
    `<div class="photo-caption">${escapeHtml(photo.caption)}</div>` +
    (isState
      ? '<div class="photo-warning">This is a real example of the game/state mechanic, but it is not automatically a PLAY. Compare the live numbers/layout to the Action Rule.</div>'
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
    const targetY =
      card.getBoundingClientRect().top + window.scrollY - headerHeight - 10;
    window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
  });
}

function scrollToPageTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
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

  const maps = game.maps
    .map(
      ([name, sid]) =>
        `<a class="map" target="_blank" rel="noopener" href="https://www.coushattacasinoresort.com/slot-map.php?sid=${sid}">📍 ${escapeHtml(name)} · SID ${sid}</a>`
    )
    .join("");

  $("#card").innerHTML =
    '<article class="card">' +
    '<div class="head">' +
    `<div class="num">#${String(game.p).padStart(2, "0")}</div>` +
    '<div class="hmain">' +
    `<div class="title">${escapeHtml(game.t)}</div>` +
    `<div class="maker">${escapeHtml(game.m)}</div>` +
    `<span class="badge" style="color:${color};background:${background}">${label}</span>` +
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
    '<details class="diagram-details">' +
    '<summary>Illustrated recognition diagram</summary>' +
    `<div class="visual">${visual(game.v)}</div>` +
    '<div class="vnote">Backup diagram only. Always read the actual meters, counters, symbols and wager on the live cabinet.</div>' +
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
