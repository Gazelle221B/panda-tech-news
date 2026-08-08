"""Discord Webhook 投稿のユニットテスト (T9)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from karyu_tech_news.collect.normalize import FetchResult, RawItem
from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.deliver.discord import format_summary, post_summary
from karyu_tech_news.store.repo import (
    create_collect_run,
    create_db_engine,
    finish_collect_run,
    init_db,
    insert_items,
    update_source_health_failure,
    upsert_source,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def engine(db_path: Path) -> Engine:
    return create_db_engine(db_path)


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    init_db(engine)
    with Session(engine) as s:
        yield s
        s.rollback()


def _make_raw_item(source_id: str, key: str, fetched_at: datetime | None = None) -> RawItem:
    if fetched_at is None:
        fetched_at = datetime.now(UTC)
    return RawItem(
        item_key=key,
        external_id=None,
        title=f"Title {key}",
        link=f"https://{source_id}/{key}",
        summary=None,
        published_at=fetched_at,
        fetched_at=fetched_at,
        source_id=source_id,
        canonical_url_hash=f"hash-{source_id}-{key}",
        raw_json={"k": "v"},
    )


def test_format_summary_basic(session: Session) -> None:
    """基本的なサマリー形式が正しいことを確認."""
    config1 = SourceConfig(
        id="src1",
        name="Source 1",
        url="https://src1/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    config2 = SourceConfig(
        id="src2",
        name="Source 2",
        url="https://src2/feed",
        tier=SourceTier.SEMI_OFFICIAL,
        category=SourceCategory.TECH,
    )
    upsert_source(session, config1)
    upsert_source(session, config2)
    session.commit()

    started = datetime(2026, 6, 1, 14, 0, 0, tzinfo=UTC)
    run = create_collect_run(session, 2)
    run.started_at = started  # type: ignore[assignment]
    session.commit()

    fetched_at = started + timedelta(seconds=5)
    item1 = _make_raw_item("src1", "key1", fetched_at)
    item2 = _make_raw_item("src2", "key2", fetched_at)
    insert_items(session, [item1, item2])
    session.commit()

    finished = started + timedelta(seconds=12.3)
    results = [
        FetchResult(source_id="src1", ok=True, items=[item1], error=None, duration_ms=100),
        FetchResult(source_id="src2", ok=True, items=[item2], error=None, duration_ms=150),
    ]
    finish_collect_run(session, run, results, 2)
    run.finished_at = finished  # type: ignore[assignment]
    session.commit()

    summary = format_summary(session, run)

    assert "📰 華流テック通信 - 収集レポート" in summary
    assert "日時: 2026-06-01 23:00 JST" in summary
    assert "実行時間: 12.3秒" in summary
    assert "✅ 成功: 2/2 ソース" in summary
    assert "❌ 失敗: 0/2 ソース" in summary
    assert "📥 新規アイテム: 2件" in summary
    assert "Tier別:" in summary
    assert "- Tier1 公式: 1件" in summary
    assert "- Tier2 ニュース: 1件" in summary
    assert "カテゴリ別:" in summary
    assert "- AI: 1" in summary
    assert "- Tech: 1" in summary


def test_format_summary_with_unhealthy_sources(session: Session) -> None:
    """consecutive_failures >= 3 の警告が表示されることを確認."""
    config = SourceConfig(
        id="src1",
        name="Source 1",
        url="https://src1/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()

    for i in range(3):
        update_source_health_failure(session, "src1", f"error{i}", datetime.now(UTC))
    session.commit()

    run = create_collect_run(session, 1)
    run.started_at = datetime(2026, 6, 1, 14, 0, 0, tzinfo=UTC)  # type: ignore[assignment]
    run.finished_at = datetime(2026, 6, 1, 14, 0, 10, tzinfo=UTC)  # type: ignore[assignment]
    run.successful_sources = 0  # type: ignore[assignment]
    run.failed_sources = 1  # type: ignore[assignment]
    run.total_items = 0  # type: ignore[assignment]
    run.new_items = 0  # type: ignore[assignment]
    session.commit()

    summary = format_summary(session, run)

    assert "⚠️ 要対応:" in summary
    assert "- src1: consecutive_failures=3" in summary


def test_post_summary_success() -> None:
    """Webhook送信成功時にTrueを返すことを確認."""
    with patch("karyu_tech_news.deliver.discord.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = post_summary("https://discord.com/webhook", "test message")

    assert result is True
    mock_post.assert_called_once_with(
        "https://discord.com/webhook",
        # allowed_mentions: {"parse": []} で @everyone/@here/ロール mention を構造的に
        # 無効化する (Issue #98 フォローアップ3 terra レビュー指摘)。
        json={"content": "test message", "allowed_mentions": {"parse": []}},
        timeout=10.0,
    )


def test_post_summary_failure() -> None:
    """Webhook送信失敗時にFalseを返すことを確認 (fail-open, FR-071)."""
    with patch("karyu_tech_news.deliver.discord.httpx.post") as mock_post:
        mock_post.side_effect = Exception("Network error")

        result = post_summary("https://discord.com/webhook", "test message")

    assert result is False


def test_post_summary_empty_url() -> None:
    """Webhook URLが空の場合にFalseを返すことを確認."""
    result = post_summary("", "test message")
    assert result is False


def test_format_summary_jst_conversion(session: Session) -> None:
    """JST変換が正しく動作することを確認."""
    config = SourceConfig(
        id="src1",
        name="Source 1",
        url="https://src1/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()

    # UTC 2026-06-01 05:00:00 -> JST 2026-06-01 14:00:00
    started_utc = datetime(2026, 6, 1, 5, 0, 0, tzinfo=UTC)
    run = create_collect_run(session, 1)
    run.started_at = started_utc  # type: ignore[assignment]
    run.finished_at = started_utc + timedelta(seconds=5.0)  # type: ignore[assignment]
    run.successful_sources = 1  # type: ignore[assignment]
    run.failed_sources = 0  # type: ignore[assignment]
    run.total_items = 0  # type: ignore[assignment]
    run.new_items = 0  # type: ignore[assignment]
    session.commit()

    summary = format_summary(session, run)

    assert "日時: 2026-06-01 14:00 JST" in summary
    assert "実行時間: 5.0秒" in summary


def test_format_summary_excludes_items_after_finished_at(session: Session) -> None:
    """run終了後に保存されたitemがTier/カテゴリ集計に含まれないことを確認."""
    config = SourceConfig(
        id="src1",
        name="Source 1",
        url="https://src1/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()

    started = datetime(2026, 6, 1, 14, 0, 0, tzinfo=UTC)
    finished = started + timedelta(seconds=10.0)
    run = create_collect_run(session, 1)
    run.started_at = started  # type: ignore[assignment]
    run.finished_at = finished  # type: ignore[assignment]
    run.successful_sources = 1  # type: ignore[assignment]
    run.failed_sources = 0  # type: ignore[assignment]
    run.total_items = 1  # type: ignore[assignment]
    run.new_items = 1  # type: ignore[assignment]
    session.commit()

    # run期間内のitem
    item_in_run = _make_raw_item("src1", "key1", fetched_at=started + timedelta(seconds=5))
    insert_items(session, [item_in_run])
    session.commit()

    # run終了後のitem
    item_after_run = _make_raw_item("src1", "key2", fetched_at=finished + timedelta(seconds=5))
    insert_items(session, [item_after_run])
    session.commit()

    summary = format_summary(session, run)

    # new_itemsは1件
    assert "📥 新規アイテム: 1件" in summary
    # Tier/カテゴリ集計はrun期間内のitemのみ（1件）
    assert "- Tier1 公式: 1件" in summary
    assert "- AI: 1" in summary
    # 2件にはならない
    assert "- Tier1 公式: 2件" not in summary
    assert "- AI: 2" not in summary
