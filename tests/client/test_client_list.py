import unittest
from unittest.mock import patch

from google_play_scraper.client import GooglePlayClient


class ClientListTest(unittest.TestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_request_formation_and_optional_age(self, mock_post, mock_parse):
        # Return empty parsed data to finish early
        mock_post.return_value = "OK"
        mock_parse.return_value = []

        res = self.client.list(
            collection="collX",
            category="catY",
            age="AGE_PARAM",
            num=7,
            lang="en",
            country="us",
        )

        self.assertEqual(res, [])

        # Verify Requester.post call shape
        (url,), kwargs = mock_post.call_args
        self.assertEqual(url, "/_/PlayStoreUi/data/batchexecute")

        # headers include the explicit Content-Type
        self.assertIn("headers", kwargs)
        self.assertEqual(
            kwargs["headers"].get("Content-Type"),
            "application/x-www-form-urlencoded;charset=UTF-8",
        )

        # params include rpcids and passthrough of lang/country and optional age
        params = kwargs.get("params")
        self.assertIsInstance(params, dict)
        self.assertEqual(params.get("rpcids"), "vyAe2")
        self.assertEqual(params.get("hl"), "en")
        self.assertEqual(params.get("gl"), "us")
        self.assertEqual(params.get("age"), "AGE_PARAM")

        # payload is a string; optionally ensure our provided values are present
        data = kwargs.get("data")
        self.assertIsInstance(data, str)
        self.assertIn("collX", data)
        self.assertIn("catY", data)
        self.assertIn("7", data)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_happy_path_extracts_app_overview_fields(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        # Build two app entries according to specs paths
        def make_app(app_id: str, title: str, price_micro: int, currency: str, free_expected: bool):
            app = [None] * 15
            # app_id at [0,0,0] -> inner[0] must be [app_id]
            app[0] = [app_id]
            # title at [0,3]
            app[3] = title
            # score_text and score at [0,4,0/1]
            app[4] = ["4.5", 4.5]
            # icon at [0,1,3,2]
            app[1] = [None, None, None, [None, None, "https://img.test/icon.png"]]
            # url path at [0,10,4,2] (joined with Requester.BASE_URL)
            app[10] = [None] * 5
            app[10][4] = [None, None, f"/store/apps/details?id={app_id}"]
            # developer and developer_id at [0,14]
            app[14] = f"{title} Dev"
            # currency and price at [0,8,1,0,1] and [0,8,1,0,0]
            app[8] = [None, [[price_micro, currency]]]
            # summary at [0,13,1]
            app[13] = [None, f"{title} summary"]
            return app, free_expected

        app1, free1 = make_app("com.example.one", "One", 0, "USD", True)
        app2, free2 = make_app("com.example.two", "Two", 1990000, "USD", False)

        # Each app_raw element should be [inner]
        apps_list = [[app1], [app2]]

        arr_with_29 = [None] * 29
        arr_with_29[28] = [apps_list]  # [28][0] -> apps_list

        # Make data so that data[0][1][0][28][0] == apps_list
        data = [[None, [arr_with_29]]]

        mock_parse.return_value = data

        results = self.client.list(num=5)

        self.assertEqual(len(results), 2)

        r1, r2 = results
        # First app
        self.assertEqual(r1.app_id, "com.example.one")
        self.assertEqual(r1.title, "One")
        self.assertEqual(str(r1.icon), "https://img.test/icon.png")
        self.assertEqual(r1.developer, "One Dev")
        self.assertEqual(r1.developer_id, "One Dev")
        self.assertTrue(r1.free)
        self.assertEqual(r1.summary, "One summary")
        self.assertEqual(r1.score_text, "4.5")
        self.assertEqual(r1.score, 4.5)

        # Second app
        self.assertEqual(r2.app_id, "com.example.two")
        self.assertEqual(r2.title, "Two")
        self.assertFalse(r2.free)
        self.assertEqual(r2.summary, "Two summary")

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_parsed_data_empty_returns_empty(self, mock_post, mock_parse):
        mock_post.return_value = "OK"
        mock_parse.return_value = []
        self.assertEqual(self.client.list(), [])

    @patch("google_play_scraper.client.ElementSpec.extract", side_effect=Exception("boom"))
    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_extract_exception_returns_empty(self, mock_post, mock_parse, _mock_extract):
        mock_post.return_value = "OK"
        # Any non-empty value to reach the extract call
        mock_parse.return_value = [1]
        self.assertEqual(self.client.list(), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_apps_root_falsy_returns_empty(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        # Construct data where [0,1,0,28,0] exists but is empty list -> falsy
        arr_with_29 = [None] * 29
        arr_with_29[28] = [[]]
        data = [[None, [arr_with_29]]]
        mock_parse.return_value = data

        self.assertEqual(self.client.list(), [])


if __name__ == "__main__":
    unittest.main()
