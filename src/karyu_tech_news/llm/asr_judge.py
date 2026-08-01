"""ASR 曖昧域判定の LLM 実装 (Sprint 2 Ticket T66, Issue #76).

`tts.asr_gate.verify_sentence` は機械比較 (difflib 類似度 + 長さ比) だけでは
表記ゆれの吸収が粗く、数字の誤読 (例: 「2027年」→「2017年」) を原理的に検出できない。
本モジュールは曖昧域 (類似度 0.5〜0.85 未満 / 長さ比異常) のみを LLM に判定させる
`tts.asr_gate.AsrJudge` Protocol の具象実装を提供する。

アーキテクチャ上の位置づけ: tts 層は llm 層を import しない (Issue #76 の設計制約)。
本モジュールも tts 層を import しない (2026-08-02 レビュー差し戻し対応: 当初
`tts.asr_gate.AsrVerdictStatus` を型として import していたが、ランタイムの層間 import を
完全に消すため、値集合が同一の `Literal` をこのモジュール内に複製した。`AsrJudge`
Protocol は構造的型付けのため、Literal の値集合が一致していれば
`tts.asr_gate.AsrJudge` を満たす)。構築 (`build_llm_asr_judge`) は main.py の produce が
persona 設定 (`tts.asr_judge_profile`) を読んで呼び出す。

fail-open 方針: プロファイル未解決・API キー未設定などの構築時失敗、および
LLM 呼び出し失敗・JSON 崩れ・スキーマ不正はすべて WARN ログの上 None を返す。
呼び出し元 (`verify_sentence`) は None を「判定不能」として従来の機械判定に
フォールバックする (ASR ゲート自体は止めない)。

judge プロンプト精緻化 (T66b, 2026-08-02 実戦投入 draft #5 の実測反映): 曖昧域 6 文中、
同音異字の ASR 誤変換 (「測る」↔「図る」、「四半期」↔「市販機」) と括弧読み下しに伴う
聞き取りノイズ (「シーシーシー認証」↔「各区、CCC認証」) を誤って mismatch/insertion
判定していたことが判明した。`ASR_JUDGE_SYSTEM_PROMPT` に (a) 書き起こしが不完全な ASR
出力である旨の明示、(b) 同音・類音の漢字違いと括弧読み下しの軽微な語増減を ok とする
基準、(c) mismatch を「同音では説明できない」明確な相違に限定する基準、(d) insertion を
文・フレーズ単位の追加発話に限定する基準を追加して対応した。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from karyu_tech_news.llm.client import LLMClient, LLMError
from karyu_tech_news.llm.profile import DEFAULT_LLM_PROFILES_PATH, load_llm_profiles

logger = logging.getLogger(__name__)

# `tts.asr_gate.AsrVerdictStatus` と値集合が同一のローカル複製 (2026-08-02 レビュー
# 差し戻し対応)。llm 層から tts 層へのランタイム import を避けるための複製であり、
# `AsrJudge` Protocol への適合は構造的型付け (Literal の値集合一致) で成立する。
_AsrVerdictStatus = Literal["ok", "mismatch", "insertion"]

JUDGE_TEMPERATURE = 0.0  # 決定性最優先 (edit/judge.py と同じ流儀)。
DEFAULT_ASR_JUDGE_PROFILE = "openai-luna"  # config/hal_persona.yaml の既定値と一致させる

ASR_JUDGE_SYSTEM_PROMPT = (
    "あなたは日本語ニュース番組の TTS 読み上げ QA 判定器。台本の期待文と ASR (音声認識) "
    "の書き起こしを突き合わせ、読み上げとして忠実かどうかを判定する。"
    "書き起こしは不完全な ASR の出力であり、TTS が台本どおり正しく読み上げていても "
    "認識ゆれ (同音異字の誤変換、助詞・読点の聞き取りゆれ等) が生じうることを踏まえて "
    "判定する。JSON だけを返し、説明・前置きを書かない。\n"
    "判定基準:\n"
    "- 表記ゆれ (カナ↔英字表記、例:「AI」↔「エーアイ」/ 漢数字↔算用数字表記、"
    "例:「二千二十七年」↔「2027年」) は同一の内容とみなし ok。\n"
    "- 同音・類音の漢字違い (例:「測る」↔「図る」、「四半期」↔「市販機」) は ASR の "
    "認識ゆれとみなし ok。助詞・読点の聞き取りゆれや、括弧「（）」の読み下しに伴う "
    "軽微な語の増減 (例:「強制製品認証（シーシーシー認証）」↔「強制製品認証各区、"
    "CCC認証」) も ok。\n"
    "- 数字の値そのものが相違している場合 (例: 期待文の「2027年」に対し書き起こしが "
    "「2017年」) は mismatch。年号・件数・金額など意味が変わる数字の誤読を最優先で拾う。\n"
    "- 同音・類音では説明できない単語レベルの明確な相違 (例:「半導体市況」に対し "
    "「半導体ガシモン」) や、文そのものの欠落も mismatch。\n"
    "- 台本に無い文・フレーズ単位の発話が挿入されている場合のみ insertion とする "
    "(単語 1 個程度の聞き取りゆれは insertion にしない)。\n"
    "- 上記いずれにも該当せず、読み上げとして意味が保たれていれば ok。\n"
    '出力スキーマ (JSON): {"verdict": "ok" または "mismatch" または "insertion", '
    '"reason": "20字程度の日本語理由"}'
)


class AsrJudgeError(Exception):
    """ASR LLM 判定の失敗 (JSON 抽出不能・スキーマ不正)."""


class _AsrJudgment(BaseModel):
    """LLM 応答の検証スキーマ."""

    verdict: _AsrVerdictStatus
    reason: str = ""


def _extract_json_object(text: str) -> dict[str, Any]:
    """LLM 出力から JSON オブジェクトを頑健に取り出す (edit/judge.py と同じ流儀を移植).

    1. まず素直に json.loads
    2. 失敗したら ```json フェンスを剥がし、最外の {...} を切り出して再試行
    """
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass

    stripped = text.replace("```json", "").replace("```", "")
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AsrJudgeError("LLM output contains no JSON object")
    try:
        loaded = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AsrJudgeError(f"LLM output JSON parse failed: {exc}") from exc
    if not isinstance(loaded, dict):
        raise AsrJudgeError("LLM output JSON is not an object")
    return loaded


def build_asr_judge_prompt(expected: str, transcript: str) -> str:
    """判定対象 1 文の user プロンプトを組み立てる."""
    return f"期待文 (台本): {expected}\nASR書き起こし: {transcript}"


class LLMAsrJudge:
    """`tts.asr_gate.AsrJudge` Protocol の LLM 実装.

    LLM 呼び出し失敗・JSON 崩れ・スキーマ不正は judge() 内で揉み消し None を返す
    (fail-open, 呼び出し元の verify_sentence が機械判定にフォールバックする)。
    """

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def judge(self, expected: str, transcript: str) -> _AsrVerdictStatus | None:
        try:
            response = self._client.chat(
                system=ASR_JUDGE_SYSTEM_PROMPT,
                user=build_asr_judge_prompt(expected, transcript),
                json_mode=True,
                temperature=JUDGE_TEMPERATURE,
            )
            data = _extract_json_object(response.content)
            judgment = _AsrJudgment.model_validate(data)
        except (LLMError, AsrJudgeError, ValidationError) as exc:
            logger.warning("ASR LLM 判定に失敗 (fail-open, 機械判定へフォールバック): %s", exc)
            return None
        return judgment.verdict


def build_llm_asr_judge(profile_label: str = DEFAULT_ASR_JUDGE_PROFILE) -> LLMAsrJudge | None:
    """persona の `tts.asr_judge_profile` から LLM judge を構築する.

    プロファイル未解決・API キー未設定などの構築時失敗も fail-open で None を返す
    (呼び出し元の produce は ASR ゲート自体を止めない)。
    """
    try:
        profiles = load_llm_profiles(DEFAULT_LLM_PROFILES_PATH)
        profile = profiles.profile_by_label(profile_label)
        client = LLMClient(profile)
    except Exception as exc:  # noqa: BLE001 -- 構築失敗は種類を問わず fail-open (persona 読み込みと同じ流儀)
        logger.warning(
            "ASR judge profile=%s の構築に失敗 (fail-open, 機械判定のみで続行): %s",
            profile_label,
            type(exc).__name__,
        )
        return None
    return LLMAsrJudge(client)
