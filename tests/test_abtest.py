"""edit.abtest のユニットテスト (Sprint 1B Ticket T20)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.edit.abtest import VariantStats, evaluate_variants, format_evaluation
from karyu_tech_news.store.repo import create_db_engine, init_db, upsert_source
from karyu_tech_news.store.schema import (
    EpisodeDraft,
    Item,
    LLMRun,
    ScriptVersion,
    TopicCandidate,
)

NOW = datetime(2026, 6, 11, 7, 0, tzinfo=UTC)


@pytest.fixture
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine: Engine = create_db_engine(tmp_path / "test.db")
    init_db(engine)
    with Session(engine) as s:
        yield s
        s.rollback()


def _add_item(session: Session, key: str) -> int:
    upsert_source(
        session,
        SourceConfig(
            id="src-a",
            name="src-a",
            url="https://example.com/feed",
            tier=SourceTier.OFFICIAL,
            category=SourceCategory.AI,
        ),
    )
    item = Item(
        source_id="src-a",
        item_key=key,
        external_id=None,
        title=key,
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


def _add_draft(session: Session, variant: str) -> int:
    draft = EpisodeDraft(
        created_at=NOW,
        variant=variant,
        title="t",
        estimated_minutes=5,
        notices_json="[]",
        markdown="m",
    )
    session.add(draft)
    session.flush()
    return int(draft.id)


def _seed_variant_a(session: Session) -> None:
    draft_id = _add_draft(session, "A")
    # 候補4本中2本採用 → 採用率 0.5
    for i, selected in enumerate([True, True, False, False]):
        item_id = _add_item(session, f"k{i}")
        session.add(
            TopicCandidate(
                draft_id=draft_id,
                item_id=item_id,
                prescore=10,
                llm_score=50,
                tone="neutral",
                source_tier=1,
                corroboration_count=1,
                selected=selected,
                position=i + 1 if selected else None,
            )
        )
    session.add(
        LLMRun(
            draft_id=draft_id,
            created_at=NOW,
            variant="A",
            role="editor",
            profile_label="mimo",
            model="m",
            prompt_tokens=100,
            completion_tokens=50,
            ok=True,
            json_stable=True,
        )
    )
    session.add(
        LLMRun(
            draft_id=draft_id,
            created_at=NOW,
            variant="A",
            role="writer",
            profile_label="deepseek",
            model="d",
            prompt_tokens=200,
            completion_tokens=100,
            ok=False,
            error="timeout",
        )
    )
    item_a = _add_item(session, "script-a")
    item_b = _add_item(session, "script-b")
    session.add(
        ScriptVersion(
            draft_id=draft_id,
            item_id=item_a,
            created_at=NOW,
            method="llm",
            attempts=1,
            body="b",
        )
    )
    session.add(
        ScriptVersion(
            draft_id=draft_id,
            item_id=item_b,
            created_at=NOW,
            method="template",
            attempts=3,
            body="b",
        )
    )
    session.flush()


def test_evaluate_variants_empty_db(session: Session) -> None:
    assert evaluate_variants(session) == []


def test_evaluate_variants_aggregates_per_variant(session: Session) -> None:
    _seed_variant_a(session)
    _add_draft(session, "B")  # 候補なしの draft のみ

    stats = evaluate_variants(session)

    by_variant = {s.variant: s for s in stats}
    assert set(by_variant) == {"A", "B"}

    a = by_variant["A"]
    assert isinstance(a, VariantStats)
    assert a.drafts == 1
    assert a.candidates == 4
    assert a.selected == 2
    assert a.adoption_rate == pytest.approx(0.5)
    assert a.llm_calls == 2
    assert a.llm_failures == 1
    assert a.prompt_tokens == 300
    assert a.completion_tokens == 150
    assert a.json_stable_rate == pytest.approx(1.0)  # editor 1回中1回安定
    assert a.method_counts == {"llm": 1, "template": 1}
    assert a.avg_attempts == pytest.approx(2.0)

    b = by_variant["B"]
    assert b.candidates == 0
    assert b.adoption_rate == 0.0
    assert b.json_stable_rate is None  # editor 実行なし


def test_format_evaluation_renders_variants(session: Session) -> None:
    _seed_variant_a(session)
    stats = evaluate_variants(session)

    text = format_evaluation(stats)

    assert "A" in text
    assert "採用率" in text
    assert "JSON" in text


def test_format_evaluation_empty() -> None:
    assert "なし" in format_evaluation([])
