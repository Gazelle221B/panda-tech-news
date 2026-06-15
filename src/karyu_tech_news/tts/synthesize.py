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
from karyu_tech_news.tts.normalize import normalize_text, strip_ascii_gloss

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 48000  # 空結合時の無音 wav 用 (要件 §17.6)

# 句点・感嘆・疑問で文を切る (区切り文字は前文に残す)。改行は区切り扱い。
_SENTENCE_RE = re.compile(r"[^。！？\n]*[。！？]|[^。！？\n]+")


def _silent_wav(sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """0 フレームの有効な wav (16bit/mono). 合成全滅時も下流が wave.open できるよう返す."""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"")
    return out.getvalue()


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
    """複数の wav バイト列を 1 本に結合する (先頭チャンクのパラメータに揃える).

    - 空入力でも**有効な無音 wav** を返す (下流が wave.open で落ちないように)。
    - 2 本目以降でパラメータ (ch/幅/sample rate) が先頭と異なる chunk はログ付きで
      skip する (異 sample rate を混ぜると速度の壊れた音声になるため, Codex レビュー指摘)。
    """
    if not chunks:
        return _silent_wav()
    out = io.BytesIO()
    params: tuple[int, int, int] | None = None
    with wave.open(out, "wb") as writer:
        for chunk in chunks:
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                cur = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
                if params is None:
                    params = cur
                    writer.setnchannels(cur[0])
                    writer.setsampwidth(cur[1])
                    writer.setframerate(cur[2])
                elif cur != params:
                    logger.warning(
                        "wav パラメータ不一致 %s != %s, skip (fail-open)", cur, params
                    )
                    continue
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
        # 「カナ (原語)」の原語グロスを落としてから読み仮名正規化 (二重読み回避)
        normalized = normalize_text(strip_ascii_gloss(seg.text), reading_dict)
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
