import unittest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from google_play_scraper.client import GooglePlayClient
from google_play_scraper.exceptions import AppNotFound


def build_nested(root, path, value):
    cur = root
    for idx, key in enumerate(path):
        while len(cur) <= key:
            cur.append(None)
        if idx == len(path) - 1:
            cur[key] = value
        else:
            if cur[key] is None:
                cur[key] = []
            cur = cur[key]


def make_root_for_happy_path():
    root = []
    build_nested(root, [0, 0], "My App")
    build_nested(root, [72, 0, 1], "Line1<br>Line2")
    build_nested(root, [73, 0, 1], "A short summary")
    build_nested(root, [13, 0], "1,000+")
    build_nested(root, [13, 1], 1000)
    build_nested(root, [13, 2], 5000)
    build_nested(root, [51, 0, 0], "4.5")
    build_nested(root, [51, 0, 1], 4.5)
    build_nested(root, [51, 2, 1], 1234)
    build_nested(root, [51, 3, 1], 321)
    histogram = [None, ["1", 1], ["2", 2], ["3", 3], ["4", 4], ["5", 5]]
    build_nested(root, [51, 1], histogram)
    build_nested(root, [57, 0, 0, 0, 0, 1, 0, 0], 1_990_000)
    build_nested(root, [57, 0, 0, 0, 0, 1, 0, 1], "USD")
    build_nested(root, [57, 0, 0, 0, 0, 1, 0, 2], "$1.99")
    build_nested(root, [18, 0], 1)
    build_nested(root, [19, 0], 0)
    build_nested(root, [140, 1, 1, 0, 0, 1], "7.0")
    build_nested(root, [140, 0, 0, 0], "1.0.0")
    build_nested(root, [68, 0], "ACME")
    build_nested(
        root, [68, 1, 4, 2], "https://play.google.com/store/apps/dev?id=ACME_INC"
    )
    build_nested(root, [69, 1, 0], "dev@acme.test")
    build_nested(root, [69, 0, 5, 2], "https://acme.test")
    build_nested(root, [69, 2, 0], "ACME Street 1")
    build_nested(root, [99, 0, 5, 2], "https://acme.test/privacy")
    build_nested(root, [79, 0, 0, 0], "Tools")
    build_nested(root, [79, 0, 0, 2], "TOOLS")
    build_nested(root, [95, 0, 3, 2], "https://img.test/icon.png")
    build_nested(root, [96, 0, 3, 2], "https://img.test/header.png")
    build_nested(
        root, [78, 0], [[None, None, None, [None, None, "https://img.test/shot1.png"]]]
    )
    build_nested(root, [100, 0, 0, 3, 2], "https://video.test/v.mp4")
    build_nested(root, [9, 0], "Everyone")
    build_nested(root, [10, 0], "2020-01-01")
    build_nested(root, [145, 0, 1, 0], 1_600_000_000)
    build_nested(root, [144, 1, 1], "Bug fixes")
    return root


def ds5_with_root(root):
    return [None, [None, None, root]]


class TestAsyncClientApp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.AsyncRequester.get", new_callable=AsyncMock)
    async def test_happy_path_extracts_and_transforms(self, mock_get, mock_parse):
        app_id = "com.example.app"
        html = "<html>dummy</html>"
        mock_get.return_value = html

        root = make_root_for_happy_path()
        ds5 = ds5_with_root(root)
        mock_parse.return_value = {"ds:5": ds5}

        details = await self.client.aapp(app_id)

        self.assertEqual(details.app_id, app_id)
        self.assertEqual(details.title, "My App")
        self.assertEqual(details.summary, "A short summary")
        self.assertEqual(str(details.icon), "https://img.test/icon.png")
        self.assertEqual(str(details.header_image), "https://img.test/header.png")
        self.assertEqual([str(u) for u in details.screenshots], ["https://img.test/shot1.png"])
        self.assertEqual(details.description_html, "Line1<br>Line2")
        self.assertEqual(details.description, "Line1\r\nLine2")
        self.assertEqual(details.score_text, "4.5")
        self.assertEqual(details.score, 4.5)
        self.assertEqual(details.ratings, 1234)
        self.assertEqual(details.reviews, 321)
        self.assertEqual(details.histogram, {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5})
        self.assertEqual(details.price, 1.99)
        self.assertEqual(details.currency, "USD")
        self.assertEqual(details.price_text, "$1.99")
        self.assertFalse(details.free)
        self.assertTrue(details.available)
        self.assertFalse(details.offers_iap)
        self.assertEqual(details.developer, "ACME")
        self.assertEqual(details.developer_id, "ACME_INC")
        self.assertEqual(details.developer_email, "dev@acme.test")
        self.assertEqual(str(details.developer_website), "https://acme.test/")
        self.assertEqual(details.developer_address, "ACME Street 1")
        self.assertEqual(str(details.privacy_policy), "https://acme.test/privacy")
        self.assertEqual(details.genre, "Tools")
        self.assertEqual(details.genre_id, "TOOLS")
        self.assertEqual(details.released, "2020-01-01")
        self.assertIsInstance(details.updated, datetime)
        self.assertEqual(details.updated, datetime.fromtimestamp(1_600_000_000))
        self.assertEqual(details.version, "1.0.0")
        self.assertEqual(details.recent_changes, "Bug fixes")

        mock_get.assert_called_once()
        called_args, called_kwargs = mock_get.call_args
        self.assertEqual(called_args[0], "/store/apps/details")
        self.assertIn("params", called_kwargs)
        self.assertEqual(called_kwargs["params"]["id"], app_id)

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.AsyncRequester.get", new_callable=AsyncMock)
    async def test_description_fallback_is_used(self, mock_get, mock_parse):
        app_id = "com.example.app"
        mock_get.return_value = "<html>dummy</html>"

        root = []
        build_nested(root, [12, 0, 0, 1], "Fallback<br>Desc")
        build_nested(root, [0, 0], "My App")
        build_nested(
            root, [51, 1], [None, ["1", 0], ["2", 0], ["3", 0], ["4", 0], ["5", 0]]
        )
        build_nested(root, [13, 0], "0")
        build_nested(root, [18, 0], 1)
        build_nested(root, [19, 0], 0)
        build_nested(root, [140, 1, 1, 0, 0, 1], "VARY")
        build_nested(root, [78, 0], [])

        ds5 = ds5_with_root(root)
        mock_parse.return_value = {"ds:5": ds5}

        details = await self.client.aapp(app_id)

        self.assertEqual(details.description_html, "Fallback<br>Desc")
        self.assertEqual(details.description, "Fallback\r\nDesc")

    @patch("google_play_scraper.client.ScriptDataParser.parse", return_value={})
    @patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_missing_ds5_raises_app_not_found(self, mock_get, mock_parse):
        with self.assertRaises(AppNotFound):
            await self.client.aapp("com.missing.app")

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse",
        return_value={"ds:5": [None, None]},
    )
    @patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_malformed_ds5_raises_app_not_found(self, mock_get, mock_parse):
        with self.assertRaises(AppNotFound):
            await self.client.aapp("com.example.app")

    async def test_empty_app_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            await self.client.aapp("")
