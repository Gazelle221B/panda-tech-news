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
import logging
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
# 参照音声(ゼロショット声クローン)は話者 latent を毎リクエスト抽出するため、長文 1 文でも
# >120s かかりうる (T33 実測: 1 文が 120s×3 リトライ全 ReadTimeout で欠落)。retry は同一の遅い
# リクエストを再送するだけで遅延は救えないため、ceiling 自体を上げる。env IRODORI_TIMEOUT で上書き可。
TIMEOUT_SECONDS = 300.0  # TTS 合成は LLM より遅い (要件 §3.3 タイムアウト必須)
MAX_RETRIES = 2  # 一過性の 5xx/接続断を想定 (FR-013 / llm・fetcher と同値)

logger = logging.getLogger(__name__)


def _resolve_timeout(raw: str | None) -> float:
    """IRODORI_TIMEOUT (秒) を解釈。未設定/不正値は既定にフォールバック (fail-open).

    無人パイプラインで不正な env 値がジョブ全体を落とさないよう、>0 の float 以外は
    既定 TIMEOUT_SECONDS を採用しログのみ残す (システム境界の入力検証)。
    """
    if not raw:
        return TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        logger.warning("IRODORI_TIMEOUT 不正値 (float でない), 既定 %ss を使用", TIMEOUT_SECONDS)
        return TIMEOUT_SECONDS
    if value <= 0:
        logger.warning("IRODORI_TIMEOUT 不正値 (<=0), 既定 %ss を使用", TIMEOUT_SECONDS)
        return TIMEOUT_SECONDS
    return value


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
        caption: str | None = None,
        api_key_env: str = "IRODORI_API_KEY",
    ) -> None:
        resolved = base_url or os.getenv("IRODORI_BASE_URL") or IRODORI_DEFAULT_BASE_URL
        self._base_url = resolved.rstrip("/")
        self._voice = voice
        # サーバの model_name と一致させる。env で上書き可 (server 設定を変えた場合)。
        self._model = model or os.getenv("IRODORI_MODEL") or IRODORI_MODEL
        self._api_key = os.getenv(api_key_env, "")
        # 参照音声で長文 1 文が既定 ceiling を超える環境向けに env で上書き可 (base_url/model と同 idiom)。
        self._timeout = _resolve_timeout(os.getenv("IRODORI_TIMEOUT"))
        # VoiceDesign キャプション (話法指示): 引数 → env IRODORI_CAPTION → なし (T34)。
        # 既定エンジン (500M) では server が無視。600M VoiceDesign checkpoint でのみ効く。
        self._caption = caption or os.getenv("IRODORI_CAPTION") or None

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
            voice_design=True,  # 600M VoiceDesign checkpoint でキャプション話法制御 (T34)
        )

    def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
        body: dict[str, object] = {
            "model": self._model,
            "input": req.text,
            "voice": req.voice_id or self._voice,
            "response_format": "wav",
            "speed": req.speed,
        }
        # VoiceDesign: 文ごとの caption (req) を優先、無ければエンジン既定。server の
        # irodori オプション経由で SamplingRequest.caption に渡る (600M でのみ有効)。
        caption = req.caption or self._caption
        if caption:
            body["irodori"] = {"caption": caption}
        headers = {}
        if self._api_key:  # キーは header のみ (URL/エラーに載せない)
            headers["Authorization"] = f"Bearer {self._api_key}"
        url = f"{self._base_url}/v1/audio/speech"
        resp = self._post_with_retry(url, body, headers)
        audio = resp.content
        if not audio:
            raise TTSError("Irodori 応答が空")
        try:
            with wave.open(io.BytesIO(audio), "rb") as reader:
                sample_rate = reader.getframerate()
        except (wave.Error, EOFError) as exc:
            raise TTSError(f"Irodori 応答が wav でない: {type(exc).__name__}") from exc
        return SynthesisResult(audio=audio, sample_rate=sample_rate, audio_format="wav")

    def _post_with_retry(
        self, url: str, body: dict[str, object], headers: dict[str, str]
    ) -> httpx.Response:
        """一過性の失敗 (接続断・5xx/429) を想定し最大 MAX_RETRIES 回リトライ (FR-013).

        既存 `llm/client.py` / `collect/fetcher.py` と同 idiom (初回 + MAX_RETRIES 回)。
        ログ・エラーには型名/status code のみ載せ、秘密 (キー/本文/ヘッダ) は載せない。
        """
        last_exc: httpx.HTTPError | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = httpx.post(url, json=body, headers=headers, timeout=self._timeout)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    logger.info(
                        "Irodori retry %d/%d: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        type(exc).__name__,
                    )
                continue
        # status code はトラブルシュートに有用 (秘密でない)。本文/ヘッダ/キーは載せない。
        detail = (
            f"HTTP {last_exc.response.status_code}"
            if isinstance(last_exc, httpx.HTTPStatusError)
            else type(last_exc).__name__
        )
        raise TTSError(
            f"Irodori 合成失敗 ({MAX_RETRIES + 1} 回試行): {detail}"
        ) from last_exc
