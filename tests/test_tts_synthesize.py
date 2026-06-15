"""tts.synthesize のユニットテスト (Sprint 2 Ticket T28). モック駆動.

文単位合成 + wav 結合を検証する。str 単位 (コードポイント) の長文分割、1 文失敗時の
fail-open (番組を止めない)、読み仮名正規化の適用、wav の正しい結合を固定する。
"""
from __future__ import annotations

import io
import wave
from datetime import UTC, datetime

from karyu_tech_news.script.structure import Segment, StructuredScript
from karyu_tech_news.tts.engine import (
    Capabilities,
    MockTTSEngine,
    SynthesisRequest,
    SynthesisResult,
    TTSError,
    Voice,
)
from karyu_tech_news.tts.synthesize import (
    concat_wav,
    split_sentences,
    synthesize_script,
)

NOW = datetime(2026, 6, 14, 7, 0, tzinfo=UTC)


def _script(*texts_tones: tuple[str, str]) -> StructuredScript:
    segs = [Segment(kind="topic", text=t, tone=tn, bgm="neutral") for t, tn in texts_tones]
    return StructuredScript(variant="A", generated_at=NOW, segments=segs)


def _nframes(wav_bytes: bytes) -> int:
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        return r.getnframes()


# ---------- split_sentences ----------

def test_split_on_japanese_punctuation() -> None:
    assert split_sentences("深刻だ。また明日。", 100) == ["深刻だ。", "また明日。"]


def test_split_drops_empty_and_whitespace() -> None:
    assert split_sentences("\n  \n文。\n", 100) == ["文。"]


def test_split_long_sentence_by_codepoints() -> None:
    # 句点なしの長文を str 単位で分割 (バイト切り禁止, design-inheritance §6)
    parts = split_sentences("あ" * 250, 100)
    assert [len(p) for p in parts] == [100, 100, 50]
    assert "".join(parts) == "あ" * 250


# ---------- concat_wav ----------

def test_concat_wav_sums_frames() -> None:
    eng = MockTTSEngine()
    a = eng.synthesize(SynthesisRequest(text="あいう", voice_id="hal")).audio
    b = eng.synthesize(SynthesisRequest(text="えお", voice_id="hal")).audio
    combined = concat_wav([a, b])
    assert _nframes(combined) == _nframes(a) + _nframes(b)


def test_concat_wav_empty_returns_empty() -> None:
    assert concat_wav([]) == b""


# ---------- synthesize_script ----------

def test_synthesize_script_returns_wav() -> None:
    res = synthesize_script(_script(("一文目。二文目。", "neutral")), MockTTSEngine(), {})
    assert isinstance(res, SynthesisResult)
    assert res.audio_format == "wav"
    assert _nframes(res.audio) > 0


def test_synthesize_script_applies_reading_dict() -> None:
    # 正規化が合成前に効く: 「小米」→「シャオミ」で渡る
    received: list[str] = []

    class _RecordingEngine:
        def name(self) -> str:
            return "rec"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            received.append(req.text)
            return MockTTSEngine().synthesize(req)

    synthesize_script(_script(("小米。", "neutral")), _RecordingEngine(), {"小米": "シャオミ"})
    assert any("シャオミ" in t for t in received)
    assert all("小米" not in t for t in received)


def test_synthesize_script_fail_open_on_sentence_error() -> None:
    # 1 文の合成失敗で番組を止めない (他文の音声は出る)
    class _FlakyEngine:
        def name(self) -> str:
            return "flaky"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            if "BOOM" in req.text:
                raise TTSError("synth failed")
            return MockTTSEngine().synthesize(req)

    res = synthesize_script(_script(("正常。BOOM。", "neutral")), _FlakyEngine(), {})
    assert _nframes(res.audio) > 0  # 「正常。」の音声は残る


def test_synthesize_script_all_fail_returns_empty_audio() -> None:
    class _DeadEngine:
        def name(self) -> str:
            return "dead"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            raise TTSError("always fails")

    res = synthesize_script(_script(("文。", "neutral")), _DeadEngine(), {})
    assert res.audio == b""  # 全滅でも例外を投げず空音声 (fail-open)
