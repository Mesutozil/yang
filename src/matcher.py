from __future__ import annotations

from dataclasses import dataclass

from src.cls_fetcher import TelegraphItem


@dataclass(frozen=True)
class MatchResult:
    item: TelegraphItem
    matched_keywords: list[str]


def match_keywords(item: TelegraphItem, keywords: list[str]) -> MatchResult | None:
    if not keywords:
        return None

    text = f"{item.title} {item.content}"
    matched = [kw for kw in keywords if kw in text]
    if not matched:
        return None

    return MatchResult(item=item, matched_keywords=matched)


def keyword_excerpt(text: str, keyword: str, radius: int = 40) -> str:
    idx = text.find(keyword)
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(keyword) + radius)
    snippet = text[start:end].replace("\n", " ")
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"
