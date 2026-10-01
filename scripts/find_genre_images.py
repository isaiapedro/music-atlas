"""Find review candidates on Wikimedia Commons without downloading or publishing images.

The script writes a private queue. A human must verify depiction and the source
file page before copying a candidate into research/genre_catalogue.json.
"""
import argparse
import json
import tempfile
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
ALLOWED_LICENSES = {
    "CC0", "PDM", "Public Domain", "CC BY 2.0", "CC BY 2.5", "CC BY 3.0",
    "CC BY 4.0", "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0",
}
USER_AGENT = "MusicAtlasImageResearch/1.0 (local editorial review queue)"


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def get(params):
    request = urllib.request.Request(
        COMMONS_API + "?" + urllib.parse.urlencode({"format": "json", "formatversion": "2", **params}),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wikipedia_get(params):
    request = urllib.request.Request(
        WIKIPEDIA_API + "?" + urllib.parse.urlencode({"format": "json", "formatversion": "2", **params}),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def openverse_candidates(query, limit):
    request = urllib.request.Request(
        OPENVERSE_API + "?" + urllib.parse.urlencode({"q": query, "page_size": limit}),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        results = json.load(response).get("results", [])
    licenses = {"cc0": "CC0", "pdm": "PDM", "by": "CC BY 4.0", "by-sa": "CC BY-SA 4.0"}
    rows = []
    for item in results:
        license_name = licenses.get(item.get("license"))
        landing = item.get("foreign_landing_url") or item.get("url")
        if not license_name or not isinstance(landing, str) or not landing.startswith("https://"):
            continue
        rows.append({
            "image_url": item.get("thumbnail") or item.get("url"),
            "source_page_url": landing,
            "title": item.get("title") or query,
            "creator": item.get("creator") or "Unknown creator",
            "license": license_name,
            "license_url": item.get("license_url") or "",
            "credit": "",
            "description": item.get("description") or item.get("title") or query,
            "provider": "openverse",
        })
    return rows


def commons_file_candidate(title):
    result = get({"action": "query", "titles": "File:" + title, "prop": "imageinfo",
                  "iiprop": "url|extmetadata", "iiurlwidth": 900})
    pages = result.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    info = (page.get("imageinfo") or [{}])[0]
    metadata = info.get("extmetadata") or {}
    license_name = text(metadata.get("LicenseShortName"))
    if license_name not in ALLOWED_LICENSES:
        return None
    return {
        "image_url": info.get("thumburl") or info.get("url"),
        "source_page_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
        "title": text(metadata.get("ObjectName")) or page["title"].removeprefix("File:"),
        "creator": text(metadata.get("Artist")) or "Unknown creator",
        "license": license_name,
        "license_url": text(metadata.get("LicenseUrl")),
        "credit": text(metadata.get("Credit")),
        "description": text(metadata.get("ImageDescription")),
        "provider": "wikimedia_commons",
    }


def text(value):
    value = value.get("value", "") if isinstance(value, dict) else value or ""
    parser = PlainText()
    parser.feed(value)
    return unescape("".join(parser.parts)).strip()


def candidates(query, limit):
    result = get({"action": "query", "generator": "search", "gsrsearch": query,
                  "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
                  "iiprop": "url|extmetadata", "iiurlwidth": 900})
    rows = []
    for page in result.get("query", {}).get("pages", []):
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata") or {}
        license_name = text(metadata.get("LicenseShortName"))
        if license_name not in ALLOWED_LICENSES:
            continue
        rows.append({
            "image_url": info.get("thumburl") or info.get("url"),
            "source_page_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
            "title": text(metadata.get("ObjectName")) or page["title"].removeprefix("File:"),
            "creator": text(metadata.get("Artist")) or "Unknown creator",
            "license": license_name,
            "license_url": text(metadata.get("LicenseUrl")),
            "credit": text(metadata.get("Credit")),
            "description": text(metadata.get("ImageDescription")),
            "provider": "wikimedia_commons",
        })
    return rows


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def reviewed_image(item):
    """Only a documented selection may leave the private discovery queue."""
    review = item.get("review") or {}
    index = review.get("candidate_index")
    if type(index) is not int or not 0 <= index < len(item.get("results", [])):
        return None
    if review.get("source_page_verified") is not True or review.get("license_verified") is not True:
        return None
    depicts = (review.get("depicts") or "").strip()
    if len(depicts) < 20:
        return None
    candidate = item["results"][index]
    if candidate.get("license") not in ALLOWED_LICENSES:
        return None
    if not str(candidate.get("image_url", "")).startswith("https://"):
        return None
    source = str(candidate.get("source_page_url", ""))
    if not source.startswith("https://"):
        return None
    provider = candidate.get("provider")
    if provider not in {"wikimedia_commons", "openverse"}:
        return None
    creator = candidate.get("creator") or "Unknown creator"
    return {
        "image_url": candidate["image_url"], "source_page_url": source.replace("File%3A", "File:"),
        "title": candidate.get("title") or "Untitled", "creator": creator,
        "license": candidate["license"],
        "attribution": f'{creator}, {candidate["license"]}, via {"Wikimedia Commons" if provider == "wikimedia_commons" else "Openverse"}',
        "depicts": depicts, "provider": provider, "reviewed_at": date.today().isoformat(),
    }


def search_with_backoff(search, *args, delay):
    """Bound retries so a throttled provider cannot stall the entire queue forever."""
    for attempt in range(4):
        try:
            return search(*args)
        except HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            retry_after = error.headers.get("Retry-After", "") if error.headers else ""
            try:
                seconds = float(retry_after)
            except ValueError:
                seconds = 0
            time.sleep(min(120, max(seconds, delay, 5 * (2 ** attempt))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", dest="ids", help="Published genre ID to search; repeatable")
    parser.add_argument("--limit", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--delay", type=float, default=1.2,
                        help="Seconds between Commons searches (default: 1.2).")
    parser.add_argument("--resume", action="store_true",
                        help="Continue an existing queue at --out without repeating completed searches.")
    parser.add_argument("--approve", action="store_true",
                        help="Apply only queue candidates with explicit review and verified source-page licence.")
    parser.add_argument("--broaden", action="store_true",
                        help="Retry queued empty searches using the genre name and aliases without a country qualifier.")
    parser.add_argument("--wiki-fallback", action="store_true",
                        help="Use lead images from verified English Wikipedia genre pages for queued empty searches.")
    parser.add_argument("--openverse-fallback", action="store_true",
                        help="Search Openverse for reusable candidates for queued empty searches.")
    parser.add_argument("--sync-queue", action="store_true",
                        help="Add every current unillustrated published genre missing from the private queue.")
    parser.add_argument("--prune-queue", action="store_true",
                        help="Remove queue rows for retired, unified, published-image, or non-published genre IDs.")
    parser.add_argument("--apply-curation", action="store_true",
                        help="Alias of --approve; requires explicit review metadata in each queue item.")
    parser.add_argument("--out", type=Path, default=ROOT / ".local" / "image_candidates.json")
    args = parser.parse_args()
    catalogue = json.loads((ROOT / "research" / "genre_catalogue.json").read_text(encoding="utf-8"))
    if args.prune_queue:
        output = json.loads(args.out.read_text(encoding="utf-8"))
        eligible = {row["id"] for row in catalogue["entries"] if row["status"] == "published" and not row.get("image")}
        before = len(output.get("candidates", []))
        output["candidates"] = [item for item in output.get("candidates", []) if item["genre_id"] in eligible]
        write(args.out, output)
        print(f"removed {before - len(output['candidates'])} stale queue rows")
        return
    if args.sync_queue:
        output = {"generated_at": date.today().isoformat(), "provider": "mixed", "candidates": []}
        if args.out.exists():
            output = json.loads(args.out.read_text(encoding="utf-8"))
        queued = {item["genre_id"] for item in output.get("candidates", [])}
        countries = json.loads((ROOT / "web" / "data" / "countries.geojson").read_text(encoding="utf-8"))
        country_names = {feature["properties"]["code"]: feature["properties"]["name"] for feature in countries["features"]}
        added = 0
        for genre in catalogue["entries"]:
            if genre["status"] != "published" or genre.get("image") or genre["id"] in queued:
                continue
            output["candidates"].append({"genre_id": genre["id"], "query": f'{genre["name"]} {country_names[genre["country"]]}', "results": []})
            added += 1
        write(args.out, output)
        print(f"added {added} unillustrated genres to the discovery queue")
        return
    if args.approve or args.apply_curation:
        queue = json.loads(args.out.read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in catalogue["entries"]}
        approved = 0
        for item in queue.get("candidates", []):
            if item["genre_id"] not in by_id:
                continue
            genre = by_id[item["genre_id"]]
            if genre.get("image") or genre.get("status") != "published":
                continue
            image = reviewed_image(item)
            if image is None:
                continue
            genre["image"] = image
            approved += 1
        if approved:
            write(ROOT / "research" / "genre_catalogue.json", catalogue)
        print(f"applied {approved} explicitly reviewed image candidates")
        return
    if args.broaden:
        queue = json.loads(args.out.read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in catalogue["entries"]}
        for item in queue.get("candidates", []):
            if item["results"] or item["genre_id"] not in by_id:
                continue
            genre = by_id[item["genre_id"]]
            queries = [genre["name"], f'{genre["name"]} music', f'{genre["name"]} tradition', f'{genre["name"]} performance', *genre.get("aliases", []), *genre.get("artists", [])]
            for query in queries:
                results = search_with_backoff(candidates, query, args.limit, delay=args.delay)
                if results:
                    item["query"] = query
                    item["results"] = results
                    write(args.out, queue)
                    break
                time.sleep(args.delay)
        write(args.out, queue)
        print("broadened empty image searches")
        return
    if args.wiki_fallback:
        queue = json.loads(args.out.read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in catalogue["entries"]}
        pending = [item for item in queue.get("candidates", [])
                   if not item["results"] and by_id.get(item["genre_id"], {}).get("wikipedia_title")]
        resolved = 0
        for offset in range(0, len(pending), 40):
            batch = pending[offset:offset + 40]
            titles = "|".join(by_id[item["genre_id"]]["wikipedia_title"] for item in batch)
            pages = wikipedia_get({"action": "query", "titles": titles, "prop": "pageimages", "piprop": "name"}).get("query", {}).get("pages", [])
            images = {page["title"]: page.get("pageimage") for page in pages if page.get("pageimage")}
            for item in batch:
                title = by_id[item["genre_id"]]["wikipedia_title"]
                filename = images.get(title)
                if not filename:
                    continue
                candidate = commons_file_candidate(filename)
                if candidate:
                    item["query"] = f"Wikipedia lead image: {title}"
                    item["results"] = [candidate]
                    resolved += 1
                    write(args.out, queue)
                time.sleep(args.delay)
        write(args.out, queue)
        print(f"resolved {resolved} empty searches through Wikipedia lead images")
        return
    if args.openverse_fallback:
        queue = json.loads(args.out.read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in catalogue["entries"]}
        resolved = 0
        for item in queue.get("candidates", []):
            if item["results"] or item["genre_id"] not in by_id:
                continue
            genre = by_id[item["genre_id"]]
            queries = [genre["name"], *genre.get("aliases", [])]
            for query in queries:
                results = search_with_backoff(openverse_candidates, query, args.limit, delay=args.delay)
                if results:
                    item["query"] = f"Openverse: {query}"
                    item["results"] = results
                    write(args.out, queue)
                    resolved += 1
                    break
                time.sleep(args.delay)
        write(args.out, queue)
        print(f"resolved {resolved} empty searches through Openverse")
        return
    countries = json.loads((ROOT / "web" / "data" / "countries.geojson").read_text(encoding="utf-8"))
    country_names = {feature["properties"]["code"]: feature["properties"]["name"]
                     for feature in countries["features"]}
    selected = [row for row in catalogue["entries"] if row["status"] == "published" and not row.get("image")]
    if args.ids:
        wanted = set(args.ids)
        selected = [row for row in selected if row["id"] in wanted]
        unknown = wanted - {row["id"] for row in selected}
        if unknown:
            parser.error("unknown, unpublished, or already illustrated ID: " + ", ".join(sorted(unknown)))
    output = {"generated_at": date.today().isoformat(), "provider": "Wikimedia Commons", "candidates": []}
    if args.resume and args.out.exists():
        output = json.loads(args.out.read_text(encoding="utf-8"))
        completed = {item["genre_id"] for item in output.get("candidates", [])}
        selected = [row for row in selected if row["id"] not in completed]
    for genre in selected:
        query = f'{genre["name"]} {country_names[genre["country"]]}'
        results = search_with_backoff(candidates, query, args.limit, delay=args.delay)
        output["candidates"].append({"genre_id": genre["id"], "query": query, "results": results})
        write(args.out, output)
        time.sleep(args.delay)
    write(args.out, output)
    print(f"wrote {len(output['candidates'])} private genre-image searches to {args.out}")


if __name__ == "__main__":
    main()
