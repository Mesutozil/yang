#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
import time

from config import load_config, validate_notify_config
from src.cls_fetcher import ClsFetcher
from src.matcher import match_keywords
from src.notifier import Notifier, create_notifier
from src.state import StateStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("monitorkeyword")


def process_batch(
    items,
    store: StateStore,
    keywords: list[str],
    notifier: Notifier | None,
    cold_start: bool,
) -> int:
    """Process fetched items. Returns number of notifications sent."""
    if cold_start:
        store.seed_items([(item.id, item.ctime) for item in items])
        logger.info("Cold start: seeded %d items without notifications", len(items))
        return 0

    sent = 0
    sorted_items = sorted(items, key=lambda item: item.ctime)
    for item in sorted_items:
        if store.has_seen(item.id):
            continue

        result = match_keywords(item, keywords)
        if result and notifier:
            if notifier.send_match(result):
                store.mark_seen(item.id, item.ctime, notified=True)
                sent += 1
            else:
                logger.warning("Notification failed for item %s; not marking as seen", item.id)
        else:
            store.mark_seen(item.id, item.ctime, notified=False)

    return sent


def run_once(cfg, store: StateStore, fetcher: ClsFetcher, notifier: Notifier | None) -> None:
    items = fetcher.fetch()
    logger.info("Fetched %d telegraph items", len(items))
    if not items:
        return

    cold_start = store.is_empty()
    logger.info("State DB: %d seen items, cold_start=%s", store.count(), cold_start)
    sent = process_batch(items, store, cfg.keywords, notifier, cold_start)
    if sent:
        logger.info("Sent %d notification(s)", sent)

    removed = store.cleanup_old()
    if removed:
        logger.info("Cleaned up %d old records", removed)


def run_loop(cfg, store: StateStore, fetcher: ClsFetcher, notifier: Notifier | None) -> None:
    logger.info(
        "Starting monitor: keywords=%s, channels=%s, interval=%ds",
        cfg.keywords,
        cfg.notify_channel,
        cfg.poll_interval_sec,
    )
    while True:
        try:
            run_once(cfg, store, fetcher, notifier)
        except Exception:
            logger.exception("Unexpected error during poll cycle")
        time.sleep(cfg.poll_interval_sec)


def main() -> int:
    parser = argparse.ArgumentParser(description="财联社关键词监测 + 钉钉/微信通知")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single fetch cycle and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and match without sending notifications",
    )
    parser.add_argument(
        "--test-notify",
        action="store_true",
        help="Send the latest keyword-matched article to verify notification",
    )
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.keywords:
        logger.error("No keywords configured. Set KEYWORDS in .env")
        return 1

    if not args.dry_run:
        error = validate_notify_config(cfg)
        if error:
            logger.error("%s. Copy .env.example to .env and configure it.", error)
            return 1

    store = StateStore(cfg.state_db_path)
    fetcher = ClsFetcher(rn=cfg.cls_rn)
    notifier = None
    if not args.dry_run:
        notifier = create_notifier(
            channel=cfg.notify_channel,
            dingtalk_webhook_urls=cfg.dingtalk_webhook_urls,
            dingtalk_secret=cfg.dingtalk_secret,
            wxpusher_app_token=cfg.wxpusher_app_token,
            wxpusher_topic_ids=cfg.wxpusher_topic_ids,
            wxpusher_uids=cfg.wxpusher_uids,
        )
        if notifier is None:
            logger.error("No notifier configured for NOTIFY_CHANNEL=%s", cfg.notify_channel)
            return 1

    try:
        if args.test_notify:
            test_fetcher = ClsFetcher(rn=max(cfg.cls_rn, 20))
            items = test_fetcher.fetch()
            matches = [
                match_keywords(item, cfg.keywords)
                for item in sorted(items, key=lambda i: i.ctime, reverse=True)
            ]
            matches = [m for m in matches if m]
            if not matches:
                logger.error("No articles matched keywords %s in latest fetch", cfg.keywords)
                return 1
            latest = matches[0]
            logger.info(
                "Test notify: id=%s keywords=%s url=%s",
                latest.item.id,
                latest.matched_keywords,
                latest.item.shareurl,
            )
            if notifier and notifier.send_match(latest):
                logger.info("Test notification sent")
            else:
                logger.error("Test notification failed")
                return 1
        elif args.once:
            run_once(cfg, store, fetcher, notifier)
        else:
            run_loop(cfg, store, fetcher, notifier)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        store.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
