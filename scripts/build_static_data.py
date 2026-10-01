"""Build the atlas's durable, reviewable browser datasets.

Usage:
  python3 scripts/build_static_data.py
  python3 scripts/build_static_data.py --check
  python3 scripts/build_static_data.py --fetch --scope countries
  python3 scripts/build_static_data.py --fetch --scope countries --skip-country-facts
  python3 scripts/build_static_data.py --fetch --scope regions --limit 100

Network access is needed only for --fetch. Successful article snapshots are
retained across runs; failed requests never replace them.
"""

import argparse
from dataclasses import dataclass
import json
import re
import tempfile
from html import unescape
from html.parser import HTMLParser
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
if __package__:
    from .validate_genres import map_keys, validate
else:
    from validate_genres import map_keys, validate

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
RESEARCH = ROOT / "research"
ARTICLE_CATALOGUE = RESEARCH / "wiki_articles.json"
USER_AGENT = "MusicAtlasResearch/1.0 (static educational atlas; contact via project repository)"
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
COUNTRY_ARTICLE_TITLES = {
    "PSX": "State of Palestine",
    "GEO": "Georgia (country)",
    "CYN": "Northern Cyprus",
}


@dataclass
class FetchReport:
    fetched: int = 0
    already_saved: int = 0
    unmapped: int = 0
    unavailable: int = 0
    failed: int = 0
    stopped_after_errors: bool = False

    def summary(self, scope):
        suffix = " (error limit reached)" if self.stopped_after_errors else ""
        return (f"{scope}: fetched={self.fetched}, already_saved={self.already_saved}, "
                f"unmapped={self.unmapped}, unavailable={self.unavailable}, failed={self.failed}{suffix}")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as temporary:
        temporary.write(payload)
        temporary.flush()
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def atlas_keys():
    countries = {f["properties"]["code"]: f["properties"]["name"] for f in read(WEB / "countries.geojson")["features"]}
    regions = {f'{f["properties"]["code"]}|{f["properties"]["name"]}' for f in read(WEB / "regions.geojson")["features"]}
    return countries, regions


def meets_media_release(record, media_required_ids):
    """New batch records need both media fields and real public citations."""
    if record["id"] not in media_required_ids:
        return True
    placeholder = any(isinstance(source, dict) and source.get("citation", "").startswith("Local dossier source;")
                      for source in record.get("sources", []))
    return bool(record.get("image") and record.get("youtube_examples") and not placeholder)


def build_genres(check):
    catalogue = read(RESEARCH / "genre_catalogue.json")
    media_release = read(RESEARCH / "genre_media_release_batch.json")
    media_required_ids = set(media_release["genre_ids"])
    assert catalogue["version"] == 1
    ids = [entry["id"] for entry in catalogue["entries"]]
    assert len(ids) == len(set(ids)), "duplicate catalogue IDs"
    assert len(media_required_ids) == len(media_release["genre_ids"]), "duplicate media release IDs"
    assert media_required_ids <= set(ids), "unknown media release ID"
    published = [{k: v for k, v in entry.items() if k not in {"status", "research"}}
                 for entry in catalogue["entries"] if entry["status"] == "published"]
    country_codes, region_names = map_keys()
    from validate_genres import validate_record
    valid = []
    skipped_validation = []
    skipped_media = []
    seen = set()
    for record in published:
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        try:
            validate_record(record, country_codes, region_names)
        except AssertionError as exc:
            skipped_validation.append((record["id"], str(exc)))
            continue
        if not meets_media_release(record, media_required_ids):
            skipped_media.append(record["id"])
            continue
        valid.append(record)
    if skipped_validation or skipped_media:
        print(f"  Held {len(skipped_validation)} published genres failing record validation and {len(skipped_media)} awaiting batch image/video review")
    payload = {"version": 1, "genres": valid}
    path = WEB / "genres.json"
    if check:
        assert read(path) == payload, "genres.json is out of sync; run build_static_data.py"
    else:
        write(path, payload)
    return valid


def build_coverage(genres, check):
    countries, _ = atlas_keys()
    inventory = read(RESEARCH / "country_inventory.json")
    rows = inventory["countries"]
    assert {row["code"] for row in rows} == set(countries), "country inventory differs from map"
    counts = Counter(genre["country"] for genre in genres)
    statuses = {"unreviewed": "unresearched", "starter_only": "in_progress", "reviewed": "reviewed"}
    payload = {"version": 1, "countries": {
        row["code"]: {
            "status": statuses[row["status"]],
            "published_genres": counts[row["code"]],
            "reviewed_at": row["reviewed_at"],
            "summary": row["summary"],
            "gaps": row["gaps"],
        } for row in rows
    }}
    path = WEB / "coverage.json"
    if check:
        assert read(path) == payload, "coverage.json is out of sync; run build_static_data.py"
    else:
        write(path, payload)


def snapshot_keys(genres):
    countries, regions = atlas_keys()
    country_titles = {code: COUNTRY_ARTICLE_TITLES.get(code, name) for code, name in countries.items()}
    return {"countries": country_titles, "regions": {key: key.split("|", 1)[1] for key in sorted(regions)},
            "genres": {genre["id"]: {"title": genre.get("wikipedia_title"),
                                     "language": genre.get("wikipedia_language", "en"),
                                     "section": genre.get("wikipedia_section"),
                                     "focus": genre.get("wikipedia_focus"),
                                     "url": genre.get("wikipedia_url")} for genre in genres}}


def load_snapshot(genres):
    path = ARTICLE_CATALOGUE
    saved = read(path) if path.exists() else {}
    output = {"version": 1, "generated_at": saved.get("generated_at"), "countries": {}, "regions": {}, "genres": {}}
    for scope, keys in snapshot_keys(genres).items():
        previous = saved.get(scope, {})
        output[scope] = {}
        for key, request in keys.items():
            article = previous.get(key)
            if scope == "genres" and article:
                requested_title = request["title"]
                saved_request = article.get("requested_title") or article.get("title")
                if (not requested_title or saved_request != requested_title
                        or article.get("language", "en") != request["language"]
                        or article.get("requested_section") != request["section"]
                        or article.get("requested_focus") != request["focus"]):
                    article = None
            output[scope][key] = article
    return output


def api(host, params):
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode({"format": "json", "formatversion": "2", **params})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            delay = error.headers.get("Retry-After")
            time.sleep(min(int(delay), 90) if delay and delay.isdigit() else min(5 * (2 ** attempt), 40))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(min(5 * (2 ** attempt), 40))


def rest_page(title, kind, language="en"):
    path = urllib.parse.quote(title.replace(" ", "_"), safe="()")
    request = urllib.request.Request(f"https://{language}.wikipedia.org/api/rest_v1/page/{kind}/{path}",
                                     headers={"User-Agent": USER_AGENT, "Accept": "application/json" if kind == "summary" else "text/html"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response) if kind == "summary" else response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            delay = error.headers.get("Retry-After")
            time.sleep(min(int(delay), 90) if delay and delay.isdigit() else min(5 * (2 ** attempt), 40))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(min(5 * (2 ** attempt), 40))


class IntroParagraphs(HTMLParser):
    """Plain text from lead paragraphs, excluding tables, citations and notes."""

    def __init__(self, include_lists=False):
        super().__init__()
        self.include_lists = include_lists
        self.stack = []
        self.paragraph = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        chrome = any(name.startswith(("bandeau", "infobox", "hatnote", "mw-editsection")) for name in classes)
        skipped = (bool(self.stack and self.stack[-1]) or chrome
                   or tag in {"table", "style", "script", "sup", "figure", "nav"}
                   or (tag == "div" and attrs.get("role") == "note"))
        self.stack.append(skipped)
        if (tag == "p" or (self.include_lists and tag == "li")) and not skipped:
            self.paragraph = []

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in ({"p", "li"} if self.include_lists else {"p"}) and self.paragraph is not None:
            paragraph = " ".join("".join(self.paragraph).split())
            if paragraph:
                self.parts.append(paragraph)
            self.paragraph = None
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.paragraph is not None and not (self.stack and self.stack[-1]):
            self.paragraph.append(data)


def intro_text(html):
    marker = '<section data-mw-section-id="0"'
    start = html.find(marker)
    if start < 0:
        return ""
    end = html.find('<section data-mw-section-id="1"', start)
    parser = IntroParagraphs()
    parser.feed(html[start:end if end >= 0 else None])
    return "\n\n".join(parser.parts)


class HeadingText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def section_text(html, title, focus=None):
    """Return only the named article section, never its broader page lead."""
    boundaries = list(re.finditer(r'<section\b[^>]*data-mw-section-id="\d+"[^>]*>', html))
    wanted = " ".join(unescape(title).split()).casefold()
    for index, boundary in enumerate(boundaries):
        end = boundaries[index + 1].start() if index + 1 < len(boundaries) else len(html)
        block = html[boundary.start():end]
        heading = re.search(r'<h[2-6]\b[^>]*>.*?</h[2-6]>', block, re.DOTALL)
        if not heading:
            continue
        plain = HeadingText()
        plain.feed(heading.group())
        actual = " ".join("".join(plain.parts).split()).casefold()
        if actual != wanted and not (":" in wanted and wanted.rsplit(":", 1)[-1].strip() == actual):
            continue
        parser = IntroParagraphs(include_lists=bool(focus))
        parser.feed(block)
        parts = parser.parts
        if focus:
            parts = [part for part in parts if focus.casefold() in part.casefold()]
        return "\n\n".join(parts)
    return ""


def quantity(entity, prop):
    claims = entity.get("claims", {}).get(prop, [])
    values = []
    for claim in claims:
        try:
            raw = claim["mainsnak"]["datavalue"]["value"]
            amount = float(raw["amount"])
            qualifier = claim.get("qualifiers", {}).get("P585", [])
            year = int(qualifier[0]["datavalue"]["value"]["time"][1:5]) if qualifier else None
            values.append((year or 0, amount, raw.get("unit")))
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    return max(values) if values else None


def facts(qid):
    if not qid:
        return None, None
    result = api("www.wikidata.org", {"action": "wbgetentities", "ids": qid, "props": "claims"})
    entity = result.get("entities", {}).get(qid, {})
    population = quantity(entity, "P1082")
    area = quantity(entity, "P2046")
    units = {"http://www.wikidata.org/entity/Q712226": 1,
             "http://www.wikidata.org/entity/Q25343": 0.000001,
             "http://www.wikidata.org/entity/Q35852": 0.01,
             "http://www.wikidata.org/entity/Q232291": 2.589988}
    area_km2 = round(area[1] * units[area[2]], 2) if area and area[2] in units else None
    return ({"value": round(population[1]), "year": population[0] or None} if population else None), area_km2


def fetch_article(title, geo=False, language="en", section=None, exact_url=None, focus=None):
    try:
        summary = rest_page(title, "summary", language)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    if summary.get("type") == "disambiguation":
        return None
    resolved = summary.get("title", title)
    html = rest_page(resolved, "html", language)
    extract = section_text(html, section, focus) if section else intro_text(html)
    if not extract:
        return None
    qid = summary.get("wikibase_item")
    population, area = None, None
    if geo and qid:
        try:
            population, area = facts(qid)
        except (urllib.error.URLError, TimeoutError, ValueError):
            # Preserve the article when Wikidata is temporarily unavailable.
            pass
    return {"title": resolved, "requested_title": title, "requested_section": section,
            "requested_focus": focus,
            "language": language, "extract": extract,
            "url": exact_url or summary.get("content_urls", {}).get("desktop", {}).get("page") or f"https://{language}.wikipedia.org/wiki/" + urllib.parse.quote(resolved.replace(" ", "_")),
            "population": population, "area_km2": area,
            "wikidata_url": f"https://www.wikidata.org/wiki/{qid}" if qid else None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "revision_id": summary.get("revision"),
            "license": LICENSE, "license_url": LICENSE_URL}


def bulk_region_articles(titles):
    """Fetch English Wikipedia lead snapshots for up to 50 requested titles."""
    if not titles:
        return {}
    if len(titles) > 50:
        raise ValueError("MediaWiki title batches cannot exceed 50")
    result = api("en.wikipedia.org", {
        "action": "query",
        "titles": "|".join(titles),
        "redirects": "1",
        "prop": "extracts|info|pageprops|revisions",
        "exintro": "1",
        "exlimit": "max",
        "explaintext": "1",
        "inprop": "url",
        "rvprop": "ids",
    })
    query = result.get("query", {})
    aliases = {title: title for title in titles}
    for item in query.get("normalized", []):
        for requested, resolved in list(aliases.items()):
            if resolved == item.get("from"):
                aliases[requested] = item.get("to", resolved)
    for item in query.get("redirects", []):
        for requested, resolved in list(aliases.items()):
            if resolved == item.get("from"):
                aliases[requested] = item.get("to", resolved)
    pages = {page.get("title"): page for page in query.get("pages", [])}
    fetched_at = datetime.now(timezone.utc).isoformat()
    articles = {}
    for requested, resolved in aliases.items():
        page = pages.get(resolved)
        extract = page.get("extract", "").strip() if page else ""
        props = page.get("pageprops", {}) if page else {}
        if not page or page.get("missing") or "disambiguation" in props or not extract:
            articles[requested] = None
            continue
        qid = props.get("wikibase_item")
        revisions = page.get("revisions", [])
        articles[requested] = {
            "title": page.get("title", resolved),
            "requested_title": requested,
            "requested_section": None,
            "requested_focus": None,
            "language": "en",
            "extract": extract,
            "url": page.get("canonicalurl") or page.get("fullurl"),
            "population": None,
            "area_km2": None,
            "wikidata_url": f"https://www.wikidata.org/wiki/{qid}" if qid else None,
            "fetched_at": fetched_at,
            "revision_id": revisions[0].get("revid") if revisions else None,
            "license": LICENSE,
            "license_url": LICENSE_URL,
        }
    return articles


def public_snapshot(snapshot, public_genre_ids=None):
    if public_genre_ids is None:
        return snapshot
    return {**snapshot, "genres": {key: value for key, value in snapshot["genres"].items()
                                   if key in public_genre_ids}}


def checkpoint(snapshot, public_genre_ids=None):
    snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
    write(ARTICLE_CATALOGUE, snapshot)
    write(WEB / "articles.json", public_snapshot(snapshot, public_genre_ids))


def refresh_articles_bulk(snapshot, scope, keys, article_titles, limit, selected, delay, max_errors, batch_size,
                          public_genre_ids=None):
    """Fetch mapped country or region leads in action-API batches and checkpoint each batch."""
    report = FetchReport()
    pending = []
    for key in keys:
        if selected and key not in selected:
            continue
        if snapshot[scope][key] is not None:
            report.already_saved += 1
            continue
        title = article_titles.get(key)
        if not title:
            report.unmapped += 1
            continue
        pending.append((key, title))
        if limit is not None and len(pending) >= limit:
            break

    # The extracts module caps non-bot clients at 20 pages even when exlimit=max.
    effective_batch_size = min(batch_size, 20)
    for offset in range(0, len(pending), effective_batch_size):
        batch = pending[offset:offset + effective_batch_size]
        titles = [title for _, title in batch]
        try:
            articles = bulk_region_articles(titles)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            report.failed += len(batch)
            print(f"{scope.title()} batch failed at {batch[0][0]} ({len(batch)} titles): {error}")
            if max_errors is not None and report.failed >= max_errors:
                report.stopped_after_errors = True
                break
        else:
            changed = False
            for key, title in batch:
                article = articles.get(title)
                if article:
                    snapshot[scope][key] = article
                    report.fetched += 1
                    changed = True
                else:
                    report.unavailable += 1
            if changed:
                checkpoint(snapshot, public_genre_ids)
        if delay and offset + effective_batch_size < len(pending):
            time.sleep(delay)
    return report


def refresh(snapshot, genres, scope, limit, selected, delay=2, max_errors=20, batch_size=50,
            country_facts=True, public_genre_ids=None):
    """Fetch missing snapshots while preserving progress across individual failures.

    ``limit`` counts network attempts rather than only successes. This makes a
    bounded batch predictable even when mappings resolve to missing pages.
    """
    keys = snapshot_keys(genres)[scope]
    region_titles_path = RESEARCH / "region_article_titles.json"
    region_titles = read(region_titles_path) if region_titles_path.exists() else {}
    report = FetchReport()
    attempted = 0
    unknown = selected - set(keys)
    for key in sorted(unknown):
        print(f"Unknown {scope} key: {key}")
    if scope == "regions":
        return refresh_articles_bulk(snapshot, scope, keys, region_titles, limit, selected,
                                     delay, max_errors, batch_size, public_genre_ids)
    if scope == "countries" and not country_facts:
        return refresh_articles_bulk(snapshot, scope, keys, keys, limit, selected,
                                     delay, max_errors, batch_size, public_genre_ids)
    for key, request in keys.items():
        if selected and key not in selected:
            continue
        if snapshot[scope][key] is not None:
            report.already_saved += 1
            continue
        if limit is not None and attempted >= limit:
            break
        if scope == "genres":
            title = request["title"]
            if not title:
                report.unmapped += 1
                continue
        else:
            title = request
        if scope == "regions":
            title = region_titles.get(key)
            if not title:
                report.unmapped += 1
                continue
        attempted += 1
        try:
            article = (fetch_article(title, False, request["language"], request["section"], request["url"], request["focus"])
                       if scope == "genres" else fetch_article(title, country_facts))
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            report.failed += 1
            print(f"Fetch failed at {scope}/{key}: {error}")
            if max_errors is not None and report.failed >= max_errors:
                report.stopped_after_errors = True
                break
            if delay:
                time.sleep(delay)
            continue
        if article:
            snapshot[scope][key] = article
            report.fetched += 1
            checkpoint(snapshot, public_genre_ids)
        else:
            report.unavailable += 1
        if delay:
            time.sleep(delay)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated files match research sources")
    parser.add_argument("--fetch", action="store_true", help="fetch missing article snapshots once, during research")
    parser.add_argument("--scope", choices=("countries", "regions", "genres"), default="countries")
    parser.add_argument("--limit", type=int, help="maximum article fetch attempts this run")
    parser.add_argument("--keys", nargs="*", help="specific country codes, region keys, or genre IDs to fetch")
    parser.add_argument("--delay", type=float, default=2,
                        help="seconds between article attempts (default: 2)")
    parser.add_argument("--max-errors", type=int, default=20,
                        help="stop after this many request errors; 0 disables the limit (default: 20)")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="MediaWiki titles per region request, 1-50 (default: 50)")
    parser.add_argument("--skip-country-facts", action="store_true",
                        help="save country article text without optional Wikidata population and area requests")
    args = parser.parse_args()
    genres = build_genres(args.check)
    build_coverage(genres, args.check)
    all_published = [entry for entry in read(RESEARCH / "genre_catalogue.json")["entries"]
                     if entry["status"] == "published"]
    snapshot = load_snapshot(all_published)
    public_ids = {genre["id"] for genre in genres}
    if args.check:
        assert read(ARTICLE_CATALOGUE) == snapshot, "saved article keys are out of sync"
        assert read(WEB / "articles.json") == public_snapshot(snapshot, public_ids), "article keys are out of sync"
        missing_countries = [key for key, article in snapshot["countries"].items()
                             if not article or not article.get("extract")]
        assert not missing_countries, f"countries lack saved descriptions: {', '.join(missing_countries)}"
    else:
        write(ARTICLE_CATALOGUE, snapshot)
        write(WEB / "articles.json", public_snapshot(snapshot, public_ids))
    if args.fetch:
        if args.check:
            parser.error("--check and --fetch cannot be combined")
        if args.limit is not None and args.limit < 1:
            parser.error("--limit must be at least 1")
        if args.delay < 0:
            parser.error("--delay cannot be negative")
        if args.max_errors < 0:
            parser.error("--max-errors cannot be negative")
        if not 1 <= args.batch_size <= 50:
            parser.error("--batch-size must be between 1 and 50")
        report = refresh(snapshot, all_published, args.scope, args.limit, set(args.keys or []),
                         args.delay, args.max_errors or None, args.batch_size,
                         country_facts=not args.skip_country_facts, public_genre_ids=public_ids)
        print(report.summary(args.scope))
    for scope in ("countries", "regions", "genres"):
        print(f"{scope}: {sum(value is not None for value in snapshot[scope].values())}/{len(snapshot[scope])} static articles")


if __name__ == "__main__":
    main()
