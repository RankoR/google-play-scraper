import httpx
import pytest


@pytest.fixture(autouse=True)
def block_real_http_requests(monkeypatch):
    def _blocked_sync_request(*args, **kwargs):
        raise AssertionError(
            "Real HTTP requests are forbidden in tests. Mock the request layer explicitly."
        )

    async def _blocked_async_request(*args, **kwargs):
        raise AssertionError(
            "Real HTTP requests are forbidden in tests. Mock the request layer explicitly."
        )

    monkeypatch.setattr(httpx.Client, "request", _blocked_sync_request)
    monkeypatch.setattr(httpx.AsyncClient, "request", _blocked_async_request)
