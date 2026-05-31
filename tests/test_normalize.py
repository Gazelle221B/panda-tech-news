"""collect.normalize のユニットテスト."""
from __future__ import annotations

import time
from datetime import UTC, datetime

from karyu_tech_news.collect.normalize import (
    FetchResult,
    RawItem,
    compute_canonical_url_hash,
    generate_item_key,
    normalize_entry,
)


def test_item_key_from_external_id() -> None:
    assert generate_item_key("ext-123", "https://x", "t", None, "s") == "ext-123"


def test_item_key_from_link() -> None:
    assert generate_item_key(None, "https://example.com/post/1", "t", None, "s") == "https://example.com/post/1"


def test_item_key_from_hash() -> None:
    key = generate_item_key(None, "", "title", None, "src")
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_item_key_never_empty() -> None:
    key = generate_item_key(None, "", "", None, "s")
    assert key != ""


def test_canonical_url_hash_strips_utm() -> None:
    a = compute_canonical_url_hash("https://example.com/page?utm_source=twitter&id=1")
    b = compute_canonical_url_hash("https://example.com/page?id=1")
    assert a == b


def test_canonical_url_hash_normalizes_case() -> None:
    a = compute_canonical_url_hash("HTTPS://Example.COM/page")
    b = compute_canonical_url_hash("https://example.com/page")
    assert a == b


def test_canonical_url_hash_strips_trailing_slash() -> None:
    a = compute_canonical_url_hash("https://example.com/page/")
    b = compute_canonical_url_hash("https://example.com/page")
    assert a == b


def test_canonical_url_hash_sorts_query() -> None:
    a = compute_canonical_url_hash("https://example.com/?b=2&a=1")
    b = compute_canonical_url_hash("https://example.com/?a=1&b=2")
    assert a == b


def test_normalize_entry_basic() -> None:
    ts = time.strptime("2026-05-30 12:00:00", "%Y-%m-%d %H:%M:%S")
    entry = {
        "id": "entry-1",
        "title": "Test Title",
        "link": "https://example.com/1",
        "summary": "Summary text",
        "published_parsed": ts,
    }
    fetched = datetime(2026, 5, 30, 13, 0, 0, tzinfo=UTC)
    item = normalize_entry(entry, "test-source", fetched)

    assert isinstance(item, RawItem)
    assert item.item_key == "entry-1"
    assert item.external_id == "entry-1"
    assert item.title == "Test Title"
    assert item.link == "https://example.com/1"
    assert item.summary == "Summary text"
    assert item.source_id == "test-source"
    assert item.fetched_at == fetched
    assert item.published_at is not None
    assert item.canonical_url_hash != ""


def test_normalize_entry_published_parsed() -> None:
    ts = time.strptime("2026-01-15 08:30:00", "%Y-%m-%d %H:%M:%S")
    entry = {"title": "T", "link": "https://x", "published_parsed": ts}
    fetched = datetime(2026, 5, 30, tzinfo=UTC)
    item = normalize_entry(entry, "s", fetched)
    assert item.published_at == datetime(2026, 1, 15, 8, 30, 0, tzinfo=UTC)


def test_normalize_entry_no_summary() -> None:
    entry = {"title": "T", "link": "https://x"}
    fetched = datetime(2026, 5, 30, tzinfo=UTC)
    item = normalize_entry(entry, "s", fetched)
    assert item.summary is None


def test_fetch_result_model() -> None:
    r = FetchResult(source_id="s", ok=True, items=[], error=None, duration_ms=100)
    assert r.ok is True
    assert r.items == []
