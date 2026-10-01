"""Search Wikipedia for matching articles for genres lacking wikipedia_title.

Writes wikipedia_title when a high-confidence match is found, marks
research.wikipedia.status = 'searched_not_found' otherwise.
Never overwrites an existing wikipedia_title.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research/genre_catalogue.json"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "MusicAtlasWikiResolver/1.0 (local editorial tool)"
TODAY = date.today().isoformat()

MUSIC_STOP_WORDS = {
    "music", "of", "and", "the", "in", "a", "an", "traditional",
}


def wiki_get(params):
    url = WIKIPEDIA_API + "?" + urllib.parse.urlencode(
        {"format": "json", "formatversion": "2", **params}
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def normalize(s):
    return s.lower().strip()


def article_exists(title):
    """Return True if Wikipedia has an article at exactly this title."""
    resp = wiki_get({"action": "query", "titles": title, "prop": "info"})
    pages = resp.get("query", {}).get("pages", [])
    if not pages:
        return False
    page = pages[0] if isinstance(pages, list) else list(pages.values())[0]
    return page.get("pageid", -1) > 0


def search_candidates(query, limit=3):
    """Return list of (title, snippet) from Wikipedia search."""
    resp = wiki_get({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srnamespace": "0",
        "srprop": "snippet|titlesnippet",
    })
    results = resp.get("query", {}).get("search", [])
    return [(r["title"], r.get("snippet", "")) for r in results]


def score_match(genre_name, country_code, candidate_title, snippet):
    """Return confidence score 0-100 for a Wikipedia candidate."""
    gn = normalize(genre_name)
    ct = normalize(candidate_title)
    score = 0

    # Exact title match
    if gn == ct:
        score += 60
    # Genre name contained in title
    elif gn in ct:
        score += 40
    # Title contained in genre name
    elif ct in gn:
        score += 30
    # Word overlap
    else:
        gwords = set(gn.split()) - MUSIC_STOP_WORDS
        cwords = set(ct.split()) - MUSIC_STOP_WORDS
        overlap = len(gwords & cwords)
        if overlap > 0:
            score += min(overlap * 10, 25)

    # Snippet must contain "music" or related terms
    snip = normalize(snippet)
    music_terms = {"music", "genre", "song", "singing", "traditional", "folk", "dance", "rhythm"}
    if any(t in snip for t in music_terms):
        score += 20

    return score


def resolve(entry):
    """Return (wikipedia_title_or_None, status, reason) for a published entry."""
    name = entry["name"]
    country = entry.get("country", "")

    # Try exact title first
    for candidate in [name, f"{name} music", f"{name} (music)"]:
        if article_exists(candidate):
            return candidate, "article", f"Exact Wikipedia article found: {candidate!r}"
        time.sleep(0.5)

    # Search-based fallback
    queries = [f"{name} music", f"{name} {country}", name]
    seen = set()
    best_title = None
    best_score = 0

    for query in queries:
        try:
            results = search_candidates(query, limit=3)
        except Exception:
            time.sleep(2)
            continue
        for title, snippet in results:
            if title in seen:
                continue
            seen.add(title)
            sc = score_match(name, country, title, snippet)
            if sc > best_score:
                best_score = sc
                best_title = title
        time.sleep(0.5)

    if best_score >= 60 and best_title:
        return best_title, "article", f"High-confidence search match (score {best_score}): {best_title!r}"

    return None, "searched_not_found", f"No confident Wikipedia match found (best score {best_score})"


def main():
    data = json.loads(CATALOGUE.read_text())
    entries = data["entries"]

    targets = [
        e for e in entries
        if e.get("status") == "published"
        and not e.get("wikipedia_title")
        and e.get("research", {}).get("wikipedia", {}).get("status") != "searched_not_found"
    ]
    print(f"Resolving Wikipedia titles for {len(targets)} entries…")

    resolved = 0
    not_found = 0
    errors = 0

    for i, entry in enumerate(targets, 1):
        eid = entry["id"]
        retries = 3
        title = status = reason = None
        for attempt in range(retries):
            try:
                title, status, reason = resolve(entry)
                break
            except Exception as exc:
                if attempt < retries - 1:
                    wait = 5 * (attempt + 1)
                    time.sleep(wait)
                else:
                    print(f"  [{i}/{len(targets)}] {eid}: ERROR {exc}")
                    errors += 1
                    title, status, reason = None, "searched_not_found", f"Error after {retries} attempts: {exc}"

        if "wikipedia" not in entry.setdefault("research", {}):
            entry["research"]["wikipedia"] = {}
        entry["research"]["wikipedia"]["status"] = status
        entry["research"]["wikipedia"]["reviewed_at"] = TODAY
        entry["research"]["wikipedia"]["reason"] = reason

        if title:
            entry["wikipedia_title"] = title
            resolved += 1
            print(f"  [{i}/{len(targets)}] {eid}: ✓ {title!r}")
        else:
            not_found += 1
            if i % 20 == 0 or i == len(targets):
                print(f"  [{i}/{len(targets)}] {eid}: – not found")

        time.sleep(2.0)

        # Save progress every 25 entries
        if i % 25 == 0:
            CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(f"  → checkpoint saved at {i}")

    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"\nDone. resolved={resolved} not_found={not_found} errors={errors}")


if __name__ == "__main__":
    main()
