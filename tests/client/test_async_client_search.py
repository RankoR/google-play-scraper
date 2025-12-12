import pytest
from unittest.mock import AsyncMock

from google_play_scraper.client import GooglePlayClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "price_str, expected_val",
    [("free", 1), ("paid", 2), ("all", 0), ("unknown", 0)],
)
async def test_price_param_mapping(mocker, price_str, expected_val):
    mock_get = mocker.patch(
        "google_play_scraper.client.AsyncRequester.get", new_callable=AsyncMock
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse",
        return_value={"ds:1": [["x", [[[[]]]]]]},
    )

    client = GooglePlayClient()
    await client.asearch("maps", price=price_str, lang="en", country="us")

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["price"] == expected_val
    assert kwargs["params"]["hl"] == "en"
    assert kwargs["params"]["gl"] == "us"


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


@pytest.mark.asyncio
async def test_happy_path_limits_num_and_skips_missing_app_id(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )

    item1 = make_item("com.example.one", "One")
    item2 = make_item("com.example.two", "Two")
    item3 = make_item(None, "NoID")
    items = [item1, item2, item3]
    ds1 = [["x", [[[items]]]]]
    mocker.patch("google_play_scraper.client.ScriptDataParser.parse", return_value={"ds:1": ds1})

    client = GooglePlayClient()
    results = await client.asearch("query", num=2)

    assert len(results) == 2
    assert results[0].app_id == "com.example.one"
    assert results[0].title == "One"
    assert results[0].developer == "One Dev"
    assert results[0].developer_id == "DEV_ID"
    assert results[0].score == 4.5
    assert results[0].score_text == "4.5"
    assert results[0].price_text == "$0.00"
    assert results[0].free
    assert results[0].summary == "One summary"


@pytest.mark.asyncio
async def test_missing_ds1_returns_empty(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    mocker.patch("google_play_scraper.client.ScriptDataParser.parse", return_value={"ds:5": []})

    client = GooglePlayClient()
    assert await client.asearch("q") == []


@pytest.mark.asyncio
async def test_indexing_error_returns_empty(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse", return_value={"ds:1": [[]]}
    )

    client = GooglePlayClient()
    assert await client.asearch("q") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("items_val", [None, []])
async def test_items_none_or_empty_returns_empty(mocker, items_val):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse",
        return_value={"ds:1": [["x", [[[items_val]]]]]},
    )

    client = GooglePlayClient()
    assert await client.asearch("q") == []
