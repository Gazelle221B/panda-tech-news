"""store モジュールのユニットテスト."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session

from karyu_tech_news.collect.normalize import FetchResult, RawItem
from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.store.repo import (
    create_collect_run,
    create_db_engine,
    finish_collect_run,
    init_db,
    insert_items,
    update_source_health_failure,
    update_source_health_success,
    upsert_source,
)
from karyu_tech_news.store.schema import CollectRun, Item, Source, SourceHealth


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


def test_init_db_idempotent(engine: Engine) -> None:
    init_db(engine)
    init_db(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"sources", "items", "source_health", "collect_runs"}.issubset(tables)


def test_init_db_creates_all_tables(engine: Engine) -> None:
    init_db(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"sources", "items", "source_health", "collect_runs"}.issubset(tables)


def test_upsert_source_insert(session: Session) -> None:
    config = SourceConfig(
        id="test-src",
        name="Test",
        url="https://example.com/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    source = upsert_source(session, config)
    session.commit()
    assert source.id == "test-src"
    assert source.tier == 1
    db_source = session.get(Source, "test-src")
    assert db_source is not None
    assert db_source.name == "Test"


def test_upsert_source_update(session: Session) -> None:
    config = SourceConfig(
        id="test-src",
        name="Test",
        url="https://example.com/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()
    config.name = "Updated"
    config.tier = SourceTier.SEMI_OFFICIAL
    upsert_source(session, config)
    session.commit()
    db_source = session.get(Source, "test-src")
    assert db_source is not None
    assert db_source.name == "Updated"
    assert db_source.tier == 2


def test_insert_items_dedupe(session: Session) -> None:
    config = SourceConfig(
        id="src1",
        name="S1",
        url="https://x/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()
    now = datetime.now(UTC)
    item = RawItem(
        item_key="key1",
        external_id=None,
        title="Title",
        link="https://x/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash1",
        raw_json={"k": "v"},
    )
    count1 = insert_items(session, [item])
    session.commit()
    assert count1 == 1
    count2 = insert_items(session, [item])
    session.commit()
    assert count2 == 0
    items = session.query(Item).filter_by(source_id="src1").all()
    assert len(items) == 1


def test_insert_items_empty_key_rejected(session: Session) -> None:
    config = SourceConfig(
        id="src1",
        name="S1",
        url="https://x/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()
    now = datetime.now(UTC)
    item = RawItem(
        item_key="",
        external_id=None,
        title="Title",
        link="https://x/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash1",
        raw_json={},
    )
    with pytest.raises(ValueError, match="item_key is empty"):
        insert_items(session, [item])


def test_update_source_health_success(session: Session) -> None:
    config = SourceConfig(
        id="src1",
        name="S1",
        url="https://x/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()
    now = datetime.now(UTC)
    update_source_health_failure(session, "src1", "error1", now)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 1
    assert health.last_error == "error1"
    update_source_health_success(session, "src1", now)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 0
    assert health.last_error is None


def test_update_source_health_failure(session: Session) -> None:
    config = SourceConfig(
        id="src1",
        name="S1",
        url="https://x/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()
    now = datetime.now(UTC)
    update_source_health_failure(session, "src1", "error1", now)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 1
    assert health.last_error == "error1"
    update_source_health_failure(session, "src1", "error2", now)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 2
    assert health.last_error == "error2"


def test_collect_run_lifecycle(session: Session) -> None:
    run = create_collect_run(session, 2)
    session.commit()
    assert run.id is not None
    assert run.total_sources == 2
    assert run.finished_at is None
    results = [
        FetchResult(source_id="s1", ok=True, items=[], error=None, duration_ms=100),
        FetchResult(source_id="s2", ok=False, items=[], error="err", duration_ms=50),
    ]
    finish_collect_run(session, run, results, 5)
    session.commit()
    db_run = session.get(CollectRun, run.id)
    assert db_run is not None
    assert db_run.finished_at is not None
    assert db_run.successful_sources == 1
    assert db_run.failed_sources == 1
    assert db_run.new_items == 5


def test_insert_items_rejects_orphan_source_id(session: Session) -> None:
    from sqlalchemy.exc import IntegrityError

    now = datetime.now(UTC)
    item = RawItem(
        item_key="orphan-key",
        external_id=None,
        title="Orphan",
        link="https://orphan/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="nonexistent-source",
        canonical_url_hash="hash-orphan",
        raw_json={},
    )
    with pytest.raises(IntegrityError):
        insert_items(session, [item])
        session.commit()


def test_update_source_health_rejects_orphan_source_id(session: Session) -> None:
    from sqlalchemy.exc import IntegrityError

    now = datetime.now(UTC)
    with pytest.raises(IntegrityError):
        update_source_health_failure(session, "nonexistent-source", "error", now)
        session.commit()


def test_finish_collect_run_rejects_total_sources_mismatch(session: Session) -> None:
    run = create_collect_run(session, 3)
    session.commit()
    results = [
        FetchResult(source_id="s1", ok=True, items=[], error=None, duration_ms=100),
        FetchResult(source_id="s2", ok=False, items=[], error="err", duration_ms=50),
    ]
    with pytest.raises(ValueError, match="total_sources mismatch"):
        finish_collect_run(session, run, results, 0)
