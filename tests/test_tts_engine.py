"""tts.engine のユニットテスト (Sprint 2 Ticket T23). 実エンジン不使用・モック駆動.

ADR-0006 の TTSEngine 抽象化 + FR-090 設定駆動エンジン選択を検証する。
実 Irodori 接続 (T24) は環境/声リファレンスが人間ブロッカーのため、ここでは
エンジン非依存の契約 (Protocol 充足・データモデル・セレクタ) のみを固定する。
"""
from __future__ import annotations

import pytest

from karyu_tech_news.tts.engine import (
    Capabilities,
    MockTTSEngine,
    SynthesisRequest,
    SynthesisResult,
    TTSEngine,
    TTSError,
    Voice,
    select_engine,
)

# ---------- データモデル ----------

def test_synthesis_request_defaults() -> None:
    req = SynthesisRequest(text="こんにちは", voice_id="hal")
    assert req.speed == 1.0  # 既定速度


def test_synthesis_request_rejects_empty_text() -> None:
    # 入力検証は境界で fail fast (coding-style §Input Validation)
    with pytest.raises(ValueError):
        SynthesisRequest(text="", voice_id="hal")


# ---------- MockTTSEngine が Protocol を満たす ----------

def test_mock_engine_satisfies_protocol() -> None:
    assert isinstance(MockTTSEngine(), TTSEngine)  # runtime_checkable


def test_mock_name() -> None:
    assert MockTTSEngine().name() == "mock"


def test_mock_voices_nonempty() -> None:
    voices = MockTTSEngine().voices()
    assert voices and all(isinstance(v, Voice) for v in voices)
    assert all(v.language == "ja" for v in voices)  # 配信言語は日本語 (ADR-0006)


def test_mock_capabilities() -> None:
    cap = MockTTSEngine().capabilities()
    assert isinstance(cap, Capabilities)
    assert cap.max_chars > 0


# ---------- 合成 (モック) ----------

def test_mock_synthesize_returns_audio() -> None:
    engine = MockTTSEngine()
    res = engine.synthesize(SynthesisRequest(text="テスト音声", voice_id="hal"))
    assert isinstance(res, SynthesisResult)
    assert res.audio  # 非空バイト列
    assert res.sample_rate > 0
    assert res.audio_format == "wav"


def test_mock_synthesize_is_deterministic() -> None:
    # モックは決定的 (同一入力→同一出力)。パイプラインの回帰テストを安定させる
    engine = MockTTSEngine()
    req = SynthesisRequest(text="同じ文", voice_id="hal")
    assert engine.synthesize(req).audio == engine.synthesize(req).audio


def test_mock_synthesize_varies_by_text() -> None:
    engine = MockTTSEngine()
    a = engine.synthesize(SynthesisRequest(text="文A", voice_id="hal")).audio
    b = engine.synthesize(SynthesisRequest(text="文B", voice_id="hal")).audio
    assert a != b


# ---------- 設定駆動セレクタ (FR-090) ----------

def test_select_engine_returns_mock() -> None:
    engine = select_engine("mock")
    assert isinstance(engine, TTSEngine)
    assert engine.name() == "mock"


def test_select_engine_unknown_raises() -> None:
    with pytest.raises(TTSError):
        select_engine("nonexistent-engine")
