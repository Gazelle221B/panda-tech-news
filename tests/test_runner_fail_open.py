"""collect runner (fail-open 統合) のユニットテスト (T8)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from karyu_tech_news.collect.normalize import FetchResult, RawItem
from karyu_tech_news.collect.runner import run_collect
from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.store.repo import (
    create_db_engine,
    init_db,
    upsert_source,
)
from karyu_tech_news.store.schema import Item, SourceHealth


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


@pytest.fixture
def setup_sources(session: Session) -> list[SourceConfig]:
    configs = [
        SourceConfig(
            id="src1",
            name="Source 1",
            url="https://src1/feed",
            tier=SourceTier.OFFICIAL,
            category=SourceCategory.AI,
        ),
        SourceConfig(
            id="src2",
            name="Source 2",
            url="https://src2/feed",
            tier=SourceTier.SEMI_OFFICIAL,
            category=SourceCategory.TECH,
        ),
        SourceConfig(
            id="src3",
            name="Source 3",
            url="https://src3/feed",
            tier=SourceTier.COMMUNITY,
            category=SourceCategory.GAME,
        ),
    ]
    for config in configs:
        upsert_source(session, config)
    session.commit()
    return configs


def _make_raw_item(source_id: str, key: str) -> RawItem:
    now = datetime.now(UTC)
    return RawItem(
        item_key=key,
        external_id=None,
        title=f"Title {key}",
        link=f"https://{source_id}/{key}",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id=source_id,
        canonical_url_hash=f"hash-{source_id}-{key}",
        raw_json={"k": "v"},
    )


def test_run_collect_all_success(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    sources = setup_sources
    item1 = _make_raw_item("src1", "key1")
    item2 = _make_raw_item("src2", "key2")
    item3 = _make_raw_item("src3", "key3")

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch:
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=True, items=[item1], error=None, duration_ms=100),
            FetchResult(source_id="src2", ok=True, items=[item2], error=None, duration_ms=150),
            FetchResult(source_id="src3", ok=True, items=[item3], error=None, duration_ms=200),
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    assert run is not None
    assert run.total_sources == 3
    assert run.successful_sources == 3
    assert run.failed_sources == 0
    assert run.total_items == 3
    assert run.new_items == 3
    assert run.finished_at is not None

    items = session.query(Item).all()
    assert len(items) == 3

    for src_id in ["src1", "src2", "src3"]:
        health = session.get(SourceHealth, src_id)
        assert health is not None
        assert health.consecutive_failures == 0


def test_run_collect_one_failure_continues(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    sources = setup_sources
    item1 = _make_raw_item("src1", "key1")
    item3 = _make_raw_item("src3", "key3")

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch:
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=True, items=[item1], error=None, duration_ms=100),
            FetchResult(source_id="src2", ok=False, items=[], error="timeout", duration_ms=30000),
            FetchResult(source_id="src3", ok=True, items=[item3], error=None, duration_ms=200),
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    assert run is not None
    assert run.total_sources == 3
    assert run.successful_sources == 2
    assert run.failed_sources == 1
    assert run.total_items == 2
    assert run.new_items == 2
    assert run.finished_at is not None

    items = session.query(Item).all()
    assert len(items) == 2
    assert {item.source_id for item in items} == {"src1", "src3"}

    health1 = session.get(SourceHealth, "src1")
    assert health1 is not None
    assert health1.consecutive_failures == 0

    health2 = session.get(SourceHealth, "src2")
    assert health2 is not None
    assert health2.consecutive_failures == 1
    assert health2.last_error == "timeout"

    health3 = session.get(SourceHealth, "src3")
    assert health3 is not None
    assert health3.consecutive_failures == 0


def test_run_collect_multiple_failures(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    sources = setup_sources
    item2 = _make_raw_item("src2", "key2")

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch:
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=False, items=[], error="error1", duration_ms=100),
            FetchResult(source_id="src2", ok=True, items=[item2], error=None, duration_ms=150),
            FetchResult(source_id="src3", ok=False, items=[], error="error3", duration_ms=200),
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    assert run is not None
    assert run.total_sources == 3
    assert run.successful_sources == 1
    assert run.failed_sources == 2
    assert run.total_items == 1
    assert run.new_items == 1
    assert run.finished_at is not None

    items = session.query(Item).all()
    assert len(items) == 1
    assert items[0].source_id == "src2"

    health1 = session.get(SourceHealth, "src1")
    assert health1 is not None
    assert health1.consecutive_failures == 1

    health2 = session.get(SourceHealth, "src2")
    assert health2 is not None
    assert health2.consecutive_failures == 0

    health3 = session.get(SourceHealth, "src3")
    assert health3 is not None
    assert health3.consecutive_failures == 1


def test_run_collect_all_fail(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    sources = setup_sources

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch:
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=False, items=[], error="error1", duration_ms=100),
            FetchResult(source_id="src2", ok=False, items=[], error="error2", duration_ms=150),
            FetchResult(source_id="src3", ok=False, items=[], error="error3", duration_ms=200),
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    assert run is not None
    assert run.total_sources == 3
    assert run.successful_sources == 0
    assert run.failed_sources == 3
    assert run.total_items == 0
    assert run.new_items == 0
    assert run.finished_at is not None

    items = session.query(Item).all()
    assert len(items) == 0

    for src_id in ["src1", "src2", "src3"]:
        health = session.get(SourceHealth, src_id)
        assert health is not None
        assert health.consecutive_failures == 1


def test_run_collect_empty_sources(session: Session) -> None:
    run = run_collect(session, [], "http://localhost:1200")

    assert run is not None
    assert run.total_sources == 0
    assert run.successful_sources == 0
    assert run.failed_sources == 0
    assert run.total_items == 0
    assert run.new_items == 0
    assert run.finished_at is not None


def test_run_collect_db_error_continues(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    sources = setup_sources
    item1 = _make_raw_item("src1", "key1")
    item2 = _make_raw_item("src2", "key2")
    item3 = _make_raw_item("src3", "key3")

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch, patch(
        "karyu_tech_news.collect.runner.insert_items"
    ) as mock_insert:
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=True, items=[item1], error=None, duration_ms=100),
            FetchResult(source_id="src2", ok=True, items=[item2], error=None, duration_ms=150),
            FetchResult(source_id="src3", ok=True, items=[item3], error=None, duration_ms=200),
        ]
        mock_insert.side_effect = [
            1,
            Exception("db error"),
            1,
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    assert run is not None
    assert run.total_sources == 3
    assert run.successful_sources == 2
    assert run.failed_sources == 1
    assert run.total_items == 3
    assert run.new_items == 2
    assert run.finished_at is not None

    health1 = session.get(SourceHealth, "src1")
    assert health1 is not None
    assert health1.consecutive_failures == 0

    health2 = session.get(SourceHealth, "src2")
    assert health2 is not None
    assert health2.consecutive_failures == 1
    assert health2.last_error is not None
    assert "db error" in health2.last_error

    health3 = session.get(SourceHealth, "src3")
    assert health3 is not None
    assert health3.consecutive_failures == 0


def test_run_collect_mocked_insert_integrity_error(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    """insert_items()をモックしてIntegrityErrorを送出した場合でもfail-openが機能することを確認するテスト.

    insert_items()をモックしてIntegrityErrorを発生させ、session.rollback()が正しく
    呼ばれ、後続のsrc3が処理されることを確認する。
    """
    from sqlalchemy.exc import IntegrityError

    sources = setup_sources
    item1 = _make_raw_item("src1", "key1")
    item2 = _make_raw_item("src2", "key2")
    item3 = _make_raw_item("src3", "key3")

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch, patch(
        "karyu_tech_news.collect.runner.insert_items"
    ) as mock_insert:
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=True, items=[item1], error=None, duration_ms=100),
            FetchResult(source_id="src2", ok=True, items=[item2], error=None, duration_ms=150),
            FetchResult(source_id="src3", ok=True, items=[item3], error=None, duration_ms=200),
        ]
        # src2でIntegrityErrorを発生させる
        mock_insert.side_effect = [
            1,  # src1: 成功
            IntegrityError("statement", {}, Exception("UNIQUE constraint failed")),  # src2: 失敗
            1,  # src3: 成功
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    # collect_runsが完了していることを確認
    assert run is not None
    assert run.total_sources == 3
    assert run.finished_at is not None

    # src1とsrc3は成功、src2は失敗
    assert run.successful_sources == 2
    assert run.failed_sources == 1

    # src2のsource_healthが失敗として記録されている
    health2 = session.get(SourceHealth, "src2")
    assert health2 is not None
    assert health2.consecutive_failures == 1
    assert health2.last_error is not None

    # src1とsrc3は成功
    health1 = session.get(SourceHealth, "src1")
    assert health1 is not None
    assert health1.consecutive_failures == 0

    health3 = session.get(SourceHealth, "src3")
    assert health3 is not None
    assert health3.consecutive_failures == 0


def test_run_collect_new_items_matches_persisted_on_commit_failure(
    session: Session, setup_sources: list[SourceConfig]
) -> None:
    """実SQLiteのcommit失敗時にrun.new_itemsが保存済みItem件数と一致することを確認する回帰テスト.

    session.commit()をモックして特定の呼び出しで失敗させ、total_new_itemsへの加算が
    commit成功後にのみ行われることを確認する。
    """
    from sqlalchemy.exc import IntegrityError

    sources = setup_sources
    item1 = _make_raw_item("src1", "key1")
    item2 = _make_raw_item("src2", "key2")
    item3 = _make_raw_item("src3", "key3")

    original_commit = session.commit
    commit_call_count = [0]

    def mock_commit() -> None:
        commit_call_count[0] += 1
        # 3回目のcommit（create_collect_runの1回 + src1の1回 + src2の1回）で失敗させる
        if commit_call_count[0] == 3:
            raise IntegrityError("statement", {}, Exception("UNIQUE constraint failed"))
        original_commit()

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch, patch.object(
        session, "commit", side_effect=mock_commit
    ):
        mock_fetch.side_effect = [
            FetchResult(source_id="src1", ok=True, items=[item1], error=None, duration_ms=100),
            FetchResult(source_id="src2", ok=True, items=[item2], error=None, duration_ms=150),
            FetchResult(source_id="src3", ok=True, items=[item3], error=None, duration_ms=200),
        ]
        run = run_collect(session, sources, "http://localhost:1200")

    # collect_runsが完了していることを確認
    assert run is not None
    assert run.total_sources == 3
    assert run.finished_at is not None

    # 保存済みItem件数を確認
    persisted_items = session.query(Item).count()

    # run.new_itemsが保存済みItem件数と一致することを確認
    assert run.new_items == persisted_items
    assert run.new_items == 2  # src1とsrc3のアイテムのみ保存されている
