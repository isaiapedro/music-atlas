import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MvpLocksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.locks = load_module("mvp_locks")
        cls.inventory = json.loads((ROOT / "research" / "country_inventory.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((ROOT / "research" / "mvp_country_locks.json").read_text(encoding="utf-8"))

    def test_afghanistan_is_locked(self):
        self.assertIn("AFG", self.locks.locked_countries())
        self.assertTrue(self.locks.locked_genre_ids() >= {
            "afg-klasik",
            "afg-popular-music",
            "afg-wedding-and-folk-music",
            "afg-contemporary",
        })
        self.assertIn("Rubab", self.locks.locked_instrument_names())

    def test_inventory_marks_afghanistan_reviewed(self):
        afg = next(row for row in self.inventory["countries"] if row["code"] == "AFG")
        self.assertEqual(afg["status"], "reviewed")
        self.assertEqual(afg["reviewed_at"], "2026-10-03")
        self.assertIn("MVP", afg["summary"])

    def test_catalogue_lock_detects_overwrite(self):
        catalogue = json.loads((ROOT / "research" / "genre_catalogue.json").read_text(encoding="utf-8"))
        before = catalogue["entries"]
        after = json.loads(json.dumps(before))
        target = next(item for item in after if item["id"] == "afg-popular-music")
        target["youtube_examples"] = []
        violations = self.locks.catalogue_lock_violations(before, after)
        self.assertTrue(any("afg-popular-music.youtube_examples" in item for item in violations))

    def test_override_flag_documented(self):
        afg = next(row for row in self.registry["locks"] if row["country"] == "AFG")
        self.assertEqual(afg["allow_explicit_override_flag"], "--allow-mvp-lock")


if __name__ == "__main__":
    unittest.main()
