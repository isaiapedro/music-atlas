"""Apply exact UNESCO practice films after a checked private review queue.

The queue must identify the official UNESCO page, UNESCO uploader, and successful
oEmbed metadata. Inaccessible or ambiguous films remain in the private queue.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
QUEUE = ROOT / ".local" / "verified_video_candidates.json"


def canonical_video(url):
    parsed = urlparse(url)
    videos = parse_qs(parsed.query).get("v", [])
    return (parsed.scheme == "https" and parsed.hostname == "www.youtube.com" and
            parsed.path == "/watch" and len(videos) == 1 and bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", videos[0])))


def main():
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in data["entries"]}
    applied = 0
    for item in queue["candidates"]:
        if item.get("promotion_ready") is not True:
            continue
        if not canonical_video(item["youtube_url"]):
            raise ValueError(f"invalid canonical video: {item['youtube_url']}")
        if not item.get("evidence_url", "").startswith("https://ich.unesco.org/en/"):
            raise ValueError(f"missing UNESCO source: {item['youtube_url']}")
        if item.get("uploader") != "UNESCO (verified channel)" or "iframe HTML" not in item.get("embed_status", ""):
            raise ValueError(f"unverified uploader/embed: {item['youtube_url']}")
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
                "fit": item["fit"], "embed_check": item["embed_status"],
            }
            if item["evidence_url"] not in [s if isinstance(s, str) else s.get("url") for s in entry["sources"]]:
                entry["sources"].append(item["evidence_url"])
            applied += 1
    if applied:
        CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied {applied} reviewed institutional video examples")


if __name__ == "__main__":
    main()
