"""deliver.youtube のユニットテスト (Sprint 3 T39, FR-120/121/122).

実 YouTube API は叩かない (IMPLEMENTATION_PLAN-3 §8)。httpx をモジュール境界で
モックし、resumable の 2 段階・AI 開示強制・privacy 変更・エラー正規化を検証する。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import httpx
import pytest

import karyu_tech_news.deliver.youtube as yt
from karyu_tech_news.deliver.youtube import (
    AI_DISCLOSURE,
    DEFAULT_PRIVACY,
    YouTubeCredentials,
    YouTubeError,
    build_auth_url,
    ensure_disclosure,
    exchange_code_for_refresh_token,
    extract_code,
    get_video_status,
    refresh_access_token,
    sanitize_title,
    set_privacy_status,
    upload_video,
    wait_for_oauth_code,
)


class _Resp:
    """httpx.Response の必要最小スタブ."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.headers = headers or {}
        self.text = json.dumps(self._json, ensure_ascii=False)

    def json(self) -> dict[str, Any]:
        return self._json


# ---- FR-121: AI 開示の強制 ----


def test_ensure_disclosure_prepends_when_missing() -> None:
    out = ensure_disclosure("今日のトピックです。")
    assert out.startswith(AI_DISCLOSURE)
    assert "今日のトピック" in out


def test_ensure_disclosure_keeps_existing() -> None:
    desc = f"前置き\n{AI_DISCLOSURE}\n本文"
    assert ensure_disclosure(desc) == desc


def test_ensure_disclosure_empty_description() -> None:
    assert ensure_disclosure("") == AI_DISCLOSURE
    assert ensure_disclosure("   ") == AI_DISCLOSURE


# ---- タイトル正規化 ----


def test_sanitize_title_replaces_angle_brackets() -> None:
    assert sanitize_title("<新モデル> a>b") == "〈新モデル〉 a〉b"


def test_sanitize_title_truncates_codepoints() -> None:
    long_title = "あ" * 150
    assert len(sanitize_title(long_title)) == 100


def test_sanitize_title_empty_falls_back() -> None:
    assert sanitize_title("  ") == "華流テック通信"


# ---- 認証情報 ----


def test_credentials_from_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(YouTubeError, match="YOUTUBE_CLIENT_ID"):
        YouTubeCredentials.from_env()


def test_credentials_from_env_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "cid")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "sec")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "ref")
    creds = YouTubeCredentials.from_env()
    assert creds.client_id == "cid"


def _creds() -> YouTubeCredentials:
    return YouTubeCredentials(client_id="cid", client_secret="sec", refresh_token="ref")


# ---- token refresh ----


def test_refresh_access_token_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> _Resp:
        assert url == yt.TOKEN_URL
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["timeout"] is not None
        return _Resp(200, {"access_token": "at-123"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert refresh_access_token(_creds()) == "at-123"


def test_refresh_access_token_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _Resp(400, {"error": "invalid_grant"})
    )
    with pytest.raises(YouTubeError, match="HTTP 400"):
        refresh_access_token(_creds())


def test_refresh_access_token_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **k: Any) -> _Resp:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(YouTubeError, match="接続失敗"):
        refresh_access_token(_creds())


class _BrokenJSONResp(_Resp):
    """200 だが本文が JSON でない応答 (プロキシの HTML 等)."""

    def json(self) -> dict[str, Any]:
        raise ValueError("not json")


def test_refresh_access_token_broken_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """200 応答の JSON 破損も YouTubeError に正規化する (traceback で落とさない)."""
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _BrokenJSONResp(200))
    with pytest.raises(YouTubeError, match="JSON ではありません"):
        refresh_access_token(_creds())


# ---- upload (resumable 2 段階) ----


def _mp4(tmp_path: Path) -> Path:
    p = tmp_path / "ep.mp4"
    p.write_bytes(b"\x00" * 128)
    return p


def test_upload_video_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _Resp:
        captured["metadata"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        assert "uploadType=resumable" in url
        return _Resp(200, headers={"Location": "https://upload.example/session1"})

    def fake_put(url: str, **kwargs: Any) -> _Resp:
        captured["put_url"] = url
        return _Resp(200, {"id": "vid42", "status": {"privacyStatus": "unlisted"}})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "put", fake_put)

    result = upload_video(
        "at", _mp4(tmp_path), title="今日の華流テック", description="本日の3本です。"
    )
    assert result.video_id == "vid42"
    assert result.url.endswith("vid42")
    assert result.privacy_status == "unlisted"
    # FR-121: 開示文言とプラットフォームフラグの二重開示
    meta = captured["metadata"]
    assert AI_DISCLOSURE in meta["snippet"]["description"]
    assert meta["status"]["containsSyntheticMedia"] is True
    assert meta["status"]["selfDeclaredMadeForKids"] is False
    # FR-120: 既定は限定公開
    assert meta["status"]["privacyStatus"] == DEFAULT_PRIVACY
    assert captured["put_url"] == "https://upload.example/session1"
    assert captured["headers"]["X-Upload-Content-Type"] == "video/mp4"


def test_upload_video_missing_file(tmp_path: Path) -> None:
    with pytest.raises(YouTubeError, match="mp4 が見つかりません"):
        upload_video("at", tmp_path / "none.mp4", title="t")


def test_upload_video_invalid_privacy(tmp_path: Path) -> None:
    with pytest.raises(YouTubeError, match="privacyStatus"):
        upload_video("at", _mp4(tmp_path), title="t", privacy="secret")


def test_upload_video_initiate_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(403, {"error": "quota"}))
    with pytest.raises(YouTubeError, match="アップロード開始失敗"):
        upload_video("at", _mp4(tmp_path), title="t")


def test_upload_video_missing_location(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(200, headers={}))
    with pytest.raises(YouTubeError, match="Location"):
        upload_video("at", _mp4(tmp_path), title="t")


def test_upload_video_put_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _Resp(200, headers={"Location": "https://u.example/s"}),
    )
    monkeypatch.setattr(httpx, "put", lambda *a, **k: _Resp(500, {"error": "backend"}))
    with pytest.raises(YouTubeError, match="動画データ送信失敗"):
        upload_video("at", _mp4(tmp_path), title="t")


# ---- privacy 変更 (approve フロー) ----


def test_get_video_status_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: _Resp(
            200, {"items": [{"status": {"privacyStatus": "unlisted", "license": "youtube"}}]}
        ),
    )
    status = get_video_status("at", "vid42")
    assert status["privacyStatus"] == "unlisted"


def test_get_video_status_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(200, {"items": []}))
    with pytest.raises(YouTubeError, match="動画が見つかりません"):
        get_video_status("at", "ghost")


def test_set_privacy_status_sends_only_mutable_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: dict[str, Any] = {}
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: _Resp(
            200,
            {
                "items": [
                    {
                        "status": {
                            "privacyStatus": "unlisted",
                            "selfDeclaredMadeForKids": False,
                            "publishAt": "2026-07-07T00:00:00Z",
                            # videos.list が返す read-only フィールド (送り返すと
                            # invalidVideoMetadata になりうる)
                            "uploadStatus": "processed",
                            "license": "youtube",
                        }
                    }
                ]
            },
        ),
    )

    def fake_put(url: str, **kwargs: Any) -> _Resp:
        sent["payload"] = kwargs["json"]
        return _Resp(200, {"status": {"privacyStatus": "public"}})

    monkeypatch.setattr(httpx, "put", fake_put)
    assert set_privacy_status("at", "vid42", "public") == "public"
    payload = sent["payload"]
    assert payload["id"] == "vid42"
    assert payload["status"]["privacyStatus"] == "public"
    # mutable フィールドは維持
    assert payload["status"]["selfDeclaredMadeForKids"] is False
    assert payload["status"]["license"] == "youtube"
    # read-only / 予約公開フィールドは送らない
    assert "uploadStatus" not in payload["status"]
    assert "publishAt" not in payload["status"]


def test_set_privacy_status_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(YouTubeError, match="privacyStatus"):
        set_privacy_status("at", "vid42", "hidden")


# ---- 初回 OAuth 補助 ----


def test_build_auth_url_offline_consent() -> None:
    url = build_auth_url("cid", "http://127.0.0.1:8765")
    assert url.startswith(yt.AUTH_URL)
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert "client_id=cid" in url


def test_extract_code_from_url_and_raw() -> None:
    assert extract_code("http://127.0.0.1:8765/?code=abc&scope=x") == "abc"
    assert extract_code("  rawcode  ") == "rawcode"
    with pytest.raises(YouTubeError, match="code"):
        extract_code("http://127.0.0.1:8765/?error=access_denied")


def test_exchange_code_for_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> _Resp:
        assert kwargs["data"]["grant_type"] == "authorization_code"
        return _Resp(200, {"refresh_token": "rt-1", "access_token": "at-1"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert exchange_code_for_refresh_token("cid", "sec", "code", "http://x") == "rt-1"


def test_exchange_code_without_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(200, {"access_token": "a"}))
    with pytest.raises(YouTubeError, match="refresh_token"):
        exchange_code_for_refresh_token("cid", "sec", "code", "http://x")


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_wait_for_oauth_code_receives(tmp_path: Path) -> None:
    port = _free_port()
    result: list[str] = []

    def serve() -> None:
        result.append(wait_for_oauth_code(port, timeout_seconds=10.0))

    t = threading.Thread(target=serve)
    t.start()
    try:
        resp = httpx.get(f"http://127.0.0.1:{port}/?code=xyz", timeout=10.0)
        assert resp.status_code == 200
    finally:
        t.join(timeout=15.0)
    assert result == ["xyz"]


def test_wait_for_oauth_code_timeout() -> None:
    port = _free_port()
    with pytest.raises(YouTubeError, match="受信できませんでした"):
        wait_for_oauth_code(port, timeout_seconds=0.2)


def test_wait_for_oauth_code_port_in_use() -> None:
    """ポート使用中は生の OSError でなく YouTubeError で案内する."""
    import socket

    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = int(blocker.getsockname()[1])
        with pytest.raises(YouTubeError, match="待受できません"):
            wait_for_oauth_code(port, timeout_seconds=0.2)
