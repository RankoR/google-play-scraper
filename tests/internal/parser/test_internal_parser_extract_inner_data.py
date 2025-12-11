import unittest

from google_play_scraper.internal.parser import ScriptDataParser


class ScriptDataParserExtractInnerDataTest(unittest.TestCase):

    def test_happy_path_extracts_inner_json(self):
        outer = [["wrb.fr", "RPC", "[1,2,3]"]]
        self.assertEqual(ScriptDataParser._extract_inner_data(outer), [1, 2, 3])

    def test_empty_outer_json_returns_empty_list(self):
        self.assertEqual(ScriptDataParser._extract_inner_data([]), [])

    def test_wrong_structure_missing_inner_returns_empty_list(self):
        # Missing the third element (index 2)
        outer = [["wrb.fr", "RPC"]]
        self.assertEqual(ScriptDataParser._extract_inner_data(outer), [])

    def test_inner_data_empty_string_returns_empty_list(self):
        outer = [["wrb.fr", "RPC", ""]]
        self.assertEqual(ScriptDataParser._extract_inner_data(outer), [])

    def test_inner_data_none_returns_empty_list(self):
        outer = [["wrb.fr", "RPC", None]]
        self.assertEqual(ScriptDataParser._extract_inner_data(outer), [])

    def test_inner_data_invalid_json_returns_empty_list(self):
        outer = [["wrb.fr", "RPC", "[1,2,]"]]
        self.assertEqual(ScriptDataParser._extract_inner_data(outer), [])


if __name__ == "__main__":
    unittest.main()
