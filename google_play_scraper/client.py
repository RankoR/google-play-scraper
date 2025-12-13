import json
import re
from datetime import datetime
from typing import Optional, List, Union, Dict, Any

import httpx

from .constants import Category, Collection, Sort, Age
from .exceptions import AppNotFound
from .internal.extractor import ElementSpec, extract_from_spec
from .internal.parser import ScriptDataParser
from .internal.request import Requester
from .internal.request_constants import LIST_PAYLOAD_TEMPLATE
from .models import AppDetails, AppOverview, Review


def _build_proxy_mounts(proxies: Optional[dict]) -> Optional[dict]:
    """Build `httpx` `mounts` from a requests-style proxies dict.

    `httpx>=0.28` removed the `proxies=` kwarg for `Client`/`AsyncClient`.
    Instead, proxies are configured via transports mounted per scheme.

    Expected input examples:
      - {"http": "http://localhost:8030", "https": "http://localhost:8031"}
      - {"http://": "http://localhost:8030", "https://": "http://localhost:8031"}
    """

    if not proxies:
        return None

    def _get_proxy_url(key: str) -> Optional[str]:
        return proxies.get(key) or proxies.get(key.rstrip(":"))

    http_proxy = _get_proxy_url("http://")
    https_proxy = _get_proxy_url("https://")

    mounts: dict[str, httpx.BaseTransport] = {}
    if http_proxy:
        mounts["http://"] = httpx.HTTPTransport(proxy=http_proxy)
    if https_proxy:
        mounts["https://"] = httpx.HTTPTransport(proxy=https_proxy)

    # If user passed only one of them, still return what we have.
    return mounts or None


def _clean_desc(html: Optional[str]) -> str:
    return re.sub(r"<br>", "\r\n", html) if html else ""


def _normalize_histogram(data: list) -> dict:
    if not data or len(data) < 6:
        return {str(i): 0 for i in range(1, 6)}

    result = {}
    for i in range(1, 6):
        try:
            result[str(i)] = data[i][1]
        except (IndexError, TypeError):
            result[str(i)] = 0
    return result


def _ts_to_date(ts: int) -> datetime:
    return datetime.fromtimestamp(ts) if ts else None


class GooglePlayClient:
    def __init__(
        self,
        country: str = "us",
        lang: str = "en",
        proxies: Optional[dict] = None,
        throttle_requests_per_second: Optional[int] = None,
        verify_ssl: bool = True,
    ):
        mounts = _build_proxy_mounts(proxies)

        self._session = httpx.Client(mounts=mounts, verify=verify_ssl)
        self._async_session = httpx.AsyncClient(mounts=mounts, verify=verify_ssl)

        self._requester = Requester(
            self._session,
            throttle_requests_per_second,
            default_lang=lang,
            default_country=country,
            async_session=self._async_session,
        )

    def _parse_app_details(self, html: str, app_id: str) -> AppDetails:
        data_map = ScriptDataParser.parse(html)
        ds5 = data_map.get("ds:5")
        if not ds5:
            raise AppNotFound(f"Could not parse data for {app_id}")

        try:
            root = ds5[1][2]
        except (IndexError, TypeError):
            raise AppNotFound(f"Unexpected data format for {app_id}")

        specs = {
            "title": ElementSpec([0, 0]),
            "description_html": ElementSpec([72, 0, 1]),
            "description": ElementSpec([72, 0, 1], transformer=_clean_desc),
            "summary": ElementSpec([73, 0, 1]),
            "installs": ElementSpec([13, 0]),
            "min_installs": ElementSpec([13, 1]),
            "max_installs": ElementSpec([13, 2]),
            "score": ElementSpec([51, 0, 1]),
            "score_text": ElementSpec([51, 0, 0]),
            "ratings": ElementSpec([51, 2, 1]),
            "reviews": ElementSpec([51, 3, 1]),
            "histogram": ElementSpec([51, 1], transformer=_normalize_histogram),
            "price": ElementSpec(
                [57, 0, 0, 0, 0, 1, 0, 0], transformer=lambda x: x / 1000000 if x else 0
            ),
            "free": ElementSpec(
                [57, 0, 0, 0, 0, 1, 0, 0], transformer=lambda x: x == 0
            ),
            "currency": ElementSpec([57, 0, 0, 0, 0, 1, 0, 1]),
            "price_text": ElementSpec([57, 0, 0, 0, 0, 1, 0, 2]),
            "available": ElementSpec([18, 0], transformer=bool),
            "offers_iap": ElementSpec([19, 0], transformer=bool),
            "android_version": ElementSpec([140, 1, 1, 0, 0, 1]),
            "developer": ElementSpec([68, 0]),
            "developer_id": ElementSpec(
                [68, 1, 4, 2],
                transformer=lambda x: x.split("id=")[1] if "id=" in x else x,
            ),
            "developer_email": ElementSpec([69, 1, 0]),
            "developer_website": ElementSpec([69, 0, 5, 2]),
            "developer_address": ElementSpec([69, 2, 0]),
            "privacy_policy": ElementSpec([99, 0, 5, 2]),
            "genre": ElementSpec([79, 0, 0, 0]),
            "genre_id": ElementSpec([79, 0, 0, 2]),
            "icon": ElementSpec([95, 0, 3, 2]),
            "header_image": ElementSpec([96, 0, 3, 2]),
            "screenshots": ElementSpec(
                [78, 0], transformer=lambda x: [i[3][2] for i in x] if x else []
            ),
            "video": ElementSpec([100, 0, 0, 3, 2]),
            "content_rating": ElementSpec([9, 0]),
            "released": ElementSpec([10, 0]),
            "updated": ElementSpec([145, 0, 1, 0], transformer=_ts_to_date),
            "version": ElementSpec([140, 0, 0, 0]),
            "recent_changes": ElementSpec([144, 1, 1]),
        }
        data = extract_from_spec(root, specs)

        if not data.get("description"):
            data["description"] = ElementSpec(
                [12, 0, 0, 1], transformer=_clean_desc
            ).extract(root)
            data["description_html"] = ElementSpec([12, 0, 0, 1]).extract(root)

        data["app_id"] = app_id
        data["url"] = f"{Requester.BASE_URL}/store/apps/details?id={app_id}"

        return AppDetails(**data)

    def _parse_search_results(self, html: str, num: int) -> List[AppOverview]:
        data_map = ScriptDataParser.parse(html)
        ds1 = data_map.get("ds:1")
        if not ds1:
            return []

        try:
            items = ds1[0][1][0][0][0]
        except (IndexError, TypeError):
            return []

        results = []
        specs = {
            "title": ElementSpec([2]),
            "app_id": ElementSpec([12, 0]),
            "icon": ElementSpec([1, 1, 0, 3, 2]),
            "developer": ElementSpec([4, 0, 0, 0]),
            "developer_id": ElementSpec(
                [4, 0, 0, 1, 4, 2],
                transformer=lambda x: x.split("id=")[1] if "id=" in x else x,
            ),
            "score": ElementSpec([6, 0, 2, 1, 1]),
            "score_text": ElementSpec([6, 0, 2, 1, 0]),
            "price_text": ElementSpec([7, 0, 3, 2, 1, 0, 2]),
            "free": ElementSpec([7, 0, 3, 2, 1, 0, 0], transformer=lambda x: x == 0),
            "summary": ElementSpec([4, 1, 1, 1, 1]),
        }

        if not items:
            return []

        for item in items[:num]:
            data = extract_from_spec(item, specs)
            if data.get("app_id"):
                results.append(AppOverview(**data))

        return results

    def _parse_list_results(self, response_text: str) -> List[AppOverview]:
        data = ScriptDataParser.parse_batchexecute_response(response_text)
        if not data:
            return []

        root_path = [0, 1, 0, 28, 0]
        try:
            apps_root = ElementSpec(root_path).extract(data)
        except Exception:
            return []

        if not apps_root:
            return []

        results = []
        specs = {
            "title": ElementSpec([0, 3]),
            "app_id": ElementSpec([0, 0, 0]),
            "url": ElementSpec(
                [0, 10, 4, 2], transformer=lambda x: f"{Requester.BASE_URL}{x}"
            ),
            "icon": ElementSpec([0, 1, 3, 2]),
            "developer": ElementSpec([0, 14]),
            "developer_id": ElementSpec([0, 14]),
            "currency": ElementSpec([0, 8, 1, 0, 1]),
            "price": ElementSpec(
                [0, 8, 1, 0, 0], transformer=lambda x: x / 1000000 if x else 0
            ),
            "free": ElementSpec([0, 8, 1, 0, 0], transformer=lambda x: x == 0),
            "summary": ElementSpec([0, 13, 1]),
            "score_text": ElementSpec([0, 4, 0]),
            "score": ElementSpec([0, 4, 1]),
        }

        for app_raw in apps_root:
            extracted = extract_from_spec(app_raw, specs)
            if extracted.get("app_id"):
                results.append(AppOverview(**extracted))

        return results

    def _parse_reviews(
        self, response_text: str
    ) -> tuple[List[Review], Optional[str]]:
        data_arr = ScriptDataParser.parse_batchexecute_response(response_text)
        if not data_arr:
            return [], None

        try:
            reviews_root = data_arr[0]
            token = data_arr[1][1] if len(data_arr) > 1 and data_arr[1] else None
        except (IndexError, TypeError):
            return [], None

        if not reviews_root or not isinstance(reviews_root, list):
            return [], None

        results = []
        specs = {
            "id": ElementSpec([0]),
            "user_name": ElementSpec([1, 0]),
            "user_image": ElementSpec([1, 1, 3, 2]),
            "date": ElementSpec(
                [5, 0], transformer=lambda x: datetime.fromtimestamp(x) if x else None
            ),
            "score": ElementSpec([2]),
            "text": ElementSpec([4]),
            "reply_date": ElementSpec(
                [7, 2, 0], transformer=lambda x: datetime.fromtimestamp(x) if x else None
            ),
            "reply_text": ElementSpec([7, 1]),
            "thumbs_up": ElementSpec([6]),
            "version": ElementSpec([10]),
        }

        for raw_review in reviews_root:
            data = extract_from_spec(raw_review, specs)
            if data.get("id"):
                results.append(Review(**data))

        return results, token

    def _parse_suggestions(self, response_text: str) -> List[str]:
        data = ScriptDataParser.parse_batchexecute_response(response_text)
        if not data:
            return []

        try:
            suggestion_list = data[0][0]
            if not suggestion_list:
                return []
            return [item[0] for item in suggestion_list if item]
        except (IndexError, TypeError):
            return []

    def app(self, app_id: str, lang: str = None, country: str = None) -> AppDetails:
        if not app_id:
            raise ValueError("app_id cannot be empty")
        html = self._requester.get(
            "/store/apps/details", params={"id": app_id, "hl": lang, "gl": country}
        )
        return self._parse_app_details(html, app_id)

    async def aapp(
        self, app_id: str, lang: str = None, country: str = None
    ) -> AppDetails:
        if not app_id:
            raise ValueError("app_id cannot be empty")
        html = await self._requester.aget(
            "/store/apps/details", params={"id": app_id, "hl": lang, "gl": country}
        )
        return self._parse_app_details(html, app_id)

    def search(
        self,
        term: str,
        num: int = 20,
        price: str = "all",
        lang: str = None,
        country: str = None,
    ) -> List[AppOverview]:
        price_map = {"free": 1, "paid": 2, "all": 0}
        p_val = price_map.get(price, 0)
        params = {"q": term, "price": p_val, "hl": lang, "gl": country}
        html = self._requester.get("/work/search", params=params)
        return self._parse_search_results(html, num)

    async def asearch(
        self,
        term: str,
        num: int = 20,
        price: str = "all",
        lang: str = None,
        country: str = None,
    ) -> List[AppOverview]:
        price_map = {"free": 1, "paid": 2, "all": 0}
        p_val = price_map.get(price, 0)
        params = {"q": term, "price": p_val, "hl": lang, "gl": country}
        html = await self._requester.aget("/work/search", params=params)
        return self._parse_search_results(html, num)

    def list(
        self,
        collection: Union[Collection, str] = Collection.TOP_FREE,
        category: Union[Category, str] = Category.APPLICATION,
        age: Union[Age, str] = None,
        num: int = 50,
        lang: str = None,
        country: str = None,
    ) -> List[AppOverview]:
        payload = LIST_PAYLOAD_TEMPLATE.format(
            num=num, collection=collection, category=category
        )
        params = self._build_list_params(age, lang, country)
        response_text = self._requester.post(
            "/_/PlayStoreUi/data/batchexecute",
            params=params,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        return self._parse_list_results(response_text)

    async def alist(
        self,
        collection: Union[Collection, str] = Collection.TOP_FREE,
        category: Union[Category, str] = Category.APPLICATION,
        age: Union[Age, str] = None,
        num: int = 50,
        lang: str = None,
        country: str = None,
    ) -> List[AppOverview]:
        payload = LIST_PAYLOAD_TEMPLATE.format(
            num=num, collection=collection, category=category
        )
        params = self._build_list_params(age, lang, country)
        response_text = await self._requester.apost(
            "/_/PlayStoreUi/data/batchexecute",
            params=params,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        return self._parse_list_results(response_text)

    def _build_list_params(
        self, age: Union[Age, str], lang: str, country: str
    ) -> Dict[str, Any]:
        params = {
            "rpcids": "vyAe2",
            "source-path": "/store/apps",
            "f.sid": "-4178618388443751758",
            "bl": "boq_playuiserver_20220612.08_p0",
            "hl": lang,
            "gl": country,
            "authuser": "0",
            "soc-app": "121",
            "soc-platform": "1",
            "soc-device": "1",
            "_reqid": "82003",
            "rt": "c",
        }
        if age:
            params["age"] = age
        return params

    def reviews(
        self,
        app_id: str,
        lang: str = None,
        country: str = None,
        sort: Sort = Sort.NEWEST,
        num: int = 100,
        pagination_token: str = None,
    ) -> tuple[List[Review], Optional[str]]:
        form_data, params = self._build_reviews_request(
            app_id, lang, country, sort, num, pagination_token
        )
        resp_text = self._requester.post(
            "/_/PlayStoreUi/data/batchexecute", params=params, data=form_data
        )
        return self._parse_reviews(resp_text)

    async def areviews(
        self,
        app_id: str,
        lang: str = None,
        country: str = None,
        sort: Sort = Sort.NEWEST,
        num: int = 100,
        pagination_token: str = None,
    ) -> tuple[List[Review], Optional[str]]:
        form_data, params = self._build_reviews_request(
            app_id, lang, country, sort, num, pagination_token
        )
        resp_text = await self._requester.apost(
            "/_/PlayStoreUi/data/batchexecute", params=params, data=form_data
        )
        return self._parse_reviews(resp_text)

    def _build_reviews_request(
        self,
        app_id: str,
        lang: str,
        country: str,
        sort: Sort,
        num: int,
        pagination_token: str,
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        rpc_id = "UsvDTd"
        req_json = json.dumps(
            [None, None, [2, int(sort), [num, None, pagination_token], None, []], [app_id, 7]]
        )
        form_data = {"f.req": json.dumps([[[rpc_id, req_json, None, "generic"]]])}
        params = {"rpcids": rpc_id, "hl": lang, "gl": country}
        return form_data, params

    def suggest(self, term: str, lang: str = None, country: str = None) -> List[str]:
        if not term:
            raise ValueError("Term cannot be empty")
        form_data, params = self._build_suggest_request(term, lang, country)
        response_text = self._requester.post(
            "/_/PlayStoreUi/data/batchexecute", params=params, data=form_data
        )
        return self._parse_suggestions(response_text)

    async def asuggest(
        self, term: str, lang: str = None, country: str = None
    ) -> List[str]:
        if not term:
            raise ValueError("Term cannot be empty")
        form_data, params = self._build_suggest_request(term, lang, country)
        response_text = await self._requester.apost(
            "/_/PlayStoreUi/data/batchexecute", params=params, data=form_data
        )
        return self._parse_suggestions(response_text)

    def _build_suggest_request(
        self, term: str, lang: str, country: str
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        rpc_id = "IJ4APc"
        inner_json = json.dumps([[None, [term], [10], [2], 4]])
        outer_json = json.dumps([[[rpc_id, inner_json, None, "generic"]]])
        form_data = {"f.req": outer_json}
        params = {
            "rpcids": rpc_id,
            "hl": lang,
            "gl": country,
            "bl": "boq_playuiserver_20190903.08_p0",
            "authuser": "0",
            "soc-app": "121",
            "soc-platform": "1",
            "soc-device": "1",
            "rt": "c",
        }
        return form_data, params
