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
import io
import wave
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, field_validator

MOCK_SAMPLE_RATE = 48000  # mp3 192kbps/48kHz 想定 (要件 §17.6) に合わせたモック値
MOCK_MAX_CHARS = 2000  # 1 リクエストの目安上限 (長文は T28 で文単位分割)
MOCK_FRAMES_PER_CHAR = 16  # モック音声長 = 文字数 × これ (テスト用に小さく)


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
    voice_design: bool = False  # キャプション(自然文)による話法制御 (Irodori 600M VoiceDesign, T34)


class SynthesisRequest(BaseModel):
    """1 合成単位の入力. 長文は呼び出し側 (T28) で文に分割してから渡す."""

    text: str
    voice_id: str
    speed: float = 1.0
    caption: str | None = None  # VoiceDesign: 話し方を指示する自然文. 非対応エンジンは無視 (T34)

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text は空にできない")
        return v


class SynthesisResult(BaseModel):
    """合成結果. audio は wav バイト列 (結合・ミックスは mix/ で行う).

    個別エンジンの `synthesize()` は 1 合成単位として既定値 (1/1/0) を返す。
    `synthesize_script()` は文単位の集約結果として counters をエピソード全体の
    attempted/synthesized/skipped 文数へ上書きする。asr_retried/asr_failed も同様に
    `synthesize_script()` が ASR 品質ゲート (T58, `tts/asr_gate.py`) 適用時のみ集計する
    (個別エンジンは常に既定値 0 のまま)。
    """

    audio: bytes
    sample_rate: int
    audio_format: str = "wav"
    attempted_sentences: int = 1
    synthesized_sentences: int = 1
    skipped_sentences: int = 0
    asr_retried_sentences: int = 0  # ASR 不一致でリトライし ok になった文数 (T58)
    asr_failed_sentences: int = 0  # ASR 不一致がリトライ上限まで解消せず skip した文数 (T58)


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
            voice_design=True,
        )

    def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        # 有効な 16bit/mono/48kHz の wav を返す (内容・長さは入力から決定的に導く)。
        # 実 wav なので T28 の wave ベース結合がモック駆動で実テストできる。
        n_frames = max(1, len(req.text)) * MOCK_FRAMES_PER_CHAR
        seed = f"{req.voice_id}|{req.speed}|{req.text}".encode()
        pattern = hashlib.sha256(seed).digest()  # 入力依存 → 文ごとに異なる波形
        nbytes = n_frames * 2  # sampwidth=2
        raw = (pattern * (nbytes // len(pattern) + 1))[:nbytes]
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(MOCK_SAMPLE_RATE)
            w.writeframes(raw)
        return SynthesisResult(
            audio=buf.getvalue(),
            sample_rate=MOCK_SAMPLE_RATE,
            audio_format="wav",
        )


# FR-090: エンジン選択は設定 (エンジン名) で解決する。実エンジンは登録するだけで増やせる。
# registry のキーは config/hal_persona.yaml の `primary_engine` 値と一致させる
# (現状 `irodori-tts-v3`)。T24 で `_ENGINES["irodori-tts-v3"]` に実 Irodori を登録し、
# 設定値が解決できる契約テストを足す (実行環境・声リファレンスの人間判断後)。
_ENGINES: dict[str, TTSEngine] = {
    "mock": MockTTSEngine(),
}


def select_engine(name: str) -> TTSEngine:
    """エンジン名から `TTSEngine` を返す (FR-090). 未知名は TTSError.

    "kokoro" は optional 依存 (extra `tts`) のため遅延 import する (循環 import 回避 +
    未導入でも構築は可能・実バックエンドは合成時に遅延ロード)。
    """
    engine = _ENGINES.get(name)
    if engine is not None:
        return engine
    if name in ("irodori-tts-v3", "irodori"):  # ADR-0006 主軸 (config primary_engine と一致)
        from karyu_tech_news.tts.irodori import IrodoriTTSEngine

        return IrodoriTTSEngine()
    if name == "kokoro":
        from karyu_tech_news.tts.kokoro import KokoroTTSEngine

        return KokoroTTSEngine()
    available = ", ".join([*sorted(_ENGINES), "irodori-tts-v3", "kokoro"])
    raise TTSError(f"未知の TTS エンジン: {name!r} (利用可能: {available})")
