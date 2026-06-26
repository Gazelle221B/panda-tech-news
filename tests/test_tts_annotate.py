"""tts.annotate のユニットテスト (Sprint 2 Ticket T27). 全て決定的.

architecture §4: tone 判定を絵文字スタイル制御に変換する後処理層。台本生成段階では
絵文字を入れず、TTS 前処理で機械的に文末挿入する。エンジンが絵文字スタイルを
サポートする場合のみ適用 (capabilities 分岐)。
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from karyu_tech_news.script.structure import Segment, StructuredScript
from karyu_tech_news.tts.annotate import (
    annotate_script,
    annotate_text,
    load_emoji_annotation,
)

PERSONA_PATH = Path("config/hal_persona.yaml")
NOW = datetime(2026, 6, 14, 7, 0, tzinfo=UTC)

MAP = {"hard_negative": ["😟", "😔"], "constructive": ["🤔"], "bright": ["✨"]}


def _script() -> StructuredScript:
    return StructuredScript(
        variant="A",
        generated_at=NOW,
        segments=[
            Segment(kind="intro", text="おはようございます。", tone="neutral", bgm="intro"),
            Segment(kind="topic", text="深刻な話題です。", tone="hard_negative", bgm="serious"),
            Segment(kind="outro", text="また明日。", tone="bright", bgm="outro"),
        ],
    )


# ---------- annotate_text ----------

def test_annotate_text_inserts_emoji_before_final_punctuation() -> None:
    # 句点の直前に挿入 (文末の後ろだと T28 分割で絵文字が単独文になる)
    assert annotate_text("テスト。", "hard_negative", MAP) == "テスト😟。"


def test_annotate_text_appends_when_no_trailing_punctuation() -> None:
    assert annotate_text("テスト", "hard_negative", MAP) == "テスト😟"


def test_annotate_text_neutral_unchanged() -> None:
    # neutral は mapping に無い → 注釈しない
    assert annotate_text("普通の文。", "neutral", MAP) == "普通の文。"


def test_annotate_text_deterministic() -> None:
    assert annotate_text("文。", "bright", MAP) == annotate_text("文。", "bright", MAP)


# ---------- annotate_script (capabilities 分岐) ----------

def test_annotate_script_enabled_annotates_by_tone() -> None:
    out = annotate_script(_script(), MAP, emoji_enabled=True)
    by_kind = {s.kind: s for s in out.segments}
    assert "😟。" in by_kind["topic"].text  # hard_negative, 句点直前
    assert "✨。" in by_kind["outro"].text  # bright, 句点直前
    assert by_kind["intro"].text == "おはようございます。"  # neutral 無注釈


def test_annotate_script_disabled_is_noop() -> None:
    out = annotate_script(_script(), MAP, emoji_enabled=False)
    assert all("😟" not in s.text and "✨" not in s.text for s in out.segments)


def test_annotate_script_does_not_mutate_input() -> None:
    original = _script()
    annotate_script(original, MAP, emoji_enabled=True)
    assert original.segments[1].text == "深刻な話題です。"  # 入力は不変


# ---------- 設定ロード ----------

def test_load_emoji_annotation_defaults_off_for_persona() -> None:
    mapping = load_emoji_annotation(PERSONA_PATH)
    assert mapping == {}


def test_load_emoji_annotation_requires_explicit_opt_in(tmp_path: Path) -> None:
    persona = tmp_path / "persona.yaml"
    persona.write_text(
        """
tts:
  emoji_annotation_enabled: true
  emoji_annotation:
    hard_negative: ["😟"]
    bright: ["😊"]
""".lstrip(),
        encoding="utf-8",
    )
    mapping = load_emoji_annotation(persona)
    assert "hard_negative" in mapping
    assert "bright" in mapping
    assert all(isinstance(v, list) and v for v in mapping.values())
