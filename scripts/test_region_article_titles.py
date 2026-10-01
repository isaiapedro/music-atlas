"""Tests for deterministic, complete region-title proposal generation."""

import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("generate_region_article_titles.py")
SPEC = importlib.util.spec_from_file_location("generate_region_article_titles", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RegionArticleTitleTests(unittest.TestCase):
    def setUp(self):
        self.payload = MODULE.generate()
        self.proposals = self.payload["proposals"]

    def test_covers_every_distinct_map_key(self):
        features = json.loads((MODULE.WEB / "regions.geojson").read_text(encoding="utf-8"))["features"]
        expected = {
            f'{feature["properties"]["code"]}|{feature["properties"]["name"]}'
            for feature in features
        }
        self.assertEqual(set(self.proposals), expected)
        self.assertEqual(self.payload["region_key_count"], 1955)
        self.assertEqual(self.payload["geometry_feature_count"], 1976)

    def test_reviewed_overrides_are_preserved(self):
        reviewed = json.loads(MODULE.CANONICAL.read_text(encoding="utf-8"))
        for key, title in reviewed.items():
            self.assertEqual(self.proposals[key]["title"], title)
            self.assertEqual(self.proposals[key]["strategy"], "reviewed_override")
            self.assertTrue(self.proposals[key]["reviewed"])

    def test_cross_country_collision_uses_reviewed_canonical_title(self):
        self.assertEqual(self.proposals["PAK|Punjab"]["title"], "Punjab, Pakistan")
        self.assertEqual(self.proposals["PAK|Punjab"]["strategy"], "reviewed_override")

    def test_generic_name_uses_reviewed_canonical_title(self):
        self.assertEqual(self.proposals["GHA|Central"]["title"], "Central Region (Ghana)")
        self.assertEqual(self.proposals["GHA|Central"]["strategy"], "reviewed_override")

    def test_unambiguous_name_preserves_reviewed_title(self):
        self.assertEqual(self.proposals["IDN|East Kalimantan"]["title"], "East Kalimantan")
        self.assertEqual(self.proposals["IDN|East Kalimantan"]["strategy"], "reviewed_override")

    def test_generation_is_deterministic(self):
        self.assertEqual(self.payload, MODULE.generate())
        self.assertEqual(list(self.proposals), sorted(self.proposals))


if __name__ == "__main__":
    unittest.main()
