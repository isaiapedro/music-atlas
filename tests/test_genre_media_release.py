"""The new batch must not appear with a description alone."""
import unittest
import json
from pathlib import Path

from scripts.build_static_data import meets_media_release
from scripts.validate_genres import validate_record


class GenreMediaReleaseTests(unittest.TestCase):
    def test_named_batch_remains_present(self):
        path = Path(__file__).resolve().parents[1] / "research" / "genre_media_release_batch.json"
        ids = json.loads(path.read_text(encoding="utf-8"))["genre_ids"]
        self.assertEqual(len(ids), 257)
        self.assertEqual(len(ids), len(set(ids)))

    def test_batch_requires_both_image_and_video(self):
        ids = {"new-genre"}
        record = {"id": "new-genre", "note": "Specific source-backed description"}
        self.assertFalse(meets_media_release(record, ids))
        record["image"] = {"reviewed_at": "2026-10-01"}
        self.assertFalse(meets_media_release(record, ids))
        record["youtube_examples"] = [{"reviewed_at": "2026-10-01"}]
        self.assertTrue(meets_media_release(record, ids))
        record["sources"] = [{"citation": "Local dossier source; see private evidence record."}]
        self.assertFalse(meets_media_release(record, ids))

    def test_older_records_keep_general_validator_policy(self):
        self.assertTrue(meets_media_release({"id": "older-genre"}, {"new-genre"}))

    def test_generic_description_cannot_pass_validation(self):
        record = {
            "id": "generic-genre", "country": "AAA", "name": "Generic",
            "kind": "tradition", "note": "Country-wide fill is a coarse association. Dates describe a source-backed approximate window or milestone, not exclusive origin or uninterrupted continuity.",
        }
        with self.assertRaisesRegex(AssertionError, "generic fallback description"):
            validate_record(record, {"AAA"}, {})


if __name__ == "__main__":
    unittest.main()
