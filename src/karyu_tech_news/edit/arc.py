"""アーク配置 (決定的コード).

Sprint 1B Ticket T16。選定済みトピックを三幕構成に並べ替える
(design-inheritance §4.3 `arrangeDeveloperNewsArc` の継承):

1. hard_negative の最高スコアを先頭 (重要ニュース)
2. bright (なければ constructive) を末尾 (明るい話題で締め)
3. constructive を中盤の midpoint に挿入 (解決策・深掘り)

採点は LLM (T15)、並べ替えは本モジュールの決定的コード。
LLM に「並べさせる」と不安定になるため分離する (同 §4.3)。
"""
from __future__ import annotations

from karyu_tech_news.edit.judge import JudgedTopic, Tone


def _highest(topics: list[JudgedTopic], tone: Tone) -> JudgedTopic | None:
    matching = [t for t in topics if t.tone is tone]
    return max(matching, key=lambda t: t.llm_score) if matching else None


def arrange_arc(topics: list[JudgedTopic]) -> list[JudgedTopic]:
    """三幕構成に並べ替えた新リストを返す. 3 本未満はそのまま (入力は変更しない)."""
    if len(topics) < 3:
        return list(topics)

    working = list(topics)

    lead = _highest(working, Tone.HARD_NEGATIVE)
    if lead is not None:
        working = [t for t in working if t is not lead]

    closer = _highest(working, Tone.BRIGHT) or _highest(working, Tone.CONSTRUCTIVE)
    if closer is not None:
        working = [t for t in working if t is not closer]

    middle = working
    constructive = _highest(middle, Tone.CONSTRUCTIVE)
    if constructive is not None and len(middle) > 1:
        rest = [t for t in middle if t is not constructive]
        midpoint = len(rest) // 2
        middle = rest[:midpoint] + [constructive] + rest[midpoint:]

    result = []
    if lead is not None:
        result.append(lead)
    result.extend(middle)
    if closer is not None:
        result.append(closer)
    return result
