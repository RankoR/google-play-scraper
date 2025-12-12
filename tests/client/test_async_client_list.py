import pytest
from unittest.mock import AsyncMock

from google_play_scraper.client import GooglePlayClient


@pytest.mark.asyncio
async def test_request_formation_and_optional_age(mocker):
    mock_post = mocker.patch(
        "google_play_scraper.client.AsyncRequester.post", new_callable=AsyncMock
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[],
    )

    client = GooglePlayClient()
    res = await client.alist(
        collection="collX",
        category="catY",
        age="AGE_PARAM",
        num=7,
        lang="en",
        country="us",
    )

    assert res == []

    (url,), kwargs = mock_post.call_args
    assert url == "/_/PlayStoreUi/data/batchexecute"
    assert "headers" in kwargs
    assert (
        kwargs["headers"].get("Content-Type")
        == "application/x-www-form-urlencoded;charset=UTF-8"
    )

    params = kwargs.get("params")
    assert isinstance(params, dict)
    assert params.get("rpcids") == "vyAe2"
    assert params.get("hl") == "en"
    assert params.get("gl") == "us"
    assert params.get("age") == "AGE_PARAM"

    data = kwargs.get("data")
    assert isinstance(data, str)
    assert "collX" in data
    assert "catY" in data
    assert "7" in data


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


@pytest.mark.asyncio
async def test_happy_path_extracts_app_overview_fields(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )

    app1 = make_app("com.example.one", "One", 0, "USD")
    app2 = make_app("com.example.two", "Two", 1990000, "USD")
    apps_list = [[app1], [app2]]
    arr_with_29 = [None] * 29
    arr_with_29[28] = [apps_list]
    data = [[None, [arr_with_29]]]
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=data,
    )

    client = GooglePlayClient()
    results = await client.alist(num=5)

    assert len(results) == 2
    r1, r2 = results
    assert r1.app_id == "com.example.one"
    assert r1.title == "One"
    assert str(r1.icon) == "https://img.test/icon.png"
    assert r1.developer == "One Dev"
    assert r1.developer_id == "One Dev"
    assert r1.free
    assert r1.summary == "One summary"
    assert r1.score_text == "4.5"
    assert r1.score == 4.5
    assert r2.app_id == "com.example.two"
    assert r2.title == "Two"
    assert not r2.free
    assert r2.summary == "Two summary"


@pytest.mark.asyncio
async def test_parsed_data_empty_returns_empty(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[],
    )

    client = GooglePlayClient()
    assert await client.alist() == []


@pytest.mark.asyncio
async def test_extract_exception_returns_empty(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[1],
    )
    mocker.patch(
        "google_play_scraper.client.ElementSpec.extract", side_effect=Exception("boom")
    )

    client = GooglePlayClient()
    assert await client.alist() == []


@pytest.mark.asyncio
async def test_apps_root_falsy_returns_empty(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    arr_with_29 = [None] * 29
    arr_with_29[28] = [[]]
    data = [[None, [arr_with_29]]]
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=data,
    )

    client = GooglePlayClient()
    assert await client.alist() == []
