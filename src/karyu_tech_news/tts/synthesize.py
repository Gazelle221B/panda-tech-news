"""文単位合成 + wav 結合 (Sprint 2 Ticket T28).

構造化台本 (T25) の各 segment を文に分割し、読み仮名正規化 (T26) を適用してから
エンジン (T23) で 1 文ずつ合成し、wav を結合する。

設計原則:
- **str 単位の長文分割** (バイト切り禁止, design-inheritance §6 / AGENTS §3.2)。
- **1 文の失敗で番組を止めない** (fail-open, 要件 §9.3)。失敗文はログに記録しスキップ。
- 絵文字注釈 (T27): `emoji_mapping` を渡すと **文単位** で tone 別絵文字を挿入する
  (T33+ 改善)。produce は台本全体を 1 segment に畳むため、segment 単位の事前
  annotate では 1 絵文字しか乗らず制御が効かなかった。エンジンが絵文字スタイル
  非対応 (kokoro 等) の場合は capabilities で自動的に無効化する。
- BGM ミックス (T29) はこの結合済み wav を入力にする (本モジュールは素材を扱わない)。
"""
from __future__ import annotations

import io
import logging
import re
import wave

from karyu_tech_news.script.structure import StructuredScript
from karyu_tech_news.tts.annotate import annotate_text
from karyu_tech_news.tts.engine import (
    SynthesisRequest,
    SynthesisResult,
    TTSEngine,
    TTSError,
)
from karyu_tech_news.tts.normalize import (
    normalize_text,
    strip_ascii_gloss,
    strip_script_markup,
)

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
    if max_chars <= 0:  # engine が誤って 0/負を返した場合に分かりやすく失敗 (Copilot 指摘)
        raise ValueError(f"max_chars は正である必要があります: {max_chars}")
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
    - 壊れた wav chunk (wave.Error/EOFError) もログ付きで skip する (fail-open, Copilot 指摘)。
    """
    params: tuple[int, int, int] | None = None
    parsed: list[bytes] = []
    for chunk in chunks:
        try:
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                cur = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
                frames = reader.readframes(reader.getnframes())
        except (wave.Error, EOFError) as exc:
            logger.warning("壊れた wav chunk を skip (fail-open): %s", exc)
            continue
        if params is None:
            params = cur
        elif cur != params:
            logger.warning("wav パラメータ不一致 %s != %s, skip (fail-open)", cur, params)
            continue
        parsed.append(frames)
    if params is None:  # 有効 chunk ゼロ (空入力 or 全破損) → 有効な無音 wav
        return _silent_wav()
    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        writer.setnchannels(params[0])
        writer.setsampwidth(params[1])
        writer.setframerate(params[2])
        for frames in parsed:
            writer.writeframes(frames)
    return out.getvalue()


def synthesize_script(
    script: StructuredScript,
    engine: TTSEngine,
    reading_dict: dict[str, str],
    *,
    voice_id: str | None = None,
    emoji_mapping: dict[str, list[str]] | None = None,
    caption: str | None = None,
) -> SynthesisResult:
    """構造化台本を 1 本の wav に合成する (正規化 → 文分割 → 絵文字注釈 → 合成 → 結合, fail-open).

    voice_id 未指定時は **エンジン自身の既定声** を使う。エンジンごとに声 ID が異なる
    (kokoro=jf_alpha / irodori=hal) ため "hal" 固定だと kokoro で全文が「声が無い」と
    fail-open し無音になる。HAL ペルソナはエンジン非依存 (FR-091) で各エンジンが
    内部の実声 ID にマップする。

    emoji_mapping (tone → 絵文字候補) を渡し、かつエンジンが絵文字スタイル制御に対応
    (capabilities().emoji_style) する場合のみ、**文単位** で tone 別絵文字を挿入する。
    正規化後・合成直前に挿入するため、絵文字は前処理 (strip/normalize) の影響を受けない。
    """
    if voice_id is None:
        voices = engine.voices()
        voice_id = voices[0].id if voices else ""
    caps = engine.capabilities()
    max_chars = caps.max_chars
    emoji_enabled = bool(emoji_mapping) and caps.emoji_style
    # caption は VoiceDesign 対応エンジンのみ渡す (非対応エンジンは無視するが明示的に None 化)
    effective_caption = caption if caps.voice_design else None
    chunks: list[bytes] = []
    for seg in script.segments:
        # TTS 前処理: Markdown マーカー除去 → 原語グロス除去 → 読み仮名正規化
        cleaned = strip_ascii_gloss(strip_script_markup(seg.text))
        normalized = normalize_text(cleaned, reading_dict)
        for sentence in split_sentences(normalized, max_chars):
            # 絵文字は正規化後・文単位で挿入 (segment 単位だと 1 文しか効かないため, T33+)
            text = (
                annotate_text(sentence, seg.tone, emoji_mapping)
                if emoji_enabled and emoji_mapping is not None
                else sentence
            )
            try:
                res = engine.synthesize(
                    SynthesisRequest(text=text, voice_id=voice_id, caption=effective_caption)
                )
            except TTSError as exc:
                logger.warning("synth failed (fail-open), skipped: %s", exc)
                continue
            chunks.append(res.audio)
    combined = concat_wav(chunks)
    # sample_rate は結合済み wav のヘッダから読む (chunk skip 時もメタデータが実値と一致)
    with wave.open(io.BytesIO(combined), "rb") as r:
        sample_rate = r.getframerate()
    return SynthesisResult(audio=combined, sample_rate=sample_rate, audio_format="wav")
