"""Irodori-TTS アダプタ (Sprint 2 Ticket T24, ADR-0006 主軸エンジン).

ADR-0006: 主軸は Irodori-TTS v3 (日本語特化・絵文字スタイル制御)。
[Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) が
**OpenAI 互換 `POST /v1/audio/speech`** を提供するので、既存 `llm/client.py` と同型の
薄い httpx ラッパーで繋ぐ (新クライアント不要)。サーバの起動・モデル DL は人間環境
(`uv run python -m irodori_openai_tts --port 8088`、初回 HF から自動 DL)。

ユニットテストは httpx をモックし実サーバを呼ばない (IMPLEMENTATION_PLAN-2 §5)。
秘密 (API キー) は Authorization ヘッダのみに置き、エラーメッセージへ漏らさない。
"""
from __future__ import annotations

import io
import os
import wave

import httpx

from karyu_tech_news.tts.engine import (
    Capabilities,
    SynthesisRequest,
    SynthesisResult,
    TTSError,
    Voice,
)

IRODORI_DEFAULT_BASE_URL = "http://localhost:8088"
IRODORI_DEFAULT_VOICE = "hal"  # 声リファレンスは試聴で確定 (ADR-0006)
# OpenAI 互換 API の `model` は Irodori-TTS-Server の settings.model_name (既定 "irodori-tts")
# と一致が必要。HF checkpoint ID (Aratako/Irodori-TTS-500M-v3) はサーバ内部ロード用
# (IRODORI_CHECKPOINT) であって API の model 値ではない (Codex レビュー指摘)。
IRODORI_MODEL = "irodori-tts"
IRODORI_MAX_CHARS = 2000  # サーバ側も自動チャンクするが、T28 でも文単位分割する
TIMEOUT_SECONDS = 120.0  # TTS 合成は LLM より遅い (要件 §3.3 タイムアウト必須)


class IrodoriTTSEngine:
    """Irodori-TTS-Server を `TTSEngine` Protocol に適合させる httpx アダプタ.

    base_url は引数 → env `IRODORI_BASE_URL` → 既定 localhost:8088 で解決。
    実サーバが無い環境では synthesize 時に TTSError (接続失敗)。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        voice: str = IRODORI_DEFAULT_VOICE,
        model: str | None = None,
        api_key_env: str = "IRODORI_API_KEY",
    ) -> None:
        resolved = base_url or os.getenv("IRODORI_BASE_URL") or IRODORI_DEFAULT_BASE_URL
        self._base_url = resolved.rstrip("/")
        self._voice = voice
        # サーバの model_name と一致させる。env で上書き可 (server 設定を変えた場合)。
        self._model = model or os.getenv("IRODORI_MODEL") or IRODORI_MODEL
        self._api_key = os.getenv(api_key_env, "")

    def name(self) -> str:
        return "irodori-tts-v3"

    def voices(self) -> list[Voice]:
        return [Voice(id=self._voice, name="HAL", language="ja")]

    def capabilities(self) -> Capabilities:
        # Irodori v3 は絵文字スタイル制御・ゼロショット声クローン対応 (ADR-0006)。
        return Capabilities(
            emoji_style=True,
            voice_clone=True,
            streaming=False,
            max_chars=IRODORI_MAX_CHARS,
        )

    def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        body = {
            "model": self._model,
            "input": req.text,
            "voice": req.voice_id or self._voice,
            "response_format": "wav",
            "speed": req.speed,
        }
        headers = {}
        if self._api_key:  # キーは header のみ (URL/エラーに載せない)
            headers["Authorization"] = f"Bearer {self._api_key}"
        url = f"{self._base_url}/v1/audio/speech"
        try:
            resp = httpx.post(url, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # status code は秘密でなくトラブルシュート (401/429/500 等) に有用。
            # 本文/ヘッダ/秘密は載せない。HTTPStatusError は HTTPError 派生のため先に置く。
            raise TTSError(
                f"Irodori 合成失敗: HTTP {exc.response.status_code}"
            ) from exc
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            # 接続失敗・タイムアウト等は型名のみ (本文/ヘッダ/秘密を載せない)
            raise TTSError(f"Irodori 合成失敗: {type(exc).__name__}") from exc
        audio = resp.content
        if not audio:
            raise TTSError("Irodori 応答が空")
        try:
            with wave.open(io.BytesIO(audio), "rb") as reader:
                sample_rate = reader.getframerate()
        except (wave.Error, EOFError) as exc:
            raise TTSError(f"Irodori 応答が wav でない: {type(exc).__name__}") from exc
        return SynthesisResult(audio=audio, sample_rate=sample_rate, audio_format="wav")
