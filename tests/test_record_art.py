import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import server


class RecordArtTests(unittest.TestCase):
    def setUp(self):
        self.status_directory = tempfile.TemporaryDirectory()
        self.status_path = server.ART_STATUS_PATH
        server.ART_STATUS_PATH = Path(self.status_directory.name) / "record_art_status.json"
        server.ART_CACHE.clear()
        server.ART_STATUS.clear()
        server.SPOTIFY_TOKEN["value"] = ""
        server.SPOTIFY_TOKEN["expires"] = 0.0

    def tearDown(self):
        server.ART_CACHE.clear()
        server.ART_STATUS.clear()
        server.ART_STATUS_PATH = self.status_path
        self.status_directory.cleanup()

    def test_falls_back_to_cover_art_archive_when_discogs_has_no_image(self):
        with patch.object(server, "public_record", return_value={
            "musicbrainz_release_group_mbid": "release-group-1"
        }), patch.object(server, "approved_discogs_release", return_value=123), patch.object(
            server, "discogs_art", return_value=None
        ), patch.object(server, "musicbrainz_art", return_value={
            "provider": "Cover Art Archive / MusicBrainz",
            "front_url": "https://coverartarchive.org/front.jpg",
            "back_url": None,
            "source_url": "https://musicbrainz.org/release/example",
            "attribution": "Cover art provided by the Cover Art Archive via MusicBrainz.",
        }):
            art = server.record_art("record-example")
        self.assertTrue(art["available"])
        self.assertEqual(art["provider"], "Cover Art Archive / MusicBrainz")

    def test_discogs_primary_and_secondary_images_are_exposed(self):
        with patch.dict("os.environ", {"DISCOGS_TOKEN": "not-a-real-token"}), patch.object(
            server, "request_json", return_value={
                "uri": "https://www.discogs.com/release/123",
                "images": [
                    {"type": "primary", "uri": "https://img.example/front.jpg"},
                    {"type": "secondary", "uri": "https://img.example/back.jpg"},
                ],
            }
        ):
            art = server.discogs_art(123)
        self.assertEqual(art["front_url"], "https://img.example/front.jpg")
        self.assertEqual(art["back_url"], "https://img.example/back.jpg")
        self.assertEqual(art["attribution"], "Data provided by Discogs.")

    def test_spotify_cover_is_used_only_when_musicbrainz_has_none(self):
        record = {"spotify_url": "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm"}
        spotify = {
            "provider": "Spotify",
            "front_url": "https://i.scdn.co/image/cover",
            "back_url": None,
            "source_url": "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm",
            "attribution": "Listen on Spotify",
        }
        with patch.object(server, "public_record", return_value=record), patch.object(
            server, "approved_discogs_release", return_value=None
        ), patch.object(server, "remembered_discogs_release", return_value=None), patch.object(
            server, "discover_discogs_release", return_value=None
        ), patch.object(server, "musicbrainz_art", return_value=None), patch.object(
            server, "spotify_art", return_value=spotify
        ) as spotify_art:
            art = server.record_art("record-spotify")
        spotify_art.assert_called_once_with(record)
        self.assertEqual(art["provider"], "Spotify")
        self.assertEqual(art["front_url"], "https://i.scdn.co/image/cover")

    def test_spotify_cover_waits_until_musicbrainz_is_missing(self):
        with patch.object(server, "public_record", return_value={"id": "record-mb"}), patch.object(
            server, "approved_discogs_release", return_value=None
        ), patch.object(server, "remembered_discogs_release", return_value=None), patch.object(
            server, "discover_discogs_release", return_value=None
        ), patch.object(server, "musicbrainz_art", return_value={
            "provider": "Cover Art Archive / MusicBrainz",
            "front_url": "https://coverartarchive.org/front.jpg",
            "back_url": None,
            "source_url": "https://musicbrainz.org/release-group/example",
            "attribution": "Cover art provided by the Cover Art Archive via MusicBrainz.",
        }), patch.object(server, "spotify_art") as spotify_art:
            art = server.record_art("record-mb")
        spotify_art.assert_not_called()
        self.assertEqual(art["provider"], "Cover Art Archive / MusicBrainz")

    def test_spotify_art_uses_the_largest_image_and_the_album_link(self):
        album = {
            "external_urls": {"spotify": "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm"},
            "images": [
                {"url": "https://i.scdn.co/image/small", "width": 64},
                {"url": "https://i.scdn.co/image/large", "width": 640},
            ],
        }
        with patch.object(server, "spotify_access_token", return_value="token"), patch.object(
            server, "request_json", return_value=album
        ):
            art = server.spotify_art({"spotify_url": "https://open.spotify.com/intl-pt/album/1fQLBZLJvYLDqXZ7Ktdipm?si=abc"})
        self.assertEqual(art["front_url"], "https://i.scdn.co/image/large")
        self.assertEqual(art["source_url"], "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm")
        self.assertIsNone(art["back_url"])
        self.assertEqual(art["attribution"], "Listen on Spotify")

    def test_spotify_art_without_credentials_is_skipped(self):
        with patch.dict("os.environ", {}, clear=False), patch.object(server, "spotify_access_token", return_value=""):
            server.SPOTIFY_TOKEN["value"] = ""
            server.SPOTIFY_TOKEN["expires"] = 0
            self.assertIsNone(server.spotify_art({"spotify_url": "https://open.spotify.com/album/1fQLBZLJvYLDqXZ7Ktdipm"}))


if __name__ == "__main__":
    unittest.main()
