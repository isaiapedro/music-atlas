import unittest

from scripts.apply_manual_genre_update import (
    apply_description,
    apply_video,
    file_title_from_image_link,
    image_record,
    watch_url_from_video_link,
)


class ManualGenreUpdateTests(unittest.TestCase):
    def test_reads_commons_file_names_from_page_and_upload_links(self):
        self.assertEqual(
            file_title_from_image_link("https://commons.wikimedia.org/wiki/File:Gojri_Folk_Singers.jpg"),
            "Gojri_Folk_Singers.jpg",
        )
        self.assertEqual(
            file_title_from_image_link("https://upload.wikimedia.org/wikipedia/commons/9/93/Gojri_Folk_Singers.jpg"),
            "Gojri_Folk_Singers.jpg",
        )

    def test_normalizes_youtube_links_to_one_watch_url(self):
        expected = "https://www.youtube.com/watch?v=abcdefghijk"
        self.assertEqual(watch_url_from_video_link("https://youtu.be/abcdefghijk"), expected)
        self.assertEqual(watch_url_from_video_link("https://www.youtube.com/shorts/abcdefghijk"), expected)
        self.assertEqual(
            watch_url_from_video_link("https://www.youtube.com/watch?v=abcdefghijk&t=12"),
            expected,
        )

    def test_description_becomes_panel_text_and_first_source(self):
        genre = {"note": "x" * 60, "sources": ["https://example.org/old"]}
        text = "A" * 60
        apply_description(genre, text, "https://example.org/article")
        self.assertEqual(genre["note"], text)
        self.assertEqual(genre["sources"][0], "https://example.org/article")
        self.assertTrue(genre["prefer_local_note"])
        self.assertIn("https://example.org/old", genre["sources"])

    def test_video_replaces_the_same_artist_and_keeps_a_canonical_url(self):
        genre = {"youtube_examples": [{
            "artist": "Kabul Dreams",
            "title": "Old",
            "youtube_url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
            "reviewed_at": "2026-10-01",
        }]}
        apply_video(genre, "https://youtu.be/bbbbbbbbbbb", "New song", "Kabul Dreams", "2026-10-02")
        self.assertEqual(len(genre["youtube_examples"]), 1)
        self.assertEqual(genre["youtube_examples"][0]["youtube_url"], "https://www.youtube.com/watch?v=bbbbbbbbbbb")
        self.assertEqual(genre["youtube_examples"][0]["attribution_basis"], "user-approved practice-level example")

    def test_image_record_uses_commons_attribution(self):
        record = image_record({
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/93/Gojri_Folk_Singers.jpg",
            "source_page_url": "https://commons.wikimedia.org/wiki/File:Gojri_Folk_Singers.jpg",
            "title": "Gojri Folk Singers",
            "creator": "Ramesh Lalwani",
            "license": "CC BY 2.0",
            "provider": "wikimedia_commons",
        }, reviewed_at="2026-10-02")
        self.assertEqual(record["license"], "CC BY 2.0")
        self.assertIn("Ramesh Lalwani", record["attribution"])
        self.assertGreaterEqual(len(record["depicts"]), 20)


if __name__ == "__main__":
    unittest.main()
