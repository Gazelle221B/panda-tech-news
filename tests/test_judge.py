"""edit.judge のユニットテスト (Sprint 1B Ticket T15). LLM はモック."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.edit.judge import (
    JUDGE_TEMPERATURE,
    JudgedTopic,
    JudgeError,
    Tone,
    build_judge_prompts,
    corroboration_counts,
    extract_json_object,
    judge_topics,
    parse_judgments,
)
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.llm.client import LLMResponse
from karyu_tech_news.store.repo import create_db_engine, init_db, upsert_source
from karyu_tech_news.store.schema import Item

NOW = datetime(2026, 6, 10, 0, 0, tzinfo=UTC)


def _candidate(
    item_id: int = 1,
    title: str = "DeepSeek 发布新模型",
    *,
    tier: int = 1,
    canonical_url_hash: str = "",
) -> ScoredCandidate:
    return ScoredCandidate(
        item_id=item_id,
        source_id="src-a",
        title=title,
        summary="概要テキスト",
        link="https://example.com/1",
        published_at=None,
        fetched_at=NOW,
        tier=tier,
        category="AI",
        canonical_url_hash=canonical_url_hash,
        prescore=40,
    )


# ---------- extract_json_object ----------

def test_extract_json_object_plain() -> None:
    assert extract_json_object('{"topics": []}') == {"topics": []}


def test_extract_json_object_fenced() -> None:
    text = '```json\n{"topics": [{"index": 1}]}\n```'
    assert extract_json_object(text) == {"topics": [{"index": 1}]}


def test_extract_json_object_with_surrounding_prose() -> None:
    text = '判定します。\n{"topics": []}\n以上です。'
    assert extract_json_object(text) == {"topics": []}


def test_extract_json_object_invalid_raises() -> None:
    with pytest.raises(JudgeError):
        extract_json_object("これはJSONではない")


# ---------- parse_judgments ----------

def test_parse_judgments_valid() -> None:
    text = '{"topics": [{"index": 1, "score": 90, "tone": "hard_negative"}]}'
    judgments = parse_judgments(text)
    assert judgments[0].index == 1
    assert judgments[0].score == 90
    assert judgments[0].tone is Tone.HARD_NEGATIVE


def test_parse_judgments_rejects_out_of_range_score() -> None:
    with pytest.raises(JudgeError):
        parse_judgments('{"topics": [{"index": 1, "score": 150, "tone": "bright"}]}')


def test_parse_judgments_rejects_unknown_tone() -> None:
    with pytest.raises(JudgeError):
        parse_judgments('{"topics": [{"index": 1, "score": 50, "tone": "angry"}]}')


def test_parse_judgments_missing_topics_key_raises() -> None:
    with pytest.raises(JudgeError):
        parse_judgments('{"items": []}')


# ---------- build_judge_prompts ----------

def test_build_judge_prompts_includes_topic_meta() -> None:
    cand = _candidate(title="T" * 300)
    system, user = build_judge_prompts([cand], {1: 2})
    assert "JSON" in system
    assert "tone" in system
    # title はプロンプト用に 180 文字へ切り詰め (styleguide §4)
    assert "T" * 180 in user
    assert "T" * 181 not in user
    assert "tier=1" in user
    assert "corroboration=2" in user


def test_build_judge_prompts_numbers_topics_from_one() -> None:
    cands = [_candidate(1, "話題A"), _candidate(2, "話題B")]
    _, user = build_judge_prompts(cands, {})
    assert "1." in user
    assert "2." in user


# ---------- corroboration_counts ----------

@pytest.fixture
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine: Engine = create_db_engine(tmp_path / "test.db")
    init_db(engine)
    with Session(engine) as s:
        yield s
        s.rollback()


def _add_item_row(
    session: Session, source_id: str, item_key: str, canonical_url_hash: str
) -> int:
    item = Item(
        source_id=source_id,
        item_key=item_key,
        external_id=None,
        title=item_key,
        link="https://example.com/x",
        summary="",
        published_at=None,
        fetched_at=NOW,
        raw_json="{}",
        canonical_url_hash=canonical_url_hash,
    )
    session.add(item)
    session.flush()
    return int(item.id)


def test_corroboration_counts_cross_source(session: Session) -> None:
    for sid in ("src-a", "src-b"):
        upsert_source(
            session,
            SourceConfig(
                id=sid,
                name=sid,
                url="https://example.com/feed",
                tier=SourceTier.COMMUNITY,
                category=SourceCategory.AI,
            ),
        )
    id_a = _add_item_row(session, "src-a", "k1", "hash-shared")
    _add_item_row(session, "src-b", "k2", "hash-shared")
    id_c = _add_item_row(session, "src-a", "k3", "hash-unique")

    cands = [
        _candidate(id_a, canonical_url_hash="hash-shared"),
        _candidate(id_c, canonical_url_hash="hash-unique"),
    ]
    counts = corroboration_counts(session, cands)

    assert counts[id_a] == 2  # 独立 2 ソースが同一 URL を報じている
    assert counts[id_c] == 1


def test_corroboration_counts_empty_hash_is_one(session: Session) -> None:
    cands = [_candidate(7, canonical_url_hash="")]
    assert corroboration_counts(session, cands) == {7: 1}


# ---------- judge_topics ----------

def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.return_value = LLMResponse(content=content)
    return client


def test_judge_topics_maps_judgments_to_candidates() -> None:
    cands = [_candidate(10, "話題A"), _candidate(20, "話題B")]
    client = _mock_client(
        '{"topics": ['
        '{"index": 1, "score": 80, "tone": "hard_negative"},'
        '{"index": 2, "score": 60, "tone": "bright"}]}'
    )

    judged = judge_topics(client, cands, {10: 1, 20: 2})

    assert len(judged) == 2
    assert isinstance(judged[0], JudgedTopic)
    assert judged[0].candidate.item_id == 10
    assert judged[0].llm_score == 80
    assert judged[0].tone is Tone.HARD_NEGATIVE
    assert judged[0].corroboration_count == 1
    assert judged[1].corroboration_count == 2

    # temp=0 (設計継承 §4.2) + JSON モードで呼んでいること
    kwargs = client.chat.call_args.kwargs
    assert kwargs["json_mode"] is True
    assert kwargs["temperature"] == JUDGE_TEMPERATURE


def test_judge_topics_skips_unknown_index_and_keeps_rest() -> None:
    cands = [_candidate(10, "話題A")]
    client = _mock_client(
        '{"topics": ['
        '{"index": 1, "score": 70, "tone": "neutral"},'
        '{"index": 99, "score": 50, "tone": "bright"}]}'
    )

    judged = judge_topics(client, cands, {})

    assert len(judged) == 1
    assert judged[0].candidate.item_id == 10


def test_judge_topics_empty_candidates_returns_empty() -> None:
    client = _mock_client('{"topics": []}')
    assert judge_topics(client, [], {}) == []
    client.chat.assert_not_called()
