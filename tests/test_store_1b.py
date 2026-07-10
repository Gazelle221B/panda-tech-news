"""store の Sprint 1B テーブルのユニットテスト (Ticket T19)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session

from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.store.dto import (
    EpisodeDraftInput,
    ScriptVersionInput,
    TopicCandidateInput,
)
from karyu_tech_news.store.repo import (
    create_db_engine,
    create_episode_draft,
    init_db,
    insert_script_versions,
    insert_topic_candidates,
    record_llm_run,
    upsert_source,
)
from karyu_tech_news.store.schema import (
    EpisodeDraft,
    Item,
    LLMRun,
    ScriptVersion,
    TopicCandidate,
)

NOW = datetime(2026, 6, 11, 7, 0, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    return create_db_engine(tmp_path / "test.db")


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    init_db(engine)
    with Session(engine) as s:
        yield s
        s.rollback()


def _add_item(session: Session, source_id: str = "src-a", title: str = "話題") -> int:
    upsert_source(
        session,
        SourceConfig(
            id=source_id,
            name=source_id,
            url="https://example.com/feed",
            tier=SourceTier.OFFICIAL,
            category=SourceCategory.AI,
        ),
    )
    item = Item(
        source_id=source_id,
        item_key=title,
        external_id=None,
        title=title,
        link="https://example.com/1",
        summary="",
        published_at=None,
        fetched_at=NOW,
        raw_json="{}",
        canonical_url_hash="",
    )
    session.add(item)
    session.flush()
    return int(item.id)


def _judged(item_id: int) -> TopicCandidateInput:
    return TopicCandidateInput(
        item_id=item_id,
        prescore=40,
        llm_score=80,
        tone="bright",
        source_tier=1,
        corroboration_count=2,
    )


def _episode() -> EpisodeDraftInput:
    return EpisodeDraftInput(
        title="華流テック通信 — HAL Daily Briefing",
        generated_at=NOW,
        variant="A",
        markdown="# 台本本文",
        estimated_minutes=5,
        notices=["噂レベルの情報を含みます: 話題 (Tier4)"],
    )


def test_init_db_creates_1b_tables(engine: Engine) -> None:
    init_db(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"topic_candidates", "episode_drafts", "llm_runs", "script_versions"}.issubset(
        tables
    )


def test_create_episode_draft_persists(session: Session) -> None:
    draft = create_episode_draft(session, _episode())
    session.flush()

    row = session.get(EpisodeDraft, draft.id)
    assert row is not None
    assert row.variant == "A"
    assert row.markdown == "# 台本本文"
    assert row.estimated_minutes == 5
    assert "噂レベル" in str(row.notices_json)


def test_insert_topic_candidates_selected_and_position(session: Session) -> None:
    item_id = _add_item(session)
    draft = create_episode_draft(session, _episode())
    session.flush()

    insert_topic_candidates(
        session, int(draft.id), [_judged(item_id)], {item_id: 1}
    )
    session.flush()

    row = session.execute(select(TopicCandidate)).scalar_one()
    assert row.item_id == item_id
    assert row.prescore == 40
    assert row.llm_score == 80
    assert row.tone == "bright"
    assert row.source_tier == 1
    assert row.corroboration_count == 2
    assert bool(row.selected) is True
    assert row.position == 1


def test_insert_topic_candidates_unselected(session: Session) -> None:
    item_id = _add_item(session)
    draft = create_episode_draft(session, _episode())
    session.flush()

    insert_topic_candidates(session, int(draft.id), [_judged(item_id)], {})
    session.flush()

    row = session.execute(select(TopicCandidate)).scalar_one()
    assert bool(row.selected) is False
    assert row.position is None


def test_record_llm_run_persists(session: Session) -> None:
    draft = create_episode_draft(session, _episode())
    session.flush()

    record_llm_run(
        session,
        draft_id=int(draft.id),
        variant="A",
        role="editor",
        profile_label="mimo",
        model="mimo-v2.5-pro",
        prompt_tokens=100,
        completion_tokens=50,
        ok=True,
        json_stable=True,
        now=NOW,
    )
    session.flush()

    row = session.execute(select(LLMRun)).scalar_one()
    assert row.role == "editor"
    assert row.profile_label == "mimo"
    assert row.prompt_tokens == 100
    assert bool(row.ok) is True
    assert bool(row.json_stable) is True
    assert row.error is None


def test_record_llm_run_failure(session: Session) -> None:
    draft = create_episode_draft(session, _episode())
    session.flush()

    record_llm_run(
        session,
        draft_id=int(draft.id),
        variant="B",
        role="writer",
        profile_label="deepseek",
        model="deepseek-chat",
        prompt_tokens=0,
        completion_tokens=0,
        ok=False,
        error="timeout",
        now=NOW,
    )
    session.flush()

    row = session.execute(select(LLMRun)).scalar_one()
    assert bool(row.ok) is False
    assert row.error == "timeout"
    assert row.json_stable is None


def test_insert_script_versions_persists(session: Session) -> None:
    item_id = _add_item(session)
    draft = create_episode_draft(session, _episode())
    session.flush()

    result = ScriptVersionInput(
        body="**Hook:** a\n**Insight:** b\n**Action:** c",
        method="llm_retry",
        attempts=2,
    )
    insert_script_versions(session, int(draft.id), [(item_id, result)], now=NOW)
    session.flush()

    row = session.execute(select(ScriptVersion)).scalar_one()
    assert row.draft_id == draft.id
    assert row.item_id == item_id
    assert row.method == "llm_retry"
    assert row.attempts == 2
    assert "Hook" in str(row.body)
