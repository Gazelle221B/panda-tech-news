"""収集ランナー (fail-open 統合)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from karyu_tech_news.collect.fetcher import fetch_one
from karyu_tech_news.collect.normalize import FetchResult
from karyu_tech_news.config import SourceConfig
from karyu_tech_news.store.repo import (
    create_collect_run,
    finish_collect_run,
    insert_items,
    update_source_health_failure,
    update_source_health_success,
)
from karyu_tech_news.store.schema import CollectRun

logger = logging.getLogger(__name__)


def run_collect(
    session: Session,
    sources: list[SourceConfig],
    rsshub_base_url: str,
) -> CollectRun:
    """全ソースを収集して CollectRun を返す. fail-open."""
    run = create_collect_run(session, len(sources))
    session.commit()

    results: list[FetchResult] = []
    total_new_items = 0

    for source in sources:
        logger.info("fetching: %s", source.id)
        result = fetch_one(source, rsshub_base_url)

        now = datetime.now(UTC)
        if result.ok:
            try:
                new_count = insert_items(session, result.items)
                update_source_health_success(session, source.id, now)
                session.commit()
                total_new_items += new_count
                logger.info(
                    "success: %s (%d items, %d new)",
                    source.id,
                    len(result.items),
                    new_count,
                )
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                logger.error("db error for %s: %s", source.id, exc)
                update_source_health_failure(session, source.id, str(exc), now)
                session.commit()
                result = FetchResult(
                    source_id=result.source_id,
                    ok=False,
                    items=result.items,
                    error=f"db error: {exc}",
                    duration_ms=result.duration_ms,
                )
        else:
            update_source_health_failure(session, source.id, result.error or "unknown", now)
            session.commit()
            logger.warning("failed: %s: %s", source.id, result.error)

        results.append(result)

    finish_collect_run(session, run, results, total_new_items)
    session.commit()
    return run
