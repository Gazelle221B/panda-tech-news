"""tts.irodori のユニットテスト (Sprint 2 Ticket T24, ADR-0006 主軸). httpx はモック.

実 Irodori-TTS-Server は呼ばず、OpenAI 互換 `POST /v1/audio/speech` の契約
(リクエスト形・wav 応答・エラー正規化・秘密非漏洩) を固定する。
"""
from __future__ import annotations

import io
import wave
from unittest.mock import MagicMock, patch

import httpx
import pytest

from karyu_tech_news.tts.engine import (
    SynthesisRequest,
    SynthesisResult,
    TTSEngine,
    TTSError,
    select_engine,
)
from karyu_tech_news.tts.irodori import IrodoriTTSEngine


def _wav_bytes(sample_rate: int = 48000, n_frames: int = 10) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


def _mock_resp(content: bytes, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    if status >= 400:
        err_resp = MagicMock()
        err_resp.status_code = status  # メッセージに status code が載る経路を固定
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=err_resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------- Protocol / メタ ----------

def test_irodori_satisfies_protocol() -> None:
    assert isinstance(IrodoriTTSEngine(), TTSEngine)


def test_irodori_name_is_config_key() -> None:
    # config/hal_persona.yaml の primary_engine と一致させる
    assert IrodoriTTSEngine().name() == "irodori-tts-v3"


def test_irodori_capabilities_supports_emoji_style() -> None:
    cap = IrodoriTTSEngine().capabilities()
    assert cap.emoji_style is True  # Irodori v3 の絵文字スタイル制御 (T27 が活きる)
    assert cap.voice_clone is True


# ---------- synthesize ----------

def test_irodori_synthesize_posts_openai_shape() -> None:
    wav = _wav_bytes()
    with patch("karyu_tech_news.tts.irodori.httpx.post", return_value=_mock_resp(wav)) as post:
        res = IrodoriTTSEngine(base_url="http://localhost:8088").synthesize(
            SynthesisRequest(text="こんにちは", voice_id="hal", speed=1.2)
        )
    assert isinstance(res, SynthesisResult)
    assert res.audio == wav
    assert res.sample_rate == 48000  # wav ヘッダから読む
    url = post.call_args.args[0] if post.call_args.args else post.call_args.kwargs.get("url")
    assert url == "http://localhost:8088/v1/audio/speech"
    body = post.call_args.kwargs["json"]
    assert body["input"] == "こんにちは"
    assert body["voice"] == "hal"
    assert body["response_format"] == "wav"
    assert body["speed"] == 1.2
    assert body["model"] == "irodori-tts"  # サーバ settings.model_name と一致 (HF ID ではない)


def test_irodori_http_error_raises_ttserror_without_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 実 API キーを設定し、Authorization header 経路で例外文字列に秘密が出ないことを固定
    monkeypatch.setenv("IRODORI_API_KEY", "sk-secret-xyz")
    with (
        patch("karyu_tech_news.tts.irodori.httpx.post", return_value=_mock_resp(b"", status=500)),
        pytest.raises(TTSError) as ei,
    ):
        IrodoriTTSEngine().synthesize(SynthesisRequest(text="x", voice_id="hal"))
    assert "sk-secret-xyz" not in str(ei.value)  # 秘密を漏らさない
    assert "Bearer" not in str(ei.value)
    assert "500" in str(ei.value)  # status code はトラブルシュート用に載せる (Copilot 指摘)


def test_irodori_connect_error_raises_ttserror() -> None:
    with (
        patch("karyu_tech_news.tts.irodori.httpx.post", side_effect=httpx.ConnectError("refused")),
        pytest.raises(TTSError),
    ):
        IrodoriTTSEngine().synthesize(SynthesisRequest(text="x", voice_id="hal"))


def test_irodori_empty_response_raises() -> None:
    with (
        patch("karyu_tech_news.tts.irodori.httpx.post", return_value=_mock_resp(b"")),
        pytest.raises(TTSError),
    ):
        IrodoriTTSEngine().synthesize(SynthesisRequest(text="x", voice_id="hal"))


def test_irodori_non_wav_response_raises() -> None:
    with (
        patch("karyu_tech_news.tts.irodori.httpx.post", return_value=_mock_resp(b"not wav")),
        pytest.raises(TTSError),
    ):
        IrodoriTTSEngine().synthesize(SynthesisRequest(text="x", voice_id="hal"))


def test_irodori_retries_transient_then_succeeds() -> None:
    # 1回目 ConnectError (一過性) → リトライで 2回目成功 (FR-013, Copilot 指摘)
    wav = _wav_bytes()
    with patch(
        "karyu_tech_news.tts.irodori.httpx.post",
        side_effect=[httpx.ConnectError("transient"), _mock_resp(wav)],
    ) as post:
        res = IrodoriTTSEngine().synthesize(SynthesisRequest(text="x", voice_id="hal"))
    assert res.audio == wav
    assert post.call_count == 2  # 初回失敗 + リトライ成功


def test_irodori_retries_exhausted_raises() -> None:
    # MAX_RETRIES 回すべて失敗 → TTSError (試行回数 = 初回 + MAX_RETRIES)
    with (
        patch(
            "karyu_tech_news.tts.irodori.httpx.post",
            side_effect=httpx.ConnectError("down"),
        ) as post,
        pytest.raises(TTSError),
    ):
        IrodoriTTSEngine().synthesize(SynthesisRequest(text="x", voice_id="hal"))
    assert post.call_count == 3  # 初回 + 2 リトライ


# ---------- select_engine 統合 (FR-090) ----------

def test_select_engine_irodori_by_config_key() -> None:
    eng = select_engine("irodori-tts-v3")
    assert isinstance(eng, TTSEngine)
    assert eng.name() == "irodori-tts-v3"


def test_select_engine_irodori_alias() -> None:
    assert select_engine("irodori").name() == "irodori-tts-v3"
