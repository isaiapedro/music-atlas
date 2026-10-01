"""Create a private MusicBrainz artist-candidate queue for manual editorial review.

MusicBrainz tags and search scores are discovery metadata, not evidence that an
artist represents a genre. The script never updates the public catalogue.
"""
import argparse
import json
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://musicbrainz.org/ws/2/artist"
USER_AGENT = "MusicAtlasArtistResearch/1.0 (local editorial review queue)"


def search(name, limit):
    query = f'tag:"{name}"'
    request = urllib.request.Request(
        API + "?" + urllib.parse.urlencode({"query": query, "limit": limit, "fmt": "json"}),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return [{
        "name": artist["name"],
        "musicbrainz_url": f'https://musicbrainz.org/artist/{artist["id"]}',
        "score": artist.get("score"),
        "disambiguation": artist.get("disambiguation", ""),
        "country": artist.get("country"),
        "genres": [genre["name"] for genre in artist.get("genres", [])],
    } for artist in payload.get("artists", [])]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", dest="ids", help="Published genre ID to search; repeatable")
    parser.add_argument("--limit", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--delay", type=float, default=1.1, help="Seconds between MusicBrainz requests")
    parser.add_argument("--out", type=Path, default=ROOT / ".local" / "artist_candidates.json")
    args = parser.parse_args()
    catalogue = json.loads((ROOT / "research" / "genre_catalogue.json").read_text(encoding="utf-8"))
    selected = [row for row in catalogue["entries"] if row["status"] == "published" and not row["artists"]]
    if args.ids:
        wanted = set(args.ids)
        selected = [row for row in selected if row["id"] in wanted]
        unknown = wanted - {row["id"] for row in selected}
        if unknown:
            parser.error("unknown, unpublished, or already attributed ID: " + ", ".join(sorted(unknown)))
    output = {"generated_at": date.today().isoformat(), "provider": "MusicBrainz", "candidates": []}
    for index, genre in enumerate(selected):
        if index:
            time.sleep(args.delay)
        row = {"genre_id": genre["id"], "query": f'tag:"{genre["name"]}"'}
        try:
            row["results"] = search(genre["name"], args.limit)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            row["results"] = []
            row["error"] = str(error)
        output["candidates"].append(row)
        write(args.out, output)
    write(args.out, output)
    print(f"wrote {len(output['candidates'])} private genre-artist searches to {args.out}")


if __name__ == "__main__":
    main()
