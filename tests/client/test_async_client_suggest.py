import json
import unittest
from unittest.mock import patch, AsyncMock

from google_play_scraper.client import GooglePlayClient


class TestAsyncClientSuggest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[[], None],
    )
    @patch("google_play_scraper.client.AsyncRequester.post", new_callable=AsyncMock)
    async def test_request_formation(self, mock_post, mock_parse):
        term = "maps"
        lang = "en"
        country = "us"

        await self.client.asuggest(term=term, lang=lang, country=country)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "/_/PlayStoreUi/data/batchexecute")

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

        form = kwargs["data"]
        self.assertIn("f.req", form)
        outer = json.loads(form["f.req"])
        self.assertIsInstance(outer, list)
        self.assertEqual(outer[0][0][0], "IJ4APc")

        inner_json = outer[0][0][1]
        inner = json.loads(inner_json)
        self.assertEqual(inner, [[None, [term], [10], [2], 4]])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_happy_path_maps_items_and_skips_none(self, mock_post, mock_parse):
        suggestion_list = [["alpha"], None, ["beta", "extra"]]
        mock_parse.return_value = [[suggestion_list]]

        out = await self.client.asuggest("al")
        self.assertEqual(out, ["alpha", "beta"])

    async def test_empty_term_raises_value_error(self):
        with self.assertRaises(ValueError):
            await self.client.asuggest("")

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_empty_or_none_parsed_data_returns_empty(
        self, mock_post, mock_parse
    ):
        for parsed_data in [[], None]:
            with self.subTest(parsed_data=parsed_data):
                mock_parse.return_value = parsed_data
                self.assertEqual(await self.client.asuggest("m"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_falsy_suggestion_list_returns_empty(self, mock_post, mock_parse):
        for suggestion_list in [None, []]:
            with self.subTest(suggestion_list=suggestion_list):
                mock_parse.return_value = [[suggestion_list]]
                self.assertEqual(await self.client.asuggest("ma"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_index_or_type_errors_return_empty(self, mock_post, mock_parse):
        for bad_data in [None, 1, [1], [[1]], [[()]]]:
            with self.subTest(bad_data=bad_data):
                mock_parse.return_value = bad_data
                self.assertEqual(await self.client.asuggest("q"), [])
