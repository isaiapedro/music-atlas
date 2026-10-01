import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rym", ROOT / "scripts/build_rym_candidates.py")
rym = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rym)
FETCH_SPEC = importlib.util.spec_from_file_location("fetch_rym", ROOT / "scripts/fetch_parse_rym.py")
fetch_rym = importlib.util.module_from_spec(FETCH_SPEC)
FETCH_SPEC.loader.exec_module(fetch_rym)
COVERAGE_SPEC = importlib.util.spec_from_file_location("rym_coverage", ROOT / "scripts/compare_rym_genres.py")
rym_coverage = importlib.util.module_from_spec(COVERAGE_SPEC)
COVERAGE_SPEC.loader.exec_module(rym_coverage)
IMPORT_SPEC = importlib.util.spec_from_file_location("rym_import", ROOT / "scripts/import_rym_chart_pages.py")
rym_import = importlib.util.module_from_spec(IMPORT_SPEC)
IMPORT_SPEC.loader.exec_module(rym_import)
RECORD_PAGE_SPEC = importlib.util.spec_from_file_location(
    "genre_record_pages", ROOT / "scripts/build_genre_record_pages.py")
genre_record_pages = importlib.util.module_from_spec(RECORD_PAGE_SPEC)
RECORD_PAGE_SPEC.loader.exec_module(genre_record_pages)


class RymCandidateTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
        CREATE TABLE artist(id INTEGER PRIMARY KEY, mbid TEXT, name TEXT, sort_name TEXT);
        CREATE TABLE genre_artist(genre_id TEXT, artist_id INTEGER, score INTEGER);
        INSERT INTO artist VALUES(1,'artist-1','Example Artist','Artist, Example');
        INSERT INTO genre_artist VALUES('genre-1',1,3);
        """)

    def tearDown(self):
        self.db.close()

    def test_normalizes_matches_and_holds_strong_undated_release(self):
        payload = {"data": {"items": [
            {"release_name":"Dated","artist":"Example Artist","year":1977,"average_rating":4.0,"rating_count":100,"reviews_count":10},
            {"release_name":"Undated","artist":"Example Artist","average_rating":4.8,"rating_count":900,"reviews_count":80}
        ]}}
        rows = rym.normalize_releases(payload, "genre-1", self.db)
        selected, holds, remainder, _ = rym.rank_releases(rows, per_decade=9, hold_min_score=.62)
        self.assertEqual(selected[0]["decade"], 1970)
        self.assertEqual(selected[0]["musicbrainz_artist_mbid"], "artist-1")
        self.assertEqual(holds[0]["title"], "Undated")
        self.assertFalse(remainder)

    def test_unmatched_artist_is_not_selected(self):
        payload = [{"title":"Release","artist":"Someone Else","year":1991,"rating":5,"rating_count":5000}]
        rows = rym.normalize_releases(payload, "genre-1", self.db)
        selected, _, remainder, _ = rym.rank_releases(rows)
        self.assertFalse(selected)
        self.assertEqual(remainder[0]["artist_match"], "unmatched")

    def test_live_request_builder_keeps_key_in_header(self):
        request = fetch_rym.build_request("get_charts", {"page":"1", "year":"1970s"}, "secret")
        self.assertNotIn("secret", request.full_url)
        self.assertEqual(request.get_header("X-api-key"), "secret")
        with self.assertRaises(ValueError):
            fetch_rym.build_request("unknown", {}, "secret")
        self.assertNotIn("genre", fetch_rym.ENDPOINT_PARAMETERS["get_charts"])
        self.assertIn("get_genres", fetch_rym.ALLOWED_ENDPOINTS)
        self.assertNotIn("genre", fetch_rym.ENDPOINT_PARAMETERS["get_charts"])

    def test_abbreviated_rating_counts_are_numeric(self):
        self.assertEqual(rym.number("96k"), 96000)
        self.assertEqual(rym.number("1.2M"), 1200000)
        self.assertEqual(rym.number("1,234"), 1234)
        self.assertEqual(rym.number("n/a"), 0)

    def test_non_latin_text_is_not_collapsed_into_an_empty_musicbrainz_match_key(self):
        self.assertIsNone(rym_import.musicbrainz_match_key("Кеманча", "Габиль Алиев"))
        self.assertEqual(rym_import.musicbrainz_match_key("Étoile", "Artist"), ("etoile", "artist"))

    def test_missing_chart_artist_credit_is_treated_as_various_artists(self):
        credit, source = rym_import.chart_artist_credit([])
        self.assertEqual(credit, "Various Artists")
        self.assertEqual(source, "inferred_various_artists")

    def test_saved_chart_record_does_not_require_musicbrainz_validation(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite3") as temporary:
            db = sqlite3.connect(temporary.name)
            db.executescript("""
                CREATE TABLE genre_assessment(
                    page_id TEXT, atlas_genre_ids_json TEXT, classification TEXT
                );
                CREATE TABLE album_candidate(
                    candidate_id TEXT, page_id TEXT, selected_within_page_decade INTEGER,
                    chart_rank INTEGER, title TEXT, artist_credit TEXT, provisional_year INTEGER
                );
                CREATE TABLE musicbrainz_resolution(
                    candidate_id TEXT, release_group_mbid TEXT, mb_first_year INTEGER,
                    year_comparison TEXT
                );
                INSERT INTO genre_assessment VALUES('page-1', '["genre-1"]', 'exact_name_candidate');
                INSERT INTO album_candidate VALUES('candidate-1', 'page-1', 1, 1, 'Chart Album', 'Chart Artist', 1984);
            """)
            db.commit()
            db.close()
            payload = genre_record_pages.build(Path(temporary.name))
        record = payload["genres"]["genre-1"]["records"][0]
        self.assertEqual(record["title"], "Chart Album")
        self.assertEqual(record["artist"], "Chart Artist")
        self.assertEqual(record["year"], 1984)
        self.assertNotIn("musicbrainz_url", record)

    def test_parse_artist_details_discography_wrapper(self):
        payload = {"status":"success", "data":{"name":"Example Artist", "discography":[{"title":"LP","year":1988}]}}
        self.assertEqual(rym.parse_items(payload), [{"title":"LP","year":1988}])

    def test_all_genre_comparison_keeps_fuzzy_matches_as_suggestions(self):
        rows = rym_coverage.compare(
            [{"id":"id-1","country":"TST","name":"Arabesk"},
             {"id":"id-2","country":"TST","name":"Gagok"}],
            [{"name":"Arabesk","url":"/genre/arabesk/"},{"name":"Gagaku","url":"/genre/gagaku/"}],
        )
        self.assertEqual(rows[0]["match_status"], "exact_normalized")
        self.assertEqual(rows[0]["review_status"], "exact_name_only")
        self.assertEqual(rows[1]["match_status"], "no_exact_match")
        self.assertIn("Gagaku", rows[1]["suggestions"])


if __name__ == "__main__":
    unittest.main()
