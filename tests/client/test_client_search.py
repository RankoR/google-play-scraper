import unittest
from unittest.mock import patch

from google_play_scraper.client import GooglePlayClient


def make_item(app_id: str | None, title: str):
    item = [None] * 13
    icon_path = [None, [[None, [None, None, "https://img.test/icon.png"]]]]
    dev_block = [[
        title + " Dev",
        [None, None, None, None, [None, None, "https://play.google.com/store/apps/dev?id=DEV_ID"]],
    ]]
    price_block = [[None, None, None, [None, None, [None, [[0, None, "$0.00"]]]]]]
    score_block = [[None, None, [None, ["4.5", 4.5]]]]
    item[1] = icon_path
    item[2] = title
    item[4] = [dev_block, [None, [None, [None, title + " summary"]]]]
    item[6] = score_block
    item[7] = price_block
    if app_id is not None:
        item[12] = [app_id]
    return item


def make_initial_search_page(items, token: str | None = None):
    sections = [items]
    if token:
        sections.append([None, token])
    return {"ds:1": [["x", [[sections]]]]}


def make_paginated_search_page(items, token: str | None = None):
    token_section = [None, token] if token else None
    return [[[items, None, None, None, None, None, None, token_section]]]


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

        item1 = make_item("com.example.one", "One")
        item2 = make_item("com.example.two", "Two")
        item3 = make_item(None, "NoID")  # should be skipped
        items = [item1, item2, item3]

        mock_parse.return_value = make_initial_search_page(items)

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

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.post")
    @patch("google_play_scraper.client.Requester.get")
    def test_paginates_until_num_is_satisfied(
        self, mock_get, mock_post, mock_parse, mock_parse_batchexecute
    ):
        first_page_items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50)]
        second_page_items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50, 70)]

        mock_get.return_value = "<html>dummy</html>"
        mock_post.return_value = "batchexecute"
        mock_parse.return_value = make_initial_search_page(first_page_items, token="TOKEN_1")
        mock_parse_batchexecute.return_value = make_paginated_search_page(second_page_items)

        results = self.client.search("query", num=60)

        self.assertEqual(len(results), 60)
        self.assertEqual(results[0].app_id, "com.example.0")
        self.assertEqual(results[-1].app_id, "com.example.59")
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["params"]["rpcids"], "qnKhOb")
        self.assertIn("TOKEN_1", kwargs["data"]["f.req"])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.post")
    @patch("google_play_scraper.client.Requester.get")
    def test_does_not_paginate_when_first_page_already_satisfies_num(
        self, mock_get, mock_post, mock_parse, mock_parse_batchexecute
    ):
        items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50)]

        mock_get.return_value = "<html>dummy</html>"
        mock_parse.return_value = make_initial_search_page(items, token="TOKEN_1")

        results = self.client.search("query", num=20)

        self.assertEqual(len(results), 20)
        mock_post.assert_not_called()
        mock_parse_batchexecute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
