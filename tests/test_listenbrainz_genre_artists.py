import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.fetch_listenbrainz_genre_artists import collect


class ListenBrainzGenreArtistTests(unittest.TestCase):
    def test_collect_excludes_global_popularity_without_strong_genre_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "catalog.sqlite3"
            db = sqlite3.connect(db_path)
            db.executescript("""
                CREATE TABLE atlas_genre(id TEXT, name TEXT, country TEXT, tag_id INTEGER);
                CREATE TABLE artist(id INTEGER, mbid TEXT, name TEXT);
                CREATE TABLE genre_artist(genre_id TEXT, artist_id INTEGER, score INTEGER, basis TEXT);
                INSERT INTO atlas_genre VALUES('g1', 'Genre One', 'AAA', 17);
                INSERT INTO artist VALUES(1, 'mbid-a', 'Artist A');
                INSERT INTO artist VALUES(2, 'mbid-b', 'Artist B');
                INSERT INTO genre_artist VALUES('g1', 1, 2, 'artist tag');
                INSERT INTO genre_artist VALUES('g1', 2, 28, 'release tag credit');
            """)
            db.close()
            catalogue = root / "genres.json"
            catalogue.write_text(json.dumps({"entries": [
                {"id": "g1", "name": "Genre One", "country": "AAA", "status": "published", "artists": []},
                {"id": "g2", "name": "Genre Two", "country": "BBB", "status": "published",
                 "artists": ["App Artist", "Community drummers"]},
                {"id": "g3", "name": "Genre Three", "country": "CCC", "status": "published",
                 "artists": ["Artist C"]},
                {"id": "g4", "name": "Genre Four", "country": "DDD", "status": "published",
                 "artists": ["Community drummers"]},
            ]}))
            output = root / "out.json"

            def fake_fetch(mbids):
                self.assertEqual(mbids, ["mbid-a", "mbid-b", "mbid-c", "mbid-app"])
                return [
                    {"artist_mbid": "mbid-a", "total_listen_count": 90, "total_user_count": 9},
                    {"artist_mbid": "mbid-b", "total_listen_count": 200, "total_user_count": 15},
                    {"artist_mbid": "mbid-app", "total_listen_count": 25, "total_user_count": 4},
                ]

            db = sqlite3.connect(db_path)
            db.execute("INSERT INTO artist VALUES(3, 'mbid-app', 'App Artist')")
            db.execute("INSERT INTO artist VALUES(4, 'mbid-c', 'Artist C')")
            db.execute("INSERT INTO genre_artist VALUES('g1', 4, 2, 'artist tag')")
            db.commit()
            db.close()

            with patch("scripts.fetch_listenbrainz_genre_artists.fetch_batch", side_effect=fake_fetch):
                payload = collect(db_path, output, batch_size=100, delay=0, catalogue_path=catalogue)

            self.assertEqual(payload["artist_ids_queried"], 4)
            self.assertEqual(payload["artists_with_listen_data"], 3)
            self.assertEqual(payload["app_representatives_with_listenbrainz_id"], 2)
            self.assertEqual(payload["app_representatives_pending_name_search"], 2)
            ranked = next(row for row in json.loads(output.read_text())["genres"]
                          if row["genre_id"] == "g1")["top_artists"]
            self.assertEqual([row["artist"] for row in ranked], ["Artist A"])
            self.assertEqual(ranked[0]["genre_tag_score"], 2)
            self.assertEqual(ranked[0]["artist_tag_score"], 2)
            self.assertEqual(ranked[0]["genre_tag_basis"], "artist tag")
            self.assertEqual(ranked[0]["listenbrainz_listeners"], 9)
            with output.with_name("genre_artist_popularity_by_tag_score.csv").open(encoding="utf-8") as stream:
                score_rows = list(csv.DictReader(stream))
            self.assertEqual([(row["artist"], row["score_band"]) for row in score_rows],
                             [("Artist A", "2"), ("Artist C", "2")])
            all_genres = json.loads(output.read_text())["genres"]
            second_genre = next(row for row in all_genres if row["genre_id"] == "g2")
            self.assertFalse(second_genre["musicbrainz_genre_covered"])
            self.assertEqual(second_genre["top_artists"][0]["artist"], "App Artist")
            self.assertEqual(second_genre["manual_name_searches"][0]["artist_match_status"],
                             "generic representative; manual name search only")
            third_genre = next(row for row in all_genres if row["genre_id"] == "g3")
            self.assertEqual(third_genre["top_artists"], [])
            with output.with_name("genres_without_listenbrainz_artists.csv").open(encoding="utf-8") as stream:
                missing_csv = list(csv.DictReader(stream))
            self.assertEqual(len(missing_csv), 2)
            by_id = {row["genre_id"]: row for row in missing_csv}
            self.assertIn("Artist C → Genre One", by_id["g3"]["artists_listed_elsewhere"])
            self.assertEqual(by_id["g4"]["artists_listed_elsewhere"], "")
            self.assertEqual(by_id["g4"]["artists_not_found_elsewhere"], "Community drummers")

    def test_rejects_unsupported_batch_size(self):
        with self.assertRaises(ValueError):
            collect(Path("unused.sqlite"), Path("unused.json"), batch_size=101)


if __name__ == "__main__":
    unittest.main()
