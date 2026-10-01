"""Keep user-supplied album seeds that are absent from the saved RYM pages.

The output is an editorial review queue, not a release verification or a public
album list. It deliberately preserves entries for genres that do not yet have
an Atlas ID, because a missing RYM page must never discard the user's lead.
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS = ROOT / "research" / "new_genre_album_candidates.csv"
DEFAULT_RYM_DB = ROOT / ".local" / "rym" / "chart_catalogue.sqlite3"
DEFAULT_OUTPUT = ROOT / "research" / "album_seeds_missing_rym_pages.csv"


def norm(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def load_rym_pairs(database: Path) -> set[tuple[str, str]]:
    db = sqlite3.connect(database)
    try:
        return {(norm(title), norm(artist)) for title, artist in db.execute(
            "SELECT title, artist_credit FROM album_candidate"
        ) if norm(title) and norm(artist)}
    finally:
        db.close()


def reconcile(seeds: Path = DEFAULT_SEEDS, database: Path = DEFAULT_RYM_DB) -> list[dict]:
    rym_pairs = load_rym_pairs(database)
    with seeds.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    missing = []
    for row in rows:
        pair = (norm(row["release_title_as_supplied"]), norm(row["artist_credit_as_supplied"]))
        if pair not in rym_pairs:
            missing.append({
                "genre_candidate": row["genre_candidate"],
                "scope_hint": row["scope_hint"],
                "release_title_as_supplied": row["release_title_as_supplied"],
                "artist_credit_as_supplied": row["artist_credit_as_supplied"],
                "year_text": row["year_text"],
                "review_note": row["review_note"],
                "rym_page_match": "absent_from_saved_pages",
                "retention": "preserve_for_musicbrainz_identity_and_genre_fit_review",
            })
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--database", type=Path, default=DEFAULT_RYM_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = reconcile(args.seeds, args.database)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [
            "genre_candidate", "scope_hint", "release_title_as_supplied", "artist_credit_as_supplied",
            "year_text", "review_note", "rym_page_match", "retention"
        ])
        writer.writeheader()
        writer.writerows(rows)
    print({"seed_rows": sum(1 for _ in csv.DictReader(args.seeds.open(encoding="utf-8-sig"))),
           "absent_from_saved_rym_pages": len(rows), "output": str(args.output)})


if __name__ == "__main__":
    main()
