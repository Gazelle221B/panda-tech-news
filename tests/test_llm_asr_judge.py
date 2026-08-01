"""llm.asr_judge のユニットテスト (Sprint 2 Ticket T66, Issue #76). 実 LLM API は呼ばない.

LLMAsrJudge.judge() の ok/mismatch/insertion/JSON崩れ分岐と、
build_llm_asr_judge() のプロファイル未解決・API キー未設定時の fail-open を固定する。
数字誤読 (2027年→2017年) を judge プロンプト経由で検出する統合テストも含む
(fake LLM 応答。verify_sentence との end-to-end 配線を確認する)。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from karyu_tech_news.llm.asr_judge import (
    DEFAULT_ASR_JUDGE_PROFILE,
    AsrJudgeError,
    LLMAsrJudge,
    _extract_json_object,
    build_asr_judge_prompt,
    build_llm_asr_judge,
)
from karyu_tech_news.llm.client import LLMError, LLMResponse
from karyu_tech_news.tts.asr_gate import verify_sentence


def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.return_value = LLMResponse(content=content)
    return client


# ---------- _extract_json_object ----------


def test_extract_json_object_plain() -> None:
    assert _extract_json_object('{"verdict": "ok"}') == {"verdict": "ok"}


def test_extract_json_object_fenced() -> None:
    text = '```json\n{"verdict": "mismatch", "reason": "数字が違う"}\n```'
    assert _extract_json_object(text) == {"verdict": "mismatch", "reason": "数字が違う"}


def test_extract_json_object_invalid_raises() -> None:
    with pytest.raises(AsrJudgeError):
        _extract_json_object("これはJSONではない")


# ---------- LLMAsrJudge.judge: ok/mismatch/insertion/JSON崩れ ----------


def test_llm_asr_judge_returns_ok() -> None:
    client = _mock_client('{"verdict": "ok", "reason": "表記ゆれのみ"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("これはAIの話です。", "これはエーアイの話です") == "ok"


def test_llm_asr_judge_returns_mismatch() -> None:
    client = _mock_client('{"verdict": "mismatch", "reason": "年の値が違う"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("2027年。", "2017年") == "mismatch"


def test_llm_asr_judge_returns_insertion() -> None:
    client = _mock_client('{"verdict": "insertion", "reason": "台本にない発話"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("対応します。", "本当にすみませんが対応します") == "insertion"


def test_llm_asr_judge_broken_json_fails_open_to_none() -> None:
    client = _mock_client("これはJSONではない応答です")
    judge = LLMAsrJudge(client)
    assert judge.judge("期待文", "書き起こし") is None


def test_llm_asr_judge_unknown_verdict_value_fails_open_to_none() -> None:
    # スキーマ不正 (verdict が未知の値) も fail-open で None
    client = _mock_client('{"verdict": "maybe", "reason": "不明"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("期待文", "書き起こし") is None


def test_llm_asr_judge_llm_error_fails_open_to_none() -> None:
    client = MagicMock()
    client.chat.side_effect = LLMError("接続失敗")
    judge = LLMAsrJudge(client)
    assert judge.judge("期待文", "書き起こし") is None


def test_llm_asr_judge_passes_json_mode_and_temperature_zero() -> None:
    client = _mock_client('{"verdict": "ok"}')
    LLMAsrJudge(client).judge("期待文", "書き起こし")
    assert client.chat.call_count == 1
    _, kwargs = client.chat.call_args
    assert kwargs["json_mode"] is True
    assert kwargs["temperature"] == 0.0


def test_build_asr_judge_prompt_contains_both_texts() -> None:
    prompt = build_asr_judge_prompt("期待文A", "書き起こしB")
    assert "期待文A" in prompt
    assert "書き起こしB" in prompt


# ---------- build_llm_asr_judge: 構築時 fail-open ----------


def test_build_llm_asr_judge_unknown_profile_fails_open_to_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    with caplog.at_level(logging.WARNING):
        judge = build_llm_asr_judge("does-not-exist-profile")
    assert judge is None
    assert "does-not-exist-profile" in caplog.text


def test_build_llm_asr_judge_missing_api_key_fails_open_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 既定プロファイル openai-luna は OPENAI_API_KEY を要求する。未設定なら
    # LLMClient 構築が LLMError を送出するが、build_llm_asr_judge は fail-open で
    # None を返し、produce の ASR ゲート自体は止めない (Issue #76)。
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    judge = build_llm_asr_judge(DEFAULT_ASR_JUDGE_PROFILE)
    assert judge is None


# ---------- 統合テスト: 数字誤読を judge プロンプト経由で検出 (fake 応答) ----------


def test_number_mismatch_detected_end_to_end_via_verify_sentence() -> None:
    """機械判定だけでは拾えない数字誤読 (2027年→2017年) を、fake LLM 応答経由の
    LLMAsrJudge が verify_sentence の曖昧域判定で mismatch として検出することを確認する
    (T66 の主目的、Issue #76 DoD)。"""
    expected, transcript = "2027年。", "2017年"

    # 機械判定のみ (judge なし) では検出できないことを先に確認 (回帰の前提)
    assert verify_sentence(expected, transcript).status == "ok"

    client = _mock_client('{"verdict": "mismatch", "reason": "年の値が2027から2017に相違"}')
    judge = LLMAsrJudge(client)
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert verdict.status == "mismatch"
    # judge に渡された内容がプロンプトへ正しく反映されていることを確認
    _, kwargs = client.chat.call_args
    assert expected in kwargs["user"]
    assert transcript in kwargs["user"]
