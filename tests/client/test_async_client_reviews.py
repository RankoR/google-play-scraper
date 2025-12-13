import json
import unittest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from google_play_scraper.client import GooglePlayClient
from google_play_scraper.constants import Sort


def make_review(rid: str | None):
    ts = int(datetime(2023, 1, 2, 3, 4, 5).timestamp())
    reply_ts = int(datetime(2023, 2, 3, 4, 5, 6).timestamp())
    r = [None] * 11
    r[0] = rid
    r[1] = ["Alice", [None, None, None, [None, None, "https://img.test/user.png"]]]
    r[2] = 5
    r[4] = "Great app!"
    r[5] = [ts]
    r[6] = 42
    r[7] = [None, "Thanks!", [reply_ts]]
    r[10] = "1.2.3"
    return r


class TestAsyncClientReviews(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[[], None],
    )
    @patch("google_play_scraper.client.Requester.apost", new_callable=AsyncMock)
    async def test_request_formation(self, mock_apost, mock_parse):
        app_id = "com.example.app"
        lang = "en"
        country = "us"
        sort = Sort.HELPFULNESS
        num = 25
        token = "pagetok"

        await self.client.areviews(
            app_id=app_id,
            lang=lang,
            country=country,
            sort=sort,
            num=num,
            pagination_token=token,
        )

        mock_apost.assert_called_once()
        _, kwargs = mock_apost.call_args
        self.assertEqual(kwargs["params"]["rpcids"], "UsvDTd")
        self.assertEqual(kwargs["params"]["hl"], lang)
        self.assertEqual(kwargs["params"]["gl"], country)

        form = kwargs["data"]
        self.assertIn("f.req", form)
        outer = json.loads(form["f.req"])
        self.assertIsInstance(outer, list)
        self.assertEqual(outer[0][0][0], "UsvDTd")

        inner_json = outer[0][0][1]
        inner = json.loads(inner_json)
        self.assertEqual(inner[3][0], app_id)
        self.assertEqual(inner[3][1], 7)
        self.assertEqual(inner[2][0], 2)
        self.assertEqual(inner[2][1], int(sort))
        self.assertEqual(inner[2][2][0], num)
        self.assertIsNone(inner[2][2][1])
        self.assertEqual(inner[2][2][2], token)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch(
        "google_play_scraper.client.Requester.apost",
        new_callable=AsyncMock,
        return_value="OK",
    )
    async def test_happy_path_mapping_and_token_and_skip_missing_id(
        self, mock_apost, mock_parse
    ):
        reviews_root = [make_review("RID_1"), make_review(None)]
        token_info = [None, "NEXT_TOKEN"]
        mock_parse.return_value = [reviews_root, token_info]

        reviews, token = await self.client.areviews(app_id="com.example")

        self.assertEqual(token, "NEXT_TOKEN")
        self.assertEqual(len(reviews), 1)
        r = reviews[0]
        self.assertEqual(r.id, "RID_1")
        self.assertEqual(r.user_name, "Alice")
        self.assertEqual(str(r.user_image), "https://img.test/user.png")
        self.assertEqual(r.score, 5)
        self.assertEqual(r.text, "Great app!")
        self.assertEqual(r.date, datetime(2023, 1, 2, 3, 4, 5))
        self.assertEqual(r.reply_text, "Thanks!")
        self.assertEqual(r.reply_date, datetime(2023, 2, 3, 4, 5, 6))
        self.assertEqual(r.thumbs_up, 42)
        self.assertEqual(r.version, "1.2.3")

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[],
    )
    async def test_edge_empty_parsed_data(self, mock_parse):
        reviews, token = await self.client.areviews(app_id="com.example")
        self.assertEqual(reviews, [])
        self.assertIsNone(token)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    async def test_edge_indexing_or_type_errors(self, mock_parse):
        for bad_data in [[None], [{}], ["x"], [1]]:
            with self.subTest(bad_data=bad_data):
                mock_parse.return_value = bad_data
                reviews, token = await self.client.areviews(app_id="com.example")
                self.assertEqual(reviews, [])
                self.assertIsNone(token)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    async def test_edge_falsy_reviews_root(self, mock_parse):
        for reviews_root in [None, []]:
            with self.subTest(reviews_root=reviews_root):
                mock_parse.return_value = [reviews_root, [None, "T"]]
                reviews, token = await self.client.areviews(app_id="com.example")
                self.assertEqual(reviews, [])
                self.assertIsNone(token)
