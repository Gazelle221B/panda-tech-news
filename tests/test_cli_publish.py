"""publish / approve / youtube-auth CLI のテスト (Sprint 3 T40).

動画生成 (render_video) と YouTube API は patch し、実 ffmpeg・実 API は使わない。
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from karyu_tech_news.deliver.youtube import YouTubeError, YouTubeUploadResult
from karyu_tech_news.main import app
from karyu_tech_news.store.repo import (
    create_db_engine,
    get_latest_audio_version,
    get_latest_uploaded_video,
    init_db,
    insert_audio_version,
    insert_video_version,
)
from karyu_tech_news.store.schema import EpisodeDraft, VideoVersion
from karyu_tech_news.video.render import VideoRenderError, VideoRenderResult

runner = CliRunner()


def _seed_audio(db: Path, tmp_path: Path) -> tuple[int, int]:
    """draft + audio_version (実在する mp3 ファイル付き) を播種し (draft_id, audio_id) を返す."""
    engine = create_db_engine(db)
    init_db(engine)
    mp3 = tmp_path / "ep.mp3"
    mp3.write_bytes(b"\x00" * 64)
    with Session(engine) as s:
        d = EpisodeDraft(
            created_at=datetime.now(UTC),
            variant="A",
            title="テスト回: 今日の3本",
            estimated_minutes=5,
            notices_json="[]",
            markdown="# テスト",
        )
        s.add(d)
        s.flush()
        av = insert_audio_version(
            s,
            int(d.id),
            engine="mock",
            duration_sec=300.0,
            lufs=-16.0,
            bitrate="192k",
            sample_rate=48000,
            path=str(mp3),
            now=datetime.now(UTC),
        )
        s.commit()
        return int(d.id), int(av.id)


def _render_result(tmp_path: Path) -> VideoRenderResult:
    return VideoRenderResult(
        path=str(tmp_path / "ep.mp4"),
        width=1280,
        height=720,
        fps=30,
        size_bytes=1024,
        used_logo=False,
    )


def _upload_result() -> YouTubeUploadResult:
    return YouTubeUploadResult(
        video_id="vid42",
        url="https://www.youtube.com/watch?v=vid42",
        privacy_status="unlisted",
        title="テスト回: 今日の3本",
    )


def _yt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "cid")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "sec")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "ref")


# ---------- repo ----------


def test_get_latest_audio_version_empty(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    engine = create_db_engine(db)
    init_db(engine)
    with Session(engine) as s:
        assert get_latest_audio_version(s) is None


def test_get_latest_uploaded_video_skips_unuploaded(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    draft_id, audio_id = _seed_audio(db, tmp_path)
    engine = create_db_engine(db)
    with Session(engine) as s:
        insert_video_version(
            s,
            draft_id,
            audio_id,
            path="data/videos/a.mp4",
            youtube_video_id="vid1",
            youtube_url="https://www.youtube.com/watch?v=vid1",
            privacy_status="unlisted",
            now=datetime.now(UTC),
        )
        insert_video_version(
            s,
            draft_id,
            audio_id,
            path="data/videos/b.mp4",
            youtube_video_id=None,  # dry-run 相当 (未アップロード)
            youtube_url=None,
            privacy_status=None,
            now=datetime.now(UTC),
        )
        s.commit()
        latest = get_latest_uploaded_video(s)
        assert latest is not None
        assert latest.youtube_video_id == "vid1"


# ---------- publish ----------


def test_publish_help() -> None:
    result = runner.invoke(app, ["publish", "--help"])
    assert result.exit_code == 0
    assert "--audio-id" in result.output
    assert "--dry-run" in result.output


def test_publish_without_audio_version(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    result = runner.invoke(app, ["publish", "--db-path", str(db)])
    assert result.exit_code == 1
    assert "audio_version" in result.output


def test_publish_rejects_public(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    result = runner.invoke(app, ["publish", "--db-path", str(db), "--privacy", "public"])
    assert result.exit_code == 1
    assert "approve" in result.output


def test_publish_dry_run_renders_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    _seed_audio(db, tmp_path)
    upload = MagicMock()
    with (
        patch(
            "karyu_tech_news.video.render.render_video",
            return_value=_render_result(tmp_path),
        ) as render,
        patch("karyu_tech_news.deliver.youtube.upload_video", upload),
    ):
        result = runner.invoke(app, ["publish", "--db-path", str(db), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    render.assert_called_once()
    upload.assert_not_called()
    engine = create_db_engine(db)
    with Session(engine) as s:
        assert s.query(VideoVersion).count() == 0


def test_publish_full_flow_records_and_posts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    draft_id, audio_id = _seed_audio(db, tmp_path)
    _yt_env(monkeypatch)
    with (
        patch(
            "karyu_tech_news.video.render.render_video",
            return_value=_render_result(tmp_path),
        ),
        patch(
            "karyu_tech_news.deliver.youtube.refresh_access_token", return_value="at"
        ),
        patch(
            "karyu_tech_news.deliver.youtube.upload_video",
            return_value=_upload_result(),
        ) as upload,
        patch(
            "karyu_tech_news.deliver.discord.post_markdown", return_value=True
        ) as post,
    ):
        result = runner.invoke(app, ["publish", "--db-path", str(db), "--post"])
    assert result.exit_code == 0, result.output
    assert "vid42" in result.output
    # FR-120: 既定 unlisted でアップロードされる
    assert upload.call_args.kwargs["privacy"] == "unlisted"
    # 朝確認メッセージに URL と approve 導線が含まれる (要件 §15.4)
    message = post.call_args.args[1]
    assert "vid42" in message
    assert "approve" in message
    engine = create_db_engine(db)
    with Session(engine) as s:
        row = s.query(VideoVersion).one()
        assert row.draft_id == draft_id
        assert row.audio_version_id == audio_id
        assert row.youtube_video_id == "vid42"
        assert row.privacy_status == "unlisted"


def test_publish_upload_failure_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    _seed_audio(db, tmp_path)
    _yt_env(monkeypatch)
    with (
        patch(
            "karyu_tech_news.video.render.render_video",
            return_value=_render_result(tmp_path),
        ),
        patch(
            "karyu_tech_news.deliver.youtube.refresh_access_token", return_value="at"
        ),
        patch(
            "karyu_tech_news.deliver.youtube.upload_video",
            side_effect=YouTubeError("quota exceeded"),
        ),
    ):
        result = runner.invoke(app, ["publish", "--db-path", str(db)])
    assert result.exit_code == 1
    assert "アップロード失敗" in result.output
    engine = create_db_engine(db)
    with Session(engine) as s:
        assert s.query(VideoVersion).count() == 0  # 失敗時は記録しない


def test_publish_render_failure_fails_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    _seed_audio(db, tmp_path)
    with patch(
        "karyu_tech_news.video.render.render_video",
        side_effect=VideoRenderError("ffmpeg が見つかりません"),
    ):
        result = runner.invoke(app, ["publish", "--db-path", str(db)])
    assert result.exit_code == 1
    assert "動画生成失敗" in result.output


def test_publish_missing_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    _seed_audio(db, tmp_path)
    for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with patch(
        "karyu_tech_news.video.render.render_video",
        return_value=_render_result(tmp_path),
    ):
        result = runner.invoke(app, ["publish", "--db-path", str(db)])
    assert result.exit_code == 1
    assert "YOUTUBE_CLIENT_ID" in result.output


# ---------- approve ----------


def test_approve_without_uploaded_video(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    result = runner.invoke(app, ["approve", "--db-path", str(db)])
    assert result.exit_code == 1
    assert "video_version" in result.output


def test_approve_switches_to_public(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    draft_id, audio_id = _seed_audio(db, tmp_path)
    engine = create_db_engine(db)
    with Session(engine) as s:
        insert_video_version(
            s,
            draft_id,
            audio_id,
            path="data/videos/a.mp4",
            youtube_video_id="vid42",
            youtube_url="https://www.youtube.com/watch?v=vid42",
            privacy_status="unlisted",
            now=datetime.now(UTC),
        )
        s.commit()
    _yt_env(monkeypatch)
    with (
        patch(
            "karyu_tech_news.deliver.youtube.refresh_access_token", return_value="at"
        ),
        patch(
            "karyu_tech_news.deliver.youtube.set_privacy_status", return_value="public"
        ) as set_privacy,
    ):
        result = runner.invoke(app, ["approve", "--db-path", str(db)])
    assert result.exit_code == 0, result.output
    assert "public" in result.output
    set_privacy.assert_called_once_with("at", "vid42", "public")
    with Session(engine) as s:
        row = s.query(VideoVersion).one()
        assert row.privacy_status == "public"


def test_approve_youtube_error_keeps_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.db"
    draft_id, audio_id = _seed_audio(db, tmp_path)
    engine = create_db_engine(db)
    with Session(engine) as s:
        insert_video_version(
            s,
            draft_id,
            audio_id,
            path="data/videos/a.mp4",
            youtube_video_id="vid42",
            youtube_url=None,
            privacy_status="unlisted",
            now=datetime.now(UTC),
        )
        s.commit()
    _yt_env(monkeypatch)
    with (
        patch(
            "karyu_tech_news.deliver.youtube.refresh_access_token", return_value="at"
        ),
        patch(
            "karyu_tech_news.deliver.youtube.set_privacy_status",
            side_effect=YouTubeError("forbidden"),
        ),
    ):
        result = runner.invoke(app, ["approve", "--db-path", str(db)])
    assert result.exit_code == 1
    with Session(engine) as s:
        row = s.query(VideoVersion).one()
        assert row.privacy_status == "unlisted"  # 失敗時は変更しない


# ---------- youtube-auth ----------


def test_youtube_auth_requires_client(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    result = runner.invoke(app, ["youtube-auth"])
    assert result.exit_code == 1
    assert "client-id" in result.output


def test_youtube_auth_manual_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch(
        "karyu_tech_news.deliver.youtube.exchange_code_for_refresh_token",
        return_value="rt-99",
    ) as exchange:
        result = runner.invoke(
            app,
            ["youtube-auth", "--client-id", "cid", "--client-secret", "sec", "--manual"],
            input="http://127.0.0.1:8765/?code=abc\n",
        )
    assert result.exit_code == 0, result.output
    assert "YOUTUBE_REFRESH_TOKEN=rt-99" in result.output
    assert exchange.call_args.args[2] == "abc"
