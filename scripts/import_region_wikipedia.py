"""Import Wikipedia leads for every Natural Earth admin-1 region.

The importer is resumable and checkpoints after every API batch. Natural
Earth Wikidata IDs are authoritative for title resolution; English Wikipedia
search is used only when a matched Natural Earth row has no usable enwiki
sitelink (including rows without a Wikidata ID).

Examples:
  python3 scripts/import_region_wikipedia.py --source regions.source.geojson --dry-run
  python3 scripts/import_region_wikipedia.py --source regions.source.geojson
  python3 scripts/import_region_wikipedia.py --source-url URL --cache /tmp/admin1.geojson
"""

import argparse
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
RESEARCH = ROOT / "research"
MAP = WEB / "regions.geojson"
COUNTRIES = WEB / "countries.geojson"
TITLES = RESEARCH / "region_article_titles.json"
ARTICLES = RESEARCH / "wiki_articles.json"
PUBLIC_ARTICLES = WEB / "articles.json"
STATUS = RESEARCH / "region_article_import_status.json"
USER_AGENT = "MusicAtlasResearch/1.0 (static educational atlas; region import)"
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
ENWIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_QUERY = "https://query.wikidata.org/sparql"


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def api(endpoint, params):
    query = urllib.parse.urlencode({"format": "json", "formatversion": 2, **params})
    request = urllib.request.Request(f"{endpoint}?{query}", headers={"User-Agent": USER_AGENT,
                                                                     "Accept": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 and not 500 <= error.code < 600:
                raise
            if attempt == 5:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
            time.sleep(min(delay, 60))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))


def chunks(values, size=50):
    values = list(values)
    for start in range(0, len(values), size):
        yield values[start:start + size]


def sparql(query):
    body = urllib.parse.urlencode({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        WIKIDATA_QUERY,
        data=body,
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            retryable = not isinstance(error, urllib.error.HTTPError) or error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == 5:
                raise
            time.sleep(min(5 * (attempt + 1), 60))


def normalized(value):
    return re.sub(r"[^0-9a-z]+", "", (value or "").casefold())


def property_value(properties, *names):
    folded = {key.casefold(): value for key, value in properties.items()}
    for name in names:
        value = folded.get(name.casefold())
        if value not in (None, "", "-99"):
            return str(value).strip()
    return None


def load_source(path=None, url=None, cache=None):
    if path:
        raw = Path(path).read_bytes()
        source_label = str(Path(path).resolve())
    else:
        if not url:
            raise ValueError("one of --source or --source-url is required")
        if cache and Path(cache).exists():
            raw = Path(cache).read_bytes()
        else:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
            if cache:
                Path(cache).write_bytes(raw)
        source_label = url
    if raw[:2] == b"PK":
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith((".geojson", ".json"))]
            if not names:
                raise ValueError("ZIP source contains no GeoJSON/JSON file")
            raw = archive.read(sorted(names)[0])
    return json.loads(raw), source_label


def map_inventory():
    features = read(MAP)["features"]
    keys = sorted({f'{f["properties"]["code"]}|{f["properties"]["name"]}' for f in features})
    countries = {feature["properties"]["code"]: feature["properties"]["name"]
                 for feature in read(COUNTRIES)["features"]}
    return keys, countries


def match_source(source, keys):
    exact = defaultdict(list)
    loose = defaultdict(list)
    for feature in source["features"]:
        props = feature.get("properties", {})
        code = property_value(props, "adm0_a3", "ADM0_A3", "code")
        name = property_value(props, "name_en", "NAME_EN", "name", "NAME")
        if not code or not name:
            continue
        exact[(code, name)].append(props)
        loose[(code, normalized(name))].append(props)
    matched, missing, ambiguous = {}, [], {}
    for key in keys:
        code, name = key.split("|", 1)
        candidates = exact.get((code, name)) or loose.get((code, normalized(name)), [])
        # Duplicate Natural Earth polygons with identical identity are harmless
        # only when their Wikidata IDs agree.
        qids = {property_value(row, "wikidataid", "wikidata_id", "WIKIDATAID") for row in candidates}
        qids.discard(None)
        if not candidates:
            missing.append(key)
        elif len(qids) > 1:
            ambiguous[key] = sorted(qids)
        else:
            matched[key] = {"qid": next(iter(qids), None), "source_name": name}
    return matched, missing, ambiguous


def resolve_qid_sitelinks(matched):
    by_qid = defaultdict(list)
    for key, row in matched.items():
        if row["qid"]:
            by_qid[row["qid"]].append(key)
    resolved = {}
    missing_sitelink = []
    # WDQS may enforce a one-request-per-minute outage policy, so resolve the
    # complete current atlas in one POST rather than issuing small batches.
    for batch in chunks(sorted(by_qid), 2000):
        values = " ".join(f"wd:{qid}" for qid in batch)
        payload = sparql(
            "SELECT ?item ?article WHERE { VALUES ?item { " + values
            + " } ?article schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>. }"
        )
        sitelinks = {
            row["item"]["value"].rsplit("/", 1)[-1]:
                urllib.parse.unquote(row["article"]["value"].rsplit("/wiki/", 1)[-1]).replace("_", " ")
            for row in payload.get("results", {}).get("bindings", [])
        }
        for qid in batch:
            title = sitelinks.get(qid)
            for key in by_qid[qid]:
                if title:
                    resolved[key] = {"title": title, "qid": qid, "method": "natural_earth_wikidata_sitelink"}
                else:
                    missing_sitelink.append(key)
    return resolved, missing_sitelink


def search_fallback(keys, countries, matched):
    resolved = {}
    for key in keys:
        code, name = key.split("|", 1)
        query = f'intitle:"{name}" {countries[code]}'
        payload = api(ENWIKI_API, {"action": "query", "generator": "search", "gsrsearch": query,
                                   "gsrnamespace": 0, "gsrlimit": 5, "prop": "pageprops"})
        pages = payload.get("query", {}).get("pages", [])
        if not pages:
            continue
        # Deterministic ordering: MediaWiki search rank, then page id. The
        # result remains marked search_fallback for later editorial review.
        page = pages[0]
        resolved[key] = {"title": page["title"],
                         "qid": page.get("pageprops", {}).get("wikibase_item") or matched[key].get("qid"),
                         "method": "enwiki_search_fallback"}
        time.sleep(0.1)
    return resolved


def fetch_leads(resolutions):
    by_title = defaultdict(list)
    for key, row in resolutions.items():
        by_title[row["title"]].append(key)
    fetched = {}
    for batch_number, batch in enumerate(chunks(sorted(by_title), 20), start=1):
        payload = api(ENWIKI_API, {"action": "query", "titles": "|".join(batch), "redirects": 1,
                                   "prop": "extracts|revisions|pageprops|info",
                                   "exintro": 1, "explaintext": 1, "rvprop": "ids|timestamp",
                                   "inprop": "url"})
        normal = {row["from"]: row["to"] for row in payload.get("query", {}).get("normalized", [])}
        redirects = {row["from"]: row["to"] for row in payload.get("query", {}).get("redirects", [])}
        pages = {page.get("title"): page for page in payload.get("query", {}).get("pages", [])}
        for requested in batch:
            title = redirects.get(normal.get(requested, requested), normal.get(requested, requested))
            page = pages.get(title)
            if not page or page.get("missing") or not page.get("extract"):
                continue
            revision = (page.get("revisions") or [{}])[0]
            for key in by_title[requested]:
                resolution = resolutions[key]
                fetched[key] = {
                    "title": page["title"], "requested_title": requested,
                    "requested_section": None, "requested_focus": None, "language": "en",
                    "extract": page["extract"], "url": page.get("fullurl"),
                    "population": None, "area_km2": None,
                    "wikidata_url": (f'https://www.wikidata.org/wiki/{resolution["qid"]}'
                                      if resolution.get("qid") else None),
                    "fetched_at": now(), "revision_id": revision.get("revid"),
                    "revision_timestamp": revision.get("timestamp"),
                    "license": LICENSE, "license_url": LICENSE_URL,
                    "region_import": {"method": resolution["method"],
                                      "natural_earth_wikidata_id": resolution.get("qid")},
                }
        yield fetched.copy()
        print(f"article batch {batch_number}: {len(fetched)}/{len(resolutions)} resolved pages", flush=True)


def checkpoint(titles, articles, status):
    atomic_write(TITLES, dict(sorted(titles.items())))
    atomic_write(ARTICLES, articles)
    atomic_write(PUBLIC_ARTICLES, articles)
    atomic_write(STATUS, status)


def run(source, source_label, dry_run=False, no_search=False, reviewed_fallbacks=None):
    keys, countries = map_inventory()
    matched, unmatched, ambiguous = match_source(source, keys)
    existing_titles = read(TITLES, {})
    articles = read(ARTICLES, {"version": 1, "generated_at": None,
                               "countries": {}, "regions": {}, "genres": {}})
    articles.setdefault("regions", {})
    status = {"version": 1, "updated_at": now(), "source": source_label,
              "map_key_count": len(keys), "source_matched_count": len(matched),
              "source_unmatched": unmatched, "source_ambiguous": ambiguous,
              "resolved": {}, "unresolved": []}
    if dry_run:
        return status
    reviewed_fallbacks = reviewed_fallbacks or {}
    predefined = {**existing_titles, **{key: title for key, title in reviewed_fallbacks.items() if title}}
    if set(keys) <= set(predefined):
        resolutions = {
            key: {"title": predefined[key], "qid": matched.get(key, {}).get("qid"),
                  "method": ("reviewed_fallback_mapping" if key in reviewed_fallbacks
                             else "natural_earth_wikidata_sitelink"
                             if matched.get(key, {}).get("qid") else "existing_reviewed_mapping")}
            for key in keys
        }
    else:
        resolutions, lacking = resolve_qid_sitelinks(matched)
        fallback_keys = sorted(set(lacking) | {key for key, row in matched.items() if not row["qid"]})
        if not no_search:
            resolutions.update(search_fallback(fallback_keys, countries, matched))
    # Existing reviewed titles win over automated resolution.
    for key, title in existing_titles.items():
        if key in matched and (key not in resolutions or resolutions[key]["title"] != title):
            resolutions[key] = {"title": title, "qid": matched[key].get("qid"),
                                "method": "existing_reviewed_mapping"}
    # Explicitly reviewed corrections override both automated and previously
    # generated titles.
    for key, title in reviewed_fallbacks.items():
        if key in keys and title:
            resolutions[key] = {"title": title, "qid": matched.get(key, {}).get("qid"),
                                "method": "reviewed_fallback_mapping"}
    titles = dict(existing_titles)
    titles.update({key: row["title"] for key, row in resolutions.items()})
    status["resolved"] = resolutions
    status["unresolved"] = sorted(set(keys) - set(resolutions))
    for key, resolution in resolutions.items():
        article = articles["regions"].get(key)
        if article:
            article["region_import"] = {
                "method": resolution["method"],
                "natural_earth_wikidata_id": resolution.get("qid"),
            }
            if resolution.get("qid"):
                article["wikidata_url"] = f'https://www.wikidata.org/wiki/{resolution["qid"]}'
    # Persist authoritative title resolution before article retrieval so a
    # transient Wikipedia failure never discards a completed Wikidata query.
    checkpoint(titles, articles, status)
    pending = {
        key: row for key, row in resolutions.items()
        if articles["regions"].get(key) is None
        or (articles["regions"][key].get("requested_title") or articles["regions"][key].get("title"))
        != row["title"]
    }
    for partial in fetch_leads(pending):
        for key, article in partial.items():
            articles["regions"][key] = article
        articles["generated_at"] = now()
        status["updated_at"] = now()
        status["article_count"] = sum(value is not None for value in articles["regions"].values())
        checkpoint(titles, articles, status)
    checkpoint(titles, articles, status)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", type=Path)
    source.add_argument("--source-url")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="match source only; do not call Wikimedia or write")
    parser.add_argument("--no-search", action="store_true", help="leave missing sitelinks unresolved")
    parser.add_argument("--reviewed-fallbacks", type=Path,
                        help="reviewed proposal JSON containing a mappings object")
    args = parser.parse_args()
    payload, label = load_source(args.source, args.source_url, args.cache)
    fallbacks = read(args.reviewed_fallbacks, {}).get("mappings", {}) if args.reviewed_fallbacks else {}
    status = run(payload, label, args.dry_run, args.no_search, fallbacks)
    print(f"map keys: {status['map_key_count']}")
    print(f"Natural Earth matches: {status['source_matched_count']}")
    print(f"unmatched: {len(status['source_unmatched'])}")
    print(f"ambiguous: {len(status['source_ambiguous'])}")
    if not args.dry_run:
        print(f"resolved titles: {len(status['resolved'])}")
        print(f"unresolved titles: {len(status['unresolved'])}")


if __name__ == "__main__":
    main()
