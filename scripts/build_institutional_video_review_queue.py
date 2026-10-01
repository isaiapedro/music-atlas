"""Create a private review index for institutional video leads.

This intentionally does not search or scrape YouTube. Each row records a
source-backed genre whose recorded source points to an institutional publisher;
an editor reviews a matching video, channel, embedding availability, and genre
fit before adding it to the public catalogue.
"""
import json
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INSTITUTIONAL_HINTS = (
    "unesco.org", "gov.", "gouv.", "go.", "ac.", "edu.", "museum",
    "archive", "archives", "library", "bibliothe", "folkways", "cultural",
)


def source_url(source):
    return source if isinstance(source, str) else source.get("url")


def institutional(url):
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return any(hint in host for hint in INSTITUTIONAL_HINTS)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main():
    catalogue = json.loads((ROOT / "research" / "genre_catalogue.json").read_text(encoding="utf-8"))
    candidates = []
    all_gaps = []
    for genre in catalogue["entries"]:
        if genre["status"] != "published" or genre.get("youtube_examples"):
            continue
        urls = [url for source in genre.get("sources", []) if (url := source_url(source)) and institutional(url)]
        artists = genre.get("artists") or []
        all_gaps.append({
            "genre_id": genre["id"],
            "genre": genre["name"],
            "country": genre["country"],
            "source_kind": "UNESCO ICH" if any("unesco.org" in urlparse(url).netloc.lower() for url in urls)
            else "institutional" if urls else "other",
            "institutional_source_urls": urls,
            "representatives_to_verify": artists,
            "representative_evidence_needed": bool(artists),
            "manual_search_queries": [
                f'"{genre["name"]}" "{artist}" official performance' for artist in artists
            ] or [f'"{genre["name"]}" {genre["country"]} official performance'],
            "review_status": "unreviewed",
            "video_url": None,
            "review_requirements": [
                "Check the representative against a specialist, community, archive, label, or artist source first.",
                "Verify that the exact video documents this practice and performer; a search result or title is insufficient.",
                "Record the uploader's authority, canonical video URL, embedding status, and review date before publication.",
                "If no exact match is found, retain the gap with queries tried and a reason; never invent a URL.",
            ],
        })
        if not urls:
            continue
        source_kind = "UNESCO ICH" if any("unesco.org" in urlparse(url).netloc.lower() for url in urls) else "institutional"
        candidates.append({
            "genre_id": genre["id"],
            "genre": genre["name"],
            "country": genre["country"],
            "source_kind": source_kind,
            "source_urls": urls,
            "manual_search_query": f'{genre["name"]} {"UNESCO" if source_kind == "UNESCO ICH" else "official"} video',
            "review_requirements": [
                "Match the video to the exact mapped practice, not merely its country or an instrument.",
                "Confirm an official artist, archive, cultural-institution, label, or other rights-holder channel.",
                "Confirm embedding remains enabled and retain the canonical YouTube watch URL.",
                "Add a source-described individual, ensemble, role-based group, or community bearer before public promotion.",
            ],
        })
    output = {
        "generated_at": date.today().isoformat(),
        "scope": "unreviewed institutional video leads; not approved public media",
        "candidates": candidates,
    }
    path = ROOT / ".local" / "institutional_video_review_queue.json"
    write(path, output)
    print(f"wrote {len(candidates)} private institutional-video leads to {path}")
    all_gaps.sort(key=lambda row: ({"UNESCO ICH": 0, "institutional": 1, "other": 2}[row["source_kind"]], row["country"], row["genre_id"]))
    gap_path = ROOT / ".local" / "video_gap_review_queue.json"
    write(gap_path, {
        "generated_at": date.today().isoformat(),
        "scope": "all published genres without a reviewed YouTube example; search prompts are not evidence or approved media",
        "candidates": all_gaps,
    })
    print(f"wrote {len(all_gaps)} private video-gap review rows to {gap_path}")


if __name__ == "__main__":
    main()
