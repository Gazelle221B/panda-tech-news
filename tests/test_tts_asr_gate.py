"""tts.asr_gate のユニットテスト (Sprint 2 Ticket T58, Issue #54). whisper 実体は使わない.

verify_sentence の判定ロジックと、WhisperAsrBackend の遅延 import 契約 (未導入時に
AsrUnavailableError) を固定する。実 openai-whisper での書き起こし精度検証は対象外
(人間環境での実 produce smoke で行う)。
"""
from __future__ import annotations

import sys

import pytest

from karyu_tech_news.tts.asr_gate import (
    AsrBackend,
    AsrUnavailableError,
    AsrVerdict,
    WhisperAsrBackend,
    verify_sentence,
)

# ---------- verify_sentence ----------


def test_verify_sentence_exact_match_is_ok() -> None:
    verdict = verify_sentence("今日は良い天気です。", "今日は良い天気です")
    assert verdict.status == "ok"
    assert verdict.similarity == pytest.approx(1.0)


def test_verify_sentence_completely_different_is_mismatch() -> None:
    # 文が丸ごと別物 (類似度が閾値未満)
    verdict = verify_sentence("今日は良い天気です。", "株価が急落しました")
    assert verdict.status == "mismatch"
    assert verdict.similarity < 0.5


def test_verify_sentence_empty_transcript_is_mismatch() -> None:
    # 無音 ASR 等で空文字が返ったケース (類似度 0)
    verdict = verify_sentence("今日は良い天気です。", "")
    assert verdict.status == "mismatch"
    assert verdict.similarity == 0.0


def test_verify_sentence_trailing_addition_is_insertion() -> None:
    # 2026-07-31 dry-run 実測の典型パターン: 文末への一言追加 (幻話疑い)
    verdict = verify_sentence(
        "対応を進めます。", "本当にすみませんが対応を進めます"
    )
    assert verdict.status == "insertion"
    assert verdict.similarity >= 0.5
    assert verdict.length_ratio > 1.6


def test_verify_sentence_notation_variance_stays_ok() -> None:
    # 表記ゆれ (「AI」↔「エーアイ」等の直交する読み違い) は誤検出しない (閾値を緩めた理由)
    verdict = verify_sentence("これはAIの話です。", "これはエーアイの話です")
    assert verdict.status == "ok"


def test_verify_sentence_ignores_case_and_punctuation() -> None:
    verdict = verify_sentence("Hello、World!", "hello world")
    assert verdict.status == "ok"


def test_asr_verdict_is_frozen_dataclass() -> None:
    verdict = AsrVerdict(status="ok", similarity=1.0, length_ratio=1.0)
    with pytest.raises(AttributeError):
        verdict.status = "mismatch"  # type: ignore[misc]


# ---------- AsrBackend protocol ----------


class _FakeAsrBackend:
    def transcribe(self, wav_bytes: bytes) -> str:
        return "テスト"


def test_fake_backend_satisfies_protocol() -> None:
    assert isinstance(_FakeAsrBackend(), AsrBackend)


# ---------- WhisperAsrBackend (遅延 import) ----------


def test_whisper_backend_missing_dependency_raises_asr_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # openai-whisper の import を強制失敗させ、未導入時 AsrUnavailableError を hermetic に固定
    monkeypatch.setitem(sys.modules, "whisper", None)
    backend = WhisperAsrBackend()
    with pytest.raises(AsrUnavailableError):
        backend.transcribe(b"not a real wav")


def test_whisper_backend_construction_does_not_require_whisper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # コンストラクタ自体は import しない (未導入環境でも produce の構築を壊さない, T58 設計)
    monkeypatch.setitem(sys.modules, "whisper", None)
    WhisperAsrBackend()  # 例外を送出しないことを確認


def test_whisper_backend_caches_loaded_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class _FakeModel:
        def transcribe(self, path: str, **kwargs: object) -> dict[str, str]:
            calls.append(path)
            return {"text": "こんにちは"}

    class _FakeWhisperModule:
        @staticmethod
        def load_model(name: str) -> _FakeModel:
            calls.append(f"load:{name}")
            return _FakeModel()

    monkeypatch.setitem(sys.modules, "whisper", _FakeWhisperModule())
    backend = WhisperAsrBackend(model_name="turbo")
    assert backend.transcribe(b"RIFF....") == "こんにちは"
    assert backend.transcribe(b"RIFF....") == "こんにちは"
    # load_model は初回のみ (2 回目以降はキャッシュ済みモデルを再利用)
    assert calls.count("load:turbo") == 1
