import unittest
from unittest.mock import patch

from google_play_scraper.client import GooglePlayClient


class ClientSearchTest(unittest.TestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get")
    def test_price_param_mapping(self, mock_get, mock_parse):
        # Minimal valid parse so that code proceeds to attempt indexing
        # but immediately returns [] due to empty structure
        mock_parse.return_value = {"ds:1": [["x", [[[[]]]]]]}  # items == [] -> []

        # free -> 1
        self.client.search("maps", price="free", lang="en", country="us")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["price"], 1)

        # paid -> 2
        self.client.search("maps", price="paid", lang="en", country="us")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["price"], 2)

        # unknown -> default 0
        self.client.search("maps", price="unknown", lang="en", country="us")
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["price"], 0)

        # Verify other params passed through
        self.assertEqual(kwargs["params"]["hl"], "en")
        self.assertEqual(kwargs["params"]["gl"], "us")

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get")
    def test_happy_path_limits_num_and_skips_missing_app_id(self, mock_get, mock_parse):
        mock_get.return_value = "<html>dummy</html>"

        # Build three items; one without app_id should be skipped; only first 2 returned
        def make_item(app_id: str | None, title: str):
            item = [None] * 13
            # icon path [1,1,0,3,2]
            icon_path = [None, [[None, [None, None, "https://img.test/icon.png"]]]]
            # developer paths
            dev_block = [[title + " Dev",
                          [None, None, None, None, [None, None, "https://play.google.com/store/apps/dev?id=DEV_ID"]]]]
            # price block -> paths:
            #   free flag at [7,0,3,2,1,0,0] (expects 0 for free)
            #   price_text at [7,0,3,2,1,0,2] (expects "$0.00")
            price_block = [
                [
                    None, None, None,
                    [
                        None, None,
                        [
                            None,
                            [
                                [0, None, "$0.00"]
                            ]
                        ]
                    ]
                ]
            ]
            # score block -> paths:
            #   score at [6,0,2,1,1] (expects 4.5)
            #   score_text at [6,0,2,1,0] (expects "4.5")
            score_block = [[None, None, [None, ["4.5", 4.5]]]]
            # summary at [4,1,1,1,1]
            item[1] = icon_path
            item[2] = title
            item[4] = [dev_block, [None, [None, [None, title + " summary"]]]]
            item[6] = score_block
            item[7] = price_block
            if app_id is not None:
                item[12] = [app_id]
            return item

        item1 = make_item("com.example.one", "One")
        item2 = make_item("com.example.two", "Two")
        item3 = make_item(None, "NoID")  # should be skipped
        items = [item1, item2, item3]

        ds1 = [["x", [[[items]]]]]
        mock_parse.return_value = {"ds:1": ds1}

        results = self.client.search("query", num=2)

        # Only first 2 items returned, and item without app_id skipped
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].app_id, "com.example.one")
        self.assertEqual(results[0].title, "One")
        self.assertEqual(results[0].developer, "One Dev")
        self.assertEqual(results[0].developer_id, "DEV_ID")
        self.assertEqual(results[0].score, 4.5)
        self.assertEqual(results[0].score_text, "4.5")
        self.assertEqual(results[0].price_text, "$0.00")
        self.assertTrue(results[0].free)
        self.assertEqual(results[0].summary, "One summary")

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get")
    def test_missing_ds1_returns_empty(self, mock_get, mock_parse):
        mock_get.return_value = "<html>dummy</html>"
        mock_parse.return_value = {"ds:5": []}
        self.assertEqual(self.client.search("q"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get")
    def test_indexing_error_returns_empty(self, mock_get, mock_parse):
        mock_get.return_value = "<html>dummy</html>"
        # Structure present but too shallow to reach items -> triggers IndexError
        mock_parse.return_value = {"ds:1": [[]]}
        self.assertEqual(self.client.search("q"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get")
    def test_items_none_or_empty_returns_empty(self, mock_get, mock_parse):
        mock_get.return_value = "<html>dummy</html>"

        # items is None
        mock_parse.return_value = {"ds:1": [["x", [[[None]]]]]}
        self.assertEqual(self.client.search("q"), [])

        # items is []
        mock_parse.return_value = {"ds:1": [["x", [[[[]]]]]]}
        self.assertEqual(self.client.search("q"), [])


if __name__ == "__main__":
    unittest.main()
