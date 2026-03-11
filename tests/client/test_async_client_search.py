import unittest
from unittest.mock import patch, AsyncMock, Mock

from google_play_scraper.client import GooglePlayClient


def make_item(app_id: str | None, title: str):
    item = [None] * 13
    icon_path = [None, [[None, [None, None, "https://img.test/icon.png"]]]]
    dev_block = [
        [
            title + " Dev",
            [
                None,
                None,
                None,
                None,
                [None, None, "https://play.google.com/store/apps/dev?id=DEV_ID"],
            ],
        ]
    ]
    price_block = [
        [
            None,
            None,
            None,
            [None, None, [None, [[0, None, "$0.00"]]]],
        ]
    ]
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


class TestAsyncClientSearch(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = GooglePlayClient()

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse",
        return_value={"ds:1": [["x", [[[[]]]]]]},
    )
    @patch("google_play_scraper.client.Requester.aget", new_callable=AsyncMock)
    async def test_price_param_mapping(self, mock_aget, mock_parse):
        for price_str, expected_val in [
            ("free", 1),
            ("paid", 2),
            ("all", 0),
            ("unknown", 0),
        ]:
            with self.subTest(price_str=price_str):
                await self.client.asearch("maps", price=price_str, lang="en", country="us")
                _, kwargs = mock_aget.call_args
                self.assertEqual(kwargs["params"]["price"], expected_val)
                self.assertEqual(kwargs["params"]["hl"], "en")
                self.assertEqual(kwargs["params"]["gl"], "us")

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_happy_path_limits_num_and_skips_missing_app_id(
        self, mock_aget, mock_parse
    ):
        item1 = make_item("com.example.one", "One")
        item2 = make_item("com.example.two", "Two")
        item3 = make_item(None, "NoID")
        items = [item1, item2, item3]
        mock_parse.return_value = make_initial_search_page(items)

        results = await self.client.asearch("query", num=2)

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

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse", return_value={"ds:5": []}
    )
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_missing_ds1_returns_empty(self, mock_aget, mock_parse):
        self.assertEqual(await self.client.asearch("q"), [])

    @patch(
        "google_play_scraper.client.ScriptDataParser.parse",
        return_value={"ds:1": [[]]},
    )
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_indexing_error_returns_empty(self, mock_aget, mock_parse):
        self.assertEqual(await self.client.asearch("q"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_items_none_or_empty_returns_empty(self, mock_aget, mock_parse):
        for items_val in [None, []]:
            with self.subTest(items_val=items_val):
                mock_parse.return_value = {"ds:1": [["x", [[[items_val]]]]]}
                self.assertEqual(await self.client.asearch("q"), [])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.apost", new_callable=AsyncMock)
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_paginates_until_num_is_satisfied(
        self, mock_aget, mock_apost, mock_parse, mock_parse_batchexecute
    ):
        first_page_items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50)]
        second_page_items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50, 70)]

        mock_apost.return_value = "batchexecute"
        mock_parse.return_value = make_initial_search_page(first_page_items, token="TOKEN_1")
        mock_parse_batchexecute.return_value = make_paginated_search_page(second_page_items)

        results = await self.client.asearch("query", num=60)

        self.assertEqual(len(results), 60)
        self.assertEqual(results[0].app_id, "com.example.0")
        self.assertEqual(results[-1].app_id, "com.example.59")
        mock_apost.assert_awaited_once()
        _, kwargs = mock_apost.call_args
        self.assertEqual(kwargs["params"]["rpcids"], "qnKhOb")
        self.assertIn("TOKEN_1", kwargs["data"]["f.req"])

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.ScriptDataParser.parse")
    @patch("google_play_scraper.client.Requester.apost", new_callable=AsyncMock)
    @patch(
        "google_play_scraper.client.Requester.aget",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    async def test_does_not_paginate_when_first_page_already_satisfies_num(
        self, mock_aget, mock_apost, mock_parse, mock_parse_batchexecute
    ):
        items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50)]
        mock_parse.return_value = make_initial_search_page(items, token="TOKEN_1")

        results = await self.client.asearch("query", num=20)

        self.assertEqual(len(results), 20)
        mock_apost.assert_not_awaited()
        mock_parse_batchexecute.assert_not_called()

    @patch("google_play_scraper.client.ScriptDataParser.parse_batchexecute_response")
    @patch("google_play_scraper.client.ScriptDataParser.parse")
    async def test_asearch_uses_client_default_locale_for_initial_and_paginated_requests(
        self, mock_parse, mock_parse_batchexecute
    ):
        first_page_items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50)]
        second_page_items = [make_item(f"com.example.{i}", f"App {i}") for i in range(50, 70)]
        mock_parse.return_value = make_initial_search_page(first_page_items, token="TOKEN_1")
        mock_parse_batchexecute.return_value = make_paginated_search_page(second_page_items)

        response_get = Mock()
        response_get.raise_for_status.return_value = None
        response_get.text = "<html>dummy</html>"

        response_post = Mock()
        response_post.raise_for_status.return_value = None
        response_post.text = "batchexecute"

        client = GooglePlayClient(country="br", lang="pt")
        client._requester._async_session = AsyncMock()
        client._requester._async_session.request.side_effect = [response_get, response_post]

        results = await client.asearch("query", num=60)

        self.assertEqual(len(results), 60)

        request_calls = client._requester._async_session.request.call_args_list
        self.assertEqual(request_calls[0].kwargs["params"]["hl"], "pt")
        self.assertEqual(request_calls[0].kwargs["params"]["gl"], "br")
        self.assertEqual(request_calls[1].kwargs["params"]["hl"], "pt")
        self.assertEqual(request_calls[1].kwargs["params"]["gl"], "br")
