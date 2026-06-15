"""tts.kokoro のユニットテスト (Sprint 2 Ticket T24). 実 kokoro-onnx 不使用.

kokoro-onnx は optional 依存のため、テストでは backend を注入してアダプタ契約を固定する。
実モデルでの合成 smoke は人間環境 (extra 導入 + モデル DL) で実施する (T13 の音声版)。
"""
from __future__ import annotations

import io
import wave

import pytest

from karyu_tech_news.tts.engine import (
    SynthesisRequest,
    SynthesisResult,
    TTSEngine,
    TTSError,
    select_engine,
)
from karyu_tech_news.tts.kokoro import KokoroTTSEngine, floats_to_wav


def _nframes(wav_bytes: bytes) -> int:
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        return r.getnframes()


# ---------- floats_to_wav (numpy 非依存) ----------

def test_floats_to_wav_produces_valid_wav() -> None:
    wav = floats_to_wav([0.0, 0.5, -0.5, 1.0], 24000)
    assert _nframes(wav) == 4
    with wave.open(io.BytesIO(wav), "rb") as r:
        assert r.getframerate() == 24000
        assert r.getnchannels() == 1
        assert r.getsampwidth() == 2


def test_floats_to_wav_clips_out_of_range() -> None:
    # [-1,1] 外もクリップして壊れない
    assert _nframes(floats_to_wav([2.0, -2.0], 24000)) == 2


# ---------- KokoroTTSEngine (backend 注入) ----------

def _fake_synth(text: str, voice: str) -> tuple[list[float], int]:
    return [0.1] * len(text), 24000  # 文字数ぶんのダミーサンプル


def test_kokoro_satisfies_protocol() -> None:
    assert isinstance(KokoroTTSEngine(synth=_fake_synth), TTSEngine)


def test_kokoro_name_and_capabilities() -> None:
    eng = KokoroTTSEngine(synth=_fake_synth)
    assert eng.name() == "kokoro"
    cap = eng.capabilities()
    assert cap.emoji_style is False  # Kokoro は絵文字スタイル制御なし (Irodori の機能)
    assert cap.max_chars > 0


def test_kokoro_synthesize_returns_wav() -> None:
    eng = KokoroTTSEngine(synth=_fake_synth)
    res = eng.synthesize(SynthesisRequest(text="あいう", voice_id="jf_alpha"))
    assert isinstance(res, SynthesisResult)
    assert res.audio_format == "wav"
    assert res.sample_rate == 24000
    assert _nframes(res.audio) == 3  # "あいう" 3文字


def test_kokoro_backend_exception_wrapped_as_ttserror() -> None:
    def _boom(text: str, voice: str) -> tuple[list[float], int]:
        raise RuntimeError("model error")

    eng = KokoroTTSEngine(synth=_boom)
    with pytest.raises(TTSError):
        eng.synthesize(SynthesisRequest(text="x", voice_id="jf_alpha"))


def test_kokoro_missing_dependency_raises_ttserror() -> None:
    # backend 未注入 + kokoro-onnx 未導入 → 合成時に TTSError (CI で導入なしを想定)
    eng = KokoroTTSEngine()
    with pytest.raises(TTSError):
        eng.synthesize(SynthesisRequest(text="x", voice_id="jf_alpha"))


# ---------- select_engine 統合 (FR-090) ----------

def test_select_engine_kokoro_without_dependency() -> None:
    # select は構築のみ (遅延ロード) なので kokoro-onnx 未導入でも取得できる
    eng = select_engine("kokoro")
    assert isinstance(eng, TTSEngine)
    assert eng.name() == "kokoro"
