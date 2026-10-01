"""Import a reviewed genre recording research JSON into a private SQLite staging DB.

The source's ``record_found`` entries are retained for the future Albums
extension. ``performance_found`` entries remain a separate, non-album fallback
pool and never count as album records. Nothing is promoted into public data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / ".local/musicbrainz/genre_recording_research.sqlite3"
OFFICIAL_CANDIDATE_TARGET = 9


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS import_batch (
  source_sha256 TEXT PRIMARY KEY,
  source_filename TEXT NOT NULL,
  source_date TEXT,
  imported_at TEXT NOT NULL,
  input_rows INTEGER NOT NULL,
  summary_json TEXT NOT NULL,
  status_definitions_json TEXT NOT NULL,
  verification_limits_json TEXT NOT NULL,
  official_candidate_target INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS genre_items (
  entry_key TEXT PRIMARY KEY,
  source_sha256 TEXT NOT NULL REFERENCES import_batch(source_sha256) ON DELETE CASCADE,
  entry_index INTEGER NOT NULL,
  genre_id TEXT NOT NULL,
  genre TEXT NOT NULL,
  country TEXT NOT NULL,
  status TEXT NOT NULL,
  recommended_performer_or_artist TEXT NOT NULL,
  item_title TEXT NOT NULL,
  assessment TEXT NOT NULL,
  access_notes TEXT NOT NULL,
  automatic_import_ready INTEGER NOT NULL CHECK (automatic_import_ready IN (0,1)),
  musicbrainz_release_mbid TEXT,
  musicbrainz_recording_mbid TEXT,
  app_defined_artists TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  UNIQUE(source_sha256, entry_index)
);
CREATE INDEX IF NOT EXISTS genre_items_genre_idx ON genre_items(source_sha256, genre_id);
CREATE TABLE IF NOT EXISTS genre_item_evidence (
  entry_key TEXT NOT NULL REFERENCES genre_items(entry_key) ON DELETE CASCADE,
  evidence_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  reference TEXT NOT NULL,
  PRIMARY KEY(entry_key, evidence_index)
);
CREATE TABLE IF NOT EXISTS album_extension_candidates (
  entry_key TEXT PRIMARY KEY REFERENCES genre_items(entry_key) ON DELETE CASCADE,
  source_sha256 TEXT NOT NULL,
  genre_id TEXT NOT NULL,
  genre TEXT NOT NULL,
  country TEXT NOT NULL,
  title TEXT NOT NULL,
  performer_credit TEXT NOT NULL,
  musicbrainz_release_mbid TEXT,
  evidence_status TEXT NOT NULL,
  extension_review_status TEXT NOT NULL,
  album_type_status TEXT NOT NULL,
  automatic_import_ready INTEGER NOT NULL CHECK (automatic_import_ready IN (0,1))
);
CREATE INDEX IF NOT EXISTS album_candidates_genre_idx
  ON album_extension_candidates(source_sha256, genre_id);
CREATE TABLE IF NOT EXISTS supplemental_recordings (
  entry_key TEXT PRIMARY KEY REFERENCES genre_items(entry_key) ON DELETE CASCADE,
  source_sha256 TEXT NOT NULL,
  genre_id TEXT NOT NULL,
  genre TEXT NOT NULL,
  country TEXT NOT NULL,
  title TEXT NOT NULL,
  performer_credit TEXT NOT NULL,
  musicbrainz_recording_mbid TEXT,
  fallback_only INTEGER NOT NULL CHECK (fallback_only IN (0,1)),
  fallback_reason TEXT NOT NULL,
  media_or_release_type TEXT NOT NULL,
  evidence_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS supplemental_recordings_genre_idx
  ON supplemental_recordings(source_sha256, genre_id);
CREATE TABLE IF NOT EXISTS genre_official_coverage (
  source_sha256 TEXT NOT NULL REFERENCES import_batch(source_sha256) ON DELETE CASCADE,
  genre_id TEXT NOT NULL,
  genre TEXT NOT NULL,
  country TEXT NOT NULL,
  official_record_candidate_count INTEGER NOT NULL,
  target_count INTEGER NOT NULL,
  insufficient_official_examples INTEGER NOT NULL CHECK (insufficient_official_examples IN (0,1)),
  coverage_note TEXT NOT NULL,
  PRIMARY KEY(source_sha256, genre_id)
);
"""


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def validate_payload(payload: dict) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError("source must be a JSON object containing an entries array")
    required = ("genre_id", "genre", "country", "status")
    entries = payload["entries"]
    for index, row in enumerate(entries):
        if not isinstance(row, dict) or any(not _text(row.get(key)) for key in required):
            raise ValueError(f"entry {index} is missing a required genre identity or status")
        if not isinstance(row.get("evidence", []), list):
            raise ValueError(f"entry {index} evidence must be an array")
    return entries


def open_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db


def import_catalogue(source: Path, database: Path = DEFAULT_DB,
                     official_target: int = OFFICIAL_CANDIDATE_TARGET) -> dict:
    if official_target < 1:
        raise ValueError("official_target must be at least 1")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw)
    entries = validate_payload(payload)
    imported_at = datetime.now(timezone.utc).isoformat()
    db = open_database(database)
    try:
        with db:
            db.execute("""INSERT OR REPLACE INTO import_batch VALUES(?,?,?,?,?,?,?,?,?)""", (
                digest, source.name, _text(payload.get("date")), imported_at, len(entries),
                json.dumps(payload.get("summary", {}), ensure_ascii=False),
                json.dumps(payload.get("status_definitions", {}), ensure_ascii=False),
                json.dumps(payload.get("verification_limits", []), ensure_ascii=False), official_target,
            ))
            # Re-importing the same exact source is idempotent and refreshes this batch.
            for table in ("genre_item_evidence", "album_extension_candidates",
                          "supplemental_recordings", "genre_official_coverage", "genre_items"):
                db.execute(f"DELETE FROM {table} WHERE " + (
                    "entry_key IN (SELECT entry_key FROM genre_items WHERE source_sha256=?)"
                    if table == "genre_item_evidence" else
                    "source_sha256=?"
                ), (digest,))
            official_counts = Counter(
                _text(row["genre_id"]) for row in entries if row["status"] == "record_found"
            )
            genres = {}
            for index, row in enumerate(entries):
                genre_id = _text(row["genre_id"])
                entry_key = f"{digest}:{index}"
                genre = {
                    "entry_key": entry_key, "source_sha256": digest, "entry_index": index,
                    "genre_id": genre_id, "genre": _text(row["genre"]), "country": _text(row["country"]),
                }
                genres.setdefault(genre_id, genre)
                status = _text(row["status"])
                release_mbid = row.get("musicbrainz_release_mbid") or None
                recording_mbid = row.get("musicbrainz_recording_mbid") or None
                db.execute("""INSERT INTO genre_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    entry_key, digest, index, genre_id, _text(row["genre"]), _text(row["country"]), status,
                    _text(row.get("recommended_performer_or_artist")),
                    _text(row.get("recording_or_archive_title")), _text(row.get("assessment")),
                    _text(row.get("access_notes")), int(bool(row.get("automatic_import_ready"))),
                    release_mbid, recording_mbid,
                    json.dumps(row.get("app_defined_artists", ""), ensure_ascii=False),
                    json.dumps(row, ensure_ascii=False),
                ))
                for evidence_index, evidence in enumerate(row.get("evidence", [])):
                    db.execute("INSERT INTO genre_item_evidence VALUES(?,?,?,?,?)", (
                        entry_key, evidence_index, _text(evidence.get("title")),
                        _text(evidence.get("url")), _text(evidence.get("reference")),
                    ))
                if status == "record_found":
                    db.execute("""INSERT INTO album_extension_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
                        entry_key, digest, genre_id, _text(row["genre"]), _text(row["country"]),
                        _text(row.get("recording_or_archive_title")),
                        _text(row.get("recommended_performer_or_artist")), release_mbid,
                        "source catalogue item found; official release metadata not yet identity-verified",
                        "private candidate; pending editorial review",
                        "unresolved: source permits album, track, or archive item",
                        int(bool(row.get("automatic_import_ready"))),
                    ))
                elif status == "performance_found":
                    count = official_counts[genre_id]
                    fallback = count < official_target
                    db.execute("""INSERT INTO supplemental_recordings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (
                        entry_key, digest, genre_id, _text(row["genre"]), _text(row["country"]),
                        _text(row.get("recording_or_archive_title")),
                        _text(row.get("recommended_performer_or_artist")), recording_mbid,
                        int(fallback),
                        (f"Only {count} official record-found candidate(s) versus target {official_target}; "
                         "kept separate as non-album supplemental recording." if fallback else
                         f"Official candidate threshold {official_target} met; retain outside album records."),
                        "performance / video / excerpt; not an album record", status,
                    ))
            for genre_id, genre in genres.items():
                count = official_counts[genre_id]
                db.execute("INSERT INTO genre_official_coverage VALUES(?,?,?,?,?,?,?,?)", (
                    digest, genre_id, genre["genre"], genre["country"], count, official_target,
                    int(count < official_target),
                    (f"{count} record_found candidate(s); target is {official_target} official examples. "
                     "No decade is inferred: source entries have no verified release year."),
                ))
        counts = {status: count for status, count in Counter(row["status"] for row in entries).items()}
        official = sum(row["status"] == "record_found" for row in entries)
        performance = sum(row["status"] == "performance_found" for row in entries)
        return {
            "database": str(database), "source_sha256": digest, "rows_imported": len(entries),
            "status_counts": counts, "official_record_candidates": official,
            "supplemental_performance_recordings": performance,
            "performance_recordings_fallback_eligible": sum(
                row["status"] == "performance_found" and
                official_counts[_text(row["genre_id"])] < official_target for row in entries
            ),
            "mbids_resolved": sum(bool(row.get("musicbrainz_release_mbid") or
                                        row.get("musicbrainz_recording_mbid")) for row in entries),
            "automatic_import_ready": sum(bool(row.get("automatic_import_ready")) for row in entries),
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--official-target", type=int, default=OFFICIAL_CANDIDATE_TARGET,
                        help="official examples required before supplemental performances stop being fallback-only (default: 9)")
    args = parser.parse_args()
    print(json.dumps(import_catalogue(args.source, args.database, args.official_target), indent=2))


if __name__ == "__main__":
    main()
