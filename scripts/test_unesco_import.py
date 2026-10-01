"""Run with: python3 -m unittest scripts.test_unesco_import"""

import json
import unittest

from scripts.import_unesco_candidates import INVENTORY, import_candidates


class UnescoImportTests(unittest.TestCase):
    def test_country_mapping_and_music_concept_strength(self):
        inventory = json.loads(INVENTORY.read_text())
        records = [
            {
                "ich_public_ref": "10", "title_en": "Music practice", "http_url_en": "https://ich.unesco.org/en/RL/00010",
                "countries": ["AZ", "IN", "FR"], "inscription_year": "2024",
                "concepts_primary_names": ["Vocal music"], "concepts_secondary_names": [],
            },
            {
                "ich_public_ref": "11", "title_en": "Festival", "http_url_en": "https://ich.unesco.org/en/RL/00011",
                "countries": ["IN"], "concepts_primary_names": ["Festivals"],
                "concepts_secondary_names": ["Instrumental music"],
            },
            {
                "ich_public_ref": "12", "title_en": "Cooperatives", "http_url_en": "https://ich.unesco.org/en/RL/00012",
                "countries": ["IN"], "concepts_primary_names": ["Cooperatives"],
                "concepts_secondary_names": [],
            },
        ]
        output = import_candidates(records, inventory)
        self.assertEqual({item["country"] for item in output["candidates"]}, {"AZE", "IND"})
        self.assertEqual(len(output["candidates"]), 3)
        self.assertEqual(output["unmatched_source_country_codes"], ["FR"])
        matches = {item["id"]: item["music_match"] for item in output["candidates"]}
        self.assertEqual(matches["unesco-11-ind"], "secondary_concept")
        self.assertEqual(matches["unesco-10-aze"], "primary_concept")

    def test_invalid_map_code_fails(self):
        with self.assertRaisesRegex(ValueError, "Country code mapping"):
            import_candidates([], {"countries": []})


if __name__ == "__main__":
    unittest.main()
