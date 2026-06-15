"""文単位合成 + wav 結合 (Sprint 2 Ticket T28).

構造化台本 (T25) の各 segment を文に分割し、読み仮名正規化 (T26) を適用してから
エンジン (T23) で 1 文ずつ合成し、wav を結合する。

設計原則:
- **str 単位の長文分割** (バイト切り禁止, design-inheritance §6 / AGENTS §3.2)。
- **1 文の失敗で番組を止めない** (fail-open, 要件 §9.3)。失敗文はログに記録しスキップ。
- 絵文字注釈 (T27) は呼び出し側で適用済みの StructuredScript を渡す前提。
- BGM ミックス (T29) はこの結合済み wav を入力にする (本モジュールは素材を扱わない)。
"""
from __future__ import annotations

import io
import logging
import re
import wave

from karyu_tech_news.script.structure import StructuredScript
from karyu_tech_news.tts.engine import (
    MOCK_SAMPLE_RATE,
    SynthesisRequest,
    SynthesisResult,
    TTSEngine,
    TTSError,
)
from karyu_tech_news.tts.normalize import normalize_text

logger = logging.getLogger(__name__)

# 句点・感嘆・疑問で文を切る (区切り文字は前文に残す)。改行は区切り扱い。
_SENTENCE_RE = re.compile(r"[^。！？\n]*[。！？]|[^。！？\n]+")


def split_sentences(text: str, max_chars: int) -> list[str]:
    """text を文に分割する. max_chars を超える文は str 単位でさらに分割する."""
    sentences: list[str] = []
    for raw in _SENTENCE_RE.findall(text):
        s = raw.strip()
        if not s:
            continue
        if len(s) <= max_chars:
            sentences.append(s)
        else:
            for i in range(0, len(s), max_chars):  # コードポイント単位の切り分け
                sentences.append(s[i : i + max_chars])
    return sentences


def concat_wav(chunks: list[bytes]) -> bytes:
    """複数の wav バイト列を 1 本に結合する (先頭チャンクのパラメータに揃える)."""
    if not chunks:
        return b""
    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        for i, chunk in enumerate(chunks):
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                if i == 0:
                    writer.setnchannels(reader.getnchannels())
                    writer.setsampwidth(reader.getsampwidth())
                    writer.setframerate(reader.getframerate())
                writer.writeframes(reader.readframes(reader.getnframes()))
    return out.getvalue()


def synthesize_script(
    script: StructuredScript,
    engine: TTSEngine,
    reading_dict: dict[str, str],
    *,
    voice_id: str = "hal",
) -> SynthesisResult:
    """構造化台本を 1 本の wav に合成する (正規化 → 文分割 → 合成 → 結合, fail-open)."""
    max_chars = engine.capabilities().max_chars
    chunks: list[bytes] = []
    sample_rate = MOCK_SAMPLE_RATE
    for seg in script.segments:
        normalized = normalize_text(seg.text, reading_dict)
        for sentence in split_sentences(normalized, max_chars):
            try:
                res = engine.synthesize(
                    SynthesisRequest(text=sentence, voice_id=voice_id)
                )
            except TTSError as exc:
                logger.warning("synth failed (fail-open), skipped: %s", exc)
                continue
            chunks.append(res.audio)
            sample_rate = res.sample_rate
    return SynthesisResult(
        audio=concat_wav(chunks), sample_rate=sample_rate, audio_format="wav"
    )
