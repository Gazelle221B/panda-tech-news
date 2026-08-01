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
    AsrJudge,
    AsrUnavailableError,
    AsrVerdict,
    AsrVerdictStatus,
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


# ---------- AsrJudge protocol / verify_sentence 段階分岐 (T66, Issue #76) ----------


class _RecordingJudge:
    """呼出有無と引数を記録する fake judge. 固定 verdict (または None) を返す."""

    def __init__(self, verdict: AsrVerdictStatus | None) -> None:
        self._verdict = verdict
        self.calls: list[tuple[str, str]] = []

    def judge(self, expected: str, transcript: str) -> AsrVerdictStatus | None:
        self.calls.append((expected, transcript))
        return self._verdict


def test_fake_judge_satisfies_protocol() -> None:
    assert isinstance(_RecordingJudge("ok"), AsrJudge)


def test_verify_sentence_fast_path_does_not_call_judge() -> None:
    # 類似度 >= FAST_PATH_SIMILARITY かつ長さ比正常 → judge を一切呼ばない
    judge = _RecordingJudge("mismatch")  # 呼ばれたら誤判定になる値をわざと設定
    verdict = verify_sentence("今日は良い天気です。", "今日は良い天気です", judge=judge)
    assert verdict.status == "ok"
    assert judge.calls == []


def test_verify_sentence_definite_mismatch_does_not_call_judge() -> None:
    # 類似度 < SIMILARITY_MISMATCH_THRESHOLD (壊滅的不一致) → judge を呼ばず即 mismatch
    judge = _RecordingJudge("ok")  # 呼ばれたら誤判定になる値をわざと設定
    verdict = verify_sentence("今日は良い天気です。", "株価が急落しました", judge=judge)
    assert verdict.status == "mismatch"
    assert judge.calls == []


def test_verify_sentence_ambiguous_zone_calls_judge_and_uses_its_verdict() -> None:
    # 曖昧域 (類似度 0.5〜0.85 未満、長さ比正常) は judge に委譲し、その結果を採用する。
    # 表記ゆれ例 (「AI」↔「エーアイ」) は機械判定のみなら ok だが、judge が mismatch を
    # 返せばそれを優先する (judge の判断を尊重する契約を固定)。
    judge = _RecordingJudge("mismatch")
    expected, transcript = "これはAIの話です。", "これはエーアイの話です"
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert 0.5 <= verdict.similarity < 0.85  # 曖昧域に入っていることの前提確認
    assert verdict.status == "mismatch"
    assert judge.calls == [(expected, transcript)]


def test_verify_sentence_judge_none_falls_back_to_mechanical_status() -> None:
    # 曖昧域で judge が None (判定不能) を返したら、従来の機械判定 (長さ比のみ) へ
    # fail-open する。
    judge = _RecordingJudge(None)
    expected, transcript = "これはAIの話です。", "これはエーアイの話です"
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert judge.calls == [(expected, transcript)]
    # judge なしの従来テスト (test_verify_sentence_notation_variance_stays_ok) と同じ結果
    assert verdict.status == "ok"


def test_verify_sentence_ambiguous_zone_without_judge_uses_mechanical_status() -> None:
    # judge 未指定なら曖昧域でも従来どおり機械判定のみ (後方互換の固定)。
    expected, transcript = "これはAIの話です。", "これはエーアイの話です"
    verdict = verify_sentence(expected, transcript)
    assert 0.5 <= verdict.similarity < 0.85
    assert verdict.status == "ok"


def test_verify_sentence_ambiguous_zone_number_mismatch_detected_via_judge() -> None:
    # T66 の主目的: 機械判定だけでは拾えない数字誤読を judge が検出する。
    expected, transcript = "2027年。", "2017年"
    mechanical_only = verify_sentence(expected, transcript)
    assert 0.5 <= mechanical_only.similarity < 0.85  # 曖昧域に入る (前提確認)
    assert mechanical_only.status == "ok"  # 機械判定だけでは数字誤読を拾えない

    judge = _RecordingJudge("mismatch")
    with_judge = verify_sentence(expected, transcript, judge=judge)
    assert with_judge.status == "mismatch"
    assert judge.calls == [(expected, transcript)]


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
