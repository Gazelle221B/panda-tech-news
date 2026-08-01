"""T29 mixer / T31 produce パイプラインのユニットテスト (Sprint 2).

TTS は mock エンジン、Discord は httpx モック。ffmpeg 依存の produce 統合は skipif。
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from karyu_tech_news.deliver.discord import post_audio
from karyu_tech_news.main import app
from karyu_tech_news.mix.mixer import find_bgm, mix_bgm
from karyu_tech_news.store.repo import (
    create_db_engine,
    get_latest_episode_draft,
    init_db,
    insert_audio_version,
)
from karyu_tech_news.store.schema import AudioVersion, EpisodeDraft

runner = CliRunner()
_HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _wav_bytes(n_frames: int = 100, sample_rate: int = 48000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x01\x00" * n_frames)
    return buf.getvalue()


def _silent_wav_bytes(n_frames: int = 100, sample_rate: int = 48000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


def _wav_with_silence_gap(gap_sec: float = 4.5, sample_rate: int = 48000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\xff\x7f" * sample_rate)
        w.writeframes(b"\x00\x00" * int(sample_rate * gap_sec))
        w.writeframes(b"\xff\x7f" * sample_rate)
    return buf.getvalue()


def _seed_draft(db: Path, markdown: str = "# テスト\n\nこんにちは。本日のニュースです。") -> int:
    engine = create_db_engine(db)
    init_db(engine)
    with Session(engine) as s:
        d = EpisodeDraft(
            created_at=datetime.now(UTC),
            variant="A",
            title="テスト回",
            estimated_minutes=5,
            notices_json="[]",
            markdown=markdown,
        )
        s.add(d)
        s.commit()
        return int(d.id)


# ---------- T29 mixer (素材非依存) ----------


def test_find_bgm_none_when_dir_missing(tmp_path: Path) -> None:
    assert find_bgm(tmp_path / "nope") is None


def test_find_bgm_none_when_empty(tmp_path: Path) -> None:
    (tmp_path / "bgm").mkdir()
    assert find_bgm(tmp_path / "bgm") is None


def test_find_bgm_picks_audio_ignores_nonaudio(tmp_path: Path) -> None:
    d = tmp_path / "bgm"
    d.mkdir()
    (d / "a.mp3").write_bytes(b"x")
    (d / "readme.txt").write_text("x")
    assert find_bgm(d) == d / "a.mp3"


def test_mix_bgm_passthrough_when_no_material() -> None:
    wav = _wav_bytes()
    assert mix_bgm(wav, bgm_path=None) == wav  # 素材なし → 素通し (素材非依存)


def test_mix_bgm_passthrough_when_path_missing(tmp_path: Path) -> None:
    wav = _wav_bytes()
    assert mix_bgm(wav, bgm_path=tmp_path / "missing.mp3") == wav


# ---------- T31 audio_versions 永続化 ----------


def test_insert_and_get_latest_draft(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    draft_id = _seed_draft(db)
    engine = create_db_engine(db)
    with Session(engine) as s:
        latest = get_latest_episode_draft(s)
        assert latest is not None and latest.id == draft_id
        av = insert_audio_version(
            s,
            draft_id,
            engine="mock",
            duration_sec=12.3,
            lufs=-16.0,
            bitrate="192k",
            sample_rate=48000,
            path="data/episodes/e.mp3",
            now=datetime.now(UTC),
        )
        s.commit()
        assert av.id is not None
        rows = s.query(AudioVersion).all()
        assert len(rows) == 1
        assert rows[0].engine == "mock"
        assert rows[0].lufs == -16.0


def test_insert_audio_version_accepts_null_lufs(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    draft_id = _seed_draft(db)
    engine = create_db_engine(db)
    with Session(engine) as s:
        av = insert_audio_version(
            s,
            draft_id,
            engine="mock",
            duration_sec=0.3,
            lufs=None,  # post-encode LUFS 測定不能 → NULL
            bitrate="192k",
            sample_rate=48000,
            path="x.mp3",
            now=datetime.now(UTC),
        )
        s.commit()
        assert av.lufs is None


def test_get_latest_draft_none_when_empty(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "state.db")
    init_db(engine)
    with Session(engine) as s:
        assert get_latest_episode_draft(s) is None


# ---------- T31 Discord 配信 (fail-open) ----------


def test_post_audio_missing_file_returns_false(tmp_path: Path) -> None:
    assert post_audio("https://discord/webhook", tmp_path / "no.mp3") is False


def test_post_audio_no_webhook_returns_false(tmp_path: Path) -> None:
    p = tmp_path / "e.mp3"
    p.write_bytes(b"x")
    assert post_audio("", p) is False


def test_post_audio_oversized_degrades_to_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "big.mp3"
    p.write_bytes(b"0123456789")  # 10 bytes
    monkeypatch.setattr("karyu_tech_news.deliver.discord.DISCORD_FILE_LIMIT_BYTES", 5)
    with patch("karyu_tech_news.deliver.discord.post_summary", return_value=True) as ps:
        ok = post_audio("https://discord/webhook", p, content="hi")
    assert ok is True
    assert ps.called  # 添付不可 → メッセージに degrade


def test_post_audio_oversized_no_leading_newline_when_content_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # content 空時に degrade メッセージ先頭へ改行を入れない (Copilot 指摘)
    p = tmp_path / "big.mp3"
    p.write_bytes(b"0123456789")
    monkeypatch.setattr("karyu_tech_news.deliver.discord.DISCORD_FILE_LIMIT_BYTES", 5)
    with patch("karyu_tech_news.deliver.discord.post_summary", return_value=True) as ps:
        post_audio("https://discord/webhook", p)  # content="" (既定)
    body = ps.call_args.args[1]  # post_summary(webhook_url, body)
    assert not body.startswith("\n")
    assert body.startswith("⚠️")


def test_post_audio_success_uploads_multipart(tmp_path: Path) -> None:
    p = tmp_path / "e.mp3"
    p.write_bytes(b"id3audio")
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    with patch("karyu_tech_news.deliver.discord.httpx.post", return_value=resp) as post:
        ok = post_audio("https://discord/webhook", p, content="hi")
    assert ok is True
    assert post.call_args.kwargs["files"]["file"][0] == "e.mp3"  # 添付名


def test_post_audio_http_error_fail_open(tmp_path: Path) -> None:
    import httpx

    p = tmp_path / "e.mp3"
    p.write_bytes(b"id3audio")
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post",
        side_effect=httpx.ConnectError("down"),
    ):
        assert post_audio("https://discord/webhook", p) is False  # 落ちず False


# Webhook URL にはトークンが含まれる。ログ・例外に漏らさないことを固定 (過去 Critical)。
_WEBHOOK_WITH_TOKEN = "https://discord.com/api/webhooks/123/secret-token-abc"


def test_post_audio_http_error_log_has_no_webhook_token(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    import httpx

    p = tmp_path / "e.mp3"
    p.write_bytes(b"id3audio")
    resp = MagicMock()
    # 例外メッセージに Webhook URL (トークン) が混入する実状況を再現し redaction を検証 (Copilot 指摘)
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"Server error '500' for url '{_WEBHOOK_WITH_TOKEN}'",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    )
    with (
        patch("karyu_tech_news.deliver.discord.httpx.post", return_value=resp),
        caplog.at_level(logging.ERROR),
    ):
        assert post_audio(_WEBHOOK_WITH_TOKEN, p) is False
    assert "secret-token-abc" not in caplog.text
    assert "discord.com/api/webhooks" not in caplog.text
    assert "500" in caplog.text  # status code は記録される


def test_post_audio_connect_error_log_has_no_webhook_token(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    import httpx

    p = tmp_path / "e.mp3"
    p.write_bytes(b"id3audio")
    with (
        patch(
            "karyu_tech_news.deliver.discord.httpx.post",
            side_effect=httpx.ConnectError(f"failed connecting to {_WEBHOOK_WITH_TOKEN}"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        assert post_audio(_WEBHOOK_WITH_TOKEN, p) is False
    assert "secret-token-abc" not in caplog.text  # 例外文字列に URL が混ざっても漏らさない


# ---------- T31 produce CLI ----------


def test_produce_help() -> None:
    result = runner.invoke(app, ["produce", "--help"])
    assert result.exit_code == 0
    assert "--engine" in result.output
    assert "--dry-run" in result.output


def test_produce_no_draft_exits_1(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    init_db(create_db_engine(db))  # 空 DB
    result = runner.invoke(
        app, ["produce", "--dry-run", "--engine", "mock", "--db-path", str(db)]
    )
    assert result.exit_code == 1
    assert "episode_draft がありません" in result.output


def test_produce_all_zero_frame_synthesis_exits_without_mp3(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)

    class _ZeroFrameEngine:
        def name(self) -> str:
            return "zero"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_wav_bytes(0), sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.tts.engine.select_engine", return_value=_ZeroFrameEngine()):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "zero",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
    )
    assert result.exit_code == 1
    assert "TTS 合成で欠落文があります 2/2 文" in result.output
    assert not list(out_dir.glob("*.mp3"))


def test_produce_all_silent_synthesis_exits_without_mp3(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)

    class _SilentEngine:
        def name(self) -> str:
            return "silent"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_silent_wav_bytes(100), sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.tts.engine.select_engine", return_value=_SilentEngine()):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "silent",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
    )
    assert result.exit_code == 1
    assert "TTS 合成で欠落文があります 2/2 文" in result.output
    assert not list(out_dir.glob("*.mp3"))


def test_produce_partial_synthesis_exits_without_mp3(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)

    class _PartialEngine:
        def __init__(self) -> None:
            self.calls = 0

        def name(self) -> str:
            return "partial"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            self.calls += 1
            audio = _silent_wav_bytes(48000) if self.calls == 2 else _wav_with_silence_gap(0.0)
            return SynthesisResult(audio=audio, sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.tts.engine.select_engine", return_value=_PartialEngine()):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "partial",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert "TTS 合成で欠落文があります 1/2 文" in result.output
    assert not list(out_dir.glob("*.mp3"))


def test_produce_long_silence_gap_exits_without_mp3(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)

    class _GapEngine:
        def name(self) -> str:
            return "gap"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_wav_with_silence_gap(3.0), sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.tts.engine.select_engine", return_value=_GapEngine()):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "gap",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert "無音区間" in result.output
    assert not list(out_dir.glob("*.mp3"))


def test_produce_allows_subthreshold_silence_gap(tmp_path: Path) -> None:
    from karyu_tech_news.mix.master import MasteringResult
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)

    class _GapEngine:
        def name(self) -> str:
            return "gap"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_wav_with_silence_gap(2.5), sample_rate=48000)

    def _fake_master_to_mp3(audio_wav: bytes, output_path: Path) -> MasteringResult:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"id3")
        return MasteringResult(
            path=str(out),
            target_lufs=-16.0,
            measured_lufs=-16.0,
            true_peak_dbtp=-1.0,
            duration_sec=5.5,
            bitrate="192k",
            sample_rate=48000,
        )

    with (
        patch("karyu_tech_news.tts.engine.select_engine", return_value=_GapEngine()),
        patch("karyu_tech_news.mix.master.master_to_mp3", side_effect=_fake_master_to_mp3),
    ):
        result = runner.invoke(
            app,
            [
                "produce",
                "--dry-run",
                "--engine",
                "gap",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(tmp_path / "episodes"),
            ],
        )
    assert result.exit_code == 0, result.output
    assert "tp=-1.0 dBTP" in result.output
    assert "max_silence=2.5s" in result.output
    assert "DRY RUN" in result.output


def test_produce_long_audio_with_unmeasurable_lufs_exits_without_mp3(tmp_path: Path) -> None:
    from karyu_tech_news.mix.master import MasteringResult

    db = tmp_path / "state.db"
    _seed_draft(db)

    def _fake_master_to_mp3(audio_wav: bytes, output_path: Path) -> MasteringResult:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"id3")
        return MasteringResult(
            path=str(out),
            target_lufs=-16.0,
            measured_lufs=float("-inf"),
            true_peak_dbtp=float("-inf"),
            duration_sec=5.0,
            bitrate="192k",
            sample_rate=48000,
        )

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.mix.master.master_to_mp3", side_effect=_fake_master_to_mp3):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "mock",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert "LUFS を測定できません" in result.output
    assert not list(out_dir.glob("*.mp3"))

    engine = create_db_engine(db)
    with Session(engine) as s:
        assert s.query(AudioVersion).all() == []


def test_produce_long_audio_with_high_true_peak_exits_without_mp3(tmp_path: Path) -> None:
    from karyu_tech_news.mix.master import MasteringResult

    db = tmp_path / "state.db"
    _seed_draft(db)

    def _fake_master_to_mp3(audio_wav: bytes, output_path: Path) -> MasteringResult:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"id3")
        return MasteringResult(
            path=str(out),
            target_lufs=-16.0,
            measured_lufs=-16.0,
            true_peak_dbtp=-0.4,
            duration_sec=5.0,
            bitrate="192k",
            sample_rate=48000,
        )

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.mix.master.master_to_mp3", side_effect=_fake_master_to_mp3):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "mock",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert "true peak が高すぎます" in result.output
    assert not list(out_dir.glob("*.mp3"))

    engine = create_db_engine(db)
    with Session(engine) as s:
        assert s.query(AudioVersion).all() == []


def test_produce_long_audio_with_unmeasurable_true_peak_exits_without_mp3(
    tmp_path: Path,
) -> None:
    from karyu_tech_news.mix.master import MasteringResult

    db = tmp_path / "state.db"
    _seed_draft(db)

    def _fake_master_to_mp3(audio_wav: bytes, output_path: Path) -> MasteringResult:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"id3")
        return MasteringResult(
            path=str(out),
            target_lufs=-16.0,
            measured_lufs=-16.0,
            true_peak_dbtp=float("nan"),
            duration_sec=5.0,
            bitrate="192k",
            sample_rate=48000,
        )

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.mix.master.master_to_mp3", side_effect=_fake_master_to_mp3):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine",
                "mock",
                "--db-path",
                str(db),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert "true peak を測定できません" in result.output
    assert not list(out_dir.glob("*.mp3"))

    engine = create_db_engine(db)
    with Session(engine) as s:
        assert s.query(AudioVersion).all() == []


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")
def test_produce_dry_run_generates_mp3(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    _seed_draft(db)
    result = runner.invoke(
        app,
        [
            "produce",
            "--dry-run",
            "--engine",
            "mock",
            "--db-path",
            str(db),
            "--bgm-dir",
            str(tmp_path / "nobgm"),
            "--out-dir",
            str(tmp_path / "episodes"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "完パケ" in result.output
    assert "DRY RUN" in result.output
    assert len(list((tmp_path / "episodes").glob("episode_1_*.mp3"))) == 1


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")
def test_produce_persists_audio_version(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    _seed_draft(db)
    result = runner.invoke(
        app,
        [
            "produce",
            "--engine",
            "mock",
            "--db-path",
            str(db),
            "--bgm-dir",
            str(tmp_path / "nobgm"),
            "--out-dir",
            str(tmp_path / "episodes"),
        ],
    )
    assert result.exit_code == 0, result.output
    engine = create_db_engine(db)
    with Session(engine) as s:
        rows = s.query(AudioVersion).all()
        assert len(rows) == 1
        assert rows[0].engine == "mock"
        assert rows[0].sample_rate == 48000
        assert Path(str(rows[0].path)).name.startswith("episode_1_")
        assert Path(str(rows[0].path)).suffix == ".mp3"


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")
def test_produce_repeated_runs_do_not_overwrite_audio_path(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    _seed_draft(db)
    args = [
        "produce",
        "--engine",
        "mock",
        "--db-path",
        str(db),
        "--bgm-dir",
        str(tmp_path / "nobgm"),
        "--out-dir",
        str(tmp_path / "episodes"),
    ]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    engine = create_db_engine(db)
    with Session(engine) as s:
        rows = s.query(AudioVersion).order_by(AudioVersion.id).all()
        paths = [str(row.path) for row in rows]
    assert len(paths) == 2
    assert len(set(paths)) == 2
    assert all(Path(path).exists() for path in paths)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")
def test_produce_uses_config_primary_engine(tmp_path: Path) -> None:
    # --engine 未指定なら config の tts.primary_engine を使う (Codex HIGH: voice 誤読の回帰)
    db = tmp_path / "state.db"
    _seed_draft(db)
    persona = tmp_path / "persona.yaml"
    persona.write_text("tts:\n  primary_engine: mock\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "produce",
            "--dry-run",
            "--db-path",
            str(db),
            "--persona",
            str(persona),
            "--bgm-dir",
            str(tmp_path / "nobgm"),
            "--out-dir",
            str(tmp_path / "ep"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "engine=mock" in result.output  # config(tts.primary_engine) 由来で mock が選ばれた


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")
def test_produce_merges_auto_and_manual_reading_dicts_manual_wins(tmp_path: Path) -> None:
    """produce は auto (writer ルビ由来) / manual 読み辞書を二層マージし、
    同一表記は manual (人間確認済み) が常に勝つ (T56, Issue #52)。"""
    from karyu_tech_news.tts.engine import (
        Capabilities,
        MockTTSEngine,
        SynthesisRequest,
        SynthesisResult,
        Voice,
    )

    db = tmp_path / "state.db"
    _seed_draft(db, markdown="# テスト\n\nダブル辞書用語について話します。")

    manual = tmp_path / "reading_dict.yaml"
    manual.write_text("companies:\n  ダブル辞書用語: マニュアルヨミ\n", encoding="utf-8")
    auto = tmp_path / "reading_dict.auto.yaml"
    auto.write_text("ダブル辞書用語: オートヨミ\n単独オート用語: 単独オートヨミ\n", encoding="utf-8")
    persona = tmp_path / "persona.yaml"
    persona.write_text(
        "tts:\n"
        "  primary_engine: mock\n"
        f"  reading_dict: {manual}\n"
        f"  auto_reading_dict: {auto}\n",
        encoding="utf-8",
    )

    seen_texts: list[str] = []

    class _RecordingEngine:
        """実 MockTTSEngine に委譲しつつ、エンジンに渡された正規化後テキストを記録する."""

        def __init__(self) -> None:
            self._inner = MockTTSEngine()

        def name(self) -> str:
            return "mock"

        def voices(self) -> list[Voice]:
            return self._inner.voices()

        def capabilities(self) -> Capabilities:
            return self._inner.capabilities()

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            seen_texts.append(req.text)
            return self._inner.synthesize(req)

    out_dir = tmp_path / "episodes"
    with patch("karyu_tech_news.tts.engine.select_engine", return_value=_RecordingEngine()):
        result = runner.invoke(
            app,
            [
                "produce",
                "--dry-run",
                "--db-path",
                str(db),
                "--persona",
                str(persona),
                "--bgm-dir",
                str(tmp_path / "nobgm"),
                "--out-dir",
                str(out_dir),
            ],
        )

    assert result.exit_code == 0, result.output
    combined = "".join(seen_texts)
    assert "マニュアルヨミ" in combined  # 競合キーは manual が勝つ
    assert "オートヨミ" not in combined  # auto の読みは使われない (manual に上書きされる)


# ---------- T58 ASR 品質ゲート (Issue #54): persona 設定の薄い契約テスト ----------
# WhisperAsrBackend は main.py の produce 内で `karyu_tech_news.tts.asr_gate` から
# import される。構築有無だけを検証するため patch し、実 whisper は使わない。


def test_produce_asr_gate_disabled_by_default_skips_backend(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)
    persona = tmp_path / "persona.yaml"
    persona.write_text("tts:\n  primary_engine: mock\n", encoding="utf-8")  # asr_gate 未設定

    class _ZeroFrameEngine:
        def name(self) -> str:
            return "zero"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_wav_bytes(0), sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with (
        patch("karyu_tech_news.tts.engine.select_engine", return_value=_ZeroFrameEngine()),
        patch("karyu_tech_news.tts.asr_gate.WhisperAsrBackend") as backend_cls,
    ):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine", "zero",
                "--db-path", str(db),
                "--persona", str(persona),
                "--bgm-dir", str(tmp_path / "nobgm"),
                "--out-dir", str(out_dir),
            ],
        )
    assert result.exit_code == 1  # zero-frame 合成自体は従来どおり fail
    assert backend_cls.call_count == 0  # asr_gate 未設定なら backend を構築しない


def test_produce_asr_gate_false_skips_backend(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)
    persona = tmp_path / "persona.yaml"
    persona.write_text("tts:\n  primary_engine: mock\n  asr_gate: false\n", encoding="utf-8")

    class _ZeroFrameEngine:
        def name(self) -> str:
            return "zero"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_wav_bytes(0), sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with (
        patch("karyu_tech_news.tts.engine.select_engine", return_value=_ZeroFrameEngine()),
        patch("karyu_tech_news.tts.asr_gate.WhisperAsrBackend") as backend_cls,
    ):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine", "zero",
                "--db-path", str(db),
                "--persona", str(persona),
                "--bgm-dir", str(tmp_path / "nobgm"),
                "--out-dir", str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert backend_cls.call_count == 0  # 明示的 false でも構築しない


def test_produce_asr_gate_enabled_constructs_backend(tmp_path: Path) -> None:
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)
    persona = tmp_path / "persona.yaml"
    persona.write_text("tts:\n  primary_engine: mock\n  asr_gate: true\n", encoding="utf-8")

    class _ZeroFrameEngine:
        def name(self) -> str:
            return "zero"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_wav_bytes(0), sample_rate=48000)

    out_dir = tmp_path / "episodes"
    with (
        patch("karyu_tech_news.tts.engine.select_engine", return_value=_ZeroFrameEngine()),
        patch("karyu_tech_news.tts.asr_gate.WhisperAsrBackend") as backend_cls,
    ):
        result = runner.invoke(
            app,
            [
                "produce",
                "--engine", "zero",
                "--db-path", str(db),
                "--persona", str(persona),
                "--bgm-dir", str(tmp_path / "nobgm"),
                "--out-dir", str(out_dir),
            ],
        )
    assert result.exit_code == 1  # zero-frame 合成自体は ASR 到達前に fail (従来どおり)
    assert backend_cls.call_count == 1  # asr_gate: true なら必ず構築する


def test_produce_asr_gate_unavailable_fails_fast(tmp_path: Path) -> None:
    # 明示的に有効化したのに ASR が使えない (未導入) 場合は黙って無効化せず ERROR + exit 1
    from karyu_tech_news.tts.asr_gate import AsrUnavailableError
    from karyu_tech_news.tts.engine import Capabilities, SynthesisRequest, SynthesisResult, Voice

    db = tmp_path / "state.db"
    _seed_draft(db)
    persona = tmp_path / "persona.yaml"
    persona.write_text("tts:\n  primary_engine: mock\n  asr_gate: true\n", encoding="utf-8")

    def _loud_wav(n_frames: int = 4800, sample_rate: int = 48000) -> bytes:
        # _wav_bytes の振幅 (\x01\x00) は無音判定閾値以下で ASR 到達前に skip されるため、
        # ここでは品質ゲートを確実に通す強い振幅 (\xff\x7f) を使う。
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(b"\xff\x7f" * n_frames)
        return buf.getvalue()

    class _OkEngine:
        def name(self) -> str:
            return "mock"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=200)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=_loud_wav(), sample_rate=48000)

    mock_backend = MagicMock()
    mock_backend.transcribe.side_effect = AsrUnavailableError("openai-whisper 未導入")
    out_dir = tmp_path / "episodes"
    with (
        patch("karyu_tech_news.tts.engine.select_engine", return_value=_OkEngine()),
        patch(
            "karyu_tech_news.tts.asr_gate.WhisperAsrBackend", return_value=mock_backend
        ),
    ):
        result = runner.invoke(
            app,
            [
                "produce",
                "--dry-run",
                "--engine", "mock",
                "--db-path", str(db),
                "--persona", str(persona),
                "--bgm-dir", str(tmp_path / "nobgm"),
                "--out-dir", str(out_dir),
            ],
        )
    assert result.exit_code == 1
    assert "ASR" in result.output
    assert not list(out_dir.glob("*.mp3"))


# ---------- 回帰: エンジン既定声フォールバック (実 smoke で発見) ----------


def test_synthesize_script_uses_engine_default_voice() -> None:
    """声 ID が "hal" でないエンジン (kokoro=jf_alpha) でも、その声で合成される。

    "hal" 固定だと kokoro が全文 fail-open し無音になる回帰を防ぐ (実 produce smoke で発見)。
    """
    from datetime import UTC, datetime

    from karyu_tech_news.script.structure import Segment, StructuredScript
    from karyu_tech_news.tts.engine import (
        Capabilities,
        SynthesisRequest,
        SynthesisResult,
        Voice,
    )
    from karyu_tech_news.tts.synthesize import synthesize_script

    seen: list[str] = []

    class FakeEngine:
        def name(self) -> str:
            return "fake"

        def voices(self) -> list[Voice]:
            return [Voice(id="jf_alpha", name="HAL", language="ja")]

        def capabilities(self) -> Capabilities:
            return Capabilities(
                emoji_style=False, voice_clone=False, streaming=False, max_chars=500
            )

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            seen.append(req.voice_id)
            return SynthesisResult(audio=_wav_bytes(), sample_rate=48000, audio_format="wav")

    script = StructuredScript(
        variant="A",
        generated_at=datetime.now(UTC),
        segments=[Segment(kind="topic", text="こんにちは。", tone="neutral", bgm="neutral")],
    )
    synthesize_script(script, FakeEngine(), {})
    assert seen and all(v == "jf_alpha" for v in seen)  # "hal" でなくエンジンの既定声


# ---------- 回帰: 見出し/メタを発話しない (実 produce smoke で発見) ----------


def test_strip_markdown_structure_drops_headers_and_meta() -> None:
    """Markdown 見出し (中国語原文タイトル) と生成メタを発話テキストから除去する。

    要件 §9.6 (中国メディア本文朗読禁止) + Kokoro の中国語誤読/尺膨張を防ぐ (実 smoke 発見)。
    """
    from karyu_tech_news.tts.normalize import strip_markdown_structure

    md = (
        "# 華流テック通信 — HAL Daily Briefing\n"
        "生成日時: 2026-06-14 10:48 / LLM profile: A\n\n"
        "華流テック通信、本日のHAL Daily Briefingです。\n\n"
        "## 1. 智谱：GLM-5.2将面向GLM Coding Plan全量用户开放\n"
        "智谱が、コード生成特化モデルを公開します。\n\n"
        "---\n"
        "## 出典\n"
        "1. [智谱：GLM-5.2将面向GLM Coding Plan全量用户开放](https://36kr.com/x)\n"
        "2. [外媒曝蚂蚁集团正秘密测试AI 版支付宝](https://36kr.com/y)\n"
    )
    out = strip_markdown_structure(md)
    assert "智谱：GLM-5.2将面向" not in out  # 中国語原文タイトル (見出し + 出典) は読まない
    assert "外媒曝" not in out  # ソース一覧の原文タイトルも除去
    assert "https://" not in out  # URL は読まない
    assert "---" not in out  # 水平線も読まない (Codex 注記)
    assert "生成日時" not in out  # ビルドメタは読まない
    assert not out.lstrip().startswith("#")
    assert "本日のHAL Daily Briefingです" in out  # 日本語ナレーションは残る
    assert "コード生成特化モデルを公開します" in out


@pytest.mark.skipif(
    # Windows では CreateProcess の探索順により "bash" が WSL bash に解決され、
    # Windows パスを解釈できない (詳細は test_daily_pipeline.py の pytestmark 参照)。
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("curl") is None,
    reason="daily_pipeline smoke requires POSIX bash and curl",
)
def test_daily_pipeline_returns_nonzero_when_produce_fails_after_alert(tmp_path: Path) -> None:
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        """#!/usr/bin/env bash
echo "UV:$*" >&2
case "$*" in
  *"karyu_tech_news collect --post"*) exit 0 ;;
  *"karyu_tech_news draft --variant A --post"*) exit 0 ;;
  *"karyu_tech_news produce --engine irodori-tts-v3 --post"*) exit 7 ;;
  run\\ python\\ -\\ *) cat >/dev/null; echo "Discord failure alert: sent"; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    health = tmp_path / "health.txt"
    health.write_text("ok", encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "KARYU_PROJECT_DIR": str(tmp_path),
            "KARYU_UV": str(fake_uv),
            "KARYU_HEALTH_URL": health.as_uri(),
            "KARYU_IRODORI_DIR": str(tmp_path),
            # T55 (Issue #49): このテストは produce (fake uv) が実際に呼ばれることを前提と
            # するため、ホストマシンの実 swap/load に関わらず資源チェックを通過する安全な値を
            # 明示注入する (資源プリフライトそのものの契約テストは test_daily_pipeline.py 側)。
            "KARYU_SWAP_USED_MB": "500",
            "KARYU_LOAD_1MIN": "1",
        }
    )
    result = subprocess.run(
        ["bash", str(root / "scripts/daily_pipeline.sh")],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 7
    logs = sorted((tmp_path / "data" / "logs").glob("daily_*.log"))
    assert logs
    log_text = logs[-1].read_text(encoding="utf-8")
    assert "WARNING: produce 失敗 (rc=7)" in log_text
    assert "produce 失敗通知: 処理完了" in log_text
    assert "日次パイプライン終了 (rc=7" in log_text
