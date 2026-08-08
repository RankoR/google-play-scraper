import unittest
from unittest.mock import Mock, patch

from google_play_scraper.client import GooglePlayClient
from tests.fixtures import make_app_entry, make_search_page


class ClientSearchTest(unittest.TestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch("google_play_scraper.client.ScriptDataParser.parse", return_value={})
    @patch("google_play_scraper.client.Requester.get")
    def test_hits_store_search_with_apps_filter(self, mock_get, _mock_parse):
        self.client.search("maps", lang="en", country="us")

        (path,), kwargs = mock_get.call_args
        self.assertEqual(path, "/store/search")
        self.assertEqual(kwargs["params"]["c"], "apps")
        self.assertEqual(kwargs["params"]["q"], "maps")
        self.assertEqual(kwargs["params"]["hl"], "en")
        self.assertEqual(kwargs["params"]["gl"], "us")

    @patch("google_play_scraper.client.ScriptDataParser.parse", return_value={})
    @patch("google_play_scraper.client.Requester.get")
    def test_price_param_mapping(self, mock_get, _mock_parse):
        for price, expected in [("free", 1), ("paid", 2), ("all", 0), ("unknown", 0)]:
            with self.subTest(price=price):
                self.client.search("maps", price=price)
                _, kwargs = mock_get.call_args
                self.assertEqual(kwargs["params"]["price"], expected)

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get", return_value="<html></html>")
    def test_happy_path_limits_num_and_skips_missing_app_id(self, _mock_get, mock_parse):
        entries = [
            make_app_entry("com.example.one", "One"),
            make_app_entry("com.example.two", "Two", 1990000, "$1.99"),
            make_app_entry(None, "NoID"),
        ]
        mock_parse.return_value = make_search_page(entries)

        results = self.client.search("query", num=2)

        self.assertEqual(len(results), 2)
        first, second = results
        self.assertEqual(first.app_id, "com.example.one")
        self.assertEqual(first.title, "One")
        self.assertEqual(str(first.icon), "https://img.test/icon.png")
        self.assertEqual(first.developer, "One Dev")
        self.assertEqual(first.score, 4.5)
        self.assertEqual(first.score_text, "4.5")
        self.assertTrue(first.free)
        self.assertEqual(first.summary, "One summary")
        self.assertFalse(second.free)
        self.assertEqual(second.price_text, "$1.99")

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get", return_value="<html></html>")
    def test_finds_cluster_at_alternate_depth(self, _mock_get, mock_parse):
        # Play nests the cluster one level deeper for some locales.
        entries = [make_app_entry("com.example.one", "One")]
        mock_parse.return_value = make_search_page(entries, depth_index=1)

        results = self.client.search("query")

        self.assertEqual([r.app_id for r in results], ["com.example.one"])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.get", return_value="<html></html>")
    def test_returns_empty_when_no_cluster_present(self, _mock_get, mock_parse):
        for payload in [{}, {"ds:4": []}, {"ds:4": [[None, [[None] * 23]]]}, {"ds:5": [1, "x"]}]:
            with self.subTest(payload=payload):
                mock_parse.return_value = payload
                self.assertEqual(self.client.search("q"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    def test_search_uses_client_default_locale(self, mock_parse):
        mock_parse.return_value = make_search_page(
            [make_app_entry("com.example.one", "One")]
        )

        response = Mock()
        response.raise_for_status.return_value = None
        response.text = "<html></html>"

        client = GooglePlayClient(country="br", lang="pt")
        client._requester._session = Mock()
        client._requester._session.request.return_value = response

        self.assertEqual(len(client.search("query")), 1)

        params = client._requester._session.request.call_args.kwargs["params"]
        self.assertEqual(params["hl"], "pt")
        self.assertEqual(params["gl"], "br")


if __name__ == "__main__":
    unittest.main()
