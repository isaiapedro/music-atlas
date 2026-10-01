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


if __name__ == "__main__":
    unittest.main()
