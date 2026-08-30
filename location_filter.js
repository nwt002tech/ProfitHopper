// Coushatta floor-area filtering for casino-floor use.
// Location codes come from current Coushatta slot/jackpot records where a
// current machine location could be resolved. Prefixes (BL, OR, RD, GR, HD)
// are Coushatta's own floor-location codes; the next two digits identify the
// local bank/aisle cluster.
(() => {
  const FLOOR = {
    1:  { zones:["UNMAPPED"], clusters:[], note:"Location code not yet resolved — use the card's Coushatta map button." },
    2:  { zones:["UNMAPPED"], clusters:[], note:"Location code not yet resolved — use the card's Coushatta map button." },
    3:  { zones:["OR"], clusters:["OR61"], note:"Golden Drums bank — OR61xx." },
    8:  { zones:["RD","GR"], clusters:["RD19","GR03"], note:"Buffalo Ascension has known banks in RD19xx and GR03xx." },
    9:  { zones:["BL"], clusters:["BL73"], note:"Buffalo Link bank — BL73xx." },
    10: { zones:["BL","OR","HD"], clusters:["BL58","OR29","HD09"], note:"Phoenix Link has banks in BL58xx and OR29xx, plus a high-denom HD09xx bank." },
    11: { zones:["UNMAPPED"], clusters:[], note:"Location code not yet resolved — use the card's Coushatta map button." },
    12: { zones:["UNMAPPED"], clusters:[], note:"Location code not yet resolved — use the card's Coushatta map button." },
    18: { zones:["RD"], clusters:["RD25"], note:"Ocean Magic — RD25xx area." },
    35: { zones:["RD"], clusters:["RD08"], note:"Wolf Run Eclipse — RD08xx area." },
    47: { zones:["RD"], clusters:["RD25"], note:"Wu Wang Zhe — RD25xx area, same cluster as Ocean Magic." }
  };

  const ZONE_ORDER = ["BL","OR","RD","GR","HD","YL","BK","UNMAPPED"];
  let floorZone = "ALL";

  const style = document.createElement("style");
  style.textContent = `
    .floor-filter{margin:8px 0 0}
    .floor-filter label{display:block;font-size:.68rem;font-weight:900;color:#10243e;letter-spacing:.05em;margin:0 0 5px}
    .floor-location{border:2px solid #cbd9e8;border-radius:12px;background:#eef4f9;padding:10px 11px;margin:0 0 10px;color:#10243e}
    .floor-location .fl-top{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
    .floor-location .fl-label{font-size:.66rem;font-weight:900;letter-spacing:.05em;color:#5b677a}
    .floor-chip{display:inline-block;background:#10243e;color:#fff;border-radius:999px;padding:5px 8px;font-size:.7rem;font-weight:900}
    .floor-chip.unmapped{background:#8a5b13}
    .floor-location .fl-note{font-size:.78rem;line-height:1.3;margin-top:6px;color:#33455b}
    .floor-help{font-size:.7rem;color:#5b677a;margin-top:5px;line-height:1.25}
  `;
  document.head.appendChild(style);

  function floorData(game){
    return FLOOR[game.p] || {zones:["UNMAPPED"],clusters:[],note:"Location code not yet resolved."};
  }

  // Chain onto any existing match filter (including Exact Entry Points Only).
  if(typeof matchesView === "function"){
    const beforeLocationMatch = matchesView;
    matchesView = function(game){
      if(!beforeLocationMatch(game)) return false;
      if(floorZone === "ALL") return true;
      return floorData(game).zones.includes(floorZone);
    };
  }

  // Keep cards in the same physical zone/cluster together, particularly in
  // Exact Route. This is grouping, not a claim of a shortest walking path.
  if(typeof visibleGames === "function"){
    const originalVisibleGames = visibleGames;
    visibleGames = function(){
      const games = originalVisibleGames();
      if(typeof tab === "undefined" || tab !== "route") return games;
      return [...games].sort((a,b)=>{
        const fa=floorData(a), fb=floorData(b);
        const za=ZONE_ORDER.indexOf(fa.zones[0]);
        const zb=ZONE_ORDER.indexOf(fb.zones[0]);
        if(za!==zb) return za-zb;
        const ca=(fa.clusters[0]||"ZZ99");
        const cb=(fb.clusters[0]||"ZZ99");
        if(ca!==cb) return ca.localeCompare(cb);
        return a.p-b.p;
      });
    };
  }

  const select = document.getElementById("floorZone");
  if(select){
    select.addEventListener("change",()=>{
      floorZone=select.value;
      if(typeof selected !== "undefined") selected=null;
      if(typeof render === "function") render();
    });
  }

  function injectLocation(){
    if(typeof selected === "undefined" || !selected) return;
    const body=document.querySelector("#card .body");
    if(!body) return;
    body.querySelectorAll(".floor-location").forEach(el=>el.remove());
    const info=FLOOR[selected] || {zones:["UNMAPPED"],clusters:[],note:"Location code not yet resolved — use the Coushatta map button."};
    const panel=document.createElement("section");
    panel.className="floor-location";
    const chips=info.clusters.length
      ? info.clusters.map(c=>`<span class="floor-chip">${c}xx</span>`).join("")
      : `<span class="floor-chip unmapped">MAP LINK</span>`;
    panel.innerHTML=`<div class="fl-top"><span class="fl-label">FLOOR LOCATION</span>${chips}</div><div class="fl-note">${info.note}</div>`;
    const quick=body.querySelector(".quick-decision");
    if(quick) quick.insertAdjacentElement("afterend",panel); else body.prepend(panel);
  }

  if(typeof renderCardOnly === "function"){
    const oldCard=renderCardOnly;
    renderCardOnly=function(){ oldCard(); injectLocation(); };
  }
  if(typeof render === "function"){
    const oldRender=render;
    render=function(){ oldRender(); injectLocation(); };
    render();
  }

  window.COUS_HATTA_FLOOR=FLOOR;
})();
