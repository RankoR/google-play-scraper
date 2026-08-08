import unittest
from unittest.mock import AsyncMock, Mock, patch

from google_play_scraper.client import GooglePlayClient
from tests.fixtures import make_app_entry, make_search_page


class TestAsyncClientSearch(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse", return_value={})
    @patch("google_play_scraper.client.Requester.aget", new_callable=AsyncMock)
    async def test_hits_store_search_with_apps_filter(self, mock_aget, _mock_parse):
        await self.client.asearch("maps", lang="en", country="us")

        (path,), kwargs = mock_aget.call_args
        self.assertEqual(path, "/store/search")
        self.assertEqual(kwargs["params"]["c"], "apps")
        self.assertEqual(kwargs["params"]["q"], "maps")
        self.assertEqual(kwargs["params"]["hl"], "en")
        self.assertEqual(kwargs["params"]["gl"], "us")

    @patch("google_play_scraper.client.ScriptDataParser.parse", return_value={})
    @patch("google_play_scraper.client.Requester.aget", new_callable=AsyncMock)
    async def test_price_param_mapping(self, mock_aget, _mock_parse):
        for price, expected in [("free", 1), ("paid", 2), ("all", 0), ("unknown", 0)]:
            with self.subTest(price=price):
                await self.client.asearch("maps", price=price)
                _, kwargs = mock_aget.call_args
                self.assertEqual(kwargs["params"]["price"], expected)

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html></html>",
    )
    async def test_happy_path_limits_num_and_skips_missing_app_id(
        self, _mock_aget, mock_parse
    ):
        entries = [
            make_app_entry("com.example.one", "One"),
            make_app_entry("com.example.two", "Two", 1990000, "$1.99"),
            make_app_entry(None, "NoID"),
        ]
        mock_parse.return_value = make_search_page(entries)

        results = await self.client.asearch("query", num=2)

        self.assertEqual([r.app_id for r in results], ["com.example.one", "com.example.two"])
        self.assertTrue(results[0].free)
        self.assertEqual(results[1].price_text, "$1.99")

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html></html>",
    )
    async def test_finds_cluster_at_alternate_depth(self, _mock_aget, mock_parse):
        mock_parse.return_value = make_search_page(
            [make_app_entry("com.example.one", "One")], depth_index=1
        )

        results = await self.client.asearch("query")

        self.assertEqual([r.app_id for r in results], ["com.example.one"])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html></html>",
    )
    async def test_returns_empty_when_no_cluster_present(self, _mock_aget, mock_parse):
        for payload in [{}, {"ds:4": []}, {"ds:4": [[None, [[None] * 23]]]}]:
            with self.subTest(payload=payload):
                mock_parse.return_value = payload
                self.assertEqual(await self.client.asearch("q"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    async def test_asearch_uses_client_default_locale(self, mock_parse):
        mock_parse.return_value = make_search_page(
            [make_app_entry("com.example.one", "One")]
        )

        response = Mock()
        response.raise_for_status.return_value = None
        response.text = "<html></html>"

        client = GooglePlayClient(country="br", lang="pt")
        client._requester._async_session = AsyncMock()
        client._requester._async_session.request.return_value = response

        self.assertEqual(len(await client.asearch("query")), 1)

        params = client._requester._async_session.request.call_args.kwargs["params"]
        self.assertEqual(params["hl"], "pt")
        self.assertEqual(params["gl"], "br")


if __name__ == "__main__":
    unittest.main()
