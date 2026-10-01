"""Run with: python3 -m unittest scripts.test_wikidata_import"""

import json
import unittest

from scripts.import_unesco_candidates import INVENTORY
from scripts.import_wikidata_candidates import parse_results, target_countries


class WikidataImportTests(unittest.TestCase):
    def test_only_unesco_gaps_are_queried(self):
        inventory = json.loads(INVENTORY.read_text())
        targets = target_countries(inventory, {"candidates": [{"country": "IND"}]})
        self.assertEqual(targets["AGO"], "AO")
        self.assertNotIn("IND", targets)
        self.assertNotIn("CYN", targets)

    def test_explicit_statement_is_saved_once(self):
        binding = {
            "iso2": {"value": "AO"},
            "country": {"value": "http://www.wikidata.org/entity/Q916"},
            "item": {"value": "http://www.wikidata.org/entity/Q1191544"},
            "itemLabel": {"value": "kuduro"},
        }
        rows = parse_results({"results": {"bindings": [binding, binding]}}, {"AGO": "AO"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["wikidata_id"], "Q1191544")
        self.assertEqual(rows[0]["review_status"], "unreviewed")


if __name__ == "__main__":
    unittest.main()
