"""構造化台本 (script → tts の境界) — Sprint 2 Ticket T25.

architecture-podcast-station §4 の決定:
- 台本はプレーンテキストではなく、音声化のため segment 構造化が必須。
- **LLM はプレーンテキスト台本を出し、コード側でパースして JSON 化** する
  (LLM に JSON と日本語コピーを同時に書かせると片方崩れる)。
- tone は edit 層 (`JudgedTopic.tone`) の判定結果から引く。

本実装は、既に構造を保持している `(JudgedTopic, body)` のリストから直接 segment を
組む (脆いマーカー解析に頼らない)。出力は絵文字注釈 (T27) と文単位合成 (T28) が
消費する。BGM キューは tone から決定的に導き、実ミックス (T29) が使う。
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from karyu_tech_news.edit.judge import JudgedTopic
from karyu_tech_news.script.generate import CLOSING_PHRASE, OPENING_PHRASE

SegmentKind = Literal["intro", "topic", "outro"]

# tone → BGM キュー (architecture §4 の例: hard_negative → serious)。実素材割当は T29。
TONE_BGM: dict[str, str] = {
    "hard_negative": "serious",
    "constructive": "hopeful",
    "bright": "bright",
    "neutral": "neutral",
}

_INTRO_TONE = "neutral"
_OUTRO_TONE = "bright"  # 明るい話題で締める (アーク, design-inheritance §4)


class Segment(BaseModel):
    """音声化の最小単位. tts レイヤーが 1 segment ずつ合成し時間軸に並べる."""

    # architecture §4 の segment "type"。Python 内部は `kind`、JSON 出力 (by_alias=True)
    # では設計文書どおり "type" を出す。
    kind: SegmentKind = Field(serialization_alias="type")
    text: str
    tone: str
    bgm: str
    voice: str = "HAL"  # HAL の声は profile で固定 (FR-091)


class StructuredScript(BaseModel):
    """1 エピソードの構造化台本 (script → tts 境界, architecture §4)."""

    variant: str
    generated_at: datetime
    segments: list[Segment]


def _bgm_for_tone(tone: str) -> str:
    """未知 tone は neutral 扱い (新 tone 追加時も BGM 欠落で壊さない)."""
    return TONE_BGM.get(tone, "neutral")


def build_structured_script(
    topics: list[tuple[JudgedTopic, str]],
    variant: str,
    generated_at: datetime,
) -> StructuredScript:
    """検証済みトピック台本を intro / topic× / outro の segment 列に構造化する.

    決定的コード (LLM 不使用)。tone は各 `JudgedTopic` から引き継ぎ、BGM は tone から導く。
    """
    segments: list[Segment] = [
        Segment(kind="intro", text=OPENING_PHRASE, tone=_INTRO_TONE, bgm="intro")
    ]
    for topic, body in topics:
        tone = topic.tone.value
        segments.append(
            Segment(kind="topic", text=body, tone=tone, bgm=_bgm_for_tone(tone))
        )
    segments.append(
        Segment(kind="outro", text=CLOSING_PHRASE, tone=_OUTRO_TONE, bgm="outro")
    )
    return StructuredScript(
        variant=variant, generated_at=generated_at, segments=segments
    )
