from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

V1_URL = "https://www.cls.cn/v1/roll/get_roll_list"
LEGACY_URL = "https://www.cls.cn/nodeapi/telegraphList"
MOBILE_URL = "https://m.cls.cn/nodeapi/telegraphs"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.cls.cn/telegraph",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass(frozen=True)
class TelegraphItem:
    id: str
    title: str
    content: str
    ctime: int
    shareurl: str
    source: str = "cls"


def _make_sign(param_string: str) -> str:
    sha1_hex = hashlib.sha1(param_string.encode("utf-8")).hexdigest()
    return hashlib.md5(sha1_hex.encode("utf-8")).hexdigest()


def _normalize_share_url(item_id: str, shareurl: str) -> str:
    """统一为财联社详情页，避免 api3 分享链接打开后看不到正文关键词。"""
    return f"https://www.cls.cn/detail/{item_id}"


def _parse_items(raw_items: list[dict[str, Any]]) -> list[TelegraphItem]:
    items: list[TelegraphItem] = []
    for raw in raw_items:
        item_id = raw.get("id")
        if item_id is None:
            continue
        title = (raw.get("title") or "").strip()
        content = (raw.get("content") or raw.get("brief") or "").strip()
        ctime = int(raw.get("ctime") or raw.get("modified_time") or 0)
        shareurl = _normalize_share_url(str(item_id), (raw.get("shareurl") or "").strip())
        items.append(
            TelegraphItem(
                id=str(item_id),
                title=title,
                content=content,
                ctime=ctime,
                shareurl=shareurl,
            )
        )
    return items


def _extract_roll_data(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    payload = data.get("data")
    if not isinstance(payload, dict):
        return None
    roll_data = payload.get("roll_data")
    if isinstance(roll_data, list):
        return roll_data
    return None


class ClsFetcher:
    def __init__(self, rn: int = 50) -> None:
        self.rn = rn
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch(self) -> list[TelegraphItem]:
        for name, fetcher in (
            ("v1_sign", self._fetch_v1_signed),
            ("legacy_simple", self._fetch_legacy_simple),
            ("mobile", self._fetch_mobile),
        ):
            items = fetcher()
            if items:
                logger.debug("CLS fetch succeeded via %s", name)
                return items
            logger.warning("CLS fetch via %s returned empty", name)

        logger.error("CLS fetch failed with all methods")
        return []

    def _fetch_v1_signed(self) -> list[TelegraphItem]:
        last_time = int(time.time())
        app = "CailianpressWeb"
        os_name = "web"
        rn = self.rn
        sv = "7.7.5"
        param_string = f"app={app}&last_time={last_time}&os={os_name}&rn={rn}&sv={sv}"
        params = {
            "app": app,
            "last_time": str(last_time),
            "os": os_name,
            "rn": str(rn),
            "sv": sv,
            "sign": _make_sign(param_string),
        }
        return self._request(V1_URL, params)

    def _fetch_legacy_simple(self) -> list[TelegraphItem]:
        params = {
            "app": "CailianpressWeb",
            "os": "web",
            "refresh_type": "1",
            "rn": str(self.rn),
            "sv": "8.4.6",
        }
        return self._request(LEGACY_URL, params)

    def _fetch_mobile(self) -> list[TelegraphItem]:
        self.session.get(
            "https://m.cls.cn/telegraph",
            headers=DEFAULT_HEADERS,
            timeout=10,
        )
        params = {
            "refresh_type": "1",
            "rn": str(self.rn),
            "last_time": "",
            "app": "CailianpressWap",
            "sv": "1",
        }
        return self._request(MOBILE_URL, params, referer="https://m.cls.cn/telegraph")

    def _request(
        self,
        url: str,
        params: dict[str, str],
        referer: str | None = None,
    ) -> list[TelegraphItem]:
        headers = dict(DEFAULT_HEADERS)
        if referer:
            headers["Referer"] = referer
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("CLS request error (%s): %s", url, exc)
            return []

        if data.get("errno") not in (None, 0) and data.get("error") not in (None, 0):
            logger.warning("CLS API returned error: %s", data)
            return []

        roll_data = _extract_roll_data(data)
        if not roll_data:
            logger.warning("Unexpected CLS response structure from %s", url)
            return []

        return _parse_items(roll_data)
