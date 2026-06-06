from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _parse_int_list(raw: str) -> list[int]:
    values: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            values.append(int(part))
    return values


def _parse_str_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_webhook_urls(raw: str) -> list[str]:
    urls: list[str] = []
    for part in raw.replace("\n", ",").split(","):
        part = part.strip()
        if part and "access_token=" in part:
            urls.append(part)
    return urls


@dataclass(frozen=True)
class Config:
    notify_channel: str
    dingtalk_webhook_urls: list[str]
    dingtalk_secret: str
    wxpusher_app_token: str
    wxpusher_topic_ids: list[int]
    wxpusher_uids: list[str]
    keywords: list[str]
    poll_interval_sec: int
    cls_rn: int
    state_db_path: Path


def load_config() -> Config:
    notify_channel = os.getenv("NOTIFY_CHANNEL", "dingtalk").strip() or "dingtalk"
    dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK_URL", "").strip()
    dingtalk_webhook_urls = _parse_webhook_urls(dingtalk_webhook)
    dingtalk_secret = os.getenv("DINGTALK_SECRET", "").strip()
    wxpusher_token = os.getenv("WXPUSHER_APP_TOKEN", "").strip()
    wxpusher_topic_ids = _parse_int_list(os.getenv("WXPUSHER_TOPIC_IDS", ""))
    wxpusher_uids = _parse_str_list(os.getenv("WXPUSHER_UIDS", ""))

    keywords_raw = os.getenv("KEYWORDS", "锂电,新能源,碳酸锂")
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    poll_interval = int(os.getenv("POLL_INTERVAL_SEC", "60"))
    cls_rn = int(os.getenv("CLS_RN", "50"))
    state_db = Path(os.getenv("STATE_DB_PATH", "data/state.db"))
    if not state_db.is_absolute():
        state_db = BASE_DIR / state_db

    return Config(
        notify_channel=notify_channel,
        dingtalk_webhook_urls=dingtalk_webhook_urls,
        dingtalk_secret=dingtalk_secret,
        wxpusher_app_token=wxpusher_token,
        wxpusher_topic_ids=wxpusher_topic_ids,
        wxpusher_uids=wxpusher_uids,
        keywords=keywords,
        poll_interval_sec=poll_interval,
        cls_rn=cls_rn,
        state_db_path=state_db,
    )


def validate_notify_config(cfg: Config) -> str | None:
    channels = {c.strip().lower() for c in cfg.notify_channel.split(",") if c.strip()}
    if not channels:
        return "NOTIFY_CHANNEL is empty"

    missing: list[str] = []
    if "dingtalk" in channels:
        if not cfg.dingtalk_webhook_urls:
            missing.append("DINGTALK_WEBHOOK_URL")

    if "wxpusher" in channels:
        if not cfg.wxpusher_app_token:
            missing.append("WXPUSHER_APP_TOKEN")
        elif not cfg.wxpusher_topic_ids and not cfg.wxpusher_uids:
            missing.append("WXPUSHER_TOPIC_IDS or WXPUSHER_UIDS")

    if missing:
        return f"Missing or invalid config: {', '.join(missing)}"
    return None
