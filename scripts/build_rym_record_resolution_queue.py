"""List private RYM chart records still needed to reach nine resolved records.

The queue contains no RYM ratings, reviews, or URLs. It is a resolver worklist
for MusicBrainz identity/date research, not public application data.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / ".local" / "rym" / "chart_catalogue.sqlite3"
PUBLIC = ROOT / "web" / "data" / "genre_records.json"
OUT = ROOT / ".local" / "rym" / "record_resolution_queue.csv"


def resolution_method(artist: str, year: int | None) -> str:
    if artist == "Various Artists":
        return ("Search MusicBrainz for an exact compilation/release-group title and chart year; "
                "verify the compilation tracklist or catalogue number before accepting.")
    if year is None:
        return ("The saved chart card exposes no year. Search MusicBrainz by exact title and artist, then verify "
                "the release-group date from the matched entity; do not infer a year from rating or chart rank.")
    return ("Search MusicBrainz by exact title, artist credit, and chart year. Resolve only one unambiguous "
            "release group; otherwise hold for manual discography review.")


def main() -> None:
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))["genres"]
    db = sqlite3.connect(DB)
    try:
        rows = []
        for genre_id, payload in sorted(public.items()):
            resolved = len(payload["records"])
            if resolved >= 9:
                continue
            candidates = db.execute("""
                SELECT a.chart_label,a.chart_rank,a.title,a.artist_credit,a.provisional_year,
                       a.displayed_year,a.primary_target_match,
                       EXISTS(SELECT 1 FROM musicbrainz_resolution m WHERE m.candidate_id=a.candidate_id)
                FROM album_candidate a
                JOIN genre_assessment g USING(page_id)
                WHERE g.classification='exact_name_candidate'
                  AND instr(g.atlas_genre_ids_json, ?) > 0
                ORDER BY a.chart_rank
            """, (genre_id,)).fetchall()
            for label, rank, title, artist, year, displayed, target, has_match in candidates:
                rows.append({
                    "atlas_genre_id": genre_id, "resolved_public_records": resolved,
                    "records_needed_to_reach_nine": 9 - resolved,
                    "chart_label": label, "chart_rank": rank, "title": title,
                    "artist_credit": artist, "chart_year": year or "",
                    "chart_date_text": displayed, "primary_target_match": "yes" if target else "no",
                    "has_musicbrainz_candidate": "yes" if has_match else "no",
                    "resolution_method": resolution_method(artist, year),
                })
    finally:
        db.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader(); writer.writerows(rows)
    print({"genres_below_nine": len({row['atlas_genre_id'] for row in rows}), "candidate_rows": len(rows), "output": str(OUT)})


if __name__ == "__main__":
    main()
