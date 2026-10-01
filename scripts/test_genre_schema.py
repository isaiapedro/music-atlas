"""Focused checks for publication rules that affect catalogue coverage."""
import copy
import json
import unittest
from pathlib import Path

from scripts.validate_genres import map_keys, validate_record

ROOT = Path(__file__).resolve().parents[1]


class GenreSchemaTests(unittest.TestCase):
    def setUp(self):
        entries = json.loads((ROOT / "research" / "genre_catalogue.json").read_text())["entries"]
        self.record = copy.deepcopy(entries[0])
        self.record.setdefault("timeline_end_status", "present" if self.record.get("active_to") is None else "ended")
        self.countries, self.regions = map_keys()

    def check(self, record):
        validate_record(record, self.countries, self.regions)

    def test_country_association_without_wikipedia_or_sample(self):
        self.record.update(map_scope="country", regions=[], wikipedia_title=None,
                           sample=None, active_from=None, start_label="Date unknown")
        self.check(self.record)

    def test_country_scope_cannot_claim_specific_regions(self):
        self.record["map_scope"] = "country"
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_regional_scope_needs_valid_mapped_region(self):
        self.record["regions"] = ["Unmapped province"]
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_approximate_scope_uses_a_direction_not_an_admin_region(self):
        self.record.update(map_scope="approximate", regions=[], approximate_region="south-west")
        self.check(self.record)

    def test_approximate_scope_needs_a_supported_direction(self):
        self.record.update(map_scope="approximate", regions=[], approximate_region="around the capital")
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_sample_must_be_valid_when_present(self):
        self.record["sample"] = {"title": "Example", "artist": self.record["artists"][0],
                                 "youtube_id": "12345678901", "start": 0, "end": 30}
        self.record["sample"]["end"] += 1
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_youtube_example_must_match_documented_artist(self):
        self.record["youtube_examples"] = [{"artist": "Unknown performer", "title": "Track",
                                                "youtube_url": "https://www.youtube.com/watch?v=12345678901",
                                                "reviewed_at": "2026-09-28"}]
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_youtube_url_must_be_canonical_video(self):
        self.record["youtube_examples"] = [{"artist": self.record["artists"][0], "title": "Track",
                                                "youtube_url": "https://www.youtube.com/watch?v=bad",
                                                "reviewed_at": "2026-09-28"}]
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_cross_country_area_requires_existing_region(self):
        self.record["associated_areas"] = [{"country": "BGD", "map_scope": "regions",
                                             "regions": ["Imaginary region"], "relationship": "practice",
                                             "active_from": 2020, "active_to": None,
                                             "timeline_end_status": "present",
                                             "start_label": "Documented by 2020", "note": "Example",
                                             "reviewed_at": "2026-09-28", "sources": ["https://example.org/source"]}]
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_cross_country_area_may_have_unknown_start(self):
        self.record["associated_areas"] = [{"country": "BGD", "map_scope": "country",
                                             "regions": [], "relationship": "practice",
                                             "active_from": None, "active_to": None,
                                             "timeline_end_status": "unknown",
                                             "start_label": "Historical onset unresolved", "note": "Example",
                                             "reviewed_at": "2026-09-28", "sources": ["https://example.org/source"]}]
        self.check(self.record)

    def test_unknown_end_is_distinct_from_present(self):
        self.record["active_to"] = None
        self.record["timeline_end_status"] = "unknown"
        self.check(self.record)

    def test_ended_status_requires_a_final_year(self):
        self.record["active_to"] = None
        self.record["timeline_end_status"] = "ended"
        with self.assertRaises(AssertionError):
            self.check(self.record)

    def test_book_citation_can_support_public_genre(self):
        self.record["sources"] = [{"citation": "R. Stone, African Music, 1998, p. 471."}]
        self.check(self.record)

    def test_private_source_path_cannot_enter_public_catalogue(self):
        self.record["sources"] = [{"citation": "R. Stone, African Music, p. 471.",
                                   "source_path": "knowledge/arts/raw/music/book.pdf"}]
        with self.assertRaises(AssertionError):
            self.check(self.record)


if __name__ == "__main__":
    unittest.main()
