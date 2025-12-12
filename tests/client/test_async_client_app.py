import pytest
from datetime import datetime
from unittest.mock import AsyncMock

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


@pytest.mark.asyncio
async def test_happy_path_extracts_and_transforms(mocker):
    app_id = "com.example.app"
    html = "<html>dummy</html>"

    mock_get = mocker.patch(
        "google_play_scraper.client.AsyncRequester.get", new_callable=AsyncMock
    )
    mock_get.return_value = html

    root = make_root_for_happy_path()
    ds5 = ds5_with_root(root)
    mocker.patch("google_play_scraper.client.ScriptDataParser.parse", return_value={"ds:5": ds5})

    client = GooglePlayClient()
    details = await client.aapp(app_id)

    assert details.app_id == app_id
    assert details.title == "My App"
    assert details.summary == "A short summary"
    assert str(details.icon) == "https://img.test/icon.png"
    assert str(details.header_image) == "https://img.test/header.png"
    assert [str(u) for u in details.screenshots] == ["https://img.test/shot1.png"]
    assert details.description_html == "Line1<br>Line2"
    assert details.description == "Line1\r\nLine2"
    assert details.score_text == "4.5"
    assert details.score == 4.5
    assert details.ratings == 1234
    assert details.reviews == 321
    assert details.histogram == {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
    assert details.price == 1.99
    assert details.currency == "USD"
    assert details.price_text == "$1.99"
    assert not details.free
    assert details.available
    assert not details.offers_iap
    assert details.developer == "ACME"
    assert details.developer_id == "ACME_INC"
    assert details.developer_email == "dev@acme.test"
    assert str(details.developer_website) == "https://acme.test/"
    assert details.developer_address == "ACME Street 1"
    assert str(details.privacy_policy) == "https://acme.test/privacy"
    assert details.genre == "Tools"
    assert details.genre_id == "TOOLS"
    assert details.released == "2020-01-01"
    assert isinstance(details.updated, datetime)
    assert details.updated == datetime.fromtimestamp(1_600_000_000)
    assert details.version == "1.0.0"
    assert details.recent_changes == "Bug fixes"

    mock_get.assert_called_once()
    called_args, called_kwargs = mock_get.call_args
    assert called_args[0] == "/store/apps/details"
    assert "params" in called_kwargs
    assert called_kwargs["params"]["id"] == app_id


@pytest.mark.asyncio
async def test_description_fallback_is_used(mocker):
    app_id = "com.example.app"

    mock_get = mocker.patch(
        "google_play_scraper.client.AsyncRequester.get", new_callable=AsyncMock
    )
    mock_get.return_value = "<html>dummy</html>"

    root = []
    build_nested(root, [12, 0, 0, 1], "Fallback<br>Desc")
    build_nested(root, [0, 0], "My App")
    build_nested(root, [51, 1], [None, ["1", 0], ["2", 0], ["3", 0], ["4", 0], ["5", 0]])
    build_nested(root, [13, 0], "0")
    build_nested(root, [18, 0], 1)
    build_nested(root, [19, 0], 0)
    build_nested(root, [140, 1, 1, 0, 0, 1], "VARY")
    build_nested(root, [78, 0], [])

    ds5 = ds5_with_root(root)
    mocker.patch("google_play_scraper.client.ScriptDataParser.parse", return_value={"ds:5": ds5})

    client = GooglePlayClient()
    details = await client.aapp(app_id)

    assert details.description_html == "Fallback<br>Desc"
    assert details.description == "Fallback\r\nDesc"


@pytest.mark.asyncio
async def test_missing_ds5_raises_app_not_found(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    mocker.patch("google_play_scraper.client.ScriptDataParser.parse", return_value={})

    client = GooglePlayClient()
    with pytest.raises(AppNotFound):
        await client.aapp("com.missing.app")


@pytest.mark.asyncio
async def test_malformed_ds5_raises_app_not_found(mocker):
    mocker.patch(
        "google_play_scraper.client.AsyncRequester.get",
        new_callable=AsyncMock,
        return_value="<html>dummy</html>",
    )
    mocker.patch(
        "google_play_scraper.client.ScriptDataParser.parse",
        return_value={"ds:5": [None, None]},
    )

    client = GooglePlayClient()
    with pytest.raises(AppNotFound):
        await client.aapp("com.example.app")


@pytest.mark.asyncio
async def test_empty_app_id_raises_value_error():
    client = GooglePlayClient()
    with pytest.raises(ValueError):
        await client.aapp("")
