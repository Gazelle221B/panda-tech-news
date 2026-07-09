"""YouTube Data API v3 配信 (Sprint 3 Ticket T39, FR-120/121/122).

httpx で OAuth token refresh / resumable upload / privacy 変更を直接実装する
(SDK 不採用の判断は ADR-0007)。使うエンドポイントは 3 つのみ:

1. `POST oauth2.googleapis.com/token` — refresh token → access token
2. `POST /upload/youtube/v3/videos?uploadType=resumable` → `PUT <location>` — 動画アップロード
3. `GET/PUT /youtube/v3/videos` — privacy 状態の取得・変更 (approve フロー)

設計判断:
- **AI 開示 (FR-121) はコードで強制**: 説明欄に開示文言が無ければ先頭へ自動挿入し、
  `status.containsSyntheticMedia=true` も併せて送る (二重開示)。
- **限定公開が既定 (FR-120)**: privacyStatus の既定は unlisted。public 化は人間の
  approve 操作のみ (IMPLEMENTATION_PLAN-3 §8)。
- **秘密をログ・例外に出さない (要件 §9.5)**: トークンはリクエスト側にのみ存在する。
  例外メッセージには status code とレスポンス本文冒頭 (Google のエラー説明) だけ含める。
- videos.update は part 指定フィールドの**全置換**のため、privacy 変更は videos.list で
  現 status を取得してから差し替えて送る (ADR-0007 影響欄)。
- HTTP は全てタイムアウト必須 (AGENTS §3.3 の精神)。
"""
from __future__ import annotations

import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

AI_DISCLOSURE = "本番組はAI音声キャスターHALによる自動生成番組です。"  # FR-121 例文どおり

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
# upload = videos.insert / youtube = videos.list・update (approve の privacy 変更)
OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload "
    "https://www.googleapis.com/auth/youtube"
)

DEFAULT_PRIVACY = "unlisted"  # FR-120
DEFAULT_CATEGORY_ID = "28"  # Science & Technology
DEFAULT_TAGS = ["テック", "中国", "AI", "ポッドキャスト", "華流テック通信"]
TITLE_LIMIT = 100  # YouTube タイトル上限 (コードポイント単位)
REQUEST_TIMEOUT = 30.0
UPLOAD_TIMEOUT = 900.0  # 数百 MB 級でも完了する余裕 (通常エピソードは数十 MB)
_BODY_SNIPPET_LEN = 200

VALID_PRIVACY = ("public", "unlisted", "private")


class YouTubeError(Exception):
    """YouTube API 呼び出し (認証・アップロード・更新) の失敗."""


class YouTubeCredentials(BaseModel):
    """OAuth クライアント情報 (.env から供給。値はリポジトリ管理外)."""

    client_id: str
    client_secret: str
    refresh_token: str

    @classmethod
    def from_env(cls) -> YouTubeCredentials:
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
        missing = [
            name
            for name, value in (
                ("YOUTUBE_CLIENT_ID", client_id),
                ("YOUTUBE_CLIENT_SECRET", client_secret),
                ("YOUTUBE_REFRESH_TOKEN", refresh_token),
            )
            if not value
        ]
        if missing:
            raise YouTubeError(
                "YouTube OAuth 環境変数が未設定です: "
                + ", ".join(missing)
                + " (初回は `karyu youtube-auth` で refresh token を取得して .env へ)"
            )
        return cls(
            client_id=client_id, client_secret=client_secret, refresh_token=refresh_token
        )


class YouTubeUploadResult(BaseModel):
    """アップロード成功時のメタデータ (video_versions 永続化 T40 の証跡)."""

    video_id: str
    url: str
    privacy_status: str
    title: str


def _error_detail(resp: httpx.Response) -> str:
    """例外メッセージ用の安全な要約 (URL・トークンを含めない)."""
    body = resp.text[:_BODY_SNIPPET_LEN].replace("\n", " ")
    return f"HTTP {resp.status_code}: {body}"


def _parse_json(resp: httpx.Response, context: str) -> dict[str, Any]:
    """200 応答の JSON を安全にパースする.

    Google 側の一時異常やプロキシの HTML 応答で json() が壊れても、生の
    JSONDecodeError を漏らさず YouTubeError に正規化する (Codex レビュー Medium)。
    """
    try:
        body = resp.json()
    except ValueError as exc:
        raise YouTubeError(f"{context} 応答が JSON ではありません: {_error_detail(resp)}") from exc
    if not isinstance(body, dict):
        raise YouTubeError(f"{context} 応答の形式が不正です (JSON object でない)")
    return body


def ensure_disclosure(description: str) -> str:
    """説明欄に AI 開示文言 (FR-121) が無ければ先頭へ挿入する."""
    if AI_DISCLOSURE in description:
        return description
    return f"{AI_DISCLOSURE}\n\n{description}" if description.strip() else AI_DISCLOSURE


def sanitize_title(title: str) -> str:
    """YouTube タイトル制約への正規化.

    `<` `>` は API に拒否されるため全角へ置換し、コードポイント単位で 100 字に
    切り詰める (バイト切り詰め禁止, AGENTS §3.2)。空タイトルは番組名に縮退。
    """
    t = title.replace("<", "〈").replace(">", "〉").strip()
    if not t:
        return "華流テック通信"
    return t[:TITLE_LIMIT]


def refresh_access_token(creds: YouTubeCredentials) -> str:
    """refresh token から access token を取得する (FR-122 の前段)."""
    try:
        resp = httpx.post(
            TOKEN_URL,
            data={
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "refresh_token": creds.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise YouTubeError(f"OAuth token refresh 接続失敗: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise YouTubeError(f"OAuth token refresh 失敗: {_error_detail(resp)}")
    token = _parse_json(resp, "OAuth token refresh").get("access_token", "")
    if not isinstance(token, str) or not token:
        raise YouTubeError("OAuth token refresh 応答に access_token がありません")
    return token


def _build_upload_metadata(
    *,
    title: str,
    description: str,
    privacy: str,
    tags: list[str],
    category_id: str,
) -> dict[str, Any]:
    return {
        "snippet": {
            "title": sanitize_title(title),
            "description": ensure_disclosure(description),
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "ja",
            "defaultAudioLanguage": "ja",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            # プラットフォーム側の AI 生成コンテンツ開示 (FR-121 の二重化, ADR-0007)
            "containsSyntheticMedia": True,
        },
    }


def upload_video(
    access_token: str,
    mp4_path: Path | str,
    *,
    title: str,
    description: str = "",
    privacy: str = DEFAULT_PRIVACY,
    tags: list[str] | None = None,
    category_id: str = DEFAULT_CATEGORY_ID,
) -> YouTubeUploadResult:
    """mp4 を YouTube にアップロードする (FR-120/122, resumable 2 段階).

    失敗は全て YouTubeError に正規化する (publish の目的そのものなので fail-fast)。
    """
    path = Path(mp4_path)
    if not path.exists():
        raise YouTubeError(f"mp4 が見つかりません: {path.name}")
    if privacy not in VALID_PRIVACY:
        raise YouTubeError(f"不正な privacyStatus: {privacy!r} (choose from {VALID_PRIVACY})")

    metadata = _build_upload_metadata(
        title=title,
        description=description,
        privacy=privacy,
        tags=tags if tags is not None else list(DEFAULT_TAGS),
        category_id=category_id,
    )
    size = path.stat().st_size
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(size),
    }
    try:
        initiate = httpx.post(
            f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            json=metadata,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise YouTubeError(f"アップロード開始の接続失敗: {type(exc).__name__}") from exc
    if initiate.status_code != 200:
        raise YouTubeError(f"アップロード開始失敗: {_error_detail(initiate)}")
    location = initiate.headers.get("Location", "")
    if not location:
        raise YouTubeError("アップロード開始応答に Location ヘッダがありません")

    try:
        with path.open("rb") as f:
            put = httpx.put(
                location,
                content=f,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(size),
                },
                timeout=UPLOAD_TIMEOUT,
            )
    except httpx.HTTPError as exc:
        raise YouTubeError(f"動画データ送信の接続失敗: {type(exc).__name__}") from exc
    if put.status_code not in (200, 201):
        raise YouTubeError(f"動画データ送信失敗: {_error_detail(put)}")

    body = _parse_json(put, "アップロード")
    video_id = body.get("id", "")
    if not isinstance(video_id, str) or not video_id:
        raise YouTubeError("アップロード応答に動画 id がありません")
    status = body.get("status") or {}
    actual_privacy = str(status.get("privacyStatus", privacy))
    logger.info("YouTube アップロード成功 (video_id=%s, privacy=%s)", video_id, actual_privacy)
    return YouTubeUploadResult(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        privacy_status=actual_privacy,
        title=sanitize_title(title),
    )


def get_video_status(access_token: str, video_id: str) -> dict[str, Any]:
    """videos.list part=status で現在の status オブジェクトを取得する."""
    try:
        resp = httpx.get(
            VIDEOS_URL,
            params={"part": "status", "id": video_id},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise YouTubeError(f"status 取得の接続失敗: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise YouTubeError(f"status 取得失敗: {_error_detail(resp)}")
    items = _parse_json(resp, "status 取得").get("items") or []
    if not items:
        raise YouTubeError(f"動画が見つかりません: video_id={video_id}")
    status = items[0].get("status")
    if not isinstance(status, dict):
        raise YouTubeError("status 取得応答の形式が不正です")
    return status


# videos.update に送ってよい status の mutable フィールド (videos.update 公式ドキュメント)。
# videos.list の応答には uploadStatus / failureReason / rejectionReason 等の read-only
# フィールドが含まれ、そのまま送り返すと invalidVideoMetadata で update が失敗しうる
# (Codex レビュー High)。
_MUTABLE_STATUS_FIELDS = (
    "privacyStatus",
    "embeddable",
    "license",
    "publicStatsViewable",
    "selfDeclaredMadeForKids",
    "containsSyntheticMedia",
)


def set_privacy_status(access_token: str, video_id: str, privacy: str) -> str:
    """privacyStatus を変更する (approve フロー: unlisted → public).

    videos.update (part=status) は status を全置換するため、現状を取得して
    mutable フィールドのみ (whitelist) を privacyStatus 差し替えで送る (ADR-0007)。
    publishAt (予約公開) は残っていると public 変更が拒否されるため送らない。
    """
    if privacy not in VALID_PRIVACY:
        raise YouTubeError(f"不正な privacyStatus: {privacy!r} (choose from {VALID_PRIVACY})")
    current = get_video_status(access_token, video_id)
    status = {k: current[k] for k in _MUTABLE_STATUS_FIELDS if k in current}
    status["privacyStatus"] = privacy
    try:
        resp = httpx.put(
            f"{VIDEOS_URL}?part=status",
            json={"id": video_id, "status": status},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise YouTubeError(f"privacy 変更の接続失敗: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise YouTubeError(f"privacy 変更失敗: {_error_detail(resp)}")
    updated = _parse_json(resp, "privacy 変更").get("status") or {}
    result = str(updated.get("privacyStatus", privacy))
    logger.info("YouTube privacy 変更 (video_id=%s → %s)", video_id, result)
    return result


# ---- 初回 OAuth (youtube-auth CLI 補助。人間が一度だけ実行する) ----


def build_auth_url(client_id: str, redirect_uri: str) -> str:
    """認可 URL を組む (refresh token を得るため offline + consent を強制)."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def extract_code(redirect_url_or_code: str) -> str:
    """リダイレクト URL 全体の手貼り、または code 単体のどちらでも受ける (--manual)."""
    raw = redirect_url_or_code.strip()
    if "://" in raw or raw.startswith("/?"):
        query = urlparse(raw).query
        code = parse_qs(query).get("code", [""])[0]
        if not code:
            raise YouTubeError("貼り付けられた URL に code パラメータがありません")
        return code
    return raw


def exchange_code_for_refresh_token(
    client_id: str, client_secret: str, code: str, redirect_uri: str
) -> str:
    """認可 code を refresh token に交換する (初回のみ)."""
    try:
        resp = httpx.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise YouTubeError(f"code 交換の接続失敗: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise YouTubeError(f"code 交換失敗: {_error_detail(resp)}")
    token = _parse_json(resp, "code 交換").get("refresh_token", "")
    if not isinstance(token, str) or not token:
        raise YouTubeError(
            "応答に refresh_token がありません "
            "(既に認可済みの場合は https://myaccount.google.com/permissions で"
            "アクセス権を削除してから再実行)"
        )
    return token


def wait_for_oauth_code(port: int, *, timeout_seconds: float = 300.0) -> str:
    """loopback リダイレクト (http://127.0.0.1:<port>) で認可 code を 1 回だけ受ける."""
    received: list[str] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler の規約)
            code = parse_qs(urlparse(self.path).query).get("code", [""])[0]
            if code:
                received.append(code)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            message = "認可を受け取りました。このタブは閉じて構いません。" if code else "code がありません。"
            self.wfile.write(f"<html><body><p>{message}</p></body></html>".encode())

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # アクセスログ (URL に code が含まれる) を出さない

    try:
        server = HTTPServer(("127.0.0.1", port), _Handler)
    except OSError as exc:
        raise YouTubeError(
            f"ポート {port} で待受できません ({type(exc).__name__})。"
            " --port で別ポートを指定するか --manual を使ってください"
        ) from exc
    server.timeout = timeout_seconds
    try:
        server.handle_request()  # 1 リクエストだけ処理して返る (timeout で諦める)
    finally:
        server.server_close()
    if not received:
        raise YouTubeError(f"{timeout_seconds:.0f} 秒以内に認可リダイレクトを受信できませんでした")
    return received[0]
