import json
import unittest
from unittest.mock import patch

from google_play_scraper.client import GooglePlayClient


class ClientSuggestTest(unittest.TestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_request_formation(self, mock_post, mock_parse):
        # Minimal valid parsed response so method proceeds and returns []
        mock_post.return_value = "OK"
        mock_parse.return_value = [[], None]

        term = "maps"
        lang = "en"
        country = "us"

        self.client.suggest(term=term, lang=lang, country=country)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        # Called endpoint
        self.assertEqual(args[0], "/_/PlayStoreUi/data/batchexecute")

        # Verify params include rpc id and passthrough lang/country and fixed fields
        params = kwargs["params"]
        self.assertEqual(params["rpcids"], "IJ4APc")
        self.assertEqual(params["hl"], lang)
        self.assertEqual(params["gl"], country)
        self.assertIn("bl", params)
        self.assertIn("authuser", params)
        self.assertIn("soc-app", params)
        self.assertIn("soc-platform", params)
        self.assertIn("soc-device", params)
        self.assertIn("rt", params)

        # Verify f.req envelope and inner JSON structure
        form = kwargs["data"]
        self.assertIn("f.req", form)
        outer = json.loads(form["f.req"])  # [[[rpc_id, inner_json, None, "generic"]]]
        self.assertIsInstance(outer, list)
        self.assertEqual(outer[0][0][0], "IJ4APc")

        inner_json = outer[0][0][1]
        inner = json.loads(inner_json)
        # Expected payload structure: [[None, [term], [10], [2], 4]]
        self.assertEqual(inner, [[None, [term], [10], [2], 4]])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_happy_path_maps_items_and_skips_none(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        # Build suggestion list where one element is None and should be skipped
        suggestion_list = [
            ["alpha"],
            None,
            ["beta", "extra"],
        ]
        # data -> data[0][0] == suggestion_list
        mock_parse.return_value = [[suggestion_list]]

        out = self.client.suggest("al")
        self.assertEqual(out, ["alpha", "beta"])

    def test_empty_term_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.client.suggest("")

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_empty_or_none_parsed_data_returns_empty(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        mock_parse.return_value = []
        self.assertEqual(self.client.suggest("m"), [])

        mock_parse.return_value = None
        self.assertEqual(self.client.suggest("m"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_falsy_suggestion_list_returns_empty(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        # suggestion_list is None
        mock_parse.return_value = [[None]]
        self.assertEqual(self.client.suggest("ma"), [])

        # suggestion_list is []
        mock_parse.return_value = [[[]]]
        self.assertEqual(self.client.suggest("ma"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_index_or_type_errors_return_empty(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        # Various malformed structures to trigger IndexError/TypeError
        for bad in (
                None,  # data is None -> TypeError
                1,  # data is int -> TypeError
                [1],  # data[0] is int -> TypeError on [0]
                [[1]],  # suggestion_list becomes int -> TypeError in listcomp
                [[()]],  # suggestion_list is tuple -> item[0] ok but item may be empty -> IndexError
        ):
            mock_parse.return_value = bad
            self.assertEqual(self.client.suggest("q"), [])


if __name__ == "__main__":
    unittest.main()
