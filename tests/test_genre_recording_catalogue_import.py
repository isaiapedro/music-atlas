import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.import_genre_recording_catalogue import import_catalogue


class GenreRecordingCatalogueImportTests(unittest.TestCase):
    def test_separates_records_from_performance_recordings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            database = root / "staging.sqlite3"
            entries = [
                {"genre_id": "g1", "genre": "Genre One", "country": "AAA", "status": "record_found",
                 "recommended_performer_or_artist": "Band", "recording_or_archive_title": "Album",
                 "automatic_import_ready": False, "musicbrainz_release_mbid": None, "evidence": []},
                {"genre_id": "g1", "genre": "Genre One", "country": "AAA", "status": "performance_found",
                 "recommended_performer_or_artist": "Singer", "recording_or_archive_title": "Video excerpt",
                 "automatic_import_ready": False, "musicbrainz_recording_mbid": None, "evidence": []},
                {"genre_id": "g2", "genre": "Genre Two", "country": "BBB", "status": "artist_found",
                 "recommended_performer_or_artist": "Another artist", "evidence": []},
            ]
            source.write_text(json.dumps({"date": "2026-09-30", "entries": entries}), encoding="utf-8")

            first = import_catalogue(source, database, official_target=2)
            second = import_catalogue(source, database, official_target=2)

            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(first["official_record_candidates"], 1)
            self.assertEqual(first["supplemental_performance_recordings"], 1)
            self.assertEqual(first["performance_recordings_fallback_eligible"], 1)
            db = sqlite3.connect(database)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM genre_items").fetchone()[0], 3)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM album_extension_candidates").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM supplemental_recordings WHERE fallback_only=1").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT automatic_import_ready FROM album_extension_candidates").fetchone()[0], 0)
            db.close()

    def test_rejects_missing_required_genre_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bad.json"
            source.write_text(json.dumps({"entries": [{"genre": "Missing ID"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                import_catalogue(source, root / "staging.sqlite3")


if __name__ == "__main__":
    unittest.main()
