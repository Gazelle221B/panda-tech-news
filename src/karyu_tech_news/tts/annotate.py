"""絵文字注釈レイヤー (Sprint 2 Ticket T27).

architecture §4 / ADR-0006: edit 層の tone 判定 (hard_negative/constructive/bright)
を Irodori-TTS の絵文字スタイル制御に変換する後処理層。台本生成段階では絵文字を
入れず (editorial-policy: 本文に絵文字禁止)、TTS 前処理で機械的に文末挿入する。

エンジンが絵文字スタイルをサポートする場合のみ適用する (capabilities 分岐)。
呼び出し側は `engine.capabilities().emoji_style` を `emoji_enabled` に渡す。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from karyu_tech_news.script.structure import StructuredScript


def load_emoji_annotation(persona_path: Path) -> dict[str, list[str]]:
    """hal_persona.yaml の `tts.emoji_annotation` (tone → 絵文字候補) を読む."""
    raw: Any = yaml.safe_load(persona_path.read_text(encoding="utf-8")) or {}
    tts = raw.get("tts", {}) if isinstance(raw, dict) else {}
    mapping = tts.get("emoji_annotation", {}) if isinstance(tts, dict) else {}
    result: dict[str, list[str]] = {}
    if isinstance(mapping, dict):
        for tone, emojis in mapping.items():
            if isinstance(emojis, list) and emojis:
                result[str(tone)] = [str(e) for e in emojis]
    return result


_SENTENCE_END = ("。", "！", "？")


def annotate_text(text: str, tone: str, mapping: dict[str, list[str]]) -> str:
    """tone に対応する絵文字を 1 個、文末に決定的に付ける (候補先頭を採用).

    末尾が句点なら**句点の直前**に挿入する。文末句点の後ろに付けると T28 の
    文分割で絵文字が単独文になり、スタイル制御が対象文から剥がれるため
    (Codex レビュー指摘)。mapping に無い tone (neutral 等) は無注釈で返す。
    """
    emojis = mapping.get(tone)
    if not emojis:
        return text
    emoji = emojis[0]
    if text and text[-1] in _SENTENCE_END:
        return f"{text[:-1]}{emoji}{text[-1]}"
    return f"{text}{emoji}"


def annotate_script(
    script: StructuredScript,
    mapping: dict[str, list[str]],
    *,
    emoji_enabled: bool,
) -> StructuredScript:
    """各 segment の text に tone 別絵文字を文末挿入した新 script を返す (入力非破壊).

    `emoji_enabled` が False (エンジンが絵文字非対応) のときは無注釈の複製を返す。
    """
    new_segments = []
    for seg in script.segments:
        text = annotate_text(seg.text, seg.tone, mapping) if emoji_enabled else seg.text
        new_segments.append(seg.model_copy(update={"text": text}))
    return script.model_copy(update={"segments": new_segments})
