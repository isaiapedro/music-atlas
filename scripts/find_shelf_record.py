"""Print shelf record ids that match a title, artist, or genre.

Usage:
  python3 scripts/find_shelf_record.py plastic words
  python3 scripts/find_shelf_record.py --genre afg-popular-music
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "web" / "data" / "genre_records.json"


def record_row(genre_id, record):
    return {
        "id": record.get("id"),
        "genre_id": genre_id,
        "year": record.get("year"),
        "artist": record.get("artist") or "",
        "title": record.get("title") or "",
    }


def find_records(catalogue, needle, genre_id=None):
    needle = " ".join(needle.casefold().split())
    genres = catalogue.get("genres", {})
    if genre_id:
        if genre_id not in genres:
            return None
        buckets = [(genre_id, genres[genre_id])]
    else:
        buckets = list(genres.items())
    found = []
    for current_id, genre in buckets:
        for record in genre.get("records", []):
            row = record_row(current_id, record)
            if needle and needle not in row["title"].casefold() and needle not in row["artist"].casefold():
                continue
            found.append(row)
    return found


def print_rows(matches):
    matches = sorted(
        matches,
        key=lambda item: (
            item["year"] is None,
            item["year"] if isinstance(item["year"], int) else 9999,
            (item["title"] or "").casefold(),
            (item["artist"] or "").casefold(),
        ),
    )
    for item in matches:
        year = item["year"] if item["year"] is not None else "date pending"
        print(f"{item['id']}  {item['genre_id']}  {year}  {item['artist']} — {item['title']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genre", help="Listening-room genre id, for example afg-popular-music")
    parser.add_argument("needle", nargs="*", help="Title or artist words to match")
    args = parser.parse_args()
    needle = " ".join(args.needle).strip()
    if not args.genre and not needle:
        parser.error("pass a title or artist, or --genre GENRE_ID")
    catalogue = json.loads(RECORDS.read_text(encoding="utf-8"))
    matches = find_records(catalogue, needle, args.genre)
    if matches is None:
        raise SystemExit(f"unknown genre {args.genre}")
    if not matches:
        target = args.genre or needle
        raise SystemExit(f"no shelf record matches {target}")
    print_rows(matches)


if __name__ == "__main__":
    main()
