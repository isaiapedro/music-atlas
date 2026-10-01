"""Unit tests for the Natural Earth/Wikimedia region importer."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("import_region_wikipedia.py")
SPEC = importlib.util.spec_from_file_location("import_region_wikipedia", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RegionWikipediaImportTests(unittest.TestCase):
    def test_source_matching_uses_country_and_normalized_name(self):
        source = {"features": [
            {"properties": {"adm0_a3": "AA", "name_en": "One Region", "wikidataid": "Q1"}},
            {"properties": {"adm0_a3": "BB", "name": "Other", "wikidataid": "Q2"}},
        ]}
        matched, missing, ambiguous = MODULE.match_source(source, ["AA|One Region", "BB|Other"])
        self.assertEqual(matched["AA|One Region"]["qid"], "Q1")
        self.assertEqual(matched["BB|Other"]["qid"], "Q2")
        self.assertEqual(missing, [])
        self.assertEqual(ambiguous, {})

    def test_conflicting_ids_are_not_silently_selected(self):
        source = {"features": [
            {"properties": {"adm0_a3": "AA", "name": "One", "wikidataid": "Q1"}},
            {"properties": {"adm0_a3": "AA", "name": "One", "wikidataid": "Q9"}},
        ]}
        matched, _, ambiguous = MODULE.match_source(source, ["AA|One"])
        self.assertNotIn("AA|One", matched)
        self.assertEqual(ambiguous["AA|One"], ["Q1", "Q9"])

    @patch.object(MODULE, "sparql")
    def test_wikidata_sitelink_resolution_is_batched(self, query):
        query.return_value = {"results": {"bindings": [{
            "item": {"value": "http://www.wikidata.org/entity/Q1"},
            "article": {"value": "https://en.wikipedia.org/wiki/One"},
        }]}}
        resolved, missing = MODULE.resolve_qid_sitelinks({"AA|One": {"qid": "Q1"}})
        self.assertEqual(resolved["AA|One"]["title"], "One")
        self.assertEqual(resolved["AA|One"]["method"], "natural_earth_wikidata_sitelink")
        self.assertEqual(missing, [])

    @patch.object(MODULE, "api")
    def test_search_fallback_records_unreviewed_method(self, api):
        api.return_value = {"query": {"pages": [{"pageid": 1, "title": "One Province",
                                                   "pageprops": {"wikibase_item": "Q3"}}]}}
        result = MODULE.search_fallback(["AA|One"], {"AA": "Aland"}, {"AA|One": {"qid": None}})
        self.assertEqual(result["AA|One"]["method"], "enwiki_search_fallback")
        self.assertEqual(result["AA|One"]["qid"], "Q3")

    @patch.object(MODULE, "api")
    def test_lead_fetch_includes_revision_and_provenance(self, api):
        api.return_value = {"query": {"pages": [{"title": "One", "extract": "Lead.",
            "fullurl": "https://en.wikipedia.org/wiki/One", "revisions": [{"revid": 7,
            "timestamp": "2026-01-01T00:00:00Z"}]}]}}
        batches = list(MODULE.fetch_leads({"AA|One": {"title": "One", "qid": "Q1",
                                                        "method": "natural_earth_wikidata_sitelink"}}))
        article = batches[-1]["AA|One"]
        self.assertEqual(article["revision_id"], 7)
        self.assertEqual(article["region_import"]["natural_earth_wikidata_id"], "Q1")


if __name__ == "__main__":
    unittest.main()
