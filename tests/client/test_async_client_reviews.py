import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from google_play_scraper.client import GooglePlayClient
from google_play_scraper.constants import Sort


@pytest.mark.asyncio
async def test_request_formation(mocker):
    mock_post = mocker.patch(
        "google_play_scraper.client.AsyncRequester.post", new_callable=AsyncMock
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[[], None],
    )

    app_id = "com.example.app"
    lang = "en"
    country = "us"
    sort = Sort.HELPFULNESS
    num = 25
    token = "pagetok"

    client = GooglePlayClient()
    await client.areviews(
        app_id=app_id,
        lang=lang,
        country=country,
        sort=sort,
        num=num,
        pagination_token=token,
    )

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["params"]["rpcids"] == "UsvDTd"
    assert kwargs["params"]["hl"] == lang
    assert kwargs["params"]["gl"] == country

    form = kwargs["data"]
    assert "f.req" in form
    outer = json.loads(form["f.req"])
    assert isinstance(outer, list)
    assert outer[0][0][0] == "UsvDTd"

    inner_json = outer[0][0][1]
    inner = json.loads(inner_json)
    assert inner[3][0] == app_id
    assert inner[3][1] == 7
    assert inner[2][0] == 2
    assert inner[2][1] == int(sort)
    assert inner[2][2][0] == num
    assert inner[2][2][1] is None
    assert inner[2][2][2] == token


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


@pytest.mark.asyncio
async def test_happy_path_mapping_and_token_and_skip_missing_id(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.post",
        new_callable=AsyncMock,
        return_value="OK",
    )

    reviews_root = [make_review("RID_1"), make_review(None)]
    token_info = [None, "NEXT_TOKEN"]
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[reviews_root, token_info],
    )

    client = GooglePlayClient()
    reviews, token = await client.areviews(app_id="com.example")

    assert token == "NEXT_TOKEN"
    assert len(reviews) == 1
    r = reviews[0]
    assert r.id == "RID_1"
    assert r.user_name == "Alice"
    assert str(r.user_image) == "https://img.test/user.png"
    assert r.score == 5
    assert r.text == "Great app!"
    assert r.date == datetime(2023, 1, 2, 3, 4, 5)
    assert r.reply_text == "Thanks!"
    assert r.reply_date == datetime(2023, 2, 3, 4, 5, 6)
    assert r.thumbs_up == 42
    assert r.version == "1.2.3"


@pytest.mark.asyncio
async def test_edge_empty_parsed_data(mocker):
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[],
    )
    client = GooglePlayClient()
    reviews, token = await client.areviews(app_id="com.example")
    assert reviews == []
    assert token is None


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_data", [[None], [{}], ["x"], [1]])
async def test_edge_indexing_or_type_errors(mocker, bad_data):
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=bad_data,
    )
    client = GooglePlayClient()
    reviews, token = await client.areviews(app_id="com.example")
    assert reviews == []
    assert token is None


@pytest.mark.asyncio
@pytest.mark.parametrize("reviews_root", [None, []])
async def test_edge_falsy_reviews_root(mocker, reviews_root):
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse_batchexecute_response",
        return_value=[reviews_root, [None, "T"]],
    )
    client = GooglePlayClient()
    reviews, token = await client.areviews(app_id="com.example")
    assert reviews == []
    # Token is present in mock but should not be returned if reviews_root is falsy
    assert token is None
