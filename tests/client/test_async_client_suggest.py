import json
import pytest
from unittest.mock import AsyncMock

from google_play_scraper.client import GooglePlayClient


@pytest.mark.asyncio
async def test_request_formation(mocker):
    mock_post = mocker.patch(
        "google_play_scraper.client.AsyncRequester.post", new_callable=AsyncMock
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[[], None],
    )

    term = "maps"
    lang = "en"
    country = "us"

    client = GooglePlayClient()
    await client.asuggest(term=term, lang=lang, country=country)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "/_/PlayStoreUi/data/batchexecute"

    params = kwargs["params"]
    assert params["rpcids"] == "IJ4APc"
    assert params["hl"] == lang
    assert params["gl"] == country
    assert "bl" in params
    assert "authuser" in params
    assert "soc-app" in params
    assert "soc-platform" in params
    assert "soc-device" in params
    assert "rt" in params

    form = kwargs["data"]
    assert "f.req" in form
    outer = json.loads(form["f.req"])
    assert isinstance(outer, list)
    assert outer[0][0][0] == "IJ4APc"

    inner_json = outer[0][0][1]
    inner = json.loads(inner_json)
    assert inner == [[None, [term], [10], [2], 4]]


@pytest.mark.asyncio
async def test_happy_path_maps_items_and_skips_none(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    suggestion_list = [["alpha"], None, ["beta", "extra"]]
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[[suggestion_list]],
    )

    client = GooglePlayClient()
    out = await client.asuggest("al")
    assert out == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_empty_term_raises_value_error():
    client = GooglePlayClient()
    with pytest.raises(ValueError):
        await client.asuggest("")


@pytest.mark.asyncio
@pytest.mark.parametrize("parsed_data", [[], None])
async def test_empty_or_none_parsed_data_returns_empty(mocker, parsed_data):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=parsed_data,
    )

    client = GooglePlayClient()
    assert await client.asuggest("m") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("suggestion_list", [None, []])
async def test_falsy_suggestion_list_returns_empty(mocker, suggestion_list):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[[suggestion_list]],
    )

    client = GooglePlayClient()
    assert await client.asuggest("ma") == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_data", [None, 1, [1], [[1]], [[()]]]
)
async def test_index_or_type_errors_return_empty(mocker, bad_data):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=bad_data,
    )
    client = GooglePlayClient()
    assert await client.asuggest("q") == []
