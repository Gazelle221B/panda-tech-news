"""edit.prescore のユニットテスト (Sprint 1B Ticket T14)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.edit.prescore import (
    CANDIDATE_LIMIT,
    RECENTLY_AIRED_LOOKBACK_DAYS,
    THIN_SUMMARY_CHARS,
    THIN_SUMMARY_PENALTY,
    TIER_BONUS,
    ScoredCandidate,
    extract_candidates,
    prescore_text,
    thin_summary_penalty,
)
from karyu_tech_news.store.repo import create_db_engine, init_db, upsert_source
from karyu_tech_news.store.schema import EpisodeDraft, Item, TopicCandidate

NOW = datetime(2026, 6, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    return create_db_engine(tmp_path / "test.db")


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    init_db(engine)
    with Session(engine) as s:
        yield s
        s.rollback()


def _add_source(
    session: Session,
    id_: str,
    tier: SourceTier = SourceTier.OFFICIAL,
    category: SourceCategory = SourceCategory.AI,
) -> None:
    upsert_source(
        session,
        SourceConfig(
            id=id_, name=id_, url="https://example.com/feed", tier=tier, category=category
        ),
    )


def _add_item(
    session: Session,
    source_id: str,
    title: str,
    *,
    summary: str | None = "",
    fetched_at: datetime = NOW,
    published_at: datetime | None = None,
    key_suffix: str = "",
) -> None:
    session.add(
        Item(
            source_id=source_id,
            item_key=f"{title}{key_suffix}",
            external_id=None,
            title=title,
            link=f"https://example.com/{title}",
            summary=summary,
            published_at=published_at,
            fetched_at=fetched_at,
            raw_json="{}",
            canonical_url_hash="",
        )
    )
    session.flush()


# ---------- prescore_text ----------

def test_prescore_text_no_keywords_is_zero() -> None:
    assert prescore_text("天气不错", "今天很好") == 0


def test_prescore_text_security_keyword_scores_30() -> None:
    assert prescore_text("某产品发现严重漏洞", "") == 30


def test_prescore_text_regulation_keyword_scores_20() -> None:
    assert prescore_text("新的AI监管政策出台", "") >= 20


def test_prescore_text_release_keyword_scores_10() -> None:
    assert prescore_text("DeepSeek 发布新模型", "") == 10


def test_prescore_text_bucket_counted_once() -> None:
    # 同一バケツのキーワードが何回出ても加点は1回 (発布 + 开源 + 上线 = +10 のみ)
    assert prescore_text("发布发布发布", "开源 上线") == 10


def test_prescore_text_buckets_are_additive() -> None:
    # 緊急 (+30) + 監管 (+20) + 発布 (+10) = 60
    assert prescore_text("紧急: 监管新规下发布漏洞修复", "") == 60


def test_prescore_text_matches_in_summary() -> None:
    assert prescore_text("无关标题", "本文涉及数据泄露事件") == 30


def test_prescore_text_japanese_keywords() -> None:
    # 日本語ソース/将来の混在に備え、日本語キーワードも辞書に含める
    assert prescore_text("大規模な脆弱性が発見", "") == 30


# ---------- TIER_BONUS ----------

def test_tier_bonus_descends_with_tier() -> None:
    assert TIER_BONUS[1] > TIER_BONUS[2] > TIER_BONUS[3] >= TIER_BONUS[4]


# ---------- thin_summary_penalty (T60, Issue #60) ----------

def test_thin_summary_penalty_applies_to_13_char_summary() -> None:
    # 実例 (Issue #60): 2026-08-01 draft #2 の summary は 13 字だった
    assert thin_summary_penalty("一二三四五六七八九十一二三") == THIN_SUMMARY_PENALTY


def test_thin_summary_penalty_no_penalty_at_40_chars_or_more() -> None:
    assert thin_summary_penalty("x" * THIN_SUMMARY_CHARS) == 0
    assert thin_summary_penalty("x" * (THIN_SUMMARY_CHARS + 10)) == 0


def test_thin_summary_penalty_applies_below_threshold() -> None:
    assert thin_summary_penalty("x" * (THIN_SUMMARY_CHARS - 1)) == THIN_SUMMARY_PENALTY


def test_thin_summary_penalty_none_summary_is_thin() -> None:
    assert thin_summary_penalty(None) == THIN_SUMMARY_PENALTY


def test_thin_summary_penalty_whitespace_only_is_thin() -> None:
    assert thin_summary_penalty("   \n\t  ") == THIN_SUMMARY_PENALTY


# ---------- extract_candidates ----------

def test_extract_candidates_scores_and_sorts(session: Session) -> None:
    _add_source(session, "official-src", tier=SourceTier.OFFICIAL)
    _add_source(session, "community-src", tier=SourceTier.COMMUNITY)
    _add_item(session, "community-src", "普通话题")  # tier3 bonus のみ (summary="" は薄記事扱い)
    _add_item(session, "official-src", "发现严重漏洞")  # +30 + tier1 bonus (同上)

    candidates = extract_candidates(session, now=NOW)

    assert [c.title for c in candidates] == ["发现严重漏洞", "普通话题"]
    # 両方とも summary="" (既定) のため THIN_SUMMARY_PENALTY が乗る (T60)
    assert candidates[0].prescore == 30 + TIER_BONUS[1] + THIN_SUMMARY_PENALTY
    assert candidates[1].prescore == TIER_BONUS[3] + THIN_SUMMARY_PENALTY
    assert isinstance(candidates[0], ScoredCandidate)
    assert candidates[0].tier == 1
    assert candidates[0].category == "AI"


def test_extract_candidates_excludes_items_outside_lookback(session: Session) -> None:
    _add_source(session, "src-a")
    _add_item(session, "src-a", "古い話題", fetched_at=NOW - timedelta(hours=72))
    _add_item(session, "src-a", "新しい話題", fetched_at=NOW - timedelta(hours=1))

    candidates = extract_candidates(session, now=NOW, lookback_hours=48)

    assert [c.title for c in candidates] == ["新しい話題"]


def test_extract_candidates_caps_at_limit(session: Session) -> None:
    _add_source(session, "src-a")
    for i in range(CANDIDATE_LIMIT + 5):
        _add_item(session, "src-a", f"话题{i}", key_suffix=str(i))

    candidates = extract_candidates(session, now=NOW)

    assert len(candidates) == CANDIDATE_LIMIT


def test_extract_candidates_recency_breaks_ties(session: Session) -> None:
    _add_source(session, "src-a")
    _add_item(session, "src-a", "旧条目", fetched_at=NOW - timedelta(hours=10))
    _add_item(session, "src-a", "新条目", fetched_at=NOW - timedelta(hours=1))

    candidates = extract_candidates(session, now=NOW)

    # 同スコアなら新しい方が先
    assert [c.title for c in candidates] == ["新条目", "旧条目"]


def test_extract_candidates_handles_null_summary(session: Session) -> None:
    _add_source(session, "src-a")
    _add_item(session, "src-a", "无摘要条目", summary=None)

    candidates = extract_candidates(session, now=NOW)

    assert candidates[0].summary == ""
    # summary=None も薄記事扱いで減点される (T60)
    assert candidates[0].prescore == TIER_BONUS[1] + THIN_SUMMARY_PENALTY


def test_extract_candidates_empty_db(session: Session) -> None:
    assert extract_candidates(session, now=NOW) == []


# ---------- 放送済みネタの再選防止 (Issue #95) ----------


def _to_naive_utc(dt: datetime) -> datetime:
    """本番の episode_drafts.created_at は naive UTC 保存 (store/repo.py
    create_episode_draft は generated_at をそのまま渡すのみで tzinfo 正規化は
    しない)。テストのシードもこの保存形式に合わせて aware → naive UTC に変換する
    (codex terra レビュー blocking-1, PR #96)。"""
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


def _add_draft_with_topic_candidate(
    session: Session,
    item_id: int,
    *,
    created_at: datetime,
    selected: bool = True,
) -> None:
    """episode_drafts + topic_candidates に「item_id が selected かどうか」の
    1 行をシードする (extract_candidates の除外フィルタ用テストヘルパー).

    created_at は本番の保存形式 (naive UTC) に正規化してから保存する。
    """
    draft = EpisodeDraft(
        created_at=_to_naive_utc(created_at),
        variant="A",
        title="テスト放送",
        estimated_minutes=1,
        notices_json="[]",
        markdown="dummy",
    )
    session.add(draft)
    session.flush()
    session.add(
        TopicCandidate(
            draft_id=draft.id,
            item_id=item_id,
            prescore=0,
            llm_score=None,
            tone=None,
            source_tier=1,
            corroboration_count=1,
            selected=selected,
            position=1 if selected else None,
        )
    )
    session.flush()


def test_extract_candidates_excludes_recently_aired_item(session: Session) -> None:
    """aware な now (production の datetime.now(UTC) を模す) と naive UTC 保存の
    created_at (production の実際の保存形式) の組合せで正しく除外される
    (codex terra レビュー blocking-1 ①, PR #96)."""
    _add_source(session, "src-a")
    _add_item(session, "src-a", "話題A")
    item_id = session.execute(select(Item).where(Item.title == "話題A")).scalar_one().id
    # テンプレ放送だったネタでも selected=True であれば除外対象
    # (topic_candidates は method を持たない = Issue #95 の許容 trade-off)。
    _add_draft_with_topic_candidate(session, item_id, created_at=NOW - timedelta(days=1))

    # ヘルパーが実際に naive UTC で保存していることを確認 (前提の固定)
    stored = session.execute(select(EpisodeDraft)).scalar_one()
    assert stored.created_at.tzinfo is None

    candidates = extract_candidates(session, now=NOW)

    assert candidates == []


def test_extract_candidates_keeps_item_selected_outside_lookback(session: Session) -> None:
    _add_source(session, "src-a")
    _add_item(session, "src-a", "話題A")
    item_id = session.execute(select(Item).where(Item.title == "話題A")).scalar_one().id
    _add_draft_with_topic_candidate(
        session,
        item_id,
        created_at=NOW - timedelta(days=RECENTLY_AIRED_LOOKBACK_DAYS, hours=1),
    )

    candidates = extract_candidates(session, now=NOW)

    assert [c.title for c in candidates] == ["話題A"]


def test_extract_candidates_excludes_at_exact_lookback_boundary(session: Session) -> None:
    """ちょうど RECENTLY_AIRED_LOOKBACK_DAYS 日前 (since と同値) の境界ケース。
    フィルタは `created_at >= since` (境界含む) なので除外される
    (codex terra レビュー blocking-1 ②, PR #96)."""
    _add_source(session, "src-a")
    _add_item(session, "src-a", "話題A")
    item_id = session.execute(select(Item).where(Item.title == "話題A")).scalar_one().id
    _add_draft_with_topic_candidate(
        session,
        item_id,
        created_at=NOW - timedelta(days=RECENTLY_AIRED_LOOKBACK_DAYS),
    )

    candidates = extract_candidates(session, now=NOW)

    assert candidates == []


def test_extract_candidates_keeps_item_not_selected_in_past_draft(session: Session) -> None:
    _add_source(session, "src-a")
    _add_item(session, "src-a", "話題A")
    item_id = session.execute(select(Item).where(Item.title == "話題A")).scalar_one().id
    _add_draft_with_topic_candidate(
        session, item_id, created_at=NOW - timedelta(days=1), selected=False
    )

    candidates = extract_candidates(session, now=NOW)

    assert [c.title for c in candidates] == ["話題A"]


def test_extract_candidates_item_selected_in_multiple_drafts(session: Session) -> None:
    """同一 item が複数 draft (いずれも selected=True) に登場するケース。
    集合演算で重複排除されるため、除外判定にも extract_candidates の結果にも
    問題が起きないことを確認する (codex terra レビュー blocking-1 ③, PR #96)."""
    _add_source(session, "src-a")
    _add_item(session, "src-a", "話題A")
    item_id = session.execute(select(Item).where(Item.title == "話題A")).scalar_one().id
    _add_draft_with_topic_candidate(session, item_id, created_at=NOW - timedelta(days=3))
    _add_draft_with_topic_candidate(session, item_id, created_at=NOW - timedelta(days=1))

    candidates = extract_candidates(session, now=NOW)

    assert candidates == []


def test_extract_candidates_logs_excluded_count(
    session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    _add_source(session, "src-a")
    _add_item(session, "src-a", "話題A")
    item_id = session.execute(select(Item).where(Item.title == "話題A")).scalar_one().id
    _add_draft_with_topic_candidate(session, item_id, created_at=NOW - timedelta(days=1))

    with caplog.at_level("INFO", logger="karyu_tech_news.edit.prescore"):
        extract_candidates(session, now=NOW)

    assert any("excluded 1" in record.message for record in caplog.records)
