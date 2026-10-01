"""Exercise resumable, bounded article fetching without network access."""

import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from scripts import build_static_data


class ArticleFetchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.catalogue = root / "wiki_articles.json"
        self.public = root / "articles.json"
        self.snapshot = {
            "version": 1,
            "generated_at": None,
            "countries": {},
            "regions": {"AA|One": None, "AA|Two": None, "AA|Three": None},
            "genres": {},
        }
        self.keys = {"AA|One": "One", "AA|Two": "Two", "AA|Three": "Three"}
        self.titles = {key: value for key, value in self.keys.items()}

    def patches(self):
        return (
            patch.object(build_static_data, "ARTICLE_CATALOGUE", self.catalogue),
            patch.object(build_static_data, "WEB", self.public.parent),
            patch.object(build_static_data, "snapshot_keys", return_value={"regions": self.keys}),
            patch.object(build_static_data, "read", side_effect=lambda path: self.titles if path.name == "region_article_titles.json" else {}),
        )

    def test_transient_failure_does_not_discard_later_progress(self):
        articles = [urllib.error.URLError("temporary"), {"Two": {"title": "Two"}},
                    {"Three": {"title": "Three"}}]
        context = self.patches()
        with context[0], context[1], context[2], context[3], \
                patch.object(build_static_data, "bulk_region_articles", side_effect=articles):
            report = build_static_data.refresh(self.snapshot, [], "regions", None, set(), delay=0, batch_size=1)

        self.assertEqual((report.fetched, report.failed), (2, 1))
        self.assertIsNone(self.snapshot["regions"]["AA|One"])
        self.assertEqual(self.snapshot["regions"]["AA|Three"]["title"], "Three")
        self.assertTrue(self.catalogue.exists(), "each success should checkpoint the durable snapshot")

    def test_limit_bounds_attempts_including_unavailable_pages(self):
        context = self.patches()
        with context[0], context[1], context[2], context[3], \
                patch.object(build_static_data, "bulk_region_articles", return_value={"One": None, "Two": None}) as fetch:
            report = build_static_data.refresh(self.snapshot, [], "regions", 2, set(), delay=0)

        self.assertEqual(fetch.call_count, 1)
        fetch.assert_called_once_with(["One", "Two"])
        self.assertEqual(report.unavailable, 2)

    def test_unmapped_regions_are_reported_without_requests(self):
        self.titles.pop("AA|Two")
        context = self.patches()
        with context[0], context[1], context[2], context[3], \
                patch.object(build_static_data, "bulk_region_articles", return_value={"One": None, "Three": None}) as fetch:
            report = build_static_data.refresh(self.snapshot, [], "regions", None, set(), delay=0)

        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(report.unmapped, 1)

    def test_error_limit_stops_a_failing_batch(self):
        context = self.patches()
        with context[0], context[1], context[2], context[3], \
                patch.object(build_static_data, "bulk_region_articles", side_effect=urllib.error.URLError("offline")) as fetch:
            report = build_static_data.refresh(self.snapshot, [], "regions", None, set(), delay=0,
                                               max_errors=2, batch_size=1)

        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(report.failed, 2)
        self.assertTrue(report.stopped_after_errors)

    def test_bulk_region_articles_normalizes_redirects_and_keeps_provenance(self):
        response = {"query": {
            "normalized": [{"from": "old name", "to": "Old name"}],
            "redirects": [{"from": "Old name", "to": "Resolved Region"}],
            "pages": [{
                "pageid": 42,
                "title": "Resolved Region",
                "extract": "A regional introduction.",
                "canonicalurl": "https://en.wikipedia.org/wiki/Resolved_Region",
                "pageprops": {"wikibase_item": "Q42"},
                "revisions": [{"revid": 1234}],
            }],
        }}
        with patch.object(build_static_data, "api", return_value=response) as api:
            articles = build_static_data.bulk_region_articles(["old name"])

        article = articles["old name"]
        self.assertEqual(article["title"], "Resolved Region")
        self.assertEqual(article["requested_title"], "old name")
        self.assertEqual(article["revision_id"], 1234)
        self.assertEqual(article["wikidata_url"], "https://www.wikidata.org/wiki/Q42")
        self.assertEqual(article["license"], build_static_data.LICENSE)
        params = api.call_args.args[1]
        self.assertEqual(params["redirects"], "1")
        self.assertIn("extracts", params["prop"])

    def test_bulk_region_articles_rejects_disambiguation_and_missing_pages(self):
        response = {"query": {"pages": [
            {"title": "Ambiguous", "extract": "Choices", "pageprops": {"disambiguation": ""}},
            {"title": "Absent", "missing": True},
        ]}}
        with patch.object(build_static_data, "api", return_value=response):
            articles = build_static_data.bulk_region_articles(["Ambiguous", "Absent"])
        self.assertEqual(articles, {"Ambiguous": None, "Absent": None})

    def test_rest_page_retries_transient_server_errors(self):
        transient = urllib.error.HTTPError("https://example.test", 503, "busy", {}, BytesIO())
        response = BytesIO(b'{"title": "Recovered"}')
        response.__enter__ = lambda value: value
        response.__exit__ = lambda *args: None
        with patch("urllib.request.urlopen", side_effect=[transient, response]) as open_url, \
                patch.object(build_static_data.time, "sleep") as sleep:
            result = build_static_data.rest_page("Recovered", "summary")

        self.assertEqual(result["title"], "Recovered")
        self.assertEqual(open_url.call_count, 2)
        sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
