"""TTSEngine 抽象化 + 設定駆動エンジン選択 (Sprint 2 Ticket T23, FR-090).

ADR-0006 の決定:
- `TTSEngine` Protocol を1枚噛ませ、エンジン (Irodori v3 主軸 / Kokoro fallback 等) を
  差し替え可能にする。台本・ミックス層は本 Protocol にのみ依存する。
- HAL の人格・声は TTS 非依存で保持 (FR-091)。エンジンが変わっても声を維持。

本モジュールはエンジン非依存の **契約とモック** のみを提供する。実 Irodori 接続
(`tts/irodori.py`) は T24 で追加し、実行環境・声リファレンスの人間判断後に有効化する
(IMPLEMENTATION_PLAN-2 §6)。それまではモック駆動で下流 (T25-T28) を先行実装できる。
"""
from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, field_validator

MOCK_SAMPLE_RATE = 48000  # mp3 192kbps/48kHz 想定 (要件 §17.6) に合わせたモック値
MOCK_MAX_CHARS = 2000  # 1 リクエストの目安上限 (長文は T28 で文単位分割)


class TTSError(Exception):
    """TTS 合成・エンジン選択の失敗 (1 文の失敗は T28 で fail-open に扱う)."""


class Voice(BaseModel):
    """エンジンが提供する話者. HAL の声は profile 側で固定する (FR-091)."""

    id: str
    name: str
    language: str = "ja"  # 配信言語は日本語 (ADR-0006)


class Capabilities(BaseModel):
    """エンジンの能力. 周辺処理 (絵文字注釈 T27 等) が分岐に使う."""

    emoji_style: bool  # 絵文字によるスタイル制御 (Irodori v3 の特徴)
    voice_clone: bool  # ゼロショット音声クローン
    streaming: bool
    max_chars: int  # 1 リクエストで安全に渡せる文字数の目安


class SynthesisRequest(BaseModel):
    """1 合成単位の入力. 長文は呼び出し側 (T28) で文に分割してから渡す."""

    text: str
    voice_id: str
    speed: float = 1.0

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text は空にできない")
        return v


class SynthesisResult(BaseModel):
    """1 合成単位の出力. audio は wav バイト列 (結合・ミックスは mix/ で行う)."""

    audio: bytes
    sample_rate: int
    audio_format: str = "wav"


@runtime_checkable
class TTSEngine(Protocol):
    """エンジン抽象 (ADR-0006)。実装は本 Protocol を構造的に満たせばよい."""

    def synthesize(self, req: SynthesisRequest) -> SynthesisResult: ...

    def voices(self) -> list[Voice]: ...

    def name(self) -> str: ...

    def capabilities(self) -> Capabilities: ...


class MockTTSEngine:
    """決定的なダミーエンジン. 実音声は出さず、下流パイプライン (T25-T28) の
    モック駆動テスト用に契約適合な `SynthesisResult` を返す.

    audio は text+voice+speed から決定的に生成 (同一入力→同一出力) し、
    回帰テストを安定させる。実音声合成は T24 (Irodori) で差し替える。
    """

    def name(self) -> str:
        return "mock"

    def voices(self) -> list[Voice]:
        return [Voice(id="hal", name="HAL", language="ja")]

    def capabilities(self) -> Capabilities:
        return Capabilities(
            emoji_style=True,
            voice_clone=True,
            streaming=False,
            max_chars=MOCK_MAX_CHARS,
        )

    def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        seed = f"{req.voice_id}|{req.speed}|{req.text}".encode()
        digest = hashlib.sha256(seed).digest()
        return SynthesisResult(
            audio=b"MOCKWAV" + digest,
            sample_rate=MOCK_SAMPLE_RATE,
            audio_format="wav",
        )


# FR-090: エンジン選択は設定 (エンジン名) で解決する。実エンジンは登録するだけで増やせる。
# Irodori は T24 で `_ENGINES["irodori"]` に登録する (実行環境・声の人間判断後)。
_ENGINES: dict[str, TTSEngine] = {
    "mock": MockTTSEngine(),
}


def select_engine(name: str) -> TTSEngine:
    """エンジン名から `TTSEngine` を返す (FR-090). 未知名は TTSError."""
    engine = _ENGINES.get(name)
    if engine is None:
        available = ", ".join(sorted(_ENGINES)) or "(なし)"
        raise TTSError(f"未知の TTS エンジン: {name!r} (利用可能: {available})")
    return engine
