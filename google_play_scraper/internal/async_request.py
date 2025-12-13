import asyncio
from typing import Optional, Any, Dict

import httpx

from google_play_scraper.exceptions import GooglePlayError, AppNotFound, QuotaExceeded


class AsyncRequester:
    BASE_URL = "https://play.google.com"

    def __init__(
        self,
        session: httpx.AsyncClient,
        throttle: Optional[int],
        default_lang: str,
        default_country: str,
    ):
        self._session = session
        self._throttle_delay = 1.0 / throttle if throttle else 0
        self._last_request_time = 0.0
        self._lang = default_lang
        self._country = default_country
        self._headers = {
            "Origin": self.BASE_URL,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/112.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }

    async def _wait_for_throttle(self):
        if self._throttle_delay > 0:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self._throttle_delay:
                await asyncio.sleep(self._throttle_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def request(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        await self._wait_for_throttle()

        url = f"{self.BASE_URL}{path}"
        final_headers = self._headers.copy()
        if headers:
            final_headers.update(headers)

        if params is None:
            params = {}
        params.setdefault("hl", self._lang)
        params.setdefault("gl", self._country)

        try:
            response = await self._session.request(
                method=method, url=url, params=params, data=data, headers=final_headers
            )
            response.raise_for_status()
            return response.text

        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code == 404:
                raise AppNotFound(f"App not found: {url}") from e
            if code == 429 or code == 503:
                raise QuotaExceeded("Too many requests or server unavailable.") from e
            raise GooglePlayError(f"HTTP Error {code}") from e
        except httpx.RequestError as e:
            raise GooglePlayError(f"Network error: {str(e)}") from e

    async def get(
        self,
        path: str,
        params: Dict[str, Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        return await self.request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        params: Dict[str, Any] = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        return await self.request(
            "POST", path, params=params, data=data, headers=headers
        )
