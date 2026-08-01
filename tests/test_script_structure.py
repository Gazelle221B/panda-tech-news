"""script.structure のユニットテスト (Sprint 2 Ticket T25). LLM 不使用・全て決定的.

architecture-podcast-station §4 の「構造化台本 (script → tts の境界)」を検証する。
LLM はプレーンテキスト台本を出し、コード側で segment 構造化する (JSON と日本語を
同時に LLM に書かせない)。tone は edit 層 (JudgedTopic) の判定結果から引く。
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from karyu_tech_news.edit.judge import JudgedTopic, Tone
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.script.structure import (
    TONE_BGM,
    Segment,
    StructuredScript,
    build_structured_script,
)

NOW = datetime(2026, 6, 14, 7, 0, tzinfo=UTC)

BODY = (
    "**Hook:** ディープシーク (DeepSeek) が新モデルを発表しました。\n"
    "**Insight:** 日本の開発者にも利用でき選択肢が広がります。\n"
    "**Action:** 公式リリースノートに注目です。"
)


def _topic(item_id: int = 1, *, tone: Tone = Tone.NEUTRAL) -> JudgedTopic:
    return JudgedTopic(
        candidate=ScoredCandidate(
            item_id=item_id,
            source_id="src-a",
            title=f"話題{item_id}",
            summary="",
            link=f"https://example.com/{item_id}",
            published_at=None,
            fetched_at=NOW,
            tier=1,
            category="AI",
            canonical_url_hash="",
            prescore=0,
        ),
        llm_score=80,
        tone=tone,
        corroboration_count=1,
    )


def test_build_wraps_topics_with_intro_and_outro() -> None:
    topics = [(_topic(1), BODY), (_topic(2), BODY)]
    script = build_structured_script(topics, variant="A", generated_at=NOW)
    assert isinstance(script, StructuredScript)
    kinds = [s.kind for s in script.segments]
    assert kinds == ["intro", "topic", "topic", "outro"]  # intro + N + outro


def test_topic_segment_carries_tone_from_edit_layer() -> None:
    topics = [(_topic(1, tone=Tone.HARD_NEGATIVE), BODY)]
    script = build_structured_script(topics, variant="A", generated_at=NOW)
    topic_seg = next(s for s in script.segments if s.kind == "topic")
    assert topic_seg.tone == "hard_negative"  # edit 層の判定を引き継ぐ
    assert topic_seg.text == BODY


def test_bgm_derived_from_tone() -> None:
    topics = [(_topic(1, tone=Tone.HARD_NEGATIVE), BODY)]
    seg = build_structured_script(topics, variant="A", generated_at=NOW).segments[1]
    assert seg.bgm == TONE_BGM["hard_negative"]


def test_all_tones_have_bgm_mapping() -> None:
    for tone in Tone:
        assert tone.value in TONE_BGM  # 全 tone に bgm キューがある


def test_all_segments_voiced_by_hal() -> None:
    topics = [(_topic(1), BODY)]
    script = build_structured_script(topics, variant="A", generated_at=NOW)
    assert all(s.voice == "HAL" for s in script.segments)


def test_intro_outro_text_nonblank() -> None:
    script = build_structured_script([(_topic(1), BODY)], variant="A", generated_at=NOW)
    intro = script.segments[0]
    outro = script.segments[-1]
    assert intro.kind == "intro" and intro.text.strip()
    assert outro.kind == "outro" and outro.text.strip()


def test_empty_topics_still_has_intro_outro() -> None:
    # 純粋な構造変換: トピック0でも intro/outro は残す (異常時も壊さない)
    script = build_structured_script([], variant="A", generated_at=NOW)
    assert [s.kind for s in script.segments] == ["intro", "outro"]


def test_structured_script_is_json_serializable() -> None:
    # script → tts 境界は JSON 化可能であること (architecture §4)
    script = build_structured_script([(_topic(1), BODY)], variant="A", generated_at=NOW)
    dumped = script.model_dump(mode="json")
    assert dumped["variant"] == "A"
    assert isinstance(dumped["segments"], list)


def test_segment_model_defaults_voice() -> None:
    seg = Segment(kind="topic", text="x", tone="neutral", bgm="neutral")
    assert seg.voice == "HAL"


def test_segment_serializes_kind_as_type_alias() -> None:
    # architecture §4 の JSON 契約: segment field は "type" (by_alias=True)
    seg = Segment(kind="topic", text="x", tone="neutral", bgm="neutral")
    assert seg.model_dump(by_alias=True)["type"] == "topic"


# ---------- 確定挨拶フレーズの反映 (T54, Issue #39) ----------


def test_intro_segment_carries_title_call_and_opening() -> None:
    """intro segment はタイトルコール + オープニング挨拶の連結 (両方とも「。」で終わる)."""
    script = build_structured_script([(_topic(1), BODY)], variant="A", generated_at=NOW)
    intro = script.segments[0]
    assert "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。" in intro.text
    assert "キャスターのHALです。支度の手を止めずに" in intro.text


def test_intro_segment_includes_broadcast_date() -> None:
    """T63, Issue #69: 音声合成に渡る intro segment にも当日日付が入る (TTS 側の反映漏れ防止).
    NOW = 2026-06-14 07:00 UTC -> JST 2026-06-14 16:00 (日曜日)."""
    script = build_structured_script([(_topic(1), BODY)], variant="A", generated_at=NOW)
    intro = script.segments[0]
    assert "6月14日、日曜日。キャスターのHALです。" in intro.text


def test_outro_segment_carries_confirmed_closing() -> None:
    script = build_structured_script([(_topic(1), BODY)], variant="A", generated_at=NOW)
    outro = script.segments[-1]
    assert outro.text.startswith("今日の華流テック通信は以上です。")


def test_build_structured_script_respects_custom_show_format_path(tmp_path: Path) -> None:
    """show_format_path 経由で intro/outro の固定句が差し替わる (ハードコードではない証明)."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text(
        "phrases:\n"
        '  title_call: "テスト用タイトルコール"\n'
        '  opening: "テスト用オープニング"\n'
        '  closing: "テスト用クロージング"\n',
        encoding="utf-8",
    )
    script = build_structured_script(
        [(_topic(1), BODY)], variant="A", generated_at=NOW, show_format_path=custom
    )
    assert "テスト用タイトルコール" in script.segments[0].text
    assert "テスト用オープニング" in script.segments[0].text
    assert script.segments[-1].text == "テスト用クロージング"
