"""scripts/v4_preview_delivery.py のユニットテスト (Issue #88 v4 プレビュー配信).

サーバ実体 (Irodori v3/v4)・DB・YouTube/Discord への実 I/O に依存しない純ロジックのみを
対象にする: worktree 解決、run_id/出力パス組み立て、v4 `seconds` pinning 計算、
YouTube タイトル/説明文組み立て、Discord サマリー組み立て、Discord 添付サイズ判定、
文セット構築 (produce と同じ正規化規則)、レポート集計。

`scripts/` はパッケージ化されていないため、`tests/test_shadow_v4_run.py` と同じ流儀で
importlib によりファイルパスから動的 import する。
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _ROOT / "scripts" / "v4_preview_delivery.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("v4_preview_delivery", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # slots dataclass の解決に必須 (Python 3.12)
    spec.loader.exec_module(module)
    return module


v4pd = _load_module()


# ---------- parse_main_worktree_path ----------


def test_parse_main_worktree_path_returns_first_worktree_entry() -> None:
    porcelain = (
        "worktree /repo/main\n"
        "HEAD abc123\n"
        "branch refs/heads/main\n"
        "\n"
        "worktree /repo/.claude/worktrees/feature\n"
        "HEAD def456\n"
        "branch refs/heads/feat/x\n"
    )
    assert v4pd.parse_main_worktree_path(porcelain) == Path("/repo/main")


def test_parse_main_worktree_path_empty_output_returns_none() -> None:
    assert v4pd.parse_main_worktree_path("") is None


def test_parse_main_worktree_path_no_worktree_line_returns_none() -> None:
    assert v4pd.parse_main_worktree_path("HEAD abc123\nbranch refs/heads/main\n") is None


# ---------- build_run_id / build_output_paths ----------


def test_build_run_id_format() -> None:
    now = datetime(2026, 8, 9, 12, 34, 56, tzinfo=UTC)
    assert v4pd.build_run_id(now) == "20260809_123456"


def test_build_output_paths_layout() -> None:
    out_dir = Path("data/v4_preview")
    episode_dir, mp3, mp4, report = v4pd.build_output_paths(out_dir, "20260809_123456")
    assert episode_dir == out_dir / "20260809_123456"
    assert mp3 == episode_dir / "v4_preview.mp3"
    assert mp4 == episode_dir / "v4_preview.mp4"
    assert report == episode_dir / "report.json"


# ---------- compute_v4_seconds (Issue #88 pinning) ----------


def test_compute_v4_seconds_adds_margin_and_rounds() -> None:
    assert v4pd.compute_v4_seconds(3.14159, 0.25) == 3.392


def test_compute_v4_seconds_zero_margin() -> None:
    assert v4pd.compute_v4_seconds(2.0, 0.0) == 2.0


# ---------- YouTube title/description ----------


def test_build_youtube_title_has_prefix_and_date() -> None:
    title = v4pd.build_youtube_title("華流テック通信 2026-08-07", "2026-08-09")
    assert title.startswith("【v4プレビュー】")
    assert "2026-08-09" in title
    assert "華流テック通信 2026-08-07" in title


def test_build_youtube_title_blank_falls_back_to_show_name() -> None:
    title = v4pd.build_youtube_title("   ", "2026-08-09")
    assert "華流テック通信" in title


def test_build_youtube_description_mentions_issue_and_preview_disclosure() -> None:
    desc = v4pd.build_youtube_description("2026-08-09", 42)
    assert "Issue #88" in desc
    assert "本番配信ではありません" in desc
    assert "2026-08-09" in desc
    assert "42" in desc


# ---------- should_shrink_for_discord ----------


def test_should_shrink_for_discord_under_limit() -> None:
    assert v4pd.should_shrink_for_discord(1_000, limit_bytes=20_000_000) is False


def test_should_shrink_for_discord_over_limit() -> None:
    assert v4pd.should_shrink_for_discord(21_000_000, limit_bytes=20_000_000) is True


def test_should_shrink_for_discord_uses_default_limit() -> None:
    assert v4pd.should_shrink_for_discord(30 * 1024 * 1024) is True
    assert v4pd.should_shrink_for_discord(1 * 1024 * 1024) is False


# ---------- build_discord_summary ----------


def test_build_discord_summary_includes_youtube_link() -> None:
    summary = v4pd.build_discord_summary(
        title="華流テック通信 2026-08-07",
        sentence_count=25,
        synthesized_count=24,
        skipped_count=1,
        asr_ok=20,
        asr_mismatch=3,
        asr_insertion=1,
        asr_unavailable=False,
        duration_sec=240.5,
        youtube_url="https://www.youtube.com/watch?v=abc123",
        youtube_error=None,
    )
    assert "華流テック通信 2026-08-07" in summary
    assert "25" in summary and "24" in summary and "1" in summary
    assert "ok=20" in summary
    assert "mismatch=3" in summary
    assert "insertion=1" in summary
    assert "https://www.youtube.com/watch?v=abc123" in summary
    assert "Issue #88" in summary
    assert "本番配信ではありません" in summary


def test_build_discord_summary_asr_unavailable_notes_it() -> None:
    summary = v4pd.build_discord_summary(
        title="t", sentence_count=1, synthesized_count=1, skipped_count=0,
        asr_ok=0, asr_mismatch=0, asr_insertion=0, asr_unavailable=True,
        duration_sec=1.0, youtube_url=None, youtube_error=None,
    )
    assert "ASR測定: 利用不可" in summary
    assert "ok=" not in summary


def test_build_discord_summary_youtube_error_shown_when_no_url() -> None:
    summary = v4pd.build_discord_summary(
        title="t", sentence_count=1, synthesized_count=1, skipped_count=0,
        asr_ok=1, asr_mismatch=0, asr_insertion=0, asr_unavailable=False,
        duration_sec=1.0, youtube_url=None, youtube_error="HTTP 403",
    )
    assert "YouTube アップロード失敗" in summary
    assert "HTTP 403" in summary


# ---------- build_preview_sentences (produce と同じ正規化) ----------


def test_build_preview_sentences_splits_by_topic_and_sentence() -> None:
    markdown = "## 1. トピックA\n本文Aです。続きです。\n\n## 2. トピックB\n本文Bです。"
    items = v4pd.build_preview_sentences(markdown, {}, max_chars=2000, min_sentence_chars=0)
    topic_indices = {item.topic_idx for item in items}
    assert topic_indices == {1, 2}
    texts = [item.text for item in items]
    assert "本文Aです。" in texts
    assert "続きです。" in texts
    assert "本文Bです。" in texts


def test_build_preview_sentences_source_id_encodes_topic_and_sentence() -> None:
    markdown = "## 1. トピックA\n一文目です。"
    items = v4pd.build_preview_sentences(markdown, {}, max_chars=2000, min_sentence_chars=0)
    assert items[0].source_id == "topic-1:s1"


def test_build_preview_sentences_merges_short_sentences_when_enabled() -> None:
    markdown = "## 1. トピックA\n短い。とても短い文が続く場合はマージされる想定です。"
    without_merge = v4pd.build_preview_sentences(
        markdown, {}, max_chars=2000, min_sentence_chars=0
    )
    with_merge = v4pd.build_preview_sentences(
        markdown, {}, max_chars=2000, min_sentence_chars=20
    )
    assert len(with_merge) <= len(without_merge)


# ---------- SentenceReport / EpisodeReport 集計 ----------


def test_sentence_report_to_dict_roundtrip() -> None:
    report = v4pd.SentenceReport(
        source_id="topic-1:s1", text_len=10, v3_duration_sec=1.5,
        v4_seconds_requested=1.75, asr_status="ok", error=None,
    )
    d = report.to_dict()
    assert d["source_id"] == "topic-1:s1"
    assert d["v4_seconds_requested"] == 1.75
    assert d["asr_status"] == "ok"


def test_episode_report_counts_synthesized_and_skipped() -> None:
    report = v4pd.EpisodeReport(
        run_id="r1", draft_id=1, title="t", started_at=datetime(2026, 8, 9, tzinfo=UTC)
    )
    report.sentence_reports = [
        v4pd.SentenceReport(source_id="s1", text_len=1, error=None, asr_status="ok"),
        v4pd.SentenceReport(source_id="s2", text_len=1, error=None, asr_status="mismatch"),
        v4pd.SentenceReport(source_id="s3", text_len=1, error="v3合成失敗: boom"),
    ]
    assert report.synthesized_count() == 2
    assert report.skipped_count() == 1
    counts = report.asr_counts()
    assert counts == {"ok": 1, "mismatch": 1, "insertion": 0}


def test_episode_report_to_dict_contains_summary_fields() -> None:
    report = v4pd.EpisodeReport(
        run_id="r1", draft_id=12, title="t", started_at=datetime(2026, 8, 9, tzinfo=UTC)
    )
    report.sentence_reports = [
        v4pd.SentenceReport(source_id="s1", text_len=1, error=None, asr_status="ok"),
    ]
    report.mp3_path = "data/v4_preview/r1/v4_preview.mp3"
    report.youtube_url = "https://www.youtube.com/watch?v=abc"
    d = report.to_dict()
    assert d["draft_id"] == 12
    assert d["sentence_count"] == 1
    assert d["synthesized_count"] == 1
    assert d["mp3_path"] == "data/v4_preview/r1/v4_preview.mp3"
    assert d["youtube_url"] == "https://www.youtube.com/watch?v=abc"
    assert len(d["sentences"]) == 1


# ---------- stop_server_tree (Windows プロセスツリー kill バグの回帰テスト) ----------
#
# 2026-08-08 の初回実行で、`shadow_v4_run.py::stop_v4_server` (terminate()→wait()) を
# 呼んでログ上は「サーバ停止」と記録されたにも関わらず、Windows では `uv run python -m
# irodori_openai_tts` の実体プロセス (孫プロセス) が孤児として残存する実害が発生した。
# `stop_server_tree` は Windows なら `taskkill /T /F` でプロセスツリーごと終了させる。


class _FakeProc:
    """`subprocess.Popen` の代わりに poll/pid/terminate/wait/kill だけを差し替える fake."""

    def __init__(self, *, alive_after_terminate: bool = False) -> None:
        self.pid = 4321
        self.terminated = False
        self.killed = False
        self._alive_after_terminate = alive_after_terminate
        self._polled_after_terminate = False

    def poll(self) -> int | None:
        if not self.terminated:
            return None  # まだ稼働中
        if self._alive_after_terminate and not self._polled_after_terminate:
            return None
        return 0

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self._polled_after_terminate = True

    def wait(self, timeout: float | None = None) -> int:
        if self._alive_after_terminate and not self.killed:
            import subprocess

            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 0)
        return 0


def test_stop_server_tree_already_exited_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = _FakeProc()
    proc.terminated = True  # poll() が None でない (= 既に終了済み) を模す

    called = {"run": False}

    def _fake_run(*args: object, **kwargs: object) -> None:
        called["run"] = True

    monkeypatch.setattr(v4pd.subprocess, "run", _fake_run)
    v4pd.stop_server_tree(proc)
    assert called["run"] is False  # 既に終了済みなら taskkill/terminate を呼ばない


def test_stop_server_tree_windows_uses_taskkill_with_tree_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proc = _FakeProc()
    captured: dict[str, object] = {}

    def _fake_run(cmd: list[str], **kwargs: object) -> None:
        captured["cmd"] = cmd

    monkeypatch.setattr(v4pd.os, "name", "nt")
    monkeypatch.setattr(v4pd.subprocess, "run", _fake_run)
    v4pd.stop_server_tree(proc)

    assert captured["cmd"] == ["taskkill", "/F", "/T", "/PID", "4321"]
    assert proc.terminated is False  # Windows 経路では Popen.terminate() を使わない


def test_stop_server_tree_posix_uses_terminate_not_taskkill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proc = _FakeProc()

    def _fail_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("POSIX 経路で taskkill (subprocess.run) を呼んではならない")

    monkeypatch.setattr(v4pd.os, "name", "posix")
    monkeypatch.setattr(v4pd.subprocess, "run", _fail_run)
    v4pd.stop_server_tree(proc)

    assert proc.terminated is True


def test_stop_server_tree_posix_kills_after_terminate_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proc = _FakeProc(alive_after_terminate=True)
    monkeypatch.setattr(v4pd.os, "name", "posix")
    v4pd.stop_server_tree(proc)
    assert proc.terminated is True
    assert proc.killed is True


def test_stop_started_servers_only_stops_handles_this_job_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stopped: list[int] = []
    monkeypatch.setattr(
        v4pd, "stop_server_tree", lambda proc: stopped.append(proc.pid)
    )
    started_proc = _FakeProc()
    handles = [
        v4pd.ServerHandle(proc=started_proc, base_url="http://127.0.0.1:8089"),
        v4pd.ServerHandle(proc=None, base_url="http://127.0.0.1:8088"),  # 既存稼働中を再利用
    ]
    v4pd.stop_started_servers(handles)
    assert stopped == [started_proc.pid]  # 既存稼働中 (proc=None) は停止対象外


# ---------- detect_main_repo_dir (subprocess 経由。失敗時の fail-open のみ確認) ----------


def test_detect_main_repo_dir_returns_none_for_nonexistent_dir(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert v4pd.detect_main_repo_dir(missing) is None


@pytest.mark.parametrize("bad_input", ["", "not a git repo", "worktree \n"])
def test_parse_main_worktree_path_handles_malformed_input(bad_input: str) -> None:
    # 空パスの worktree 行は None (呼び出し元が fail-open する)
    assert v4pd.parse_main_worktree_path(bad_input) is None
