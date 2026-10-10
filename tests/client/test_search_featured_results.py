"""Search layouts reduced from public Play pages observed on 2026-10-10.

The featured payload was at ds:4[0][1][0][23][16] on US xbxplay.
All content here is synthetic; only the structural indices are retained.
"""

import asyncio
import json

import pytest

from google_play_scraper.client import GooglePlayClient
from tests.fixtures import make_app_entry, make_search_page


def featured_section(entries, app_id="com.example.featured", title="Featured"):
    section = make_search_page(entries)["ds:4"][0][1][0]
    section.append([None] * 17)
    details = [None] * 96
    details[0] = [title]
    details[51] = [["4.6", 4.6]]
    details[57] = [[[[[None, [[1990000, "USD", "$1.99"]]]]]]]
    details[68] = ["Example Developer"]
    details[73] = [[None, "Featured summary"]]
    details[95] = [[None, None, None, [None, None, "https://img.test/featured.png"]]]
    section[23][16] = [None, None, details, {"12": [[app_id, 7]]}]
    return section


def page_html(sections, extra_data=""):
    data = {"ds:4": [[None, sections]]}
    return "".join(
        "<script>AF_initDataCallback({key: '" + key + "', data:"
        + json.dumps(value) + ", sideChannel: {}});</script>"
        for key, value in data.items()
    ) + extra_data


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def search(request, monkeypatch):
    client = GooglePlayClient()

    def run(html, num=30):
        def get(*args, **kwargs):
            return html

        async def aget(*args, **kwargs):
            return html

        monkeypatch.setattr(client._requester, "get", get)
        monkeypatch.setattr(client._requester, "aget", aget)
        if request.param:
            return asyncio.run(client.asearch("query", num=num))
        return client.search("query", num=num)

    yield run
    client._session.close()
    asyncio.run(client._async_session.aclose())


def test_featured_app_precedes_recommendations(search):
    html = page_html([featured_section([make_app_entry("com.example.other", "Other")])])
    results = search(html)
    assert [app.app_id for app in results] == ["com.example.featured", "com.example.other"]
    assert results[0].title == "Featured"
    assert str(results[0].icon) == "https://img.test/featured.png"
    assert results[0].developer == "Example Developer"
    assert results[0].score == 4.6
    assert results[0].price_text == "$1.99"
    assert results[0].free is False
    assert results[0].summary == "Featured summary"


def test_featured_only_page(search):
    results = search(page_html([featured_section([])]))
    assert [app.app_id for app in results] == ["com.example.featured"]


def test_duplicates_and_invalid_entries_do_not_consume_limit(search):
    section = featured_section([
        make_app_entry("com.example.featured", "Duplicate"),
        make_app_entry(None, "No identity"),
        {"separator": True},
        make_app_entry("com.example.other", "Other"),
        make_app_entry("com.example.other", "Duplicate other"),
        make_app_entry("com.example.third", "Third"),
    ])
    results = search(page_html([section]), num=3)
    assert [app.app_id for app in results] == [
        "com.example.featured", "com.example.other", "com.example.third",
    ]
    assert results[0].title == "Featured"


def test_limit_includes_featured_card(search):
    results = search(page_html([
        featured_section([make_app_entry("com.example.other", "Other")]),
    ]), num=1)
    assert [app.app_id for app in results] == ["com.example.featured"]


def test_multiple_sections_keep_order_and_skip_unrelated_datasets(search):
    ordinary = make_search_page([make_app_entry("com.example.first", "First")])["ds:4"][0][1][0]
    featured = featured_section([make_app_entry("com.example.last", "Last")])
    unrelated = page_html([featured_section([], "com.example.unrelated")]).replace("ds:4", "ds:5")
    results = search(page_html([ordinary, featured], unrelated))
    assert [app.app_id for app in results] == [
        "com.example.first", "com.example.featured", "com.example.last",
    ]


def test_malformed_featured_card_preserves_valid_cluster(search):
    for app_id, title in [(None, "Featured"), ("com.example.featured", None)]:
        section = featured_section([make_app_entry("com.example.other", "Other")], app_id, title)
        results = search(page_html([section]))
        assert [app.app_id for app in results] == ["com.example.other"]


def test_ordinary_page_still_works(search):
    ordinary = make_search_page([
        make_app_entry(None, "No identity"),
        make_app_entry("com.example.one", "One"),
        make_app_entry("com.example.two", "Two"),
    ])["ds:4"][0][1][0]
    results = search(page_html([ordinary]), num=2)
    assert [app.app_id for app in results] == ["com.example.one", "com.example.two"]


def test_non_positive_limit_returns_empty(search):
    for num in [0, -1]:
        assert search(page_html([featured_section([])]), num=num) == []
