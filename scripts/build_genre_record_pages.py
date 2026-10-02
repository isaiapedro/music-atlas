"""Publish safe saved-chart album listings for Atlas genre pages.

The underlying RYM chart captures, ranks, rating counts and URLs remain private.
The browser receives only a saved chart card's title, artist credit and year.
An unambiguous MusicBrainz match is optional enrichment: it adds a link and
can supply a year only when the saved card has none.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / ".local" / "rym" / "chart_catalogue.sqlite3"
DEFAULT_OUTPUT = ROOT / "web" / "data" / "genre_records.json"
ROUGH_GUIDE_RECORDS = ROOT / "research" / "rough_guide_album_records.json"
MANUAL_SELECTIONS = ROOT / "research" / "manual_record_selections.json"
PLAYER_FIELDS = ("youtube_url", "spotify_url", "apple_music_url")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    temporary.replace(path)


def record_id(title: str, artist: str, year: int | None) -> str:
    """Stable public identifier; it contains no provider URL or chart metric."""
    value = "\x1f".join((title.casefold(), artist.casefold(), str(year or "")))
    return "record-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def build(database: Path = DEFAULT_DATABASE) -> dict:
    if not database.exists():
        raise FileNotFoundError(f"private chart catalogue not found: {database}")
    db = sqlite3.connect(database)
    try:
        rows = db.execute("""
            SELECT a.candidate_id, g.atlas_genre_ids_json,
                   a.selected_within_page_decade, a.chart_rank, a.title,
                   a.artist_credit, a.provisional_year, m.release_group_mbid,
                   m.mb_first_year
            FROM album_candidate AS a
            JOIN genre_assessment AS g USING(page_id)
            LEFT JOIN musicbrainz_resolution AS m
              ON m.candidate_id = a.candidate_id
             AND m.year_comparison IN ('same_year', 'year_unresolved_in_one_or_both_sources')
             AND (SELECT COUNT(*) FROM musicbrainz_resolution AS possible
                  WHERE possible.candidate_id = a.candidate_id) = 1
            WHERE g.classification = 'exact_name_candidate'
            ORDER BY a.selected_within_page_decade DESC, a.chart_rank,
                     a.provisional_year, a.title COLLATE NOCASE, a.artist_credit COLLATE NOCASE
        """).fetchall()
    finally:
        db.close()

    grouped: dict[str, list[dict]] = {}
    for candidate_id, genre_ids_json, selected, rank, title, artist, chart_year, mbid, mb_year in rows:
        year = chart_year if chart_year is not None else mb_year
        record = {
            "candidate_id": candidate_id, "id": record_id(title, artist, year),
            "title": title, "artist": artist, "year": year,
            "year_source": "rym_chart" if chart_year is not None else (
                "musicbrainz_resolved" if mb_year is not None else "unresolved"),
            "record_source": "saved_rym_chart", "chart_rank": rank,
            "threshold_selected": bool(selected),
        }
        if mbid:
            record.update({"musicbrainz_release_group_mbid": mbid,
                           "musicbrainz_url": f"https://musicbrainz.org/release-group/{mbid}"})
        for genre_id in json.loads(genre_ids_json):
            grouped.setdefault(genre_id, []).append(record)

    genres = {}
    for genre_id, candidates in sorted(grouped.items()):
        chosen: dict[str, dict] = {}
        for candidate in candidates:
            if candidate["threshold_selected"]:
                key = candidate.get("musicbrainz_release_group_mbid") or candidate["candidate_id"]
                chosen.setdefault(key, candidate)
        # A genre with fewer than nine selected records takes the remaining
        # saved chart recommendations in rank order. Ratings/reviews are never
        # included in browser data or used in this minimum-coverage pass.
        if len(chosen) < 9:
            for candidate in sorted(candidates, key=lambda record: (
                    record["chart_rank"], record["year"] is None,
                    record["year"] or 9999, record["title"].casefold())):
                key = candidate.get("musicbrainz_release_group_mbid") or candidate["candidate_id"]
                chosen.setdefault(key, candidate)
                if len(chosen) >= 9:
                    break
        records = []
        for record in chosen.values():
            record = dict(record)
            record.pop("candidate_id"); record.pop("chart_rank"); record.pop("threshold_selected")
            records.append(record)
        genres[genre_id] = {"records": sorted(records, key=lambda record: (
            record["year"] is None, record["year"] or 9999,
            record["title"].casefold(), record["artist"].casefold(),
        ))}
    merge_rough_guide_records(genres)
    apply_manual_selections(genres)
    return {
        "version": 1,
        "notice": "Album listings use saved chart title, artist-credit, and year fields. Rating-qualified recommendations are used first; genres with fewer than nine selected records are filled from their saved chart in rank order, independent of ratings and reviews. MusicBrainz identity is optional enrichment. Rough Guide discography rows are added beside chart rows when a reviewed year is named.",
        "genres": genres,
    }


def record_sort_key(record: dict) -> tuple:
    return (
        record["year"] is None, record["year"] or 9999,
        record["title"].casefold(), record["artist"].casefold(),
    )


def merge_rough_guide_records(genres: dict) -> None:
    """Add reviewed Rough Guide discography rows without dropping chart records."""
    if not ROUGH_GUIDE_RECORDS.exists():
        return
    payload = json.loads(ROUGH_GUIDE_RECORDS.read_text(encoding="utf-8"))
    for item in payload["records"]:
        year = item["year"]
        record = {
            "id": record_id(item["title"], item["artist"], year),
            "title": item["title"],
            "artist": item["artist"],
            "year": year,
            "year_source": "rough_guide",
            "record_source": "rough_guide_discography",
        }
        for field in ("youtube_url", "spotify_url", "apple_music_url"):
            value = item.get(field)
            if isinstance(value, str) and value.startswith("https://"):
                record[field] = value
        bucket = genres.setdefault(item["genre_id"], {"records": []})
        existing = next((row for row in bucket["records"] if row["id"] == record["id"]), None)
        if existing:
            for field in ("youtube_url", "spotify_url", "apple_music_url"):
                if field in record and not existing.get(field):
                    existing[field] = record[field]
            continue
        bucket["records"].append(record)
        bucket["records"].sort(key=record_sort_key)


def apply_manual_selections(genres: dict, selections: dict | None = None) -> None:
    if selections is None:
        if not MANUAL_SELECTIONS.exists():
            return
        selections = json.loads(MANUAL_SELECTIONS.read_text(encoding="utf-8"))
    chosen = selections.get("records", {}) if isinstance(selections, dict) else {}
    if not isinstance(chosen, dict):
        return
    for bucket in genres.values():
        for record in bucket.get("records", []):
            selection = chosen.get(record.get("id"))
            if not isinstance(selection, dict):
                continue
            cover = selection.get("cover")
            if isinstance(cover, dict) and isinstance(cover.get("front_url"), str) and cover["front_url"].startswith("https://"):
                record["cover"] = cover
            for field in PLAYER_FIELDS:
                value = selection.get(field)
                if isinstance(value, str) and value.startswith("https://"):
                    record[field] = value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build(args.database)
    if args.check:
        current = json.loads(args.output.read_text(encoding="utf-8"))
        if current != payload:
            raise SystemExit("genre_records.json is out of sync; run build_genre_record_pages.py")
    else:
        write_json(args.output, payload)
    print(json.dumps({"output": str(args.output), "genres": len(payload["genres"]),
                      "records": sum(len(value["records"]) for value in payload["genres"].values())}))


if __name__ == "__main__":
    main()
