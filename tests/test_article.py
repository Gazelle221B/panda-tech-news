"""collect.article のユニットテスト (T61, Issue #61)."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest

from karyu_tech_news.collect.article import (
    MAX_RETRIES,
    MIN_EXTRACTED_CHARS,
    TIMEOUT_SECONDS,
    USER_AGENT,
    fetch_article_text,
)

URL = "https://example.com/news/article-1"


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def test_fetch_article_text_success() -> None:
    resp = _mock_response("<html><body>記事本文</body></html>")
    extracted = "本文" * (MIN_EXTRACTED_CHARS // 2 + 5)  # MIN_EXTRACTED_CHARS 以上

    with patch("karyu_tech_news.collect.article.httpx.get", return_value=resp) as mock_get, \
         patch("trafilatura.extract", return_value=extracted) as mock_extract:
        result = fetch_article_text(URL)

    assert result == extracted
    mock_get.assert_called_once_with(
        URL,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    mock_extract.assert_called_once_with(resp.text)


def test_fetch_article_text_http_error_returns_none() -> None:
    with patch(
        "karyu_tech_news.collect.article.httpx.get",
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock()),
    ) as mock_get:
        result = fetch_article_text(URL)

    assert result is None
    assert mock_get.call_count == MAX_RETRIES + 1


def test_fetch_article_text_timeout_returns_none() -> None:
    with patch(
        "karyu_tech_news.collect.article.httpx.get",
        side_effect=httpx.TimeoutException("timeout"),
    ) as mock_get:
        result = fetch_article_text(URL)

    assert result is None
    assert mock_get.call_count == MAX_RETRIES + 1


def test_fetch_article_text_extraction_none_returns_none() -> None:
    resp = _mock_response("<html><body>薄い</body></html>")

    with patch("karyu_tech_news.collect.article.httpx.get", return_value=resp), \
         patch("trafilatura.extract", return_value=None):
        result = fetch_article_text(URL)

    assert result is None


def test_fetch_article_text_too_short_returns_none() -> None:
    resp = _mock_response("<html><body>短い</body></html>")
    short_text = "x" * (MIN_EXTRACTED_CHARS - 1)

    with patch("karyu_tech_news.collect.article.httpx.get", return_value=resp), \
         patch("trafilatura.extract", return_value=short_text):
        result = fetch_article_text(URL)

    assert result is None


def test_fetch_article_text_exactly_min_chars_is_kept() -> None:
    resp = _mock_response("<html><body>ちょうど</body></html>")
    text = "x" * MIN_EXTRACTED_CHARS

    with patch("karyu_tech_news.collect.article.httpx.get", return_value=resp), \
         patch("trafilatura.extract", return_value=text):
        result = fetch_article_text(URL)

    assert result == text


def test_fetch_article_text_trafilatura_not_installed_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resp = _mock_response("<html><body>本文</body></html>")
    # sys.modules[name] = None は import 文を ImportError にする標準的な手法
    # (trafilatura 未導入環境の遅延 import 失敗をシミュレート)。
    monkeypatch.setitem(sys.modules, "trafilatura", None)

    with patch("karyu_tech_news.collect.article.httpx.get", return_value=resp):
        result = fetch_article_text(URL)

    assert result is None
