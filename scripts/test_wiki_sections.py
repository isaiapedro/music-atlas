"""Protect focused encyclopedia excerpts from falling back to unrelated page leads."""

import unittest

from scripts.build_static_data import section_text


HTML = '''
<section data-mw-section-id="0"><p>Broad page overview.</p></section>
<section data-mw-section-id="1"><h2 id="History">History</h2><p>Unrelated history.</p></section>
<section data-mw-section-id="2"><h3 id="Music_and_dance">Music and dance</h3>
<p>General performance context.</p><p>Yak Béra accompanies low-country dance.</p></section>
'''


class WikiSectionTests(unittest.TestCase):
    def test_focused_section_excludes_page_lead_and_other_sections(self):
        excerpt = section_text(HTML, "Music and dance")
        self.assertIn("General performance context.", excerpt)
        self.assertNotIn("Broad page overview.", excerpt)
        self.assertNotIn("Unrelated history.", excerpt)

    def test_focus_limits_a_broad_section_to_matching_paragraphs(self):
        self.assertEqual(section_text(HTML, "Music and dance", "Yak Béra"),
                         "Yak Béra accompanies low-country dance.")
        self.assertEqual(section_text(HTML, "Music and dance", "Gengetone"), "")


if __name__ == "__main__":
    unittest.main()
