"""Print shelf record ids that match a title or artist.

Usage:
  python3 scripts/find_shelf_record.py plastic words
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "web" / "data" / "genre_records.json"


def find_records(catalogue, needle):
    needle = " ".join(needle.casefold().split())
    if not needle:
        return []
    found = []
    for genre_id, genre in catalogue.get("genres", {}).items():
        for record in genre.get("records", []):
            title = record.get("title") or ""
            artist = record.get("artist") or ""
            if needle in title.casefold() or needle in artist.casefold():
                found.append({
                    "id": record.get("id"),
                    "genre_id": genre_id,
                    "year": record.get("year"),
                    "artist": artist,
                    "title": title,
                })
    return found


def main():
    needle = " ".join(sys.argv[1:]).strip()
    if not needle:
        raise SystemExit("usage: python3 scripts/find_shelf_record.py TITLE OR ARTIST")
    catalogue = json.loads(RECORDS.read_text(encoding="utf-8"))
    matches = find_records(catalogue, needle)
    if not matches:
        raise SystemExit(f"no shelf record matches {needle}")
    for item in matches:
        year = item["year"] if item["year"] is not None else "date pending"
        print(f"{item['id']}  {item['genre_id']}  {year}  {item['artist']} — {item['title']}")


if __name__ == "__main__":
    main()
