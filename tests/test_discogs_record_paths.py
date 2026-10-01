import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "discogs_paths", ROOT / "scripts/build_discogs_record_path_candidates.py")
discogs_paths = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discogs_paths)


class DiscogsPathCandidateTests(unittest.TestCase):
    def test_prefers_exact_album_edition_over_a_single_with_the_same_title(self):
        record = {"title": "Expensive Shit", "artist": "Fela Kuti", "year": 1975}
        candidate, score = discogs_paths.select_candidate(record, [
            {"id": 2, "title": "Fela Kuti - Expensive Shit", "year": "1975"},
            {"id": 1, "title": "Fela Kuti - Expensive Shit / Water No Get Enemy", "year": "1975"},
        ])
        self.assertEqual(candidate["id"], 2)
        self.assertGreaterEqual(score, 0.95)

    def test_unmatched_result_needs_review(self):
        row = discogs_paths.row_for(
            {"id": "record-1", "title": "Album", "artist": "Artist", "year": 1980}, [], "")
        self.assertEqual(row["status"], "no_result")


if __name__ == "__main__":
    unittest.main()
