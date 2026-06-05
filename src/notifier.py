from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from datetime import datetime
from typing import Protocol

import requests

from src.matcher import MatchResult, keyword_excerpt

logger = logging.getLogger(__name__)

WXPUSHER_URL = "https://wxpusher.zjiecode.com/api/send/message"
MAX_CONTENT_BYTES = 2000


class Notifier(Protocol):
    def send_match(self, result: MatchResult) -> bool: ...


def _truncate_utf8(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes]
    while truncated:
        try:
            return truncated.decode("utf-8") + "..."
        except UnicodeDecodeError:
            truncated = truncated[:-1]
    return "..."


def _format_time(ctime: int) -> str:
    if ctime <= 0:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")


def build_title(result: MatchResult) -> str:
    primary_kw = result.matched_keywords[0]
    return f"财联社关键词命中：{primary_kw}"


def build_markdown_content(result: MatchResult) -> str:
    item = result.item
    keywords_str = "、".join(result.matched_keywords)
    title = item.title or "(无标题)"
    body = _truncate_utf8(item.content or title, MAX_CONTENT_BYTES)

    lines = [
        f"**时间**：{_format_time(item.ctime)}",
        f"**命中词**：{keywords_str}",
        "",
        f"**{title}**",
        "",
        body,
    ]
    if item.shareurl:
        lines.extend(["", f"[查看原文]({item.shareurl})"])

    return "\n".join(lines)


def _build_excerpts(result: MatchResult) -> list[str]:
    text = f"{result.item.title} {result.item.content}"
    excerpts: list[str] = []
    for kw in result.matched_keywords:
        excerpt = keyword_excerpt(text, kw)
        if excerpt:
            excerpts.append(f"- **{kw}**：{excerpt}")
    return excerpts


def build_dingtalk_markdown(result: MatchResult) -> tuple[str, str]:
    title = build_title(result)
    item = result.item
    keywords_str = "、".join(result.matched_keywords)
    headline = item.title or item.content[:60] or "(无标题)"
    body = _truncate_utf8(item.content or headline, MAX_CONTENT_BYTES)
    excerpts = _build_excerpts(result)

    lines = [
        f"### {title}",
        f"> 时间：{_format_time(item.ctime)}",
        f"> 命中词：**{keywords_str}**",
        "",
        f"**{headline}**",
        "",
    ]
    if excerpts:
        lines.append("**关键词上下文：**")
        lines.extend(excerpts)
        lines.append("")
    lines.append(body)
    if item.shareurl:
        lines.extend(["", f"[查看原文（含关键词文章）]({item.shareurl})"])

    return title, "\n".join(lines)


class DingTalkNotifier:
    """钉钉自定义群机器人 Webhook（免费）。"""

    def __init__(self, webhook_url: str, secret: str = "", label: str = "") -> None:
        self.webhook_url = webhook_url
        self.secret = secret.strip()
        self.label = label or webhook_url[-12:]

    def _signed_url(self) -> str:
        if not self.secret:
            return self.webhook_url

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        separator = "&" if "?" in self.webhook_url else "?"
        return f"{self.webhook_url}{separator}timestamp={timestamp}&sign={sign}"

    def send_match(self, result: MatchResult) -> bool:
        title, text = build_dingtalk_markdown(result)
        payload = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        }
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        try:
            response = requests.post(
                self._signed_url(),
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            body = response.json()
            if body.get("errcode", 0) != 0:
                logger.error("DingTalk webhook error: %s", body)
                return False
            logger.info(
                "DingTalk notification sent for item %s (webhook ...%s)",
                result.item.id,
                self.label,
            )
            return True
        except (requests.RequestException, ValueError) as exc:
            logger.error("Failed to send DingTalk notification: %s", exc)
            return False


class WxPusherNotifier:
    """WxPusher 推送到个人微信（免费，需关注应用/主题）。"""

    def __init__(
        self,
        app_token: str,
        topic_ids: list[int] | None = None,
        uids: list[str] | None = None,
    ) -> None:
        self.app_token = app_token
        self.topic_ids = topic_ids or []
        self.uids = uids or []

    def send_match(self, result: MatchResult) -> bool:
        payload: dict = {
            "appToken": self.app_token,
            "content": build_markdown_content(result),
            "summary": build_title(result),
            "contentType": 3,
            "verifyPayType": 0,
        }
        if result.item.shareurl:
            payload["url"] = result.item.shareurl
        if self.topic_ids:
            payload["topicIds"] = self.topic_ids
        if self.uids:
            payload["uids"] = self.uids

        headers = {"Content-Type": "application/json; charset=UTF-8"}
        try:
            response = requests.post(
                WXPUSHER_URL,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            body = response.json()
            if body.get("code") != 1000:
                logger.error("WxPusher error: %s", body)
                return False
            logger.info("WxPusher notification sent for item %s", result.item.id)
            return True
        except (requests.RequestException, ValueError) as exc:
            logger.error("Failed to send WxPusher notification: %s", exc)
            return False


class MultiNotifier:
    """同时推送到多个渠道，任一成功即视为发送成功。"""

    def __init__(self, notifiers: list[Notifier]) -> None:
        self.notifiers = notifiers

    def send_match(self, result: MatchResult) -> bool:
        if not self.notifiers:
            return False

        success = False
        for notifier in self.notifiers:
            if notifier.send_match(result):
                success = True
        return success


def create_notifier(
    channel: str,
    dingtalk_webhook_urls: list[str] | None = None,
    dingtalk_secret: str = "",
    wxpusher_app_token: str = "",
    wxpusher_topic_ids: list[int] | None = None,
    wxpusher_uids: list[str] | None = None,
) -> Notifier | None:
    notifiers: list[Notifier] = []
    channels = {c.strip().lower() for c in channel.split(",") if c.strip()}

    if "dingtalk" in channels and dingtalk_webhook_urls:
        for url in dingtalk_webhook_urls:
            token_tail = url.split("access_token=")[-1][-8:]
            notifiers.append(DingTalkNotifier(url, dingtalk_secret, label=token_tail))

    if "wxpusher" in channels and wxpusher_app_token:
        notifiers.append(
            WxPusherNotifier(
                wxpusher_app_token,
                topic_ids=wxpusher_topic_ids,
                uids=wxpusher_uids,
            )
        )

    if not notifiers:
        return None
    if len(notifiers) == 1:
        return notifiers[0]
    return MultiNotifier(notifiers)
