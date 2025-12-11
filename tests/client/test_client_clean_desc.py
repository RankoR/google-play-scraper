import unittest

from google_play_scraper.client import _clean_desc


class ClientCleanDescTest(unittest.TestCase):

    def test_replaces_br_with_crlf(self):
        self.assertEqual(_clean_desc("Line1<br>Line2"), "Line1\r\nLine2")

    def test_replaces_multiple_br_occurrences(self):
        self.assertEqual(_clean_desc("A<br>B<br>C"), "A\r\nB\r\nC")

    def test_none_or_empty_returns_empty_string(self):
        self.assertEqual(_clean_desc(None), "")
        self.assertEqual(_clean_desc(""), "")

    def test_variants_not_replaced(self):
        # Current implementation replaces only exact '<br>' (lowercase, no slash)
        self.assertEqual(_clean_desc("X<br/>Y"), "X<br/>Y")
        self.assertEqual(_clean_desc("X<BR>Y"), "X<BR>Y")

    def test_string_without_br_remains_unchanged(self):
        self.assertEqual(_clean_desc("No breaks here."), "No breaks here.")


if __name__ == "__main__":
    unittest.main()
