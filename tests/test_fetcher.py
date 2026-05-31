"""collect.fetcher のユニットテスト."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from karyu_tech_news.collect.fetcher import (
    MAX_RETRIES,
    TIMEOUT_SECONDS,
    USER_AGENT,
    expand_rsshub_url,
    fetch_one,
)
from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier

MOCK_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test Feed</title>
<item>
<title>Article 1</title>
<link>https://example.com/1</link>
<guid>entry-1</guid>
<description>Summary 1</description>
</item>
<item>
<title>Article 2</title>
<link>https://example.com/2</link>
<guid>entry-2</guid>
<description>Summary 2</description>
</item>
</channel>
</rss>"""

MOCK_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Test Atom</title>
<entry>
<title>Release v1.0</title>
<link href="https://github.com/test/repo/releases/tag/v1.0"/>
<id>tag:github.com,2008:Repository/test</id>
<summary>First release</summary>
</entry>
</feed>"""

MOCK_BOZO_EMPTY = """this is not xml at all, just random text that will confuse feedparser"""


def _make_source(url: str = "https://example.com/feed", id_: str = "test-src") -> SourceConfig:
    return SourceConfig(
        id=id_,
        name="Test",
        url=url,
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )


def test_expand_rsshub_url() -> None:
    assert expand_rsshub_url(
        "http://localhost:1200/juejin/category/ai",
        "http://myhost:1200",
    ) == "http://myhost:1200/juejin/category/ai"


def test_expand_rsshub_url_trailing_slash() -> None:
    assert expand_rsshub_url(
        "http://localhost:1200/juejin/category/ai",
        "http://myhost:1200/",
    ) == "http://myhost:1200/juejin/category/ai"


def test_expand_rsshub_url_no_match() -> None:
    url = "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"
    assert expand_rsshub_url(url, "http://myhost:1200") == url


def test_fetch_one_success() -> None:
    source = _make_source()
    mock_resp = MagicMock()
    mock_resp.text = MOCK_RSS
    mock_resp.raise_for_status = MagicMock()

    with patch("karyu_tech_news.collect.fetcher.httpx.get", return_value=mock_resp) as mock_get:
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is True
    assert result.source_id == "test-src"
    assert len(result.items) == 2
    assert result.items[0].title == "Article 1"
    assert result.items[0].item_key == "entry-1"
    assert result.error is None
    assert result.duration_ms >= 0
    mock_get.assert_called_once_with(
        "https://example.com/feed",
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def test_fetch_one_atom_feed() -> None:
    source = _make_source(url="https://github.com/test/repo/releases.atom")
    mock_resp = MagicMock()
    mock_resp.text = MOCK_ATOM
    mock_resp.raise_for_status = MagicMock()

    with patch("karyu_tech_news.collect.fetcher.httpx.get", return_value=mock_resp):
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is True
    assert len(result.items) == 1
    assert result.items[0].title == "Release v1.0"


def test_fetch_one_bozo_with_entries_adopted() -> None:
    bozo_with_entries = """<?xml version="1.0"?>
<rss version="2.0">
<channel><title>Bozo</title>
<item><title>OK</title><link>https://x/1</link><guid>g1</guid></item>
</channel></rss>"""
    source = _make_source()
    mock_resp = MagicMock()
    mock_resp.text = bozo_with_entries
    mock_resp.raise_for_status = MagicMock()

    with patch("karyu_tech_news.collect.fetcher.httpx.get", return_value=mock_resp):
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is True
    assert len(result.items) == 1


def test_fetch_one_bozo_no_entries_failed() -> None:
    source = _make_source()
    mock_resp = MagicMock()
    mock_resp.text = MOCK_BOZO_EMPTY
    mock_resp.raise_for_status = MagicMock()

    with patch("karyu_tech_news.collect.fetcher.httpx.get", return_value=mock_resp):
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is False
    assert result.items == []
    assert result.error is not None
    assert "bozo" in result.error


def test_fetch_one_timeout_retries_then_succeeds() -> None:
    source = _make_source()
    mock_resp = MagicMock()
    mock_resp.text = MOCK_RSS
    mock_resp.raise_for_status = MagicMock()

    with patch(
        "karyu_tech_news.collect.fetcher.httpx.get",
        side_effect=[
            httpx.TimeoutException("timeout 1"),
            httpx.TimeoutException("timeout 2"),
            mock_resp,
        ],
    ) as mock_get:
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is True
    assert len(result.items) == 2
    assert mock_get.call_count == MAX_RETRIES + 1


def test_fetch_one_timeout_retries_exhausted() -> None:
    source = _make_source()

    with patch(
        "karyu_tech_news.collect.fetcher.httpx.get",
        side_effect=httpx.TimeoutException("timeout"),
    ) as mock_get:
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is False
    assert result.items == []
    assert "timeout" in (result.error or "")
    assert mock_get.call_count == MAX_RETRIES + 1


def test_fetch_one_fail_open_wraps_exception() -> None:
    source = _make_source()

    with patch(
        "karyu_tech_news.collect.fetcher.httpx.get",
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock()),
    ):
        result = fetch_one(source, "http://localhost:1200")

    assert result.ok is False
    assert result.items == []
    assert result.error is not None


def test_fetch_one_rsshub_url_expanded() -> None:
    source = _make_source(url="http://localhost:1200/juejin/category/ai")
    mock_resp = MagicMock()
    mock_resp.text = MOCK_RSS
    mock_resp.raise_for_status = MagicMock()

    with patch("karyu_tech_news.collect.fetcher.httpx.get", return_value=mock_resp) as mock_get:
        result = fetch_one(source, "http://rsshub:1200")

    assert result.ok is True
    mock_get.assert_called_once_with(
        "http://rsshub:1200/juejin/category/ai",
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def test_user_agent_and_timeout_constants() -> None:
    assert USER_AGENT == "karyu-tech-news/0.1"
    assert TIMEOUT_SECONDS == 30
    assert MAX_RETRIES == 2
