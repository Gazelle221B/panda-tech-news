"""CRUD 操作."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, event, select
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session

from karyu_tech_news.collect.normalize import FetchResult, RawItem
from karyu_tech_news.config import SourceConfig
from karyu_tech_news.store.schema import (
    CollectRun,
    Item,
    Source,
    SourceHealth,
)


def create_db_engine(db_path: Path) -> Engine:
    """SQLite エンジン作成."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = sa_create_engine(f"sqlite:///{db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: object, connection_record: object) -> None:
        cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    """スキーマ初期化（冪等）."""
    from karyu_tech_news.store.schema import Base

    Base.metadata.create_all(engine)


def upsert_source(session: Session, config: SourceConfig) -> Source:
    """ソース追加/更新."""
    existing = session.get(Source, config.id)
    if existing:
        existing.name = config.name  # type: ignore[assignment]
        existing.url = config.url  # type: ignore[assignment]
        existing.tier = config.tier.value  # type: ignore[assignment]
        existing.category = config.category.value  # type: ignore[assignment]
        existing.enabled = config.enabled  # type: ignore[assignment]
        existing.requires_cookie = config.requires_cookie  # type: ignore[assignment]
        existing.notes = config.notes  # type: ignore[assignment]
        return existing
    source = Source(
        id=config.id,
        name=config.name,
        url=config.url,
        tier=config.tier.value,
        category=config.category.value,
        enabled=config.enabled,
        requires_cookie=config.requires_cookie,
        notes=config.notes,
    )
    session.add(source)
    return source


def insert_items(session: Session, items: list[RawItem]) -> int:
    """アイテム追加（dedupe: UNIQUE制約で自動スキップ）. 新規追加数を返す."""
    new_count = 0
    for item in items:
        if not item.item_key:
            msg = f"item_key is empty for source={item.source_id}"
            raise ValueError(msg)
        existing = session.execute(
            select(Item).where(
                Item.source_id == item.source_id,
                Item.item_key == item.item_key,
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db_item = Item(
            source_id=item.source_id,
            item_key=item.item_key,
            external_id=item.external_id,
            title=item.title,
            link=item.link,
            summary=item.summary,
            published_at=item.published_at,
            fetched_at=item.fetched_at,
            raw_json=json.dumps(item.raw_json, ensure_ascii=False),
            canonical_url_hash=item.canonical_url_hash,
        )
        session.add(db_item)
        new_count += 1
    return new_count


def update_source_health_success(session: Session, source_id: str, now: datetime) -> None:
    """成功時: consecutive_failures=0 にリセット."""
    health = session.get(SourceHealth, source_id)
    if not health:
        health = SourceHealth(source_id=source_id, consecutive_failures=0)
        session.add(health)
    health.last_success_at = now  # type: ignore[assignment]
    health.last_failure_at = None  # type: ignore[assignment]
    health.consecutive_failures = 0  # type: ignore[assignment]
    health.last_error = None  # type: ignore[assignment]


def update_source_health_failure(
    session: Session, source_id: str, error: str, now: datetime
) -> None:
    """失敗時: consecutive_failures += 1, last_error 保存."""
    health = session.get(SourceHealth, source_id)
    if not health:
        health = SourceHealth(source_id=source_id, consecutive_failures=0)
        session.add(health)
    health.last_failure_at = now  # type: ignore[assignment]
    health.consecutive_failures = (health.consecutive_failures or 0) + 1  # type: ignore[assignment]
    health.last_error = error  # type: ignore[assignment]


def create_collect_run(session: Session, total_sources: int) -> CollectRun:
    """収集実行記録作成."""
    run = CollectRun(
        started_at=datetime.now(UTC),
        total_sources=total_sources,
        successful_sources=0,
        failed_sources=0,
        total_items=0,
        new_items=0,
    )
    session.add(run)
    session.flush()
    return run


def finish_collect_run(
    session: Session,
    run: CollectRun,
    results: list[FetchResult],
    new_items: int,
) -> None:
    """収集実行記録完了."""
    if run.total_sources != len(results):
        msg = (
            f"total_sources mismatch: run.total_sources={run.total_sources}, "
            f"len(results)={len(results)}"
        )
        raise ValueError(msg)
    run.finished_at = datetime.now(UTC)  # type: ignore[assignment]
    successful = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    run.successful_sources = len(successful)  # type: ignore[assignment]
    run.failed_sources = len(failed)  # type: ignore[assignment]
    run.total_items = sum(len(r.items) for r in results)  # type: ignore[assignment,misc]
    run.new_items = new_items  # type: ignore[assignment]
