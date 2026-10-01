import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_region_articles import audit, failures


def feature(code, name):
    return {"properties": {"code": code, "name": name}}


def article(requested_title):
    return {"title": requested_title, "requested_title": requested_title, "extract": "Text",
            "url": "https://en.wikipedia.org/wiki/Example", "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/"}


class RegionArticleCoverageTests(unittest.TestCase):
    def test_multipart_geometry_counts_as_one_region(self):
        features = [feature("AAA", "North"), feature("AAA", "North")]
        report = audit(features, {"AAA|North": "North Province"},
                       {"AAA|North": article("North Province")})
        self.assertEqual(report["feature_count"], 2)
        self.assertEqual(report["region_count"], 1)
        self.assertEqual(report["multipart_regions"], ["AAA|North"])
        self.assertEqual(failures(report), {})

    def test_missing_mapping_and_snapshot_fail_completion(self):
        report = audit([feature("AAA", "North"), feature("AAA", "South")],
                       {"AAA|North": "North Province"}, {"AAA|North": None})
        self.assertEqual(report["missing_title_keys"], ["AAA|South"])
        self.assertEqual(report["missing_article_keys"], ["AAA|South"])
        self.assertEqual(report["null_article_keys"], ["AAA|North"])
        self.assertTrue(failures(report))

    def test_stale_keys_title_collisions_and_request_mismatch_fail(self):
        report = audit([feature("AAA", "North"), feature("BBB", "South")],
                       {"AAA|North": "Province", "BBB|South": "Province", "AAA|Old": "Old"},
                       {"AAA|North": article("Wrong"), "BBB|South": article("Province"),
                        "AAA|Old": article("Old")})
        self.assertEqual(report["extra_title_keys"], ["AAA|Old"])
        self.assertEqual(report["extra_article_keys"], ["AAA|Old"])
        self.assertEqual(report["request_mismatch_keys"], ["AAA|North"])
        self.assertEqual(report["duplicate_titles"], {"province": ["AAA|North", "BBB|South"]})


if __name__ == "__main__":
    unittest.main()
