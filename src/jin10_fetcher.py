from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.cls_fetcher import TelegraphItem

logger = logging.getLogger(__name__)

FLASH_URL = "https://qh-flash-api.jin10.com/get_flash_list"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://qihuo.jin10.com/",
    "Origin": "https://qihuo.jin10.com",
    "x-app-id": "KxBcVoDHStE6CUkQ",
    "x-version": "1.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_TITLE_RE = re.compile(r"^【(.*?)】")


def _parse_time(time_str: str) -> int:
    if not time_str:
        return 0
    try:
        return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp())
    except ValueError:
        logger.warning("Unexpected Jin10 time format: %s", time_str)
        return 0


def _extract_title_content(raw_title: str, content: str) -> tuple[str, str]:
    title = raw_title.strip()
    body = content.strip()
    match = _TITLE_RE.match(body)
    if match:
        if not title:
            title = match.group(1).strip()
        body = body[match.end() :].strip()
    if not title:
        title = body[:60] if body else "(无标题)"
    return title, body


def _normalize_share_url(item_id: str) -> str:
    return f"https://qihuo.jin10.com/flashDetail.html?id={item_id}"


def _parse_items(raw_items: list[dict[str, Any]]) -> list[TelegraphItem]:
    items: list[TelegraphItem] = []
    for raw in raw_items:
        if raw.get("type") == 1:
            continue

        item_id = raw.get("id")
        if not item_id:
            continue

        data = raw.get("data") or {}
        if not isinstance(data, dict):
            continue

        content = (data.get("content") or "").strip()
        if not content:
            continue

        title, body = _extract_title_content(data.get("title") or "", content)
        items.append(
            TelegraphItem(
                id=f"jin10:{item_id}",
                title=title,
                content=body or content,
                ctime=_parse_time(raw.get("time") or ""),
                shareurl=_normalize_share_url(str(item_id)),
                source="jin10",
            )
        )
    return items


class Jin10QihuoFetcher:
    """金十期货 qihuo.jin10.com 7x24 快讯。"""

    def __init__(self, channel: str = "") -> None:
        self.channel = channel.strip()
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
        params: dict[str, str] = {"vip": "1"}
        if self.channel:
            params["channel"] = self.channel

        try:
            response = self.session.get(
                FLASH_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("Jin10 qihuo request error: %s", exc)
            return []

        if payload.get("status") not in (None, 200):
            logger.warning("Jin10 qihuo API returned error: %s", payload)
            return []

        raw_items = payload.get("data")
        if not isinstance(raw_items, list):
            logger.warning("Unexpected Jin10 qihuo response structure")
            return []

        return _parse_items(raw_items)
