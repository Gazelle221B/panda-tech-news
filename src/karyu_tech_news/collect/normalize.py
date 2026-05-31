"""feedparser entry の RawItem 正規化."""
from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel


class RawItem(BaseModel):
    """取得した記事・リリース・投稿の1件."""

    item_key: str
    external_id: str | None
    title: str
    link: str
    summary: str | None
    published_at: datetime | None
    fetched_at: datetime
    source_id: str
    canonical_url_hash: str
    raw_json: dict[str, Any]


class FetchResult(BaseModel):
    """1ソース取得の成否・items・error・所要時間を包む値オブジェクト."""

    source_id: str
    ok: bool
    items: list[RawItem]
    error: str | None
    duration_ms: int


def _time_struct_to_datetime(t: time.struct_time) -> datetime:
    return datetime(*t[:6], tzinfo=UTC)


def compute_canonical_url_hash(url: str) -> str:
    """URL を正規化して sha256.

    正規化: scheme/host 小文字化, 末尾スラッシュ除去, UTM パラメータ除去, クエリソート.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    host = host.lower()
    port = f":{parts.port}" if parts.port and parts.port not in (80, 443) else ""
    path = parts.path.rstrip("/") or "/"

    query_params = parse_qs(parts.query, keep_blank_values=True)
    filtered = {k: v for k, v in query_params.items() if not k.startswith("utm_")}
    sorted_query = urlencode(sorted(filtered.items()), doseq=True)

    normalized = urlunsplit((scheme, f"{host}{port}", path, sorted_query, ""))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_item_key(
    external_id: str | None,
    link: str,
    title: str,
    published_at: datetime | None,
    source_id: str,
) -> str:
    """FR-021: external_id → link → sha256(title|published_at|source_id)."""
    if external_id:
        return external_id
    if link:
        return link
    pub_str = published_at.isoformat() if published_at else ""
    raw = f"{title}|{pub_str}|{source_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_entry_text(entry: dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = entry.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            return val
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, dict):
                return str(first.get("value", ""))
            return str(first)
        if isinstance(val, dict):
            return str(val.get("value", ""))
    return ""


def _extract_published_at(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t is not None:
            try:
                return _time_struct_to_datetime(t)
            except (TypeError, ValueError):
                continue
    return None


def normalize_entry(
    entry: dict[str, Any], source_id: str, fetched_at: datetime
) -> RawItem:
    """feedparser の entry dict を RawItem に変換."""
    external_id_raw = entry.get("id") or entry.get("guid") or ""
    external_id = str(external_id_raw) if external_id_raw else None

    link = _extract_entry_text(entry, "link")
    title = _extract_entry_text(entry, "title")
    summary = _extract_entry_text(entry, "summary", "description") or None
    published_at = _extract_published_at(entry)

    item_key = generate_item_key(
        external_id=external_id,
        link=link,
        title=title,
        published_at=published_at,
        source_id=source_id,
    )

    if not item_key:
        msg = f"item_key is empty for source={source_id}, title={title!r}"
        raise ValueError(msg)

    canonical_url_hash = compute_canonical_url_hash(link) if link else ""

    raw_json: dict[str, Any] = {}
    for k, v in entry.items():
        try:
            if isinstance(v, time.struct_time):
                raw_json[k] = list(v)
            else:
                raw_json[k] = v
        except Exception:  # noqa: BLE001
            raw_json[k] = str(v)

    return RawItem(
        item_key=item_key,
        external_id=external_id,
        title=title,
        link=link,
        summary=summary,
        published_at=published_at,
        fetched_at=fetched_at,
        source_id=source_id,
        canonical_url_hash=canonical_url_hash,
        raw_json=raw_json,
    )
