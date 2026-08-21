from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.coushattacasinoresort.com"
SEARCH_URL = f"{BASE_URL}/gaming/slot-search/"
DETAIL_URL = f"{BASE_URL}/slot-map.php?sid={{sid}}"
CASINO_NAME = "Coushatta Casino Resort"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclasses.dataclass
class SlotRecord:
    sid: int
    name: str
    manufacturer: str = ""
    game_type: str = ""
    denomination: str = ""
    volatility_text: str = ""
    volatility_score: int | None = None
    location: str = ""
    map_url: str = ""
    source_url: str = ""
    casino: str = CASINO_NAME
    scraped_at: str = ""

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def volatility_score(value: str) -> int | None:
    v = clean(value).lower()
    if "very low" in v:
        return 1
    if "low" in v:
        return 2
    if "medium" in v or "moderate" in v:
        return 3
    if "very high" in v:
        return 5
    if "high" in v:
        return 4
    return None


def extract_sids(text: str) -> set[int]:
    return {int(x) for x in re.findall(r"slot-map\.php\?sid=(\d+)", text or "", flags=re.I)}


def discover_active_sids(wildcard: str = "%%%", timeout_ms: int = 90000) -> tuple[list[int], dict]:
    """Use Coushatta's live Slot Finder as the ONLY source of active floor SIDs."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400}, user_agent=HEADERS["User-Agent"])
        captured_bodies: list[str] = []

        def on_response(resp):
            try:
                if resp.request.resource_type in {"xhr", "fetch", "document"}:
                    body = resp.text()
                    if "slot-map.php?sid=" in body:
                        captured_bodies.append(body)
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=timeout_ms)

        field = None
        candidates = [
            lambda: page.get_by_label(re.compile(r"game\s*title", re.I)),
            lambda: page.locator('input[placeholder*="title" i]'),
            lambda: page.locator('input[name*="title" i]'),
            lambda: page.locator('input[id*="title" i]'),
            lambda: page.locator('input[type="text"]'),
        ]
        for fn in candidates:
            try:
                loc = fn()
                if loc.count() > 0:
                    field = loc.first
                    break
            except Exception:
                continue
        if field is None:
            browser.close()
            raise RuntimeError("Could not locate Coushatta Game Title search field")

        field.fill(wildcard)

        clicked = False
        for locator in [
            page.get_by_role("button", name=re.compile(r"^search$", re.I)),
            page.locator('input[type="submit"][value*="search" i]'),
            page.locator('button:has-text("SEARCH")'),
        ]:
            try:
                if locator.count() > 0:
                    locator.first.click()
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            field.press("Enter")

        page.wait_for_timeout(2500)
        sids: set[int] = set()
        stable_rounds = 0
        last_count = -1

        for _ in range(40):
            sids |= extract_sids(page.content())
            for body in captured_bodies:
                sids |= extract_sids(body)

            for selector in ['a', 'button', '[onclick]', '[data-url]', '[data-href]']:
                try:
                    nodes = page.locator(selector)
                    for i in range(nodes.count()):
                        try:
                            outer = nodes.nth(i).evaluate("el => el.outerHTML")
                            sids |= extract_sids(outer)
                        except Exception:
                            pass
                except Exception:
                    pass

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(700)

            next_clicked = False
            for nxt in [
                page.get_by_role("button", name=re.compile(r"^next$", re.I)),
                page.get_by_role("link", name=re.compile(r"^next$", re.I)),
                page.locator('a:has-text("Next")'),
                page.locator('button:has-text("Next")'),
            ]:
                try:
                    if nxt.count() > 0 and nxt.first.is_visible() and nxt.first.is_enabled():
                        classes = (nxt.first.get_attribute("class") or "").lower()
                        aria_disabled = (nxt.first.get_attribute("aria-disabled") or "").lower()
                        if "disabled" not in classes and aria_disabled != "true":
                            nxt.first.click()
                            page.wait_for_timeout(1200)
                            next_clicked = True
                            break
                except Exception:
                    continue

            if len(sids) == last_count and not next_clicked:
                stable_rounds += 1
            else:
                stable_rounds = 0
            last_count = len(sids)
            if stable_rounds >= 3:
                break

        diagnostics = {
            "search_url": SEARCH_URL,
            "wildcard": wildcard,
            "active_sid_count": len(sids),
            "captured_response_count": len(captured_bodies),
            "page_title": page.title(),
            "strategy": "live_playwright_wildcard_search",
        }
        browser.close()

    if not sids:
        raise RuntimeError("Live Coushatta wildcard search returned zero active slot SIDs")
    return sorted(sids), diagnostics


def parse_detail_html(html: str, sid: int, source_url: str) -> SlotRecord | None:
    soup = BeautifulSoup(html or "", "html.parser")
    text = clean(soup.get_text(" ", strip=True))
    if not text:
        return None

    labels = {
        "manufacturer": r"Manufacturer\s*:\s*(.*?)\s*(?=Type\s*:|Denomination\s*:|Volatility\s*:|Location\s*:|$)",
        "game_type": r"Type\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Denomination\s*:|Volatility\s*:|Location\s*:|$)",
        "denomination": r"Denomination\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Type\s*:|Volatility\s*:|Location\s*:|$)",
        "volatility_text": r"Volatility\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Type\s*:|Denomination\s*:|Location\s*:|$)",
        "location": r"Location\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Type\s*:|Denomination\s*:|Volatility\s*:|$)",
    }
    values = {}
    for key, pattern in labels.items():
        m = re.search(pattern, text, flags=re.I)
        if m:
            values[key] = clean(m.group(1))

    if not any(values.get(k) for k in ("manufacturer", "game_type", "denomination", "volatility_text")):
        return None

    name = ""
    for selector in [".slot-name", ".game-title", ".slot-title", "h1", "h2", "h3", "h4", ".modal-title", "strong"]:
        for node in soup.select(selector):
            v = clean(node.get_text(" ", strip=True))
            if v and len(v) <= 140 and not re.match(r"^(Manufacturer|Type|Denomination|Volatility|Location)\s*:", v, re.I):
                name = v
                break
        if name:
            break

    if not name:
        prefix = re.split(r"\s+(?:Manufacturer|Type|Denomination|Volatility|Location)\s*:", text, maxsplit=1, flags=re.I)[0]
        if 0 < len(prefix) <= 180:
            name = clean(prefix)
    if not name:
        return None

    canonical_map_url = DETAIL_URL.format(sid=sid)
    return SlotRecord(
        sid=sid,
        name=name,
        manufacturer=values.get("manufacturer", ""),
        game_type=values.get("game_type", ""),
        denomination=values.get("denomination", ""),
        volatility_text=values.get("volatility_text", ""),
        volatility_score=volatility_score(values.get("volatility_text", "")),
        location=values.get("location", ""),
        map_url=canonical_map_url,
        source_url=source_url,
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )


def fetch_detail(sid: int, timeout: int = 20) -> SlotRecord | None:
    url = DETAIL_URL.format(sid=sid)
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException:
        return None
    return parse_detail_html(r.text, sid, r.url)


def fetch_active_records(sids: Iterable[int], workers: int = 8, timeout: int = 20) -> list[SlotRecord]:
    ids = sorted(set(int(x) for x in sids))
    results: list[SlotRecord] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 12))) as pool:
        futures = {pool.submit(fetch_detail, sid, timeout): sid for sid in ids}
        for future in concurrent.futures.as_completed(futures):
            rec = future.result()
            if rec is not None:
                results.append(rec)
    return sorted(results, key=lambda x: x.sid)


def normalize_inventory(records: Iterable[SlotRecord]) -> pd.DataFrame:
    rows = [r.as_dict() for r in records]
    cols = [f.name for f in dataclasses.fields(SlotRecord)]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=["sid"], keep="last").sort_values(["name", "sid"], kind="stable")
    return df.reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract ACTIVE Coushatta floor inventory from the live wildcard Slot Finder")
    parser.add_argument("--wildcard", default="%%%")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output", default="data/coushatta_slot_inventory.csv")
    parser.add_argument("--diagnostics", default="data/coushatta_slot_inventory_diagnostics.json")
    args = parser.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    active_sids, diag = discover_active_sids(args.wildcard)
    records = fetch_active_records(active_sids, workers=args.workers, timeout=args.timeout)
    df = normalize_inventory(records)

    if len(active_sids) < 50:
        raise RuntimeError(f"Wildcard search exposed only {len(active_sids)} SIDs; refusing to publish incomplete inventory")
    parse_ratio = (len(df) / len(active_sids)) if active_sids else 0.0
    if parse_ratio < 0.80:
        raise RuntimeError(f"Only parsed {len(df)} of {len(active_sids)} active SIDs ({parse_ratio:.1%}); refusing to publish")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    diag.update({
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "active_sid_count": len(active_sids),
        "parsed_record_count": len(df),
        "parse_ratio": parse_ratio,
        "unique_games": int(df["name"].nunique()) if not df.empty else 0,
        "manufacturers": int(df["manufacturer"].replace("", pd.NA).nunique()) if not df.empty else 0,
        "denominations": int(df["denomination"].replace("", pd.NA).nunique()) if not df.empty else 0,
        "volatility_known": int(df["volatility_text"].fillna("").str.strip().ne("").sum()) if not df.empty else 0,
        "map_url_known": int(df["map_url"].fillna("").str.strip().ne("").sum()) if not df.empty else 0,
        "source_of_truth": "Coushatta live wildcard search results only",
        "numeric_sid_scan_used": False,
    })
    Path(args.diagnostics).write_text(json.dumps(diag, indent=2), encoding="utf-8")
    print(json.dumps(diag, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
