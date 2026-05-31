"""RSS/RSSHub フィード取得."""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import feedparser  # type: ignore[import-untyped]
import httpx

from karyu_tech_news.collect.normalize import FetchResult, normalize_entry
from karyu_tech_news.config import SourceConfig

logger = logging.getLogger(__name__)

USER_AGENT = "karyu-tech-news/0.1"
TIMEOUT_SECONDS = 30
MAX_RETRIES = 2


def expand_rsshub_url(url: str, rsshub_base_url: str) -> str:
    """http://localhost:1200 を rsshub_base_url で置換."""
    prefix = "http://localhost:1200"
    if url.startswith(prefix):
        return rsshub_base_url.rstrip("/") + url[len(prefix):]
    return url


def _fetch_with_retry(url: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_SECONDS,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                logger.info("retry %d/%d for %s: %s", attempt + 1, MAX_RETRIES, url, exc)
            continue
    raise last_exc  # type: ignore[misc]


def _parse_feed(text: str, source_id: str) -> FetchResult:
    start = time.monotonic()
    feed = feedparser.parse(text)
    fetched_at = datetime.now(UTC)

    if feed.bozo and len(feed.entries) == 0:
        elapsed = int((time.monotonic() - start) * 1000)
        bozo_exc = feed.get("bozo_exception", "unknown")
        return FetchResult(
            source_id=source_id,
            ok=False,
            items=[],
            error=f"bozo=1 with no entries: {bozo_exc}",
            duration_ms=elapsed,
        )

    items = [normalize_entry(entry, source_id, fetched_at) for entry in feed.entries]
    elapsed = int((time.monotonic() - start) * 1000)
    return FetchResult(
        source_id=source_id,
        ok=True,
        items=items,
        error=None,
        duration_ms=elapsed,
    )


def fetch_one(source: SourceConfig, rsshub_base_url: str) -> FetchResult:
    """1ソースを取得して FetchResult を返す. fail-open."""
    url = expand_rsshub_url(source.url, rsshub_base_url)
    start = time.monotonic()

    try:
        text = _fetch_with_retry(url)
        return _parse_feed(text, source.id)
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.monotonic() - start) * 1000)
        logger.warning("fetch failed: %s: %s", source.id, exc)
        return FetchResult(
            source_id=source.id,
            ok=False,
            items=[],
            error=str(exc),
            duration_ms=elapsed,
        )
