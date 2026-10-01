import unittest

from scripts.validate_genres import valid_image
from scripts.find_genre_images import reviewed_image


class GenreImageValidationTests(unittest.TestCase):
    def image(self, **changes):
        record = {
            "image_url": "https://upload.wikimedia.org/example.jpg",
            "source_page_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
            "title": "Example performance",
            "creator": "Example photographer",
            "license": "CC BY-SA 4.0",
            "attribution": "Example photographer, CC BY-SA 4.0, via Wikimedia Commons",
            "depicts": "An identified performance of the example genre",
            "provider": "wikimedia_commons",
            "reviewed_at": "2026-09-28",
        }
        record.update(changes)
        return record

    def test_accepts_complete_reusable_image(self):
        self.assertTrue(valid_image(self.image()))

    def test_rejects_noncommercial_or_incomplete_image(self):
        self.assertFalse(valid_image(self.image(license="CC BY-NC 4.0")))
        image = self.image()
        del image["depicts"]
        self.assertFalse(valid_image(image))

    def test_queue_candidate_requires_explicit_source_and_depiction_review(self):
        item = {"results": [{"image_url": "https://example.org/a.jpg",
                             "source_page_url": "https://commons.wikimedia.org/wiki/File:A.jpg",
                             "title": "A", "creator": "Author", "license": "CC BY 4.0",
                             "provider": "wikimedia_commons"}]}
        self.assertIsNone(reviewed_image(item))
        item["review"] = {"candidate_index": 0, "source_page_verified": True,
                          "license_verified": True, "depicts": "A documented local music performance"}
        self.assertTrue(valid_image(reviewed_image(item)))
        item["review"]["license_verified"] = False
        self.assertIsNone(reviewed_image(item))
        item["review"]["license_verified"] = True
        item["results"][0]["license"] = "CC BY-NC 4.0"
        self.assertIsNone(reviewed_image(item))


if __name__ == "__main__":
    unittest.main()
