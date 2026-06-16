"""Kokoro (ONNX) TTS アダプタ (Sprint 2 Ticket T24).

ADR-0006: 主軸は Irodori v3 だが、開発機が macOS のため当面 **Kokoro (Apache 2.0)**
を fallback として実音声化に使う (人間判断 2026-06-14)。kokoro-onnx は **optional 依存**
(extra `tts`) で、コア (収集→台本) は依存最小のまま保つ (§5)。

実バックエンドは遅延ロードする (未導入なら TTSError)。実モデルでの合成 smoke は
人間環境 (`uv sync --extra tts` + モデル/voices DL) で実施する (T13 の音声版)。
HAL の声は Kokoro のプリセット声を当面採用し、試聴で確定する (ADR-0006)。
"""
from __future__ import annotations

import array
import io
import os
import wave
from collections.abc import Callable, Sequence

from karyu_tech_news.tts.engine import (
    Capabilities,
    SynthesisRequest,
    SynthesisResult,
    TTSError,
    Voice,
)

KOKORO_SAMPLE_RATE = 24000  # Kokoro の出力 sample rate
KOKORO_DEFAULT_VOICE = "jf_alpha"  # 日本語女性プリセット (HAL 用に試聴で確定, ADR-0006)
KOKORO_MAX_CHARS = 500

# backend: (text, voice, speed) -> (float サンプル列 [-1,1], sample_rate)
SynthBackend = Callable[[str, str, float], tuple[Sequence[float], int]]


def floats_to_wav(samples: Sequence[float], sample_rate: int) -> bytes:
    """float [-1,1] サンプル列を 16bit PCM mono wav に変換する (numpy 非依存).

    範囲外はクリップする。結合・ミックス (T28/T29) はこの wav を入力にする。
    """
    pcm = array.array(
        "h", (int(max(-1.0, min(1.0, float(s))) * 32767) for s in samples)
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class KokoroTTSEngine:
    """Kokoro ONNX を `TTSEngine` Protocol に適合させるアダプタ.

    `synth` を注入するとテスト用バックエンドになる (実 kokoro-onnx 不要)。
    省略時は合成実行時に kokoro-onnx を遅延ロードする (未導入なら TTSError)。
    """

    def __init__(
        self, *, voice: str = KOKORO_DEFAULT_VOICE, synth: SynthBackend | None = None
    ) -> None:
        self._voice = voice
        self._synth = synth

    def _backend(self) -> SynthBackend:
        if self._synth is not None:
            return self._synth
        try:
            from kokoro_onnx import Kokoro  # type: ignore[import-not-found]
        except ImportError as exc:
            raise TTSError(
                "kokoro-onnx 未導入。`uv sync --extra tts` で導入してください"
            ) from exc
        model = os.environ.get("KOKORO_MODEL_PATH", "kokoro-v1.0.onnx")
        voices = os.environ.get("KOKORO_VOICES_PATH", "voices-v1.0.bin")
        kokoro = Kokoro(model, voices)

        def _run(text: str, voice: str, speed: float) -> tuple[Sequence[float], int]:
            samples, sample_rate = kokoro.create(
                text, voice=voice, speed=speed, lang="ja"
            )
            return samples, sample_rate

        self._synth = _run
        return _run

    def name(self) -> str:
        return "kokoro"

    def voices(self) -> list[Voice]:
        return [Voice(id=self._voice, name="HAL", language="ja")]

    def capabilities(self) -> Capabilities:
        # Kokoro はプリセット声・絵文字スタイル制御なし (絵文字注釈 T27 は適用されない)
        return Capabilities(
            emoji_style=False,
            voice_clone=False,
            streaming=False,
            max_chars=KOKORO_MAX_CHARS,
        )

    def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        voice = req.voice_id or self._voice
        try:
            samples, sample_rate = self._backend()(req.text, voice, req.speed)
        except TTSError:
            raise  # 遅延ロード失敗はそのまま
        except Exception as exc:  # 実合成中の任意の失敗を TTSError に正規化 (fail-open は呼び出し側)
            raise TTSError(f"Kokoro 合成失敗: {exc}") from exc
        return SynthesisResult(
            audio=floats_to_wav(samples, sample_rate),
            sample_rate=sample_rate,
            audio_format="wav",
        )
