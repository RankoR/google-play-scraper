import unittest
from unittest.mock import patch, AsyncMock

from google_play_scraper.client import GooglePlayClient


def make_app(app_id: str, title: str, price_micro: int, currency: str):
    app = [None] * 15
    app[0] = [app_id]
    app[3] = title
    app[4] = ["4.5", 4.5]
    app[1] = [None, None, None, [None, None, "https://img.test/icon.png"]]
    app[10] = [None] * 5
    app[10][4] = [None, None, f"/store/apps/details?id={app_id}"]
    app[14] = f"{title} Dev"
    app[8] = [None, [[price_micro, currency]]]
    app[13] = [None, f"{title} summary"]
    return app


class TestAsyncClientList(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[],
    )
    @patch("google_play_scraper.client.Requester.apost", new_callable=AsyncMock)
    async def test_request_formation_and_optional_age(self, mock_apost, mock_parse):
        res = await self.client.alist(
            collection="collX",
            category="catY",
            age="AGE_PARAM",
            num=7,
            lang="en",
            country="us",
        )

        self.assertEqual(res, [])

        args, kwargs = mock_apost.call_args
        # Patched method is called with the path as the first positional arg.
        self.assertEqual(args[0], "/_/PlayStoreUi/data/batchexecute")
        self.assertIn("headers", kwargs)
        self.assertEqual(
            kwargs["headers"].get("Content-Type"),
            "application/x-www-form-urlencoded;charset=UTF-8",
        )

        params = kwargs.get("params")
        self.assertIsInstance(params, dict)
        self.assertEqual(params.get("rpcids"), "vyAe2")
        self.assertEqual(params.get("hl"), "en")
        self.assertEqual(params.get("gl"), "us")
        self.assertEqual(params.get("age"), "AGE_PARAM")

        data = kwargs.get("data")
        self.assertIsInstance(data, str)
        self.assertIn("collX", data)
        self.assertIn("catY", data)
        self.assertIn("7", data)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.Requester.apost",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_happy_path_extracts_app_overview_fields(self, mock_apost, mock_parse):
        app1 = make_app("com.example.one", "One", 0, "USD")
        app2 = make_app("com.example.two", "Two", 1990000, "USD")
        apps_list = [[app1], [app2]]
        arr_with_29 = [None] * 29
        arr_with_29[28] = [apps_list]
        data = [[None, [arr_with_29]]]
        mock_parse.return_value = data

        results = await self.client.alist(num=5)

        self.assertEqual(len(results), 2)
        r1, r2 = results
        self.assertEqual(r1.app_id, "com.example.one")
        self.assertEqual(r1.title, "One")
        self.assertEqual(str(r1.icon), "https://img.test/icon.png")
        self.assertEqual(r1.developer, "One Dev")
        self.assertEqual(r1.developer_id, "One Dev")
        self.assertTrue(r1.free)
        self.assertEqual(r1.summary, "One summary")
        self.assertEqual(r1.score_text, "4.5")
        self.assertEqual(r1.score, 4.5)
        self.assertEqual(r2.app_id, "com.example.two")
        self.assertEqual(r2.title, "Two")
        self.assertFalse(r2.free)
        self.assertEqual(r2.summary, "Two summary")

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[],
    )
    @patch(
        "google_play_scraper.client.Requester.apost",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_parsed_data_empty_returns_empty(self, mock_apost, mock_parse):
        self.assertEqual(await self.client.alist(), [])

    @patch(
        "google_play_scraper.client.ElementSpec.extract", side_effect=Exception("boom")
    )
    @patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[1],
    )
    @patch(
        "google_play_scraper.client.Requester.apost",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_extract_exception_returns_empty(
        self, mock_apost, mock_parse, mock_extract
    ):
        self.assertEqual(await self.client.alist(), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.Requester.apost",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_apps_root_falsy_returns_empty(self, mock_apost, mock_parse):
        arr_with_29 = [None] * 29
        arr_with_29[28] = [[]]
        data = [[None, [arr_with_29]]]
        mock_parse.return_value = data

        self.assertEqual(await self.client.alist(), [])
