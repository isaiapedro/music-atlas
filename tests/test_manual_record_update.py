import unittest
from unittest.mock import patch

import server
from scripts.apply_manual_record_update import (
    apple_music_url,
    cover_from_link,
    discogs_target,
    player_updates,
    spotify_url,
)
from scripts.find_shelf_record import find_records
from scripts.build_genre_record_pages import apply_manual_selections


class ManualRecordUpdateTests(unittest.TestCase):
    def test_normalizes_spotify_and_apple_links(self):
        self.assertEqual(
            spotify_url("https://open.spotify.com/intl-pt/album/1fQLBZLJvYLDqXZ7Ktdipm?si=abc"),
            "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm",
        )
        self.assertEqual(
            spotify_url("https://open.spotify.com/embed/track/6i2xB4blH8hAmrm0PBmV4q"),
            "https://open.spotify.com/track/6i2xB4blH8hAmrm0PBmV4q",
        )
        self.assertEqual(
            apple_music_url("https://music.apple.com/us/album/music-of-afghanistan/219127328?uo=4"),
            "https://music.apple.com/us/album/music-of-afghanistan/219127328",
        )

    def test_discogs_release_page_saves_cover_and_back(self):
        self.assertEqual(
            discogs_target("https://www.discogs.com/release/1234567-Artist-Title"),
            ("release", 1234567),
        )
        self.assertEqual(discogs_target("https://discogs.com/master/89-Name"), ("master", 89))
        self.assertIsNone(discogs_target("https://i.discogs.com/front.jpeg"))
        cover = cover_from_link(
            "https://www.discogs.com/release/1234567-Artist-Title",
            discogs_payload={
                "uri": "https://www.discogs.com/release/1234567",
                "images": [
                    {"type": "primary", "uri": "https://i.discogs.com/front.jpeg"},
                    {"type": "secondary", "uri": "https://i.discogs.com/back.jpeg"},
                ],
            },
        )
        self.assertEqual(cover["front_url"], "https://i.discogs.com/front.jpeg")
        self.assertEqual(cover["back_url"], "https://i.discogs.com/back.jpeg")
        self.assertEqual(cover["attribution"], "Data provided by Discogs.")

    def test_title_search_returns_the_shelf_id(self):
        catalogue = {"genres": {"afg-contemporary": {"records": [
            {"id": "record-9ae0cd25d2bb438f5484", "title": "Plastic Words", "artist": "Kabul Dreams", "year": 2013},
        ]}}}
        matches = find_records(catalogue, "plastic")
        self.assertEqual(matches[0]["id"], "record-9ae0cd25d2bb438f5484")
        self.assertEqual(find_records(catalogue, "missing"), [])

    def test_direct_cover_keeps_the_source_page(self):
        cover = cover_from_link(
            "https://example.org/covers/front.jpg",
            "https://example.org/album",
            "Example label",
        )
        self.assertEqual(cover["front_url"], "https://example.org/covers/front.jpg")
        self.assertEqual(cover["source_url"], "https://example.org/album")
        self.assertEqual(cover["attribution"], "Example label")

    def test_direct_cover_without_a_source_page_is_rejected(self):
        with self.assertRaises(ValueError):
            cover_from_link("https://example.org/covers/front.jpg")

    def test_players_become_canonical_shelf_fields(self):
        updates = player_updates(
            youtube="https://youtu.be/abcdefghijk",
            spotify="https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm",
            apple="https://music.apple.com/us/song/example/219127328",
        )
        self.assertEqual(updates["youtube_url"], "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(updates["spotify_url"], "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm")
        self.assertIn("/song/example/219127328", updates["apple_music_url"])

    def test_rebuild_keeps_the_chosen_cover_and_player(self):
        genres = {"afg-klasik": {"records": [{
            "id": "record-example",
            "title": "Example",
            "artist": "Player",
            "year": 2001,
            "youtube_url": "https://www.youtube.com/watch?v=oldvideoid1",
        }]}}
        apply_manual_selections(genres, {"records": {"record-example": {
            "cover": {
                "front_url": "https://example.org/front.jpg",
                "source_url": "https://example.org/album",
                "attribution": "Selected cover.",
            },
            "youtube_url": "https://www.youtube.com/watch?v=abcdefghijk",
        }}})
        record = genres["afg-klasik"]["records"][0]
        self.assertEqual(record["cover"]["front_url"], "https://example.org/front.jpg")
        self.assertEqual(record["youtube_url"], "https://www.youtube.com/watch?v=abcdefghijk")

    def test_selected_cover_is_served_before_discogs(self):
        server.ART_CACHE.clear()
        record = {"id": "record-manual-cover", "cover": {
            "front_url": "https://example.org/front.jpg",
            "back_url": "https://example.org/back.jpg",
            "source_url": "https://example.org/album",
            "attribution": "Example label",
        }}
        with patch.object(server, "public_record", return_value=record), patch.object(
            server, "discover_discogs_release"
        ) as discover:
            art = server.record_art("record-manual-cover")
        discover.assert_not_called()
        self.assertTrue(art["available"])
        self.assertEqual(art["front_url"], "https://example.org/front.jpg")
        self.assertEqual(art["back_url"], "https://example.org/back.jpg")
        self.assertEqual(art["attribution"], "Example label")


if __name__ == "__main__":
    unittest.main()
