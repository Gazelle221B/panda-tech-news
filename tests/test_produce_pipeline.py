"""T29 mixer / T31 produce パイプラインのユニットテスト (Sprint 2).

TTS は mock エンジン、Discord は httpx モック。ffmpeg 依存の produce 統合は skipif。
"""
from __future__ import annotations

import io
import shutil
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
            lufs=None,  # 無音 fail-open は測定不能 → NULL
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
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "err", request=MagicMock(), response=MagicMock(status_code=500)
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
    assert (tmp_path / "episodes" / "episode_1.mp3").exists()


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
        "智谱が、コード生成特化モデルを公開します。\n"
    )
    out = strip_markdown_structure(md)
    assert "智谱：GLM-5.2将面向" not in out  # 中国語原文タイトル (見出し) は読まない
    assert "生成日時" not in out  # ビルドメタは読まない
    assert not out.lstrip().startswith("#")
    assert "本日のHAL Daily Briefingです" in out  # 日本語ナレーションは残る
    assert "コード生成特化モデルを公開します" in out
