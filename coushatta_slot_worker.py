from __future__ import annotations

import concurrent.futures
import dataclasses
import json
import re
from datetime import datetime, timezone
from typing import Callable, Iterable
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.coushattacasinoresort.com"
SEARCH_URL = f"{BASE_URL}/gaming/slot-search/"
DETAIL_URL = f"{BASE_URL}/slot-map.php?sid={{sid}}"
CASINO_NAME = "Coushatta Casino Resort"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

ProgressCallback = Callable[[int, int, str], None]


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
    source_url: str = ""
    casino: str = CASINO_NAME
    scraped_at: str = ""

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def _new_session(timeout: int = 20) -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.request_timeout = timeout
    return session


def _request(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    timeout = kwargs.pop("timeout", getattr(session, "request_timeout", 20))
    response = session.request(method, url, timeout=timeout, allow_redirects=True, **kwargs)
    response.raise_for_status()
    return response


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _volatility_score(value: str) -> int | None:
    v = _clean(value).lower()
    if not v:
        return None
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


def _extract_sid(value: str) -> int | None:
    m = re.search(r"(?:[?&]sid=|\bsid\s*[:=]\s*['\"]?)(\d+)", value or "", flags=re.I)
    return int(m.group(1)) if m else None


def _looks_like_missing_page(text: str) -> bool:
    compact = _clean(text).lower()
    if not compact:
        return True
    markers = (
        "slot not found",
        "no slot found",
        "record not found",
        "invalid slot",
        "404 not found",
    )
    return any(marker in compact for marker in markers)


def parse_detail_html(html: str, sid: int, source_url: str | None = None) -> SlotRecord | None:
    if not html or _looks_like_missing_page(html):
        return None

    soup = BeautifulSoup(html, "html.parser")
    text = _clean(soup.get_text(" ", strip=True))
    if not text:
        return None

    candidate_nodes = []
    for selector in [
        "#slot-map-info", ".slot-map-info", ".slot-info", ".slot-details",
        ".map-details", ".slotmap-details", ".slot-detail", ".modal-content",
        ".info", "main", "body",
    ]:
        candidate_nodes.extend(soup.select(selector))

    candidates = []
    seen_text = set()
    for node in candidate_nodes:
        node_text = _clean(node.get_text(" ", strip=True))
        if node_text and node_text not in seen_text:
            seen_text.add(node_text)
            candidates.append(node_text)
    if text not in seen_text:
        candidates.append(text)

    labels = {
        "manufacturer": r"Manufacturer\s*:\s*(.*?)\s*(?=Type\s*:|Denomination\s*:|Volatility\s*:|Location\s*:|$)",
        "game_type": r"Type\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Denomination\s*:|Volatility\s*:|Location\s*:|$)",
        "denomination": r"Denomination\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Type\s*:|Volatility\s*:|Location\s*:|$)",
        "volatility_text": r"Volatility\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Type\s*:|Denomination\s*:|Location\s*:|$)",
        "location": r"Location\s*:\s*(.*?)\s*(?=Manufacturer\s*:|Type\s*:|Denomination\s*:|Volatility\s*:|$)",
    }

    values: dict[str, str] = {}
    detail_text = ""
    for candidate in candidates:
        local: dict[str, str] = {}
        for key, pattern in labels.items():
            m = re.search(pattern, candidate, flags=re.I)
            if m:
                local[key] = _clean(m.group(1))
        if len(local) > len(values):
            values = local
            detail_text = candidate
        if all(k in local for k in ("manufacturer", "game_type", "denomination", "volatility_text")):
            values = local
            detail_text = candidate
            break

    if not any(k in values for k in ("manufacturer", "game_type", "denomination", "volatility_text")):
        return None

    name = ""
    for selector in [
        ".slot-name", ".game-title", ".slot-title", "h1", "h2", "h3", "h4",
        ".modal-title", "strong",
    ]:
        for node in soup.select(selector):
            v = _clean(node.get_text(" ", strip=True))
            if not v:
                continue
            if re.search(r"^(Manufacturer|Type|Denomination|Volatility|Location)\s*:", v, re.I):
                continue
            if len(v) <= 120:
                name = v
                break
        if name:
            break

    if not name and detail_text:
        prefix = re.split(
            r"\s+(?:Manufacturer|Type|Denomination|Volatility|Location)\s*:",
            detail_text,
            maxsplit=1,
            flags=re.I,
        )[0]
        prefix = _clean(prefix)
        if 0 < len(prefix) <= 160:
            name = prefix

    if not name:
        title = _clean(soup.title.get_text(" ", strip=True) if soup.title else "")
        title = re.sub(r"\s*[|\-–]\s*Coushatta.*$", "", title, flags=re.I)
        name = title

    if not name:
        return None

    return SlotRecord(
        sid=int(sid),
        name=name,
        manufacturer=values.get("manufacturer", ""),
        game_type=values.get("game_type", ""),
        denomination=values.get("denomination", ""),
        volatility_text=values.get("volatility_text", ""),
        volatility_score=_volatility_score(values.get("volatility_text", "")),
        location=values.get("location", ""),
        source_url=source_url or DETAIL_URL.format(sid=sid),
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )


def fetch_detail(sid: int, timeout: int = 20) -> SlotRecord | None:
    session = _new_session(timeout=timeout)
    url = DETAIL_URL.format(sid=int(sid))
    try:
        response = _request(session, "GET", url)
    except requests.RequestException:
        return None
    return parse_detail_html(response.text, int(sid), response.url)


def _find_sid_links(html: str, base_url: str = SEARCH_URL) -> list[int]:
    soup = BeautifulSoup(html or "", "html.parser")
    sids: set[int] = set()
    for tag in soup.find_all(["a", "button"]):
        for attr in ("href", "onclick", "data-url", "data-href", "value"):
            sid = _extract_sid(str(tag.get(attr, "")))
            if sid is not None:
                sids.add(sid)
    for m in re.finditer(r"slot-map\.php\?sid=(\d+)", html or "", flags=re.I):
        sids.add(int(m.group(1)))
    return sorted(sids)


def _form_candidates(html: str) -> list[tuple[str, str, dict[str, str], list[str]]]:
    soup = BeautifulSoup(html or "", "html.parser")
    forms = []
    for form in soup.find_all("form"):
        action = urljoin(SEARCH_URL, form.get("action") or SEARCH_URL)
        method = (form.get("method") or "GET").upper()
        defaults: dict[str, str] = {}
        title_fields: list[str] = []
        for field in form.find_all(["input", "select", "textarea"]):
            name = field.get("name")
            if not name:
                continue
            value = field.get("value") or ""
            defaults[name] = value
            hay = " ".join(_clean(field.get(x)) for x in ("name", "id", "placeholder", "class")).lower()
            if any(k in hay for k in ("title", "game", "slot", "name", "search")):
                title_fields.append(name)
        forms.append((method, action, defaults, list(dict.fromkeys(title_fields))))
    return forms


def discover_sids_via_search(timeout: int = 25, wildcard: str = "%%%") -> tuple[list[int], str]:
    session = _new_session(timeout=timeout)
    try:
        landing = _request(session, "GET", SEARCH_URL)
    except requests.RequestException as exc:
        return [], f"Search page request failed: {exc}"

    direct = _find_sid_links(landing.text, landing.url)
    if direct:
        return direct, f"Found {len(direct)} SID links on the initial search page."

    attempts = 0
    for method, action, defaults, title_fields in _form_candidates(landing.text):
        candidate_fields = title_fields or ["title", "game", "game_title", "slot", "search", "q"]
        for field in candidate_fields:
            payload = dict(defaults)
            payload[field] = wildcard
            attempts += 1
            try:
                if method == "POST":
                    response = _request(session, "POST", action, data=payload)
                else:
                    response = _request(session, "GET", action, params=payload)
            except requests.RequestException:
                continue
            sids = _find_sid_links(response.text, response.url)
            if sids:
                return sids, f"Wildcard form discovery succeeded after {attempts} attempt(s)."

    endpoints = set()
    for pattern in [
        r"['\"]([^'\"]*(?:slot|search)[^'\"]*\.php[^'\"]*)['\"]",
        r"(?:url\s*:\s*)['\"]([^'\"]+)['\"]",
    ]:
        for m in re.finditer(pattern, landing.text, flags=re.I):
            endpoint = urljoin(landing.url, m.group(1))
            if endpoint.startswith(BASE_URL):
                endpoints.add(endpoint)

    for endpoint in sorted(endpoints):
        for method in ("GET", "POST"):
            for field in ("title", "game", "game_title", "slot", "search", "q", "slotname"):
                attempts += 1
                try:
                    if method == "POST":
                        response = _request(session, method, endpoint, data={field: wildcard})
                    else:
                        response = _request(session, method, endpoint, params={field: wildcard})
                except requests.RequestException:
                    continue
                sids = _find_sid_links(response.text, response.url)
                if sids:
                    return sids, f"AJAX endpoint discovery succeeded after {attempts} attempt(s)."

    return [], f"No SID links discovered from wildcard search after {attempts} request pattern(s)."


def _probe_sid(sid: int, timeout: int = 15) -> tuple[int, SlotRecord | None]:
    return sid, fetch_detail(sid=sid, timeout=timeout)


def scan_sid_range(
    start_sid: int = 1,
    end_sid: int = 5000,
    workers: int = 6,
    timeout: int = 15,
    progress: ProgressCallback | None = None,
) -> list[SlotRecord]:
    start_sid = max(1, int(start_sid))
    end_sid = max(start_sid, int(end_sid))
    workers = max(1, min(int(workers), 12))
    ids = list(range(start_sid, end_sid + 1))
    total = len(ids)
    results: list[SlotRecord] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_probe_sid, sid, timeout): sid for sid in ids}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            done += 1
            sid = futures[future]
            try:
                _, record = future.result()
            except Exception:
                record = None
            if record is not None:
                results.append(record)
            if progress and (done == total or done % 20 == 0):
                progress(done, total, f"Scanning Coushatta SID {sid}; found {len(results)} valid records")

    return sorted(results, key=lambda r: r.sid)


def fetch_records_for_sids(
    sids: Iterable[int],
    workers: int = 6,
    timeout: int = 15,
    progress: ProgressCallback | None = None,
) -> list[SlotRecord]:
    ids = sorted({int(s) for s in sids if int(s) > 0})
    total = len(ids)
    results: list[SlotRecord] = []
    workers = max(1, min(int(workers), 12))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_probe_sid, sid, timeout): sid for sid in ids}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            done += 1
            sid = futures[future]
            try:
                _, record = future.result()
            except Exception:
                record = None
            if record is not None:
                results.append(record)
            if progress and (done == total or done % 10 == 0):
                progress(done, total, f"Loading Coushatta detail {sid}; parsed {len(results)} records")
    return sorted(results, key=lambda r: r.sid)


def normalize_inventory(records: Iterable[SlotRecord | dict]) -> pd.DataFrame:
    rows = [r.as_dict() if isinstance(r, SlotRecord) else dict(r) for r in records]
    columns = [f.name for f in dataclasses.fields(SlotRecord)]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    df = df[columns]
    df["sid"] = pd.to_numeric(df["sid"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["sid", "name"]).copy()
    df["sid"] = df["sid"].astype(int)
    for col in ["name", "manufacturer", "game_type", "denomination", "volatility_text", "location", "source_url", "casino"]:
        df[col] = df[col].fillna("").astype(str).map(_clean)
    df["volatility_score"] = pd.to_numeric(df["volatility_score"], errors="coerce").astype("Int64")
    df = df.sort_values(["name", "denomination", "sid"], key=lambda s: s.astype(str).str.lower())
    df = df.drop_duplicates(subset=["sid"], keep="last").reset_index(drop=True)
    return df


def inventory_summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"records": 0, "unique_games": 0, "manufacturers": 0, "denominations": 0, "volatility_known": 0}
    return {
        "records": int(len(df)),
        "unique_games": int(df["name"].nunique(dropna=True)),
        "manufacturers": int(df["manufacturer"].replace("", pd.NA).nunique(dropna=True)),
        "denominations": int(df["denomination"].replace("", pd.NA).nunique(dropna=True)),
        "volatility_known": int(df["volatility_text"].replace("", pd.NA).notna().sum()),
    }


def run_coushatta_inventory_worker(
    start_sid: int = 1,
    end_sid: int = 5000,
    workers: int = 6,
    timeout: int = 15,
    wildcard_first: bool = True,
    progress: ProgressCallback | None = None,
) -> tuple[pd.DataFrame, dict]:
    diagnostics: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "",
        "search_diagnostic": "",
        "requested_sid_range": [int(start_sid), int(end_sid)],
    }

    records: list[SlotRecord] = []
    if wildcard_first:
        if progress:
            progress(0, 1, "Trying Coushatta's %%% wildcard search…")
        sids, diag = discover_sids_via_search(timeout=max(timeout, 20), wildcard="%%%")
        diagnostics["search_diagnostic"] = diag
        diagnostics["wildcard_sid_count"] = len(sids)
        if sids:
            diagnostics["strategy"] = "wildcard_search"
            records = fetch_records_for_sids(sids, workers=workers, timeout=timeout, progress=progress)

    if not records:
        diagnostics["strategy"] = "numeric_sid_scan"
        if progress:
            progress(0, max(1, int(end_sid) - int(start_sid) + 1), "Wildcard endpoint unavailable; scanning public SID records…")
        records = scan_sid_range(start_sid, end_sid, workers, timeout, progress)

    df = normalize_inventory(records)
    diagnostics["summary"] = inventory_summary(df)
    diagnostics["finished_at"] = datetime.now(timezone.utc).isoformat()
    return df, diagnostics


def diagnostics_json(diagnostics: dict) -> str:
    return json.dumps(diagnostics, indent=2, default=str)


def _cli() -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Extract Coushatta Casino Resort's public slot inventory")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--output", default="data/coushatta_slot_inventory.csv")
    parser.add_argument("--diagnostics", default="data/coushatta_slot_inventory_diagnostics.json")
    parser.add_argument("--no-wildcard", action="store_true")
    args = parser.parse_args()

    def progress(done: int, total: int, message: str):
        print(f"[{done}/{total}] {message}", flush=True)

    df, diagnostics = run_coushatta_inventory_worker(
        start_sid=args.start,
        end_sid=args.end,
        workers=args.workers,
        timeout=args.timeout,
        wildcard_first=not args.no_wildcard,
        progress=progress,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)

    diag_path = Path(args.diagnostics)
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    diag_path.write_text(diagnostics_json(diagnostics) + "\n", encoding="utf-8")

    print(json.dumps(inventory_summary(df), indent=2), flush=True)
    if df.empty:
        print("ERROR: no Coushatta records were extracted.", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
