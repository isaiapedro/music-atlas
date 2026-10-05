import unittest

from scripts.apply_manual_record_replace import replace_shelf_record, rewrite_rough_guide
from scripts.build_genre_record_pages import apply_manual_replacements, apply_one_replacement, record_id


class ManualRecordReplaceTests(unittest.TestCase):
    def test_replaces_title_and_gives_a_new_id(self):
        old_id = record_id("Old Album", "Old Artist", 1970)
        catalogue = {"genres": {"afg-popular-music": {"records": [{
            "id": old_id,
            "title": "Old Album",
            "artist": "Old Artist",
            "year": 1970,
            "record_source": "rough_guide_discography",
        }]}}}
        replacements = {"version": 1, "replacements": []}
        selections = {"version": 1, "records": {old_id: {
            "youtube_url": "https://www.youtube.com/watch?v=abcdefghijk",
        }}}
        rough = {"records": [{
            "genre_id": "afg-popular-music",
            "title": "Old Album",
            "artist": "Old Artist",
            "year": 1970,
            "apple_music_url": "https://music.apple.com/us/album/old/1",
        }]}
        new_record = replace_shelf_record(
            catalogue,
            replacements,
            selections,
            rough,
            old_id,
            "afg-popular-music",
            "New Album",
            "New Artist",
            2019,
            {"spotify_url": "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm"},
            apply_one_replacement,
            record_id,
        )
        new_id = record_id("New Album", "New Artist", 2019)
        self.assertEqual(new_record["id"], new_id)
        shelf = catalogue["genres"]["afg-popular-music"]["records"]
        self.assertEqual(len(shelf), 1)
        self.assertEqual(shelf[0]["title"], "New Album")
        self.assertEqual(shelf[0]["spotify_url"], "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm")
        self.assertEqual(shelf[0]["youtube_url"], "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertNotIn(old_id, selections["records"])
        self.assertEqual(
            selections["records"][new_id]["spotify_url"],
            "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm",
        )
        self.assertEqual(rough["records"][0]["title"], "New Album")
        self.assertEqual(rough["records"][0]["apple_music_url"], "https://music.apple.com/us/album/old/1")

    def test_rebuild_applies_the_stored_replacement(self):
        old_id = record_id("Old Album", "Old Artist", 1970)
        new_id = record_id("New Album", "New Artist", 2019)
        genres = {"afg-popular-music": {"records": [{
            "id": old_id,
            "title": "Old Album",
            "artist": "Old Artist",
            "year": 1970,
        }]}}
        apply_manual_replacements(genres, {"replacements": [{
            "genre_id": "afg-popular-music",
            "from_id": old_id,
            "title": "New Album",
            "artist": "New Artist",
            "year": 2019,
            "spotify_url": "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm",
        }]})
        shelf = genres["afg-popular-music"]["records"]
        self.assertEqual(shelf[0]["id"], new_id)
        self.assertEqual(shelf[0]["spotify_url"], "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm")

    def test_rejects_an_album_already_on_the_genre(self):
        first = record_id("Keep Me", "Band", 2001)
        second = record_id("Swap Me", "Band", 2002)
        catalogue = {"genres": {"afg-klasik": {"records": [
            {"id": first, "title": "Keep Me", "artist": "Band", "year": 2001},
            {"id": second, "title": "Swap Me", "artist": "Band", "year": 2002},
        ]}}}
        with self.assertRaises(ValueError):
            replace_shelf_record(
                catalogue,
                {"replacements": []},
                {"records": {}},
                None,
                second,
                "afg-klasik",
                "Keep Me",
                "Band",
                2001,
                {},
                apply_one_replacement,
                record_id,
            )

    def test_rough_guide_rewrite_skips_other_genres(self):
        old_id = record_id("Shared", "Artist", 1990)
        payload = {"records": [
            {"genre_id": "afg-klasik", "title": "Shared", "artist": "Artist", "year": 1990},
            {"genre_id": "afg-popular-music", "title": "Shared", "artist": "Artist", "year": 1990},
        ]}
        changed = rewrite_rough_guide(
            payload,
            "afg-popular-music",
            old_id,
            "Replacement",
            "Artist",
            1991,
            record_id,
            {},
        )
        self.assertTrue(changed)
        self.assertEqual(payload["records"][0]["title"], "Shared")
        self.assertEqual(payload["records"][1]["title"], "Replacement")

    def test_sort_puts_years_in_order(self):
        from scripts.build_genre_record_pages import sort_record_lists
        genres = {"demo": {"records": [
            {"title": "Late", "artist": "A", "year": 2019},
            {"title": "Early", "artist": "B", "year": 1970},
            {"title": "Unknown", "artist": "C", "year": None},
        ]}}
        sort_record_lists(genres)
        self.assertEqual([row["title"] for row in genres["demo"]["records"]], ["Early", "Late", "Unknown"])


if __name__ == "__main__":
    unittest.main()
