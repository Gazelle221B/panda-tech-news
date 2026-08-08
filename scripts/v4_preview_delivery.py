"""Irodori-TTS v4 プレビュー配信 (Issue #88).

プロダクトオーナー依頼「v4 の配信を Discord と YouTube で確認させてください」に応える
one-shot 配信スクリプト。**本番の v3 配信系には一切触れない** (daily_pipeline.sh /
episodes 出力 / state.db への書き込みを行わない、読み取り専用)。

処理の流れ:
1. 本番 DB から最新 (または指定) episode_draft の markdown を **SELECT のみ** で読む
   (`scripts/shadow_v4_run.py::load_latest_draft_markdown` と同じ経路)。
2. produce と同じ正規化 (二層読み辞書・トピック分割・文分割・短文マージ) で文セットを組む。
3. 各文について v3 (本番, port 8088) で合成して実測 duration を取得し、v4 (port 8089) を
   `irodori.seconds = v3実測 + 0.25s` に固定して合成する (Issue #88 の duration predictor
   短文過大予測対策。`scripts/shadow_v4_run.py` と同じ pinning 方式を流用)。
4. v4 音声のみを SFX トランジション付きで結合し、produce と同じ -16 LUFS 正規化で mp3 化する。
5. ASR (Whisper) で全文を測定してレポートに含めるが、**結果に関わらず配信は止めない**
   (fail-open。プレビュー目的であり、本番の ASR ゲートとは別物)。
6. produce/publish と同じ動画生成関数で mp4 化し、YouTube へ **unlisted 限定** でアップロード
   する (public 化 API は本スクリプトからは絶対に呼ばない)。
7. Discord Webhook に mp3 を添付投稿する (`deliver.discord.post_audio` を再利用。25MB 超は
   ビットレートを下げて再マスタリングする)。

**state.db への書き込みは一切行わない** (episode_drafts の SELECT のみ。audio_versions /
video_versions への INSERT はしない)。出力は `data/v4_preview/<run_id>/` 配下のみ。

使い方: `uv run --no-sync python scripts/v4_preview_delivery.py`
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import yaml
from sqlalchemy.orm import Session

from karyu_tech_news.config import load_settings
from karyu_tech_news.deliver.discord import post_audio
from karyu_tech_news.deliver.youtube import (
    YouTubeCredentials,
    YouTubeError,
    YouTubeUploadResult,
    refresh_access_token,
    upload_video,
)
from karyu_tech_news.mix.master import MasteringError, master_to_mp3
from karyu_tech_news.mix.mixer import find_bgm, mix_bgm
from karyu_tech_news.mix.transitions import concat_with_transitions
from karyu_tech_news.script.ruby import load_auto_readings
from karyu_tech_news.store.repo import create_db_engine, get_latest_episode_draft, init_db
from karyu_tech_news.store.schema import EpisodeDraft
from karyu_tech_news.tts.asr_gate import AsrUnavailableError, WhisperAsrBackend, verify_sentence
from karyu_tech_news.tts.irodori import IRODORI_DEFAULT_VOICE, IRODORI_MAX_CHARS, IRODORI_MODEL
from karyu_tech_news.tts.normalize import load_reading_dict, prepare_tts_text, split_markdown_topics
from karyu_tech_news.tts.quality import analyze_wav_signal
from karyu_tech_news.tts.synthesize import _merge_short_sentences, concat_wav, split_sentences
from karyu_tech_news.video.render import VideoRenderError, render_video

logger = logging.getLogger(__name__)

_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKTREE_ROOT = _SCRIPT_DIR.parent

# ---------- 既定値 ----------

ISSUE_NUMBER = 88
DEFAULT_SEED = 42
DEFAULT_SECONDS_MARGIN = 0.25  # Issue #88: v3 実測尺 + 0.25s を正とする (shadow と同一)
DEFAULT_MIN_SENTENCE_CHARS = 20  # Issue #88 推奨値 (短文の duration predictor 過大予測対策)
DEFAULT_V3_BASE_URL = "http://127.0.0.1:8088"
DEFAULT_V4_BASE_URL = "http://127.0.0.1:8089"
DEFAULT_V3_SERVER_DIR = Path.home() / "tools" / "Irodori-TTS-Server"
DEFAULT_V4_SERVER_DIR = Path.home() / "tools" / "Irodori-TTS-Server-v4"
DEFAULT_SYNTH_TIMEOUT_SECONDS = 1800.0
DEFAULT_SERVER_HEALTH_TIMEOUT_SECONDS = 180.0
DEFAULT_SERVER_HEALTH_POLL_SECONDS = 3.0
DEFAULT_WHISPER_MODEL = "turbo"
STOP_SERVER_TIMEOUT_SECONDS = 15.0
GIT_WORKTREE_LIST_TIMEOUT_SECONDS = 10.0
DISCORD_SAFE_LIMIT_BYTES = 20 * 1024 * 1024  # 25MB 上限に余裕を持たせた再マスタリング閾値
SHRINK_BITRATE = "128k"
YOUTUBE_TITLE_PREFIX = "【v4プレビュー】"
YOUTUBE_DISCLOSURE = (
    "IrodoriTTS v4 移行検討用のプレビュー (Issue #88)。本番配信ではありません。"
)
JST = timezone(timedelta(hours=9))


# ---------- shadow_v4_run.py の動的 import (T68 と同じサーバ起動/health 経路を再利用) ----------


def _load_shadow_module() -> ModuleType:
    """`scripts/shadow_v4_run.py` を動的 import する (`tests/test_shadow_v4_run.py` と同じ手法).

    scripts/ はパッケージ化されていないため importlib でファイルパスから読み込む。
    slots dataclass が `sys.modules[cls.__module__]` の存在を要求するため、
    `exec_module` 前に `sys.modules` へ登録する。
    """
    spec = importlib.util.spec_from_file_location(
        "shadow_v4_run", _SCRIPT_DIR / "shadow_v4_run.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------- 純ロジック (単体テスト対象) ----------


def detect_main_repo_dir(worktree_root: Path) -> Path | None:
    """`git worktree list --porcelain` の実行結果から main worktree のパスを引く.

    本スクリプトは worktree (`ptn-v4-preview` 等) から実行される想定で、本番 DB /
    reading_dict.auto.yaml / BGM 素材は main worktree の `data/`/`assets/` 配下にしか
    存在しない (git 非追跡)。呼び出し失敗時は None (呼び出し元が worktree_root 自身へ
    fail-open する)。
    """
    try:
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(worktree_root),
            capture_output=True,
            text=True,
            timeout=GIT_WORKTREE_LIST_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return parse_main_worktree_path(proc.stdout)


def parse_main_worktree_path(porcelain_output: str) -> Path | None:
    """`git worktree list --porcelain` 出力の先頭 `worktree ` 行 (= main worktree) を解く."""
    for line in porcelain_output.splitlines():
        if line.startswith("worktree "):
            path_str = line[len("worktree ") :].strip()
            return Path(path_str) if path_str else None
    return None


def build_run_id(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%S")


def build_output_paths(out_dir: Path, run_id: str) -> tuple[Path, Path, Path, Path]:
    """(episode_dir, mp3_path, mp4_path, report_path) を返す."""
    episode_dir = out_dir / run_id
    return (
        episode_dir,
        episode_dir / "v4_preview.mp3",
        episode_dir / "v4_preview.mp4",
        episode_dir / "report.json",
    )


def compute_v4_seconds(v3_duration_sec: float, margin: float) -> float:
    """v3 実測 duration + margin を v4 `irodori.seconds` へ丸める (Issue #88 pinning)."""
    return round(v3_duration_sec + margin, 3)


def build_youtube_title(base_title: str, date_str: str) -> str:
    """`【v4プレビュー】<タイトル> (<日付>)` を組む (sanitize_title は upload_video 側で適用)."""
    title = base_title.strip() or "華流テック通信"
    return f"{YOUTUBE_TITLE_PREFIX}{title} ({date_str})"


def build_youtube_description(date_str: str, sentence_count: int) -> str:
    return (
        f"{YOUTUBE_DISCLOSURE}\n"
        f"配信日: {date_str} JST\n"
        f"対象文数: {sentence_count}"
    )


def should_shrink_for_discord(
    size_bytes: int, limit_bytes: int = DISCORD_SAFE_LIMIT_BYTES
) -> bool:
    """mp3 が Discord 添付の安全域を超えていれば再マスタリング (ビットレート低下) が要るか."""
    return size_bytes > limit_bytes


def build_discord_summary(
    *,
    title: str,
    sentence_count: int,
    synthesized_count: int,
    skipped_count: int,
    asr_ok: int,
    asr_mismatch: int,
    asr_insertion: int,
    asr_unavailable: bool,
    duration_sec: float,
    youtube_url: str | None,
    youtube_error: str | None,
) -> str:
    """Discord 添付投稿の content 用サマリー (Issue #88 v4 プレビュー)."""
    lines = [
        f"🔬 IrodoriTTS v4 プレビュー: {title}",
        f"文数: {sentence_count} (合成成功 {synthesized_count} / skip {skipped_count})",
        f"尺: {duration_sec:.1f}s",
    ]
    if asr_unavailable:
        lines.append("ASR測定: 利用不可 (未導入, fail-open で配信続行)")
    else:
        lines.append(f"ASR測定: ok={asr_ok} mismatch={asr_mismatch} insertion={asr_insertion}")
    if youtube_url:
        lines.append(f"🎬 YouTube (unlisted): {youtube_url}")
    elif youtube_error:
        lines.append(f"⚠️ YouTube アップロード失敗: {youtube_error}")
    lines.append(f"詳細: Issue #{ISSUE_NUMBER}。本番配信ではありません。")
    return "\n".join(lines)


# ---------- 文セット構築 (produce と同じ正規化を流用) ----------


@dataclass(frozen=True, slots=True)
class PreviewSentence:
    """1 文 (トピック内の位置つき)."""

    text: str
    topic_idx: int
    sentence_idx: int

    @property
    def source_id(self) -> str:
        return f"topic-{self.topic_idx}:s{self.sentence_idx}"


def build_preview_sentences(
    markdown: str,
    reading_dict: dict[str, str],
    *,
    max_chars: int,
    min_sentence_chars: int,
) -> list[PreviewSentence]:
    """トピック境界ごとに文分割 (+ 短文マージ) する (produce の synthesize_script と同じ規則)."""
    items: list[PreviewSentence] = []
    for topic_idx, topic_text in enumerate(split_markdown_topics(markdown), start=1):
        normalized = prepare_tts_text(topic_text, reading_dict)
        sentences = split_sentences(normalized, max_chars)
        if min_sentence_chars > 0:
            sentences = _merge_short_sentences(sentences, min_sentence_chars, max_chars)
        for sent_idx, sentence in enumerate(sentences, start=1):
            items.append(
                PreviewSentence(text=sentence, topic_idx=topic_idx, sentence_idx=sent_idx)
            )
    return items


# ---------- レポート型 ----------


@dataclass(slots=True)
class SentenceReport:
    source_id: str
    text_len: int
    v3_duration_sec: float | None = None
    v4_seconds_requested: float | None = None
    asr_status: str | None = None  # "ok" | "mismatch" | "insertion" | None (未測定)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "text_len": self.text_len,
            "v3_duration_sec": self.v3_duration_sec,
            "v4_seconds_requested": self.v4_seconds_requested,
            "asr_status": self.asr_status,
            "error": self.error,
        }


@dataclass(slots=True)
class EpisodeReport:
    run_id: str
    draft_id: int
    title: str
    started_at: datetime
    finished_at: datetime | None = None
    sentence_reports: list[SentenceReport] = field(default_factory=list)
    asr_available: bool = True
    mp3_path: str | None = None
    mp3_duration_sec: float | None = None
    mp3_size_bytes: int | None = None
    mp3_lufs: float | None = None
    mp4_path: str | None = None
    youtube_video_id: str | None = None
    youtube_url: str | None = None
    youtube_privacy_status: str | None = None
    youtube_error: str | None = None
    discord_posted: bool | None = None

    def synthesized_count(self) -> int:
        return sum(1 for r in self.sentence_reports if r.error is None)

    def skipped_count(self) -> int:
        return sum(1 for r in self.sentence_reports if r.error is not None)

    def asr_counts(self) -> dict[str, int]:
        counts = {"ok": 0, "mismatch": 0, "insertion": 0}
        for r in self.sentence_reports:
            if r.asr_status in counts:
                counts[r.asr_status] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "draft_id": self.draft_id,
            "title": self.title,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "sentence_count": len(self.sentence_reports),
            "synthesized_count": self.synthesized_count(),
            "skipped_count": self.skipped_count(),
            "asr_available": self.asr_available,
            "asr_counts": self.asr_counts(),
            "mp3_path": self.mp3_path,
            "mp3_duration_sec": self.mp3_duration_sec,
            "mp3_size_bytes": self.mp3_size_bytes,
            "mp3_lufs": self.mp3_lufs,
            "mp4_path": self.mp4_path,
            "youtube_video_id": self.youtube_video_id,
            "youtube_url": self.youtube_url,
            "youtube_privacy_status": self.youtube_privacy_status,
            "youtube_error": self.youtube_error,
            "discord_posted": self.discord_posted,
            "sentences": [r.to_dict() for r in self.sentence_reports],
        }


# ---------- DB 読み取り (SELECT のみ) ----------


def load_target_draft(db_path: Path, draft_id: int | None) -> EpisodeDraft | None:
    """本番 DB から対象 episode_draft を読み取り専用で取得する (書き込み一切なし)."""
    engine = create_db_engine(db_path)
    init_db(engine)  # CREATE TABLE IF NOT EXISTS のみ (冪等・データ変更なし)
    with Session(engine) as session:
        if draft_id is not None:
            draft = session.get(EpisodeDraft, draft_id)
        else:
            draft = get_latest_episode_draft(session)
        if draft is None:
            return None
        session.expunge(draft)  # session close 後も属性アクセスできるようにする
        return draft


# ---------- 文単位処理 (実サーバ依存) ----------


def process_preview_sentence(
    item: PreviewSentence,
    *,
    client: httpx.Client,
    synthesize_wav: Any,
    analyze_wav_signal_fn: Any,
    v3_base_url: str,
    v4_base_url: str,
    voice: str,
    model: str,
    seed: int,
    seconds_margin: float,
    synth_timeout: float,
    whisper_backend: Any | None,
) -> tuple[SentenceReport, bytes | None]:
    """1 文の v3 実測→v4 pinning 合成→(可能なら) ASR 測定を行う (fail-open, Issue #88)."""
    report = SentenceReport(source_id=item.source_id, text_len=len(item.text))
    try:
        v3_audio = synthesize_wav(
            client,
            v3_base_url,
            item.text,
            voice=voice,
            model=model,
            irodori_options={"seed": seed},
            timeout=synth_timeout,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        report.error = f"v3合成失敗: {type(exc).__name__}: {exc}"
        return report, None

    v3_signal = analyze_wav_signal_fn(v3_audio)
    if not v3_signal.valid_wav:
        report.error = "v3応答が不正なwav"
        return report, None
    report.v3_duration_sec = v3_signal.duration_sec

    v4_seconds = compute_v4_seconds(v3_signal.duration_sec, seconds_margin)
    report.v4_seconds_requested = v4_seconds
    try:
        v4_audio = synthesize_wav(
            client,
            v4_base_url,
            item.text,
            voice=voice,
            model=model,
            irodori_options={"seconds": v4_seconds, "seed": seed},
            timeout=synth_timeout,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        report.error = f"v4合成失敗: {type(exc).__name__}: {exc}"
        return report, None

    v4_signal = analyze_wav_signal_fn(v4_audio)
    if not v4_signal.valid_wav or not v4_signal.has_pcm_signal:
        report.error = "v4応答が不正/無音なwav"
        return report, None

    if whisper_backend is not None:
        try:
            transcript = whisper_backend.transcribe(v4_audio)
            verdict = verify_sentence(item.text, transcript, judge=None)
            report.asr_status = verdict.status
        except AsrUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — ASR 内部失敗はこの文だけ fail-open (測定のみ)
            logger.warning("ASR 測定失敗 (fail-open, 配信は続行): %s", exc)

    return report, v4_audio


# ---------- SFX 設定読み込み (produce の show_format 読み込みと同じ流儀) ----------


def load_sfx_paths(show_format_file: Path) -> tuple[Path | None, Path | None, Path | None]:
    """`sfx.enabled` のときだけ transition/opening/ending の実パスを返す (fail-open)."""
    if not show_format_file.exists():
        return None, None, None
    try:
        cfg = yaml.safe_load(show_format_file.read_text(encoding="utf-8")) or {}
        sfx_cfg = cfg.get("sfx") or {}
        if not bool(sfx_cfg.get("enabled", False)):
            return None, None, None

        def _resolve(key: str) -> Path | None:
            value = sfx_cfg.get(key)
            if not value:
                return None
            candidate = Path(str(value))
            return candidate if candidate.exists() else None

        return _resolve("transition"), _resolve("opening"), _resolve("ending")
    except Exception as exc:  # noqa: BLE001
        logger.warning("show_format 読み込み失敗 (SFX なしで続行): %s", exc)
        return None, None, None


# ---------- サーバ lifecycle ----------


@dataclass
class ServerHandle:
    proc: Any | None  # subprocess.Popen | None (このジョブが起動した場合のみ非 None)
    base_url: str


def ensure_server(
    shadow: ModuleType,
    client: httpx.Client,
    *,
    base_url: str,
    server_dir: Path,
    host: str,
    port: int,
    log_path: Path,
    health_timeout: float,
    health_poll: float,
) -> ServerHandle:
    """health OK ならそのまま利用、down なら起動して health を待つ (shadow_v4_run と同じ流儀)."""
    if shadow.is_server_healthy(client, base_url, require_loaded=True):
        logger.info("サーバ: 既に稼働中 (既存を利用) — %s", base_url)
        return ServerHandle(proc=None, base_url=base_url)
    logger.info("サーバ: 未起動 → 起動 — %s", base_url)
    proc = shadow.start_v4_server(server_dir, host=host, port=port, log_path=log_path)
    if not shadow.wait_for_health(
        client,
        base_url,
        timeout_sec=health_timeout,
        poll_interval_sec=health_poll,
        require_loaded=True,
    ):
        stop_server_tree(proc)
        raise RuntimeError(f"サーバが health に到達せず: {base_url}")
    return ServerHandle(proc=proc, base_url=base_url)


def stop_server_tree(proc: Any) -> None:
    """このジョブが起動した Irodori サーバプロセスをプロセスツリーごと確実に停止する.

    実運用 (2026-08-08 v4 プレビュー配信初回実行) で、`shadow_v4_run.py::stop_v4_server`
    (= `proc.terminate()` → `wait()`) を呼んでログ上は「サーバ停止」と記録されたにも
    関わらず、実際には両サーバ (port 8088/8089) のプロセスがポートを占有したまま残存する
    実害が発生した (人間が PID を直接 kill して復旧)。

    原因は Windows の `execve` 非対応: `subprocess.Popen(["uv","run","--no-sync",
    "python","-m","irodori_openai_tts",...])` は POSIX では uv がプロセスを exec 置換
    するため Popen の PID = 実サーバの PID になるが、Windows では uv.exe が python.exe を
    **子プロセスとして** 起動するほかない。`Popen.terminate()` は直接の子 (uv.exe) にしか
    シグナルが届かず、実際にポートを listen している python.exe (孫プロセス) が孤児として
    残る。Issue #98 (swap 枯渇) の一因が常駐 Irodori プロセスである以上、看過できないため
    Windows では `taskkill /T /F` でプロセスツリー全体を終了させる。POSIX は
    `proc.terminate()`→`wait()`→(タイムアウトなら)`proc.kill()` の従来どおりの経路を使う
    (プロセスグループの扱いが異なり taskkill 相当の道具がないため)。
    """
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            timeout=STOP_SERVER_TIMEOUT_SECONDS,
            check=False,
        )
        try:
            proc.wait(timeout=STOP_SERVER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            logger.warning("taskkill 後もプロセス終了を確認できません (PID=%s)", proc.pid)
        return
    proc.terminate()
    try:
        proc.wait(timeout=STOP_SERVER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=STOP_SERVER_TIMEOUT_SECONDS)


def stop_started_servers(handles: list[ServerHandle]) -> None:
    """このジョブが起動したサーバのみ停止する (Issue #98 の swap 枯渇対策、放置禁止)."""
    for handle in handles:
        if handle.proc is not None:
            logger.info("サーバ停止: %s", handle.base_url)
            stop_server_tree(handle.proc)


# ---------- CLI ----------


def build_arg_parser() -> argparse.ArgumentParser:
    default_main_repo = detect_main_repo_dir(_WORKTREE_ROOT) or _WORKTREE_ROOT

    parser = argparse.ArgumentParser(
        description="IrodoriTTS v4 プレビュー配信 (Discord mp3 添付 + YouTube unlisted, Issue #88)"
    )
    parser.add_argument(
        "--db-path", type=Path, default=default_main_repo / "data" / "state.db",
        help="本番 SQLite DB (読み取り専用)",
    )
    parser.add_argument("--draft-id", type=int, default=None, help="対象 episode_draft の id (未指定で最新)")
    parser.add_argument(
        "--reading-dict", type=Path, default=_WORKTREE_ROOT / "config" / "reading_dict.yaml"
    )
    parser.add_argument(
        "--auto-reading-dict",
        type=Path,
        default=default_main_repo / "data" / "reading_dict.auto.yaml",
    )
    parser.add_argument(
        "--show-format-file", type=Path, default=_WORKTREE_ROOT / "config" / "show_format.yaml"
    )
    parser.add_argument("--bgm-dir", type=Path, default=default_main_repo / "assets" / "bgm")
    parser.add_argument("--logo-file", type=Path, default=_WORKTREE_ROOT / "assets" / "logo.png")
    parser.add_argument("--out-dir", type=Path, default=_WORKTREE_ROOT / "data" / "v4_preview")
    parser.add_argument("--env-file", type=Path, default=default_main_repo / ".env")

    parser.add_argument("--v3-server-dir", type=Path, default=DEFAULT_V3_SERVER_DIR)
    parser.add_argument("--v3-base-url", default=DEFAULT_V3_BASE_URL)
    parser.add_argument("--v3-host", default="127.0.0.1")
    parser.add_argument("--v3-port", type=int, default=8088)

    parser.add_argument("--v4-server-dir", type=Path, default=DEFAULT_V4_SERVER_DIR)
    parser.add_argument("--v4-base-url", default=DEFAULT_V4_BASE_URL)
    parser.add_argument("--v4-host", default="127.0.0.1")
    parser.add_argument("--v4-port", type=int, default=8089)

    parser.add_argument(
        "--server-health-timeout-sec", type=float, default=DEFAULT_SERVER_HEALTH_TIMEOUT_SECONDS
    )
    parser.add_argument(
        "--server-health-poll-sec", type=float, default=DEFAULT_SERVER_HEALTH_POLL_SECONDS
    )

    parser.add_argument("--voice", default=IRODORI_DEFAULT_VOICE)
    parser.add_argument("--model", default=IRODORI_MODEL)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--seconds-margin", type=float, default=DEFAULT_SECONDS_MARGIN)
    parser.add_argument("--min-sentence-chars", type=int, default=DEFAULT_MIN_SENTENCE_CHARS)
    parser.add_argument("--max-chars", type=int, default=IRODORI_MAX_CHARS)
    parser.add_argument("--synth-timeout-sec", type=float, default=DEFAULT_SYNTH_TIMEOUT_SECONDS)
    parser.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL)

    parser.add_argument("--skip-video", action="store_true", help="mp4 生成をスキップ")
    parser.add_argument("--skip-youtube", action="store_true", help="YouTube アップロードをスキップ")
    parser.add_argument("--skip-discord", action="store_true", help="Discord 投稿をスキップ")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="mp3/mp4 は生成するが YouTube アップロード・Discord 投稿はしない",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    shadow = _load_shadow_module()

    now = datetime.now(UTC)
    run_id = build_run_id(now)
    episode_dir, mp3_path, mp4_path, report_path = build_output_paths(args.out_dir, run_id)
    episode_dir.mkdir(parents=True, exist_ok=True)

    draft = load_target_draft(args.db_path, args.draft_id)
    if draft is None:
        logger.error("対象の episode_draft がありません (db_path=%s)", args.db_path)
        return 1
    draft_id = int(draft.id)
    title = str(draft.title)
    markdown = str(draft.markdown)
    logger.info("対象 draft: id=%d title=%s", draft_id, title)

    manual_reading_dict = load_reading_dict(args.reading_dict) if args.reading_dict.exists() else {}
    auto_reading_dict = load_auto_readings(args.auto_reading_dict)
    reading_dict = {**auto_reading_dict, **manual_reading_dict}

    sentences = build_preview_sentences(
        markdown, reading_dict, max_chars=args.max_chars, min_sentence_chars=args.min_sentence_chars
    )
    logger.info("文セット構築: %d 文", len(sentences))

    report = EpisodeReport(run_id=run_id, draft_id=draft_id, title=title, started_at=now)

    handles: list[ServerHandle] = []
    topic_wavs: list[bytes] = []
    current_topic = None
    topic_chunks: list[bytes] = []

    with httpx.Client() as client:
        try:
            v3_handle = ensure_server(
                shadow, client,
                base_url=args.v3_base_url, server_dir=args.v3_server_dir,
                host=args.v3_host, port=args.v3_port,
                log_path=episode_dir / "v3_server.log",
                health_timeout=args.server_health_timeout_sec,
                health_poll=args.server_health_poll_sec,
            )
            handles.append(v3_handle)
            v4_handle = ensure_server(
                shadow, client,
                base_url=args.v4_base_url, server_dir=args.v4_server_dir,
                host=args.v4_host, port=args.v4_port,
                log_path=episode_dir / "v4_server.log",
                health_timeout=args.server_health_timeout_sec,
                health_poll=args.server_health_poll_sec,
            )
            handles.append(v4_handle)
        except RuntimeError as exc:
            logger.error("サーバ起動に失敗、プレビュー配信を中断します: %s", exc)
            stop_started_servers(handles)
            return 1

        whisper_backend: Any | None = WhisperAsrBackend(args.whisper_model)
        asr_unavailable_logged = False
        try:
            for item in sentences:
                if current_topic != item.topic_idx:
                    if topic_chunks:
                        topic_wavs.append(concat_wav(topic_chunks))
                    topic_chunks = []
                    current_topic = item.topic_idx
                try:
                    sent_report, audio = process_preview_sentence(
                        item,
                        client=client,
                        synthesize_wav=shadow.synthesize_wav,
                        analyze_wav_signal_fn=analyze_wav_signal,
                        v3_base_url=args.v3_base_url,
                        v4_base_url=args.v4_base_url,
                        voice=args.voice,
                        model=args.model,
                        seed=args.seed,
                        seconds_margin=args.seconds_margin,
                        synth_timeout=args.synth_timeout_sec,
                        whisper_backend=whisper_backend,
                    )
                except AsrUnavailableError as exc:
                    if not asr_unavailable_logged:
                        logger.warning(
                            "ASR バックエンド利用不可、以降は測定なしで続行 (fail-open): %s", exc
                        )
                        asr_unavailable_logged = True
                        report.asr_available = False
                    whisper_backend = None
                    sent_report, audio = process_preview_sentence(
                        item,
                        client=client,
                        synthesize_wav=shadow.synthesize_wav,
                        analyze_wav_signal_fn=analyze_wav_signal,
                        v3_base_url=args.v3_base_url,
                        v4_base_url=args.v4_base_url,
                        voice=args.voice,
                        model=args.model,
                        seed=args.seed,
                        seconds_margin=args.seconds_margin,
                        synth_timeout=args.synth_timeout_sec,
                        whisper_backend=None,
                    )
                report.sentence_reports.append(sent_report)
                if audio is not None:
                    topic_chunks.append(audio)
                else:
                    logger.warning("文をskip (fail-open): %s (%s)", item.source_id, sent_report.error)
            if topic_chunks:
                topic_wavs.append(concat_wav(topic_chunks))
        finally:
            # Issue #98 (swap 枯渇疑惑) 対策: 音声合成が終わり次第、起動したサーバを即座に停止する。
            stop_started_servers(handles)

    if not topic_wavs or report.synthesized_count() == 0:
        logger.error("合成成功文が 0 件です。プレビュー配信を中止します。")
        report.finished_at = datetime.now(UTC)
        report_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 1

    transition_path, opening_path, ending_path = load_sfx_paths(args.show_format_file)
    combined_audio = concat_with_transitions(
        topic_wavs, transition_path=transition_path, opening_path=opening_path, ending_path=ending_path
    )
    mixed = mix_bgm(combined_audio, bgm_path=find_bgm(args.bgm_dir))

    try:
        mastering = master_to_mp3(mixed, mp3_path)
    except MasteringError as exc:
        logger.error("マスタリング失敗: %s", exc)
        return 1
    logger.info(
        "mp3 生成: %s (%.1fs, %.1f LUFS, %d bytes)",
        mastering.path, mastering.duration_sec, mastering.measured_lufs, mp3_path.stat().st_size,
    )

    if should_shrink_for_discord(mp3_path.stat().st_size):
        logger.info("mp3 が Discord 安全域を超過、ビットレート %s で再マスタリング", SHRINK_BITRATE)
        try:
            mastering = master_to_mp3(mixed, mp3_path, bitrate=SHRINK_BITRATE)
        except MasteringError as exc:
            logger.warning("再マスタリング失敗 (元 mp3 のまま続行, fail-open): %s", exc)

    report.mp3_path = str(mp3_path)
    report.mp3_duration_sec = mastering.duration_sec
    report.mp3_size_bytes = mp3_path.stat().st_size
    report.mp3_lufs = mastering.measured_lufs

    if not args.skip_video:
        try:
            video = render_video(mp3_path, mp4_path, logo_path=args.logo_file)
            report.mp4_path = video.path
            logger.info("mp4 生成: %s (%.1fMB)", video.path, video.size_bytes / 1024 / 1024)
        except VideoRenderError as exc:
            logger.error("動画生成失敗 (YouTube アップロードはスキップ): %s", exc)

    settings = load_settings(args.env_file)
    date_str = now.astimezone(JST).strftime("%Y-%m-%d")

    if not args.dry_run and not args.skip_youtube and report.mp4_path:
        try:
            creds = YouTubeCredentials.from_env()
            token = refresh_access_token(creds)
            yt_title = build_youtube_title(title, date_str)
            yt_description = build_youtube_description(date_str, len(sentences))
            result: YouTubeUploadResult = upload_video(
                token, Path(report.mp4_path),
                title=yt_title, description=yt_description, privacy="unlisted",
            )
            report.youtube_video_id = result.video_id
            report.youtube_url = result.url
            report.youtube_privacy_status = result.privacy_status
            logger.info("YouTube アップロード成功 (%s): %s", result.privacy_status, result.url)
        except YouTubeError as exc:
            report.youtube_error = str(exc)
            logger.error("YouTube アップロード失敗 (fail-open, Discord 投稿は継続): %s", exc)

    if not args.dry_run and not args.skip_discord:
        asr_counts = report.asr_counts()
        summary = build_discord_summary(
            title=title,
            sentence_count=len(sentences),
            synthesized_count=report.synthesized_count(),
            skipped_count=report.skipped_count(),
            asr_ok=asr_counts["ok"],
            asr_mismatch=asr_counts["mismatch"],
            asr_insertion=asr_counts["insertion"],
            asr_unavailable=not report.asr_available,
            duration_sec=mastering.duration_sec,
            youtube_url=report.youtube_url,
            youtube_error=report.youtube_error,
        )
        ok = post_audio(settings.discord_webhook_url, mp3_path, content=summary)
        report.discord_posted = ok
        logger.info("Discord 投稿: %s", "成功" if ok else "失敗 (fail-open)")

    report.finished_at = datetime.now(UTC)
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("レポート出力: %s", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
