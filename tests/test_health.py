"""source_health 更新のユニットテスト (T7)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.store.repo import (
    create_db_engine,
    init_db,
    update_source_health_failure,
    update_source_health_success,
    upsert_source,
)
from karyu_tech_news.store.schema import SourceHealth


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
def setup_source(session: Session) -> None:
    config = SourceConfig(
        id="src1",
        name="Source 1",
        url="https://src1/feed",
        tier=SourceTier.OFFICIAL,
        category=SourceCategory.AI,
    )
    upsert_source(session, config)
    session.commit()


def test_health_first_success_creates_record(session: Session, setup_source: None) -> None:
    now = datetime.now(UTC)
    update_source_health_success(session, "src1", now)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.source_id == "src1"
    assert health.last_success_at is not None
    assert health.last_success_at.replace(tzinfo=None) == now.replace(tzinfo=None)
    assert health.last_failure_at is None
    assert health.consecutive_failures == 0
    assert health.last_error is None


def test_health_first_failure_creates_record(session: Session, setup_source: None) -> None:
    now = datetime.now(UTC)
    update_source_health_failure(session, "src1", "first error", now)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.source_id == "src1"
    assert health.last_success_at is None
    assert health.last_failure_at is not None
    assert health.last_failure_at.replace(tzinfo=None) == now.replace(tzinfo=None)
    assert health.consecutive_failures == 1
    assert health.last_error == "first error"


def test_health_success_resets_after_failures(session: Session, setup_source: None) -> None:
    t1 = datetime.now(UTC)
    update_source_health_failure(session, "src1", "error1", t1)
    session.commit()
    t2 = t1 + timedelta(minutes=1)
    update_source_health_failure(session, "src1", "error2", t2)
    session.commit()
    t3 = t2 + timedelta(minutes=1)
    update_source_health_failure(session, "src1", "error3", t3)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 3
    assert health.last_error == "error3"
    t4 = t3 + timedelta(minutes=1)
    update_source_health_success(session, "src1", t4)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 0
    assert health.last_error is None
    assert health.last_success_at is not None
    assert health.last_success_at.replace(tzinfo=None) == t4.replace(tzinfo=None)
    assert health.last_failure_at is None


def test_health_consecutive_failures_accumulate(session: Session, setup_source: None) -> None:
    base_time = datetime.now(UTC)
    for i in range(5):
        t = base_time + timedelta(minutes=i)
        update_source_health_failure(session, "src1", f"error{i}", t)
        session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 5
    assert health.last_error == "error4"


def test_health_warning_threshold(session: Session, setup_source: None) -> None:
    base_time = datetime.now(UTC)
    for i in range(3):
        t = base_time + timedelta(minutes=i)
        update_source_health_failure(session, "src1", f"error{i}", t)
        session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures >= 3


def test_health_last_error_updates(session: Session, setup_source: None) -> None:
    t1 = datetime.now(UTC)
    update_source_health_failure(session, "src1", "first error", t1)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.last_error == "first error"
    t2 = t1 + timedelta(minutes=1)
    update_source_health_failure(session, "src1", "second error", t2)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.last_error == "second error"


def test_health_timestamps_update_correctly(session: Session, setup_source: None) -> None:
    t1 = datetime.now(UTC)
    update_source_health_failure(session, "src1", "error1", t1)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.last_failure_at is not None
    assert health.last_failure_at.replace(tzinfo=None) == t1.replace(tzinfo=None)
    assert health.last_success_at is None
    t2 = t1 + timedelta(minutes=1)
    update_source_health_success(session, "src1", t2)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.last_success_at is not None
    assert health.last_success_at.replace(tzinfo=None) == t2.replace(tzinfo=None)
    assert health.last_failure_at is None
    t3 = t2 + timedelta(minutes=1)
    update_source_health_failure(session, "src1", "error2", t3)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.last_failure_at is not None
    assert health.last_failure_at.replace(tzinfo=None) == t3.replace(tzinfo=None)


def test_health_success_failure_cycle(session: Session, setup_source: None) -> None:
    t1 = datetime.now(UTC)
    update_source_health_success(session, "src1", t1)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 0
    t2 = t1 + timedelta(minutes=1)
    update_source_health_failure(session, "src1", "error1", t2)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 1
    t3 = t2 + timedelta(minutes=1)
    update_source_health_success(session, "src1", t3)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 0
    t4 = t3 + timedelta(minutes=1)
    update_source_health_failure(session, "src1", "error2", t4)
    session.commit()
    health = session.get(SourceHealth, "src1")
    assert health is not None
    assert health.consecutive_failures == 1
