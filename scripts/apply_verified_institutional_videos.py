"""Apply exact institutional practice films after a checked private review queue.

The queue must identify the official institution page, matching uploader, and successful
oEmbed metadata. Inaccessible or ambiguous films remain in the private queue.
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
QUEUE = ROOT / ".local" / "verified_video_candidates.json"
TRUSTED_UPLOADERS = {
    "ich.unesco.org": "UNESCO",
    "www.si.edu": "Smithsonian National Museum of African Art",
    "folkways.si.edu": "Smithsonian Folkways",
    "disbudpar.bulelengkab.go.id": "Dinas Kebudayaan Buleleng",
}


def canonical_video(url):
    parsed = urlparse(url)
    videos = parse_qs(parsed.query).get("v", [])
    return (parsed.scheme == "https" and parsed.hostname == "www.youtube.com" and
            parsed.path == "/watch" and len(videos) == 1 and bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", videos[0])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=QUEUE)
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in data["entries"]}
    applied = 0
    for item in queue["candidates"]:
        if item.get("promotion_ready") is not True:
            continue
        if not canonical_video(item["youtube_url"]):
            raise ValueError(f"invalid canonical video: {item['youtube_url']}")
        evidence = urlparse(item.get("evidence_url", ""))
        expected_uploader = TRUSTED_UPLOADERS.get(evidence.hostname)
        if evidence.scheme != "https" or not expected_uploader:
            raise ValueError(f"missing approved institutional source: {item['youtube_url']}")
        if not item.get("uploader", "").startswith(expected_uploader):
            raise ValueError(f"unverified uploader/embed: {item['youtube_url']}")
        embed_check = item.get("embed_status") or queue.get("verification", "")
        if "iframe HTML" not in embed_check:
            raise ValueError(f"missing oEmbed check: {item['youtube_url']}")
        for genre_id in item["genre_ids"]:
            entry = by_id[genre_id]
            if entry["status"] != "published":
                raise ValueError(f"non-published target: {genre_id}")
            if entry.get("youtube_examples"):
                continue
            entry["youtube_examples"] = [{
                "artist": item["artist"], "title": item["title"],
                "youtube_url": item["youtube_url"], "reviewed_at": queue["reviewed_at"],
                "attribution_basis": "institutional practice-level example",
            }]
            entry.setdefault("research", {})["video_evidence"] = {
                "source_url": item["evidence_url"], "uploader": item["uploader"],
                "fit": item["fit"], "embed_check": embed_check,
            }
            if item["evidence_url"] not in [s if isinstance(s, str) else s.get("url") for s in entry["sources"]]:
                entry["sources"].append(item["evidence_url"])
            representative_url = item.get("representative_evidence_url")
            if representative_url and representative_url not in [s if isinstance(s, str) else s.get("url") for s in entry["sources"]]:
                entry["sources"].append(representative_url)
            applied += 1
    if applied:
        CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied {applied} reviewed institutional video examples")


if __name__ == "__main__":
    main()
