import json
import unittest
from datetime import datetime
from unittest.mock import patch

from google_play_scraper.client import GooglePlayClient
from google_play_scraper.constants import Sort


class ClientReviewsTest(unittest.TestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_request_formation(self, mock_post, mock_parse):
        # Minimal parsed response to let the method proceed and return empty
        mock_parse.return_value = [[], None]

        app_id = "com.example.app"
        lang = "en"
        country = "us"
        sort = Sort.HELPFULNESS
        num = 25
        token = "pagetok"

        self.client.reviews(app_id=app_id, lang=lang, country=country, sort=sort, num=num, pagination_token=token)

        # Verify POST called to the correct endpoint with proper rpc id and parameters
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["params"]["rpcids"], "UsvDTd")
        self.assertEqual(kwargs["params"]["hl"], lang)
        self.assertEqual(kwargs["params"]["gl"], country)

        # Verify f.req JSON envelope and inner JSON structure
        form = kwargs["data"]
        self.assertIn("f.req", form)
        outer = json.loads(form["f.req"])  # [[[rpc_id, inner_json, None, "generic"]]]
        self.assertIsInstance(outer, list)
        self.assertEqual(outer[0][0][0], "UsvDTd")

        inner_json = outer[0][0][1]
        inner = json.loads(inner_json)
        # Expected: [None, None, [2, int(sort), [num, None, pagination_token], None, []], [app_id, 7]]
        self.assertEqual(inner[3][0], app_id)
        self.assertEqual(inner[3][1], 7)
        self.assertEqual(inner[2][0], 2)
        self.assertEqual(inner[2][1], int(sort))
        self.assertEqual(inner[2][2][0], num)
        self.assertIsNone(inner[2][2][1])
        self.assertEqual(inner[2][2][2], token)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_happy_path_mapping_and_token_and_skip_missing_id(self, mock_post, mock_parse):
        mock_post.return_value = "OK"

        # Build one full review and one missing id (should be skipped)
        ts = int(datetime(2023, 1, 2, 3, 4, 5).timestamp())
        reply_ts = int(datetime(2023, 2, 3, 4, 5, 6).timestamp())

        def make_review(rid: str | None):
            r = [None] * 11
            r[0] = rid
            # user_name at [1,0], user_image at [1,1,3,2]
            r[1] = [
                "Alice",
                [None, None, None, [None, None, "https://img.test/user.png"]],
            ]
            r[2] = 5  # score
            r[4] = "Great app!"
            r[5] = [ts]
            r[6] = 42  # thumbs_up
            r[7] = [None, "Thanks!", [reply_ts]]
            r[10] = "1.2.3"
            return r

        reviews_root = [make_review("RID_1"), make_review(None)]
        token_info = [None, "NEXT_TOKEN"]
        mock_parse.return_value = [reviews_root, token_info]

        reviews, token = self.client.reviews(app_id="com.example")

        self.assertEqual(token, "NEXT_TOKEN")
        self.assertEqual(len(reviews), 1)
        r = reviews[0]
        self.assertEqual(r.id, "RID_1")
        self.assertEqual(r.user_name, "Alice")
        self.assertEqual(str(r.user_image), "https://img.test/user.png")
        self.assertEqual(r.score, 5)
        self.assertEqual(r.text, "Great app!")
        self.assertEqual(r.date, datetime.fromtimestamp(ts))
        self.assertEqual(r.reply_text, "Thanks!")
        self.assertEqual(r.reply_date, datetime.fromtimestamp(reply_ts))
        self.assertEqual(r.thumbs_up, 42)
        self.assertEqual(r.version, "1.2.3")

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_edge_empty_parsed_data(self, mock_post, mock_parse):
        mock_parse.return_value = []
        reviews, token = self.client.reviews(app_id="com.example")
        self.assertEqual(reviews, [])
        self.assertIsNone(token)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_edge_indexing_or_type_errors(self, mock_post, mock_parse):
        # Not enough elements, or wrong types, should be caught and return ([], None)
        for bad in ([None], [{}], ["x"], [1]):
            mock_parse.return_value = bad
            reviews, token = self.client.reviews(app_id="com.example")
            self.assertEqual(reviews, [])
            self.assertIsNone(token)

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.Requester.post")
    def test_edge_falsy_reviews_root(self, mock_post, mock_parse):
        # reviews_root is None
        mock_parse.return_value = [None, None]
        reviews, token = self.client.reviews(app_id="com.example")
        self.assertEqual(reviews, [])
        self.assertIsNone(token)

        # reviews_root is []
        mock_parse.return_value = [[], [None, "T"]]
        reviews, token = self.client.reviews(app_id="com.example")
        self.assertEqual(reviews, [])
        self.assertIsNone(token)


if __name__ == "__main__":
    unittest.main()
