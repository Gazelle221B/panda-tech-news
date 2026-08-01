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
    ASR_JUDGE_SYSTEM_PROMPT,
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


# ---------- judge プロンプト精緻化 (T66b, Issue #76 続き): 実測 draft #5 の同音異字誤検出対応 ----------
#
# 実戦投入 (draft #5 produce, 全25文中曖昧域6文) で以下の誤判定が判明した:
# - 「実需を測る」↔「実需を図る」(同音異字 はかる) が mismatch に誤検出
# - 「四半期決算」↔「市販機決算」(同音 しはんき) が mismatch に誤検出
# - 「強制製品認証（シーシーシー認証）」↔「強制製品認証各区、CCC認証」
#   (括弧読み下しに伴う聞き取りノイズ) が insertion に誤検出
# - 「半導体市況」↔「半導体ガシモン」(同音ではない、TTS の実誤読の可能性) は mismatch の
#   ままで良い (真陽性疑い)
#
# プロンプトが実際にこれらを正しく判定するかは実 API でしか検証できないため、ここでは
# (a) プロンプトが該当基準・実例を含むこと (プロンプト文言の存在アサート) と、
# (b) fake LLM 応答を注入した場合に LLMAsrJudge がその verdict をそのまま通すこと
# (配線確認、既存の fake 方式を踏襲) の 2 点を固定する。実 API は呼ばない。


def test_prompt_mentions_transcript_is_imperfect_asr_output() -> None:
    assert "不完全な ASR" in ASR_JUDGE_SYSTEM_PROMPT


def test_prompt_treats_homophone_kanji_variance_as_ok() -> None:
    assert "測る" in ASR_JUDGE_SYSTEM_PROMPT
    assert "図る" in ASR_JUDGE_SYSTEM_PROMPT
    assert "四半期" in ASR_JUDGE_SYSTEM_PROMPT
    assert "市販機" in ASR_JUDGE_SYSTEM_PROMPT


def test_prompt_treats_parenthetical_readout_noise_as_ok() -> None:
    assert "括弧" in ASR_JUDGE_SYSTEM_PROMPT
    assert "シーシーシー認証" in ASR_JUDGE_SYSTEM_PROMPT


def test_prompt_mismatch_definition_requires_non_homophone_difference() -> None:
    assert "同音" in ASR_JUDGE_SYSTEM_PROMPT
    assert "半導体市況" in ASR_JUDGE_SYSTEM_PROMPT
    assert "半導体ガシモン" in ASR_JUDGE_SYSTEM_PROMPT


def test_prompt_insertion_definition_restricted_to_phrase_or_sentence_level() -> None:
    assert "フレーズ単位" in ASR_JUDGE_SYSTEM_PROMPT
    assert "単語 1 個" in ASR_JUDGE_SYSTEM_PROMPT


def test_llm_asr_judge_homophone_kanji_hakaru_returns_ok() -> None:
    # 「測る」↔「図る」(同音異字 はかる) は ok と判定されるべき (fake 応答で配線確認)
    client = _mock_client('{"verdict": "ok", "reason": "同音異字(測る/図る)の認識ゆれ"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("実需を測る。", "実需を図る") == "ok"


def test_llm_asr_judge_homophone_shihanki_returns_ok() -> None:
    # 「四半期」↔「市販機」(同音 しはんき) は ok と判定されるべき (fake 応答で配線確認)
    client = _mock_client('{"verdict": "ok", "reason": "同音(四半期/市販機)の認識ゆれ"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("四半期決算。", "市販機決算") == "ok"


def test_llm_asr_judge_parenthetical_readout_noise_returns_ok() -> None:
    # 括弧読み下しに伴う聞き取りノイズは ok と判定されるべき (fake 応答で配線確認)
    client = _mock_client('{"verdict": "ok", "reason": "括弧読み下しの聞き取りノイズ"}')
    judge = LLMAsrJudge(client)
    expected = "強制製品認証（シーシーシー認証）。"
    transcript = "強制製品認証各区、CCC認証"
    assert judge.judge(expected, transcript) == "ok"


def test_llm_asr_judge_true_misread_gashimon_returns_mismatch() -> None:
    # 「半導体市況」↔「半導体ガシモン」(同音ではない) は mismatch のまま (真陽性疑い、fake 応答で配線確認)
    client = _mock_client('{"verdict": "mismatch", "reason": "同音では説明できない相違"}')
    judge = LLMAsrJudge(client)
    assert judge.judge("半導体市況。", "半導体ガシモン") == "mismatch"
