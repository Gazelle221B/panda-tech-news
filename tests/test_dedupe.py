"""seen 管理 / dedupe のユニットテスト (T6)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from karyu_tech_news.collect.normalize import RawItem
from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.store.repo import (
    create_db_engine,
    init_db,
    insert_items,
    upsert_source,
)
from karyu_tech_news.store.schema import Item


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
def setup_sources(session: Session) -> None:
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


def test_dedupe_same_source_same_key(session: Session, setup_sources: None) -> None:
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
    items = session.query(Item).filter_by(source_id="src1", item_key="key1").all()
    assert len(items) == 1


def test_dedupe_different_source_same_key(session: Session, setup_sources: None) -> None:
    now = datetime.now(UTC)
    item1 = RawItem(
        item_key="shared-key",
        external_id=None,
        title="Title from src1",
        link="https://src1/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash1",
        raw_json={"source": "src1"},
    )
    item2 = RawItem(
        item_key="shared-key",
        external_id=None,
        title="Title from src2",
        link="https://src2/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src2",
        canonical_url_hash="hash2",
        raw_json={"source": "src2"},
    )
    count1 = insert_items(session, [item1])
    session.commit()
    assert count1 == 1
    count2 = insert_items(session, [item2])
    session.commit()
    assert count2 == 1
    items_src1 = session.query(Item).filter_by(source_id="src1").all()
    items_src2 = session.query(Item).filter_by(source_id="src2").all()
    assert len(items_src1) == 1
    assert len(items_src2) == 1


def test_dedupe_same_source_different_keys(session: Session, setup_sources: None) -> None:
    now = datetime.now(UTC)
    item1 = RawItem(
        item_key="key1",
        external_id=None,
        title="Title 1",
        link="https://x/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash1",
        raw_json={"id": 1},
    )
    item2 = RawItem(
        item_key="key2",
        external_id=None,
        title="Title 2",
        link="https://x/2",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash2",
        raw_json={"id": 2},
    )
    count = insert_items(session, [item1, item2])
    session.commit()
    assert count == 2
    items = session.query(Item).filter_by(source_id="src1").all()
    assert len(items) == 2


def test_dedupe_batch_insert_mixed(session: Session, setup_sources: None) -> None:
    now = datetime.now(UTC)
    item1 = RawItem(
        item_key="key1",
        external_id=None,
        title="Title 1",
        link="https://x/1",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash1",
        raw_json={"id": 1},
    )
    count1 = insert_items(session, [item1])
    session.commit()
    assert count1 == 1
    item2 = RawItem(
        item_key="key2",
        external_id=None,
        title="Title 2",
        link="https://x/2",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash2",
        raw_json={"id": 2},
    )
    item1_dup = RawItem(
        item_key="key1",
        external_id=None,
        title="Title 1 Updated",
        link="https://x/1-updated",
        summary="Updated summary",
        published_at=now,
        fetched_at=now,
        source_id="src1",
        canonical_url_hash="hash1-updated",
        raw_json={"id": 1, "updated": True},
    )
    count2 = insert_items(session, [item2, item1_dup])
    session.commit()
    assert count2 == 1
    items = session.query(Item).filter_by(source_id="src1").all()
    assert len(items) == 2
    item1_db = session.query(Item).filter_by(source_id="src1", item_key="key1").one()
    assert item1_db.title == "Title 1"
    assert item1_db.link == "https://x/1"


def test_dedupe_empty_batch(session: Session, setup_sources: None) -> None:
    count = insert_items(session, [])
    session.commit()
    assert count == 0
    items = session.query(Item).all()
    assert len(items) == 0
