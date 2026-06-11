"""edit.select / edit.arc のユニットテスト (Sprint 1B Ticket T16). LLM 不使用・全て決定的."""
from __future__ import annotations

from datetime import UTC, datetime

from karyu_tech_news.edit.arc import arrange_arc
from karyu_tech_news.edit.judge import JudgedTopic, Tone
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.edit.select import SELECT_MAX, select_topics

NOW = datetime(2026, 6, 10, 0, 0, tzinfo=UTC)


def _topic(
    item_id: int,
    *,
    score: int = 50,
    tone: Tone = Tone.NEUTRAL,
    tier: int = 1,
    corroboration: int = 1,
    source_id: str = "src-a",
    category: str = "AI",
    fetched_at: datetime = NOW,
) -> JudgedTopic:
    return JudgedTopic(
        candidate=ScoredCandidate(
            item_id=item_id,
            source_id=source_id,
            title=f"話題{item_id}",
            summary="",
            link=f"https://example.com/{item_id}",
            published_at=None,
            fetched_at=fetched_at,
            tier=tier,
            category=category,
            canonical_url_hash="",
            prescore=0,
        ),
        llm_score=score,
        tone=tone,
        corroboration_count=corroboration,
    )


# ---------- select_topics ----------

def test_select_drops_tier3_without_corroboration() -> None:
    topics = [
        _topic(1, tier=3, corroboration=1, score=99),
        _topic(2, tier=1, corroboration=1, score=10),
    ]
    selected = select_topics(topics)
    assert [t.candidate.item_id for t in selected] == [2]


def test_select_keeps_tier3_with_two_sources() -> None:
    topics = [_topic(1, tier=3, corroboration=2, score=80)]
    assert len(select_topics(topics)) == 1


def test_select_drops_tier4_without_corroboration() -> None:
    topics = [_topic(1, tier=4, corroboration=1, score=99)]
    assert select_topics(topics) == []


def test_select_orders_by_llm_score() -> None:
    topics = [
        _topic(1, score=50, source_id="s1", category="AI"),
        _topic(2, score=90, source_id="s2", category="Tech"),
        _topic(3, score=70, source_id="s3", category="Game"),
    ]
    selected = select_topics(topics)
    assert [t.candidate.item_id for t in selected] == [2, 3, 1]


def test_select_caps_at_five() -> None:
    topics = [
        _topic(i, score=90 - i, source_id=f"s{i}", category=cat)
        for i, cat in enumerate(["AI", "Tech", "Game", "OSS", "Anime", "Subculture"], start=1)
    ]
    selected = select_topics(topics)
    assert len(selected) == SELECT_MAX


def test_select_source_cap_prefers_diversity() -> None:
    # 同一ソース3本 + 他ソース1本 → 同一ソースは2本まで、他ソースが入る
    topics = [
        _topic(1, score=90, source_id="juejin", category="AI"),
        _topic(2, score=85, source_id="juejin", category="Tech"),
        _topic(3, score=80, source_id="juejin", category="Game"),
        _topic(4, score=10, source_id="other", category="OSS"),
    ]
    selected = select_topics(topics)
    ids = [t.candidate.item_id for t in selected]
    assert 4 in ids
    assert ids.count(3) + ids.count(2) + ids.count(1) <= 2 + 1  # juejin 由来は厳格パスで2本


def test_select_category_cap_prefers_diversity() -> None:
    # 同一カテゴリ3本 + 他カテゴリ1本 → 他カテゴリが必ず入る
    topics = [
        _topic(1, score=90, source_id="s1", category="AI"),
        _topic(2, score=85, source_id="s2", category="AI"),
        _topic(3, score=80, source_id="s3", category="AI"),
        _topic(4, score=10, source_id="s4", category="Game"),
    ]
    selected = select_topics(topics)
    assert 4 in [t.candidate.item_id for t in selected]


def test_select_fills_from_single_source_when_no_alternatives() -> None:
    # 全部同一ソースでも (キャップ緩和パスで) 埋まる — 番組を出すことを優先
    topics = [
        _topic(i, score=90 - i, source_id="only-src", category="AI") for i in range(1, 5)
    ]
    selected = select_topics(topics)
    assert len(selected) == 4


def test_select_does_not_mutate_input() -> None:
    topics = [_topic(1, score=50), _topic(2, score=90, source_id="s2")]
    before = [t.candidate.item_id for t in topics]
    select_topics(topics)
    assert [t.candidate.item_id for t in topics] == before


def test_select_empty_input() -> None:
    assert select_topics([]) == []


# ---------- arrange_arc ----------

def test_arc_fewer_than_three_returned_as_is() -> None:
    topics = [_topic(1, tone=Tone.BRIGHT), _topic(2, tone=Tone.HARD_NEGATIVE)]
    assert [t.candidate.item_id for t in arrange_arc(topics)] == [1, 2]


def test_arc_three_act_structure() -> None:
    topics = [
        _topic(1, score=60, tone=Tone.BRIGHT),
        _topic(2, score=90, tone=Tone.HARD_NEGATIVE),
        _topic(3, score=70, tone=Tone.CONSTRUCTIVE),
        _topic(4, score=80, tone=Tone.NEUTRAL),
    ]
    arranged = arrange_arc(topics)
    assert arranged[0].tone is Tone.HARD_NEGATIVE  # 重要ニュース先頭
    assert arranged[-1].tone is Tone.BRIGHT  # 明るい話題で締め
    assert Tone.CONSTRUCTIVE in [t.tone for t in arranged[1:-1]]  # 解決策は中盤


def test_arc_highest_hard_negative_leads() -> None:
    topics = [
        _topic(1, score=50, tone=Tone.HARD_NEGATIVE),
        _topic(2, score=95, tone=Tone.HARD_NEGATIVE),
        _topic(3, score=70, tone=Tone.BRIGHT),
    ]
    arranged = arrange_arc(topics)
    assert arranged[0].candidate.item_id == 2


def test_arc_constructive_closes_when_no_bright() -> None:
    topics = [
        _topic(1, score=90, tone=Tone.HARD_NEGATIVE),
        _topic(2, score=70, tone=Tone.CONSTRUCTIVE),
        _topic(3, score=80, tone=Tone.NEUTRAL),
    ]
    arranged = arrange_arc(topics)
    assert arranged[-1].tone is Tone.CONSTRUCTIVE


def test_arc_all_neutral_keeps_score_order() -> None:
    topics = [
        _topic(1, score=90),
        _topic(2, score=80),
        _topic(3, score=70),
    ]
    arranged = arrange_arc(topics)
    assert [t.candidate.item_id for t in arranged] == [1, 2, 3]


def test_arc_does_not_mutate_input() -> None:
    topics = [
        _topic(1, score=60, tone=Tone.BRIGHT),
        _topic(2, score=90, tone=Tone.HARD_NEGATIVE),
        _topic(3, score=70, tone=Tone.CONSTRUCTIVE),
    ]
    before = [t.candidate.item_id for t in topics]
    arrange_arc(topics)
    assert [t.candidate.item_id for t in topics] == before
