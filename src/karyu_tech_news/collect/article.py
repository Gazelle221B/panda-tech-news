"""記事本文ページの取得 (T61, Issue #61 薄記事素材強化).

RSS の summary がティザー1行しかない薄い候補だけ、edit/enrich.py がこのモジュールを
使って記事本文ページを直接フェッチし、editor 判定・writer 生成の素材を補う。
取得した本文はメモリ内でのみ使用し、DB へは保存しない (要件 §9.6 法務: 記事本文の
転載禁止、要約素材としてのみ利用)。

collect/fetcher.py の流儀 (UA・タイムアウト 30 秒・リトライ 2 回) を踏襲する。
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "karyu-tech-news/0.1"
TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2
MIN_EXTRACTED_CHARS = 100  # これ未満は素材として使えない薄い抽出扱い (fail-open)


def _fetch_with_retry(url: str, timeout: float) -> str | None:
    """HTML を取得する. fail-open (fetcher.py と異なり例外を投げず None を返す)."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                logger.info("retry %d/%d for article %s: %s", attempt + 1, MAX_RETRIES, url, exc)
            continue
    logger.warning("article fetch failed: %s: %s", url, last_exc)
    return None


def fetch_article_text(url: str, *, timeout: float = TIMEOUT_SECONDS) -> str | None:
    """記事本文ページを取得し、trafilatura で本文を抽出する.

    失敗 (HTTP エラー・タイムアウト・非 HTML・抽出失敗・短すぎる本文) はすべて
    None を返す fail-open。trafilatura は関数内で遅延 import する
    (未導入でも collect モジュール自体の import は壊さない, kokoro/pydub の
    遅延 import 流儀)。非 HTML なページを渡した場合は trafilatura.extract が
    None を返す (別途 content-type 判定はしない)。
    """
    html = _fetch_with_retry(url, timeout)
    if html is None:
        return None

    try:
        import trafilatura
    except ImportError:
        logger.warning("trafilatura 未導入のため本文抽出をスキップ: %s", url)
        return None

    try:
        extracted = trafilatura.extract(html)
    except Exception as exc:  # noqa: BLE001
        logger.warning("trafilatura extraction failed for %s: %s", url, exc)
        return None

    if extracted is None or len(extracted.strip()) < MIN_EXTRACTED_CHARS:
        return None
    return extracted.strip()
