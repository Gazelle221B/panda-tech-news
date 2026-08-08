"""Irodori-TTS v4 シャドーランナー (T68, Issue #91 / v4 移行トラック Phase 2-b).

Issue #88 の P0 診断で、v4 短文幻話の根本原因は duration predictor の短文過大予測と
確定し、`irodori.seconds` 固定で解消することを実証済み。本番 (v3, port 8088) は
無停止・無変更のまま、当日の実台本 + 固定回帰セットをシャドー (v4, port 8089) で
毎日レンダリングし、三層測定でメトリクスを蓄積する (15 運用+600/300 文の昇格判定用)。

設計方針:
- **本番 DB・config・音声には一切書き込まない** (AGENTS.md §3)。episode_drafts の
  SELECT のみ行う。v4 シャドーサーバのディレクトリ (`~/tools/Irodori-TTS-Server-v4`)
  も起動コマンドを叩くだけで、ファイルは変更しない。
- **fail-open**: v4 サーバ起動失敗・個別文の合成/書き起こし失敗は記録して続行する。
  例外は (a) v3 (本番, 実測尺の供給源) の health 不在 = 即 abort、(b) ASR バックエンド
  自体が利用不可 (`AsrUnavailableError`) = 全文が同じ理由で失敗するため即 abort。
- **engine 抽象を経由しない**: per-request の irodori オプション制御 (seconds/seed) が
  主目的のため、`tts/irodori.py` の `IrodoriTTSEngine` は使わず直接 httpx で
  `POST /v1/audio/speech` を叩く。文セット構築 (辞書適用・分割・マージ) は
  `tts/normalize.py` / `tts/synthesize.py` の repo モジュールをそのまま再利用する。
- **seconds の供給源は v3 実測尺 + 0.25s** (Issue #88 T-d の負の知見: 文字数→秒の回帰は
  残差が大きく単独では使えない。「同文を v3 で実測した尺」が正)。
- **model/server/config/ref を SHA 固定** (Sol 指摘, Issue #88): 構成変更を検知したら
  history / Issue コメントに明記し、昇格カウントのリセットを促す。
- **v4 サーバは常駐させない** (Issue #98 フォローアップ): シャドーランは平日 12:00 の
  1 日 1 回のみのため、ラン終了時 (成功・失敗問わず) に必ず v4 サーバを停止する。
  自分で起動した場合はそのプロセスハンドルで、既存稼働を利用した場合はポートから
  PID を特定して停止する (特定できなければ WARNING ログのみで fail-open)。
  `SHADOW_KEEP_SERVER=1` で停止を抑止できる (連続手動検証用の逃げ道)。

使い方: `uv run python scripts/shadow_v4_run.py [--no-report-issue] [--v4-server-dir ...]`
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import json
import logging
import os
import re
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from sqlalchemy.orm import Session

from karyu_tech_news.config import PROJECT_ROOT, load_settings
from karyu_tech_news.deliver.discord import post_summary
from karyu_tech_news.script.ruby import load_auto_readings
from karyu_tech_news.store.repo import create_db_engine, get_latest_episode_draft, init_db
from karyu_tech_news.tts.asr_gate import AsrBackend, AsrUnavailableError, WhisperAsrBackend
from karyu_tech_news.tts.irodori import IRODORI_DEFAULT_VOICE, IRODORI_MAX_CHARS, IRODORI_MODEL
from karyu_tech_news.tts.normalize import (
    load_reading_dict,
    prepare_tts_text,
    split_markdown_topics,
)
from karyu_tech_news.tts.quality import analyze_wav_signal
from karyu_tech_news.tts.synthesize import (
    # private だが Issue #91 の指示どおり短文マージのロジックをそのまま再利用する
    # (T67 でテスト済みのマージ規則との乖離を避けるため独自再実装はしない)。
    _merge_short_sentences,
    split_sentences,
)

logger = logging.getLogger(__name__)

# ---------- 既定パス・定数 ----------

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "state.db"
DEFAULT_READING_DICT_PATH = PROJECT_ROOT / "config" / "reading_dict.yaml"
DEFAULT_AUTO_READING_DICT_PATH = PROJECT_ROOT / "data" / "reading_dict.auto.yaml"
DEFAULT_REGRESSION_SENTENCES_PATH = (
    PROJECT_ROOT / "scripts" / "data" / "shadow_regression_sentences.yaml"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "shadow_v4"
DEFAULT_V4_SERVER_DIR = Path.home() / "tools" / "Irodori-TTS-Server-v4"
DEFAULT_V4_LOG_PATH = DEFAULT_OUT_DIR / "v4_server.log"
DEFAULT_V3_BASE_URL = "http://127.0.0.1:8088"
DEFAULT_V4_BASE_URL = "http://127.0.0.1:8089"
DEFAULT_ISSUE_NUMBER = 88  # v4 移行トラック本体 Issue (Issue #91 の指示どおり)
DEFAULT_SEED = 42
DEFAULT_SECONDS_MARGIN = 0.25  # Issue #88: v3 実測尺 + 0.25s を正とする
DEFAULT_MIN_SENTENCE_CHARS = 20  # Issue #88: 20 字未満は短文マージ対象の目安
DEFAULT_SYNTH_TIMEOUT_SECONDS = 1800.0  # tts/irodori.py の既定と同値 (T55)
DEFAULT_WHISPER_MODEL = "turbo"
DEFAULT_V4_HEALTH_TIMEOUT_SECONDS = 180.0  # daily_pipeline.sh の初回モデルロード待ちと同値
DEFAULT_V4_HEALTH_POLL_SECONDS = 3.0
HEALTH_CHECK_TIMEOUT_SECONDS = 5.0  # daily_pipeline.sh の --max-time と同値
GIT_REV_TIMEOUT_SECONDS = 5.0
GH_COMMENT_TIMEOUT_SECONDS = 15.0
STOP_SERVER_TIMEOUT_SECONDS = 10.0
NETSTAT_TIMEOUT_SECONDS = 5.0  # 既存稼働サーバの PID 特定用 (Issue #98)
TASKLIST_TIMEOUT_SECONDS = 5.0
TASKKILL_TIMEOUT_SECONDS = 5.0
STOP_EXISTING_POLL_SECONDS = 0.5

# ラン終了時の v4 サーバ停止を抑止する環境変数 (連続手動検証用の逃げ道, Issue #98)。
# 既定は停止 (未設定/"0"/"false" は停止する側)。
SHADOW_KEEP_SERVER_ENV = "SHADOW_KEEP_SERVER"
_TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}

# 幻話疑い判定の閾値 (Issue #91 指定)。
LENGTH_RATIO_SUSPICION_THRESHOLD = 1.15
TRAILING_INSERTION_MIN_CHARS = 3

# Kana-CER / 幻話判定用の正規化 (asr_gate.verify_sentence と同じ規則を意図的に独立定義する。
# private な asr_gate._normalize への直接結合は避け、本モジュール単体で完結させる)。
_NORMALIZE_STRIP_RE = re.compile(r"[\s　。、,.!?！？「」『』・…]+")


def _normalize_for_metrics(text: str) -> str:
    """小文字化 + 主要な空白/句読点除去 (asr_gate と同じ正規化方針)."""
    return _NORMALIZE_STRIP_RE.sub("", text.lower())


# ---------- データ型 ----------


@dataclass(frozen=True, slots=True)
class SentenceItem:
    """三層測定の 1 文 (Issue #88 三層: daily_draft / known_failure / stratified)."""

    text: str
    layer: str
    bucket: str
    category: str
    source_id: str


@dataclass(frozen=True, slots=True)
class KanaCerResult:
    """挿入/削除/置換を分離集計した Kana-CER 近似 (Issue #91 指定)."""

    insertions: int
    deletions: int
    substitutions: int
    cer: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "insertions": self.insertions,
            "deletions": self.deletions,
            "substitutions": self.substitutions,
            "cer": self.cer,
        }


@dataclass(frozen=True, slots=True)
class HallucinationVerdict:
    """幻話疑い判定 (長さ比 > 閾値 or 末尾挿入 >= 閾値文字, Issue #91 指定)."""

    suspected: bool
    length_ratio: float
    trailing_insertion_chars: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "suspected": self.suspected,
            "length_ratio": self.length_ratio,
            "trailing_insertion_chars": self.trailing_insertion_chars,
        }


@dataclass(frozen=True, slots=True)
class ShadowConfig:
    """構成変更検知のためのハッシュ対象一式 (Sol 指摘: model/server/config/ref を SHA 固定)."""

    whisper_model: str
    seed: int
    min_sentence_chars: int
    v3_voice: str
    v4_voice: str
    model: str
    v4_server_rev: str | None
    v4_ref_audio_sha256: str | None
    length_ratio_threshold: float = LENGTH_RATIO_SUSPICION_THRESHOLD
    trailing_insertion_min_chars: int = TRAILING_INSERTION_MIN_CHARS

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def config_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return sha256_hex(payload.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class SentenceResult:
    """1 文の v3/v4 比較結果. error が None でなければ fail-open で skip された文."""

    source_id: str
    layer: str
    bucket: str
    category: str
    expected_text: str
    error: str | None = None
    v3_duration_sec: float | None = None
    v4_seconds_requested: float | None = None
    v3_transcript: str | None = None
    v4_transcript: str | None = None
    kana_cer: KanaCerResult | None = None
    hallucination: HallucinationVerdict | None = None
    v3_v4_transcript_agreement: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "layer": self.layer,
            "bucket": self.bucket,
            "category": self.category,
            "expected_text": self.expected_text,
            "error": self.error,
            "v3_duration_sec": self.v3_duration_sec,
            "v4_seconds_requested": self.v4_seconds_requested,
            "v3_transcript": self.v3_transcript,
            "v4_transcript": self.v4_transcript,
            "kana_cer": self.kana_cer.to_dict() if self.kana_cer is not None else None,
            "hallucination": (
                self.hallucination.to_dict() if self.hallucination is not None else None
            ),
            "v3_v4_transcript_agreement": self.v3_v4_transcript_agreement,
        }


@dataclass(frozen=True, slots=True)
class ShadowRunReport:
    """1 回のシャドーラン全体の結果 (report_YYYYMMDD_HHMM.json の元データ)."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    config: ShadowConfig
    config_hash: str
    sentence_results: list[SentenceResult]
    v4_available: bool
    v4_startup_note: str | None

    def sentence_count(self) -> int:
        return len(self.sentence_results)

    def error_count(self) -> int:
        return sum(1 for r in self.sentence_results if r.error is not None)

    def hallucination_suspect_count(self) -> int:
        return sum(
            1
            for r in self.sentence_results
            if r.hallucination is not None and r.hallucination.suspected
        )

    def cer_median(self) -> float | None:
        values = [r.kana_cer.cer for r in self.sentence_results if r.kana_cer is not None]
        return statistics.median(values) if values else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "config": self.config.to_dict(),
            "config_hash": self.config_hash,
            "v4_available": self.v4_available,
            "v4_startup_note": self.v4_startup_note,
            "summary": {
                "sentence_count": self.sentence_count(),
                "error_count": self.error_count(),
                "hallucination_suspect_count": self.hallucination_suspect_count(),
                "cer_median": self.cer_median(),
            },
            "sentences": [r.to_dict() for r in self.sentence_results],
        }


# ---------- 文セット構築 (三層, Issue #88) ----------


def build_daily_draft_sentences(
    markdown: str,
    reading_dict: dict[str, str],
    *,
    max_chars: int,
    min_sentence_chars: int,
) -> list[SentenceItem]:
    """当日実台本 (①) から文セットを構築する. produce と同じ正規化・分割・マージを適用する.

    トピック境界 (`## ` 見出し) ごとに `split_markdown_topics` で分割し、各パートへ
    `prepare_tts_text` (二層辞書適用) → `split_sentences` → `_merge_short_sentences`
    (`min_sentence_chars` 指定時のみ) の順で適用する。マージはトピック単位のリストにのみ
    適用するため、`tts/synthesize.py::synthesize_script` と同様に境界を越えない。
    """
    items: list[SentenceItem] = []
    for topic_idx, topic_text in enumerate(split_markdown_topics(markdown), start=1):
        normalized = prepare_tts_text(topic_text, reading_dict)
        sentences = split_sentences(normalized, max_chars)
        if min_sentence_chars > 0:
            sentences = _merge_short_sentences(sentences, min_sentence_chars, max_chars)
        bucket = f"topic-{topic_idx}"
        for sent_idx, sentence in enumerate(sentences, start=1):
            items.append(
                SentenceItem(
                    text=sentence,
                    layer="daily_draft",
                    bucket=bucket,
                    category="",
                    source_id=f"daily_draft:{bucket}:s{sent_idx}",
                )
            )
    return items


def _prepare_fixed_sentences(text: str, reading_dict: dict[str, str], max_chars: int) -> list[str]:
    """既知失敗文/層化回帰セット共通の正規化 (マージは適用しない, 意図的に生の文長を保つ)."""
    return split_sentences(prepare_tts_text(text, reading_dict), max_chars)


def load_regression_sentence_set(
    path: Path,
    reading_dict: dict[str, str],
    *,
    max_chars: int,
) -> list[SentenceItem]:
    """`scripts/data/shadow_regression_sentences.yaml` から②既知失敗文/③層化回帰セットを読む.

    ②③はマージ (min_sentence_chars) を適用しない — 短文の duration predictor 挙動を
    そのまま観測するのが層化回帰セットの目的のため (①daily_draft のみマージ対象)。
    """
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"回帰セット YAML の形式が不正です (dict でない): {path}")

    items: list[SentenceItem] = []

    known_failures = raw.get("known_failures") or []
    if not isinstance(known_failures, list):
        raise ValueError(f"known_failures はリストである必要があります: {path}")
    for idx, raw_text in enumerate(known_failures, start=1):
        for sent_idx, sentence in enumerate(
            _prepare_fixed_sentences(str(raw_text), reading_dict, max_chars), start=1
        ):
            items.append(
                SentenceItem(
                    text=sentence,
                    layer="known_failure",
                    bucket="known_failure",
                    category="",
                    source_id=f"known_failure:{idx}:s{sent_idx}",
                )
            )

    stratified = raw.get("stratified") or {}
    if not isinstance(stratified, dict):
        raise ValueError(f"stratified はマップである必要があります: {path}")
    for bucket_label, categories in stratified.items():
        if not isinstance(categories, dict):
            raise ValueError(f"stratified.{bucket_label} はマップである必要があります: {path}")
        for category, raw_text in categories.items():
            for sent_idx, sentence in enumerate(
                _prepare_fixed_sentences(str(raw_text), reading_dict, max_chars), start=1
            ):
                items.append(
                    SentenceItem(
                        text=sentence,
                        layer="stratified",
                        bucket=str(bucket_label),
                        category=str(category),
                        source_id=f"stratified:{bucket_label}:{category}:s{sent_idx}",
                    )
                )
    return items


def build_sentence_set(
    markdown: str,
    reading_dict: dict[str, str],
    regression_path: Path,
    *,
    max_chars: int,
    min_sentence_chars: int,
) -> list[SentenceItem]:
    """三層 (①当日実台本 ②既知失敗文 ③層化回帰セット) を結合した文セットを返す."""
    return [
        *build_daily_draft_sentences(
            markdown, reading_dict, max_chars=max_chars, min_sentence_chars=min_sentence_chars
        ),
        *load_regression_sentence_set(regression_path, reading_dict, max_chars=max_chars),
    ]


# ---------- メトリクス (Issue #91 指定) ----------


def compute_kana_cer(expected: str, transcript: str) -> KanaCerResult:
    """`difflib.SequenceMatcher.get_opcodes()` で insert/delete/replace を分離集計する.

    `replace` opcode は短い側の長さ分だけ置換とみなし、余剰は insert/delete へ計上する
    (CER 計算での一般的な近似)。CER は (insertions+deletions+substitutions)/期待文長。
    """
    norm_expected = _normalize_for_metrics(expected)
    norm_transcript = _normalize_for_metrics(transcript)
    matcher = difflib.SequenceMatcher(None, norm_expected, norm_transcript)

    insertions = 0
    deletions = 0
    substitutions = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            insertions += j2 - j1
        elif tag == "delete":
            deletions += i2 - i1
        elif tag == "replace":
            expected_len = i2 - i1
            transcript_len = j2 - j1
            substitutions += min(expected_len, transcript_len)
            if expected_len > transcript_len:
                deletions += expected_len - transcript_len
            elif transcript_len > expected_len:
                insertions += transcript_len - expected_len

    denom = max(len(norm_expected), 1)
    cer = (insertions + deletions + substitutions) / denom
    return KanaCerResult(
        insertions=insertions, deletions=deletions, substitutions=substitutions, cer=cer
    )


def detect_hallucination_suspicion(expected: str, transcript: str) -> HallucinationVerdict:
    """幻話疑い = (長さ比 > 1.15) or (末尾 diff が挿入で 3 文字以上) (Issue #91 指定)."""
    norm_expected = _normalize_for_metrics(expected)
    norm_transcript = _normalize_for_metrics(transcript)
    length_ratio = len(norm_transcript) / max(len(norm_expected), 1)

    opcodes = difflib.SequenceMatcher(None, norm_expected, norm_transcript).get_opcodes()
    trailing_insertion_chars = 0
    if opcodes:
        tag, _i1, _i2, j1, j2 = opcodes[-1]
        if tag == "insert":
            trailing_insertion_chars = j2 - j1

    suspected = (
        length_ratio > LENGTH_RATIO_SUSPICION_THRESHOLD
        or trailing_insertion_chars >= TRAILING_INSERTION_MIN_CHARS
    )
    return HallucinationVerdict(
        suspected=suspected,
        length_ratio=length_ratio,
        trailing_insertion_chars=trailing_insertion_chars,
    )


def transcript_agreement(a: str, b: str) -> float:
    """v3/v4 書き起こし同士の類似度 (0-1). 期待文でなく互いを突き合わせる (Issue #91 (d))."""
    return difflib.SequenceMatcher(
        None, _normalize_for_metrics(a), _normalize_for_metrics(b)
    ).ratio()


# ---------- ハッシュ / 補助 ----------


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    """存在しない/読めないファイルは None (fail-open, ハッシュ欠落を許容する)."""
    try:
        return sha256_hex(path.read_bytes())
    except OSError:
        return None


def git_rev(repo_dir: Path) -> str | None:
    """シャドーサーバの git commit を取得する (fail-open: 失敗時 None)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_REV_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    rev = proc.stdout.strip()
    return rev or None


# ---------- v3/v4 サーバ lifecycle ----------


def is_server_healthy(client: httpx.Client, base_url: str, *, require_loaded: bool) -> bool:
    """`/health` を叩く. require_loaded=True なら JSON body の `loaded` も確認する."""
    try:
        resp = client.get(f"{base_url.rstrip('/')}/health", timeout=HEALTH_CHECK_TIMEOUT_SECONDS)
    except httpx.HTTPError:
        return False
    if resp.status_code != 200:
        return False
    if not require_loaded:
        return True
    try:
        body = resp.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    # 実サーバの health は {"runtime": {"loaded": true}, ...} とネストしている
    # (初回実走 2026-08-03 で発覚: トップレベル参照だと永久に False → health タイムアウト)。
    # 後方互換でトップレベル "loaded" も受ける。
    runtime = body.get("runtime")
    if isinstance(runtime, dict) and "loaded" in runtime:
        return bool(runtime.get("loaded"))
    return bool(body.get("loaded"))


def wait_for_health(
    client: httpx.Client,
    base_url: str,
    *,
    timeout_sec: float,
    poll_interval_sec: float,
    require_loaded: bool,
) -> bool:
    """health OK になるまで poll_interval_sec 間隔で待つ (最大 timeout_sec)."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if is_server_healthy(client, base_url, require_loaded=require_loaded):
            return True
        time.sleep(poll_interval_sec)
    return is_server_healthy(client, base_url, require_loaded=require_loaded)


def start_v4_server(
    server_dir: Path, *, host: str, port: int, log_path: Path
) -> subprocess.Popen[bytes]:
    """v4 シャドーサーバを起動する (このプロセスの存命中のみ). 起動コマンドはチケット仕様固定."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("ab")
    return subprocess.Popen(
        [
            "uv",
            "run",
            "--no-sync",
            "python",
            "-m",
            "irodori_openai_tts",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(server_dir),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )


def stop_v4_server(proc: subprocess.Popen[bytes]) -> None:
    """本ジョブが起動した v4 サーバを停止する (daily_pipeline.sh と同じ流儀)."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=STOP_SERVER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=STOP_SERVER_TIMEOUT_SECONDS)


def keep_server_requested() -> bool:
    """`SHADOW_KEEP_SERVER=1` 等で停止抑止が指定されているか (Issue #98 の逃げ道)."""
    value = os.environ.get(SHADOW_KEEP_SERVER_ENV, "")
    return value.strip().lower() in _TRUTHY_ENV_VALUES


def find_listening_pid(port: int, *, timeout: float = NETSTAT_TIMEOUT_SECONDS) -> int | None:
    """`netstat -ano` で `port` を LISTENING している PID を特定する.

    既存稼働の v4 サーバを停止するため、自プロセスが起動していない場合の PID 特定に使う
    (Issue #98)。0 件/複数件/コマンド失敗はすべて fail-open で None を返し、呼び出し元は
    WARNING ログのみで停止をスキップする (誤って無関係なプロセスを kill しないため)。
    """
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None

    suffix = f":{port}"
    pids: set[int] = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local_addr, _remote_addr, state, pid_text = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
            parts[4],
        )
        if proto.upper() != "TCP" or state.upper() != "LISTENING":
            continue
        if not local_addr.endswith(suffix):
            continue
        try:
            pids.add(int(pid_text))
        except ValueError:
            continue

    if len(pids) != 1:
        return None
    return next(iter(pids))


def _pid_exists(pid: int, *, timeout: float = TASKLIST_TIMEOUT_SECONDS) -> bool:
    """`tasklist` で PID の生死を確認する (取得失敗時は存在するとみなし過剰な /F kill を避ける)."""
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    if proc.returncode != 0:
        return True
    return str(pid) in proc.stdout


def kill_pid(
    pid: int,
    *,
    graceful_timeout: float = STOP_SERVER_TIMEOUT_SECONDS,
    poll_interval: float = STOP_EXISTING_POLL_SECONDS,
) -> bool:
    """`taskkill` で PID を停止する (まず通常終了、猶予後に `/F` 強制終了).

    既存稼働 (本ジョブが起動していない) v4 サーバの停止用 (Issue #98)。成否を bool で返し、
    呼び出し元は fail-open (失敗してもランの exit code は変えない) で扱う。
    """
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            ["taskkill", "/PID", str(pid)],
            capture_output=True,
            text=True,
            timeout=TASKKILL_TIMEOUT_SECONDS,
            check=False,
        )

    deadline = time.monotonic() + graceful_timeout
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return True
        time.sleep(poll_interval)

    if not _pid_exists(pid):
        return True

    try:
        proc = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            timeout=TASKKILL_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def shutdown_v4_server(
    *,
    started_by_us: bool,
    proc: subprocess.Popen[bytes] | None,
    reused_existing: bool,
    port: int,
) -> None:
    """ラン終了時の v4 サーバ停止をディスパッチする (Issue #98: 常駐対策).

    `SHADOW_KEEP_SERVER=1` が指定されていれば何もしない (逃げ道)。自分で起動した場合は
    そのプロセスハンドルで `stop_v4_server` を使い、既存稼働を利用しただけの場合はポート
    から PID を特定して `kill_pid` で停止する。いずれも fail-open (失敗は WARNING ログの
    みで呼び出し元の exit code には影響させない)。
    """
    if keep_server_requested():
        logger.info("%s=1 のため v4 シャドーサーバの停止をスキップします", SHADOW_KEEP_SERVER_ENV)
        return

    if started_by_us:
        if proc is None:
            return
        logger.info("v4 シャドーサーバ (自起動分) を停止します")
        try:
            stop_v4_server(proc)
        except OSError as exc:
            logger.warning("v4 シャドーサーバ (自起動分) の停止に失敗しました (fail-open): %s", exc)
            return
        if proc.poll() is None:
            logger.warning("v4 シャドーサーバ (自起動分) が停止確認できません (fail-open)")
        else:
            logger.info("v4 シャドーサーバ (自起動分) を停止しました")
        return

    if not reused_existing:
        return

    pid = find_listening_pid(port)
    if pid is None:
        logger.warning(
            "v4 シャドーサーバ (既存利用分) の PID を特定できず停止をスキップします "
            "(fail-open, port=%d)",
            port,
        )
        return

    logger.info("v4 シャドーサーバ (既存利用分, PID %d) を停止します", pid)
    if kill_pid(pid):
        logger.info("v4 シャドーサーバ (既存利用分, PID %d) を停止しました", pid)
    else:
        logger.warning(
            "v4 シャドーサーバ (既存利用分, PID %d) の停止に失敗しました (fail-open)", pid
        )


def synthesize_wav(
    client: httpx.Client,
    base_url: str,
    text: str,
    *,
    voice: str,
    model: str,
    irodori_options: dict[str, Any] | None,
    timeout: float,
) -> bytes:
    """OpenAI 互換 `POST /v1/audio/speech` を直接叩く (engine 抽象を経由しない, Issue #91)."""
    body: dict[str, Any] = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "wav",
        "speed": 1.0,
    }
    if irodori_options:
        body["irodori"] = irodori_options
    resp = client.post(f"{base_url.rstrip('/')}/v1/audio/speech", json=body, timeout=timeout)
    resp.raise_for_status()
    audio = resp.content
    if not audio:
        raise RuntimeError("応答が空 (合成失敗)")
    return audio


# ---------- DB 読み取り (SELECT のみ, 書き込み禁止) ----------


def load_latest_draft_markdown(db_path: Path) -> str | None:
    """本番 DB から最新 episode_draft の markdown を読み取り専用で取得する.

    produce (main.py) と同じ `create_db_engine`/`init_db` を使うが、本モジュールは
    episode_drafts に対して SELECT のみ行い、一切書き込まない (AGENTS.md §3)。
    """
    engine = create_db_engine(db_path)
    init_db(engine)
    with Session(engine) as session:
        draft = get_latest_episode_draft(session)
        return str(draft.markdown) if draft is not None else None


# ---------- 文単位処理 (実サーバ依存, 単体テスト対象外) ----------


def _base_result(item: SentenceItem, **overrides: Any) -> SentenceResult:
    return SentenceResult(
        source_id=item.source_id,
        layer=item.layer,
        bucket=item.bucket,
        category=item.category,
        expected_text=item.text,
        **overrides,
    )


def process_sentence(
    item: SentenceItem,
    *,
    client: httpx.Client,
    v3_base_url: str,
    v4_base_url: str,
    v3_voice: str,
    v4_voice: str,
    model: str,
    seed: int,
    whisper_backend: AsrBackend,
    synth_timeout: float,
    seconds_margin: float,
) -> SentenceResult:
    """1 文の v3→実測尺→v4(seconds 固定)→両方 ASR→メトリクス を fail-open で行う.

    `AsrUnavailableError` (ASR バックエンド未導入) は揉み消さず呼び出し元へ伝播させる
    (全文が同じ理由で失敗するため、個別 skip ではなくラン全体の abort 対象, main 参照)。
    """
    try:
        v3_audio = synthesize_wav(
            client,
            v3_base_url,
            item.text,
            voice=v3_voice,
            model=model,
            irodori_options={"seed": seed},
            timeout=synth_timeout,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        return _base_result(item, error=f"v3合成失敗: {type(exc).__name__}: {exc}")

    v3_signal = analyze_wav_signal(v3_audio)
    if not v3_signal.valid_wav:
        return _base_result(item, error="v3応答が不正なwav")
    dur3 = v3_signal.duration_sec

    try:
        v3_transcript = whisper_backend.transcribe(v3_audio)
    except AsrUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — ASR 内部の予期せぬ失敗はこの文だけ fail-open
        return _base_result(
            item, v3_duration_sec=dur3, error=f"v3書き起こし失敗: {type(exc).__name__}: {exc}"
        )

    v4_seconds = round(dur3 + seconds_margin, 3)
    v4_options: dict[str, Any] = {"seconds": v4_seconds, "seed": seed}
    try:
        v4_audio = synthesize_wav(
            client,
            v4_base_url,
            item.text,
            voice=v4_voice,
            model=model,
            irodori_options=v4_options,
            timeout=synth_timeout,
        )
    except (httpx.HTTPError, RuntimeError) as exc:
        return _base_result(
            item,
            v3_duration_sec=dur3,
            v4_seconds_requested=v4_seconds,
            v3_transcript=v3_transcript,
            error=f"v4合成失敗: {type(exc).__name__}: {exc}",
        )

    v4_signal = analyze_wav_signal(v4_audio)
    if not v4_signal.valid_wav:
        return _base_result(
            item,
            v3_duration_sec=dur3,
            v4_seconds_requested=v4_seconds,
            v3_transcript=v3_transcript,
            error="v4応答が不正なwav",
        )

    try:
        v4_transcript = whisper_backend.transcribe(v4_audio)
    except AsrUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — ASR 内部の予期せぬ失敗はこの文だけ fail-open
        return _base_result(
            item,
            v3_duration_sec=dur3,
            v4_seconds_requested=v4_seconds,
            v3_transcript=v3_transcript,
            error=f"v4書き起こし失敗: {type(exc).__name__}: {exc}",
        )

    kana_cer = compute_kana_cer(item.text, v4_transcript)
    hallucination = detect_hallucination_suspicion(item.text, v4_transcript)
    agreement = transcript_agreement(v3_transcript, v4_transcript)

    return _base_result(
        item,
        v3_duration_sec=dur3,
        v4_seconds_requested=v4_seconds,
        v3_transcript=v3_transcript,
        v4_transcript=v4_transcript,
        kana_cer=kana_cer,
        hallucination=hallucination,
        v3_v4_transcript_agreement=agreement,
    )


# ---------- レポート / history 出力 ----------


def write_report(report: ShadowRunReport, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report.started_at.strftime("%Y%m%d_%H%M")
    path = out_dir / f"report_{stamp}.json"
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_history_line(report: ShadowRunReport, *, config_changed: bool) -> dict[str, Any]:
    return {
        "run_id": report.run_id,
        "started_at": report.started_at.isoformat(),
        "sentence_count": report.sentence_count(),
        "error_count": report.error_count(),
        "hallucination_suspect_count": report.hallucination_suspect_count(),
        "cer_median": report.cer_median(),
        "config_hash": report.config_hash,
        "config_changed": config_changed,
        "v4_available": report.v4_available,
    }


def read_last_history_line(history_path: Path) -> dict[str, Any] | None:
    """history.jsonl の末尾行を返す (構成変更検知用)。無い/壊れていれば None (fail-open)."""
    if not history_path.exists():
        return None
    last: str | None = None
    for raw_line in history_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped:
            last = stripped
    if last is None:
        return None
    try:
        parsed: Any = json.loads(last)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def append_history(history_path: Path, line: dict[str, Any]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False))
        f.write("\n")


# ---------- Issue コメント ----------


def _format_optional_float(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def build_issue_comment(report: ShadowRunReport, *, config_changed: bool) -> str:
    """Issue #88 への集計コメント本文を組み立てる (10 行以内, Issue #91 指定)."""
    stamp = report.started_at.strftime("%Y%m%d_%H%M")
    lines = [
        f"## v4 シャドーラン {report.run_id}",
        f"- v4 利用可否: {'OK' if report.v4_available else f'NG ({report.v4_startup_note})'}",
        f"- 文数: {report.sentence_count()} (エラー {report.error_count()})",
        f"- 幻話疑い: {report.hallucination_suspect_count()}",
        f"- Kana-CER 中央値: {_format_optional_float(report.cer_median())}",
        f"- config_hash: {report.config_hash[:12]}",
        f"- レポート: `data/shadow_v4/report_{stamp}.json`",
    ]
    if config_changed:
        lines.append("- ⚠️ 前回からの構成変更を検知 → 昇格カウントリセット")
    return "\n".join(lines)


def post_issue_comment(comment: str, *, issue_number: int) -> bool:
    """`gh issue comment` で投稿する (fail-open: 失敗してもランは成功扱い)."""
    try:
        proc = subprocess.run(
            ["gh", "issue", "comment", str(issue_number), "--body", comment],
            capture_output=True,
            text=True,
            timeout=GH_COMMENT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Issue コメント投稿に失敗 (fail-open): %s", exc)
        return False
    if proc.returncode != 0:
        logger.warning("gh issue comment が非ゼロ終了 (fail-open): %s", proc.stderr.strip())
        return False
    return True


# ---------- Discord 通知 (Issue #95 PR-B) ----------


def build_discord_summary(report: ShadowRunReport) -> str:
    """Discord 投稿用の1行サマリーを組み立てる (Issue #95 PR-B 指定)."""
    return (
        f"🔬 v4 シャドーラン {report.run_id}: "
        f"文数 {report.sentence_count()} (エラー {report.error_count()}) / "
        f"幻話疑い {report.hallucination_suspect_count()} / "
        f"Kana-CER 中央値 {_format_optional_float(report.cer_median())}。"
        "詳細: Issue #88"
    )


def post_shadow_summary_to_discord(report: ShadowRunReport) -> bool:
    """シャドーラン結果のサマリーを Discord Webhook へ投稿する.

    レポート出力・Issue #88 コメント投稿の後段に位置づける。既存の `deliver/discord.py`
    (`post_summary`) を再利用し、投稿失敗は fail-open (WARNING ログのみ、呼び出し元の
    exit code には影響させない)。DISCORD_WEBHOOK_URL 未設定時は投稿を試みず、
    黙って skip せず INFO ログで明示する。
    """
    settings = load_settings(PROJECT_ROOT / ".env")
    webhook_url = settings.discord_webhook_url
    if not webhook_url:
        logger.info("DISCORD_WEBHOOK_URL 未設定のため v4 シャドーラン通知をスキップします")
        return False

    ok = post_summary(webhook_url, build_discord_summary(report))
    if not ok:
        logger.warning("v4 シャドーラン Discord 通知の送信に失敗しました (fail-open)")
    return ok


# ---------- オーケストレーション (実サーバ依存, 単体テスト対象外) ----------


def run_shadow(
    *,
    client: httpx.Client,
    args: argparse.Namespace,
    v4_available: bool,
    v4_startup_note: str | None,
) -> ShadowRunReport:
    started_at = datetime.now(UTC)
    run_id = started_at.strftime("%Y%m%d_%H%M%S")

    manual_reading_dict = load_reading_dict(args.reading_dict) if args.reading_dict.exists() else {}
    auto_reading_dict = load_auto_readings(args.auto_reading_dict)
    reading_dict = {**auto_reading_dict, **manual_reading_dict}

    markdown = load_latest_draft_markdown(args.db_path)
    if markdown is not None:
        sentence_items = build_sentence_set(
            markdown,
            reading_dict,
            args.regression_sentences,
            max_chars=args.max_chars,
            min_sentence_chars=args.min_sentence_chars,
        )
    else:
        logger.warning("episode_draft が見つかりません。回帰セットのみでランします (fail-open)")
        sentence_items = load_regression_sentence_set(
            args.regression_sentences, reading_dict, max_chars=args.max_chars
        )

    v4_server_rev = git_rev(args.v4_server_dir)
    v4_ref_audio_sha256 = sha256_file(args.v4_server_dir / "voices" / "hal.wav")
    config = ShadowConfig(
        whisper_model=args.whisper_model,
        seed=args.seed,
        min_sentence_chars=args.min_sentence_chars,
        v3_voice=args.voice,
        v4_voice=args.voice,
        model=args.model,
        v4_server_rev=v4_server_rev,
        v4_ref_audio_sha256=v4_ref_audio_sha256,
    )

    sentence_results: list[SentenceResult] = []
    if v4_available and sentence_items:
        whisper_backend = WhisperAsrBackend(args.whisper_model)
        for item in sentence_items:
            sentence_results.append(
                process_sentence(
                    item,
                    client=client,
                    v3_base_url=args.v3_base_url,
                    v4_base_url=args.v4_base_url,
                    v3_voice=args.voice,
                    v4_voice=args.voice,
                    model=args.model,
                    seed=args.seed,
                    whisper_backend=whisper_backend,
                    synth_timeout=args.synth_timeout_sec,
                    seconds_margin=args.seconds_margin,
                )
            )
    elif not v4_available:
        logger.warning(
            "v4 シャドー利用不可のため文単位測定をスキップ (fail-open): %s", v4_startup_note
        )

    finished_at = datetime.now(UTC)
    return ShadowRunReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        config=config,
        config_hash=config.config_hash(),
        sentence_results=sentence_results,
        v4_available=v4_available,
        v4_startup_note=v4_startup_note,
    )


# ---------- CLI ----------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Irodori-TTS v4 移行トラック: 日次シャドーレンダリング + 三層測定 (Issue #91)")
    )
    parser.add_argument(
        "--db-path", type=Path, default=DEFAULT_DB_PATH, help="本番 SQLite DB (読み取り専用)"
    )
    parser.add_argument("--reading-dict", type=Path, default=DEFAULT_READING_DICT_PATH)
    parser.add_argument("--auto-reading-dict", type=Path, default=DEFAULT_AUTO_READING_DICT_PATH)
    parser.add_argument(
        "--regression-sentences", type=Path, default=DEFAULT_REGRESSION_SENTENCES_PATH
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v3-base-url", default=DEFAULT_V3_BASE_URL)
    parser.add_argument("--v4-base-url", default=DEFAULT_V4_BASE_URL)
    parser.add_argument("--v4-server-dir", type=Path, default=DEFAULT_V4_SERVER_DIR)
    parser.add_argument("--v4-host", default="127.0.0.1")
    parser.add_argument("--v4-port", type=int, default=8089)
    parser.add_argument("--v4-log-path", type=Path, default=DEFAULT_V4_LOG_PATH)
    parser.add_argument(
        "--v4-health-timeout-sec", type=float, default=DEFAULT_V4_HEALTH_TIMEOUT_SECONDS
    )
    parser.add_argument("--v4-health-poll-sec", type=float, default=DEFAULT_V4_HEALTH_POLL_SECONDS)
    parser.add_argument("--voice", default=IRODORI_DEFAULT_VOICE)
    parser.add_argument("--model", default=IRODORI_MODEL)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--seconds-margin", type=float, default=DEFAULT_SECONDS_MARGIN)
    parser.add_argument("--synth-timeout-sec", type=float, default=DEFAULT_SYNTH_TIMEOUT_SECONDS)
    parser.add_argument("--min-sentence-chars", type=int, default=DEFAULT_MIN_SENTENCE_CHARS)
    parser.add_argument("--max-chars", type=int, default=IRODORI_MAX_CHARS)
    parser.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL)
    parser.add_argument("--issue-number", type=int, default=DEFAULT_ISSUE_NUMBER)
    parser.add_argument(
        "--report-issue",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Issue へ集計コメントを投稿する (既定 on。--no-report-issue で抑止)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Issue #98: v4 サーバの起動状況を outer try/finally の外側で追跡し、
    # レポート出力・Issue コメント・Discord 通知の「後」に必ず停止処理を行う
    # (成功・失敗問わず fail-open。停止の成否は exit code に影響させない)。
    v4_started = False
    v4_proc: subprocess.Popen[bytes] | None = None
    v4_reused_existing = False

    try:
        with httpx.Client() as client:
            if not is_server_healthy(client, args.v3_base_url, require_loaded=False):
                logger.error(
                    "v3 (本番) サーバの health が確認できません。シャドーランを中断します: %s",
                    args.v3_base_url,
                )
                return 1

            v4_available = True
            v4_startup_note: str | None = None
            if is_server_healthy(client, args.v4_base_url, require_loaded=True):
                v4_reused_existing = True
                logger.info("v4 シャドーサーバ: 既に稼働中 (既存を利用)")
            else:
                logger.info("v4 シャドーサーバ: 未起動 → 起動")
                try:
                    v4_proc = start_v4_server(
                        args.v4_server_dir,
                        host=args.v4_host,
                        port=args.v4_port,
                        log_path=args.v4_log_path,
                    )
                    v4_started = True
                except OSError as exc:
                    v4_available = False
                    v4_startup_note = f"起動失敗: {type(exc).__name__}: {exc}"
                    logger.warning("v4 シャドーサーバの起動に失敗 (fail-open): %s", exc)
                if v4_available and not wait_for_health(
                    client,
                    args.v4_base_url,
                    timeout_sec=args.v4_health_timeout_sec,
                    poll_interval_sec=args.v4_health_poll_sec,
                    require_loaded=True,
                ):
                    v4_available = False
                    v4_startup_note = "health タイムアウト"
                    logger.warning("v4 シャドーサーバが health に到達せず (fail-open)")

            try:
                report = run_shadow(
                    client=client,
                    args=args,
                    v4_available=v4_available,
                    v4_startup_note=v4_startup_note,
                )
            except AsrUnavailableError as exc:
                logger.error("ASR バックエンドが利用できません。シャドーランを中断します: %s", exc)
                return 1

        report_path = write_report(report, args.out_dir)
        logger.info("レポート出力: %s", report_path)

        history_path = args.out_dir / "history.jsonl"
        previous = read_last_history_line(history_path)
        config_changed = previous is not None and previous.get("config_hash") != report.config_hash
        append_history(history_path, build_history_line(report, config_changed=config_changed))

        if args.report_issue:
            comment = build_issue_comment(report, config_changed=config_changed)
            post_issue_comment(comment, issue_number=args.issue_number)

        post_shadow_summary_to_discord(report)

        return 0
    finally:
        shutdown_v4_server(
            started_by_us=v4_started,
            proc=v4_proc,
            reused_existing=v4_reused_existing,
            port=args.v4_port,
        )


if __name__ == "__main__":
    raise SystemExit(main())
