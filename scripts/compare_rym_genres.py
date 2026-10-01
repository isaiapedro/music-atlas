"""Compare all selected Atlas genre names with a saved Parse get_genres response."""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / ".local/musicbrainz/catalog.sqlite3"
DEFAULT_OUT = ROOT / ".local/rym/genre_coverage.csv"


def norm(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def get_genres(payload):
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, dict) and isinstance(data.get("genres"), list):
            return data["genres"]
    raise ValueError("Expected Parse get_genres response with data.genres array")


def compare(atlas, rym_genres, suggestions=3):
    by_norm = {}
    for genre in rym_genres:
        name = genre.get("name", "") if isinstance(genre, dict) else str(genre)
        if name:
            by_norm.setdefault(norm(name), []).append(genre)
    names = list(by_norm)
    rows = []
    for entry in atlas:
        name = entry["name"]
        key = norm(name)
        exact = by_norm.get(key, [])
        ranked = sorted(((difflib.SequenceMatcher(None, key, candidate).ratio(), candidate)
                         for candidate in names if candidate != key), reverse=True)[:suggestions]
        rows.append({
            "atlas_genre_id": entry["id"], "country": entry["country"], "atlas_name": name,
            "match_status": "exact_normalized" if exact else "no_exact_match",
            "rym_matches": json.dumps([g if isinstance(g, dict) else {"name": g} for g in exact], ensure_ascii=False),
            "suggestions": json.dumps([
                {"name": by_norm[candidate][0].get("name") if isinstance(by_norm[candidate][0], dict) else by_norm[candidate][0],
                 "url": by_norm[candidate][0].get("url", "") if isinstance(by_norm[candidate][0], dict) else "",
                 "similarity": round(score, 4)} for score, candidate in ranked if score >= .55
            ], ensure_ascii=False),
            "review_status": "pending" if not exact else "exact_name_only",
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Saved Parse get_genres JSON response")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    with sqlite3.connect(args.db) as db:
        atlas = [{"id": r[0], "name": r[1], "country": r[2]} for r in db.execute(
            "SELECT id,name,country FROM atlas_genre ORDER BY name,country")]
    genres = get_genres(payload)
    rows = compare(atlas, genres)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    exact = sum(row["match_status"] == "exact_normalized" for row in rows)
    print(json.dumps({"atlas_genres": len(rows), "rym_genres": len(genres),
                      "exact_name_matches": exact, "needs_review": len(rows) - exact,
                      "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
