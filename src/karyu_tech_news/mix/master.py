"""ラウドネス正規化 + mp3 完パケ (Sprint 2 Ticket T30, FR-102/103).

T28 が結合した音声 wav (bytes) を入力に、EBU R128 ラウドネス正規化 (-16 LUFS) を施し
mp3 192kbps/48kHz で書き出す。BGM ミックス (T29) はこの前段 (mixer.py) で行う想定だが、
本モジュールは入力 wav 単体で完結するため、BGM 素材待ち (人間ゲート) でも素の音声を
完パケ mp3 にするエンドツーエンド経路を提供できる。

設計判断:
- **依存最小 (AGENTS §5)**: ffmpeg の `loudnorm` フィルタ単体で「測定 + 正規化 + mp3
  エンコード」が完結するため pydub を足さない (pydub が要るのは T29 の BGM 時間軸合成)。
- **2-pass loudnorm**: pass1 で入力ラウドネスを測定 (print_format=json) し、pass2 で
  測定値を渡した線形補正をかける。1-pass の dynamic より integrated 目標を正確に狙える。
- **fail-open**: 無音等で測定不能 (-inf) のときは measured_* なしの単一パスに縮退する。
- ffmpeg 呼び出しには必ずタイムアウトを付ける (AGENTS §3.3 タイムアウト必須の精神)。
"""
from __future__ import annotations

import io
import json
import math
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from pydantic import BaseModel

TARGET_LUFS = -16.0  # FR-102: 配信ラウドネス目標 (EBU R128 / ポッドキャスト実務)
TRUE_PEAK_DBTP = -1.5  # ロッシー化のクリップ余裕 (dBTP)
TARGET_LRA = 11.0  # loudnorm の LRA 目標 (EBU R128 既定)
OUTPUT_SAMPLE_RATE = 48000  # FR-103
MP3_BITRATE = "192k"  # FR-103
FFMPEG_TIMEOUT_SECONDS = 600.0  # 1 エピソード (数分) の余裕を見たマスタリング上限

# loudnorm が print_format=json で stderr 末尾に出す JSON ブロック (ネストなし)
_JSON_BLOCK_RE = re.compile(r"\{[^{}]*\}")


class MasteringError(Exception):
    """マスタリング (ffmpeg 実行・ラウドネス測定・mp3 化) の失敗."""


class LoudnormStats(BaseModel):
    """loudnorm pass1 が測定した入力ラウドネス指標 (pass2 に渡す)."""

    input_i: float  # integrated loudness (LUFS)
    input_tp: float  # true peak (dBTP)
    input_lra: float  # loudness range (LU)
    input_thresh: float  # gating threshold (LUFS)
    target_offset: float  # loudnorm が推奨するオフセット


class MasteringResult(BaseModel):
    """完パケ mp3 のメタデータ (永続化 T31 / 観察 T32 の証跡)."""

    path: str
    target_lufs: float
    measured_lufs: float  # 出力 mp3 を再測定した実 integrated loudness
    true_peak_dbtp: float
    duration_sec: float
    bitrate: str
    sample_rate: int
    audio_format: str = "mp3"


def _ensure_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise MasteringError("ffmpeg が見つかりません (T30 マスタリングに必須)")
    return ffmpeg


def _run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess[str]:
    """ffmpeg を実行する (タイムアウト必須). 戻り値判定は呼び出し側."""
    ffmpeg = _ensure_ffmpeg()
    try:
        return subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", *args],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MasteringError(f"ffmpeg タイムアウト ({FFMPEG_TIMEOUT_SECONDS}s)") from exc


def _parse_loudnorm_stats(stderr: str) -> LoudnormStats:
    """loudnorm pass1 の stderr から JSON ブロックを抽出して指標化する."""
    matches = _JSON_BLOCK_RE.findall(stderr)
    if not matches:
        raise MasteringError("loudnorm の測定 JSON が見つかりません (ffmpeg 失敗の可能性)")
    raw = json.loads(matches[-1])  # 末尾ブロックが測定結果

    def _f(key: str, default: float = 0.0) -> float:
        val = raw.get(key)
        if val is None:
            return default
        return float(val)  # "-inf" 等も float() で扱える

    return LoudnormStats(
        input_i=_f("input_i"),
        input_tp=_f("input_tp"),
        input_lra=_f("input_lra"),
        input_thresh=_f("input_thresh"),
        target_offset=_f("target_offset"),
    )


def _is_measurable(stats: LoudnormStats) -> bool:
    """測定値が全て有限か (無音入力では -inf になり 2-pass 補正に使えない)."""
    return all(
        math.isfinite(v)
        for v in (stats.input_i, stats.input_tp, stats.input_lra, stats.input_thresh)
    )


def _build_loudnorm_filter(
    stats: LoudnormStats | None,
    *,
    target_i: float,
    target_tp: float,
    target_lra: float,
) -> str | None:
    """loudnorm フィルタ文字列を組む (測定値があれば 2-pass 線形補正).

    測定不能 (無音で input_i=-inf 等) のときは **None** を返し、呼び出し側は
    loudnorm を通さず素エンコードする。dynamic loudnorm を無音に通すと
    libmp3lame が assertion で落ち fail-open を破るため (Codex 指摘)。
    """
    if stats is None or not _is_measurable(stats):
        return None
    return (
        f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
        f":measured_I={stats.input_i}"
        f":measured_TP={stats.input_tp}"
        f":measured_LRA={stats.input_lra}"
        f":measured_thresh={stats.input_thresh}"
        f":offset={stats.target_offset}"
        f":linear=true"
    )


def _wav_duration_seconds(audio_wav: bytes) -> float:
    try:
        with wave.open(io.BytesIO(audio_wav), "rb") as r:
            frames = r.getnframes()
            rate = r.getframerate()
    except (wave.Error, EOFError):
        return 0.0
    return frames / rate if rate else 0.0


def _wav_frames_rate(audio_wav: bytes) -> tuple[int, int]:
    """有効 wav の (nframes, framerate). 不正 wav は MasteringError (素エンコードと区別)."""
    try:
        with wave.open(io.BytesIO(audio_wav), "rb") as r:
            return r.getnframes(), r.getframerate()
    except (wave.Error, EOFError) as exc:
        raise MasteringError(f"入力が有効な wav でない: {type(exc).__name__}") from exc


def _short_silence(sample_rate: int, *, seconds: float = 0.3) -> bytes:
    """短い無音 wav (16bit/mono). 0フレーム入力 (T28 全滅 fail-open 産物) の退避用."""
    n = max(1, int(sample_rate * seconds))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n)
    return out.getvalue()


def _measure_loudness_path(path: Path) -> LoudnormStats:
    """ファイルのラウドネスを測定する (pass1 相当)."""
    flt = f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_DBTP}:LRA={TARGET_LRA}:print_format=json"
    proc = _run_ffmpeg(["-i", str(path), "-af", flt, "-f", "null", "-"])
    return _parse_loudnorm_stats(proc.stderr)


def measure_loudness(audio_wav: bytes) -> LoudnormStats:
    """wav bytes のラウドネスを測定する (一時ファイル経由)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.wav"
        src.write_bytes(audio_wav)
        return _measure_loudness_path(src)


def master_to_mp3(
    audio_wav: bytes,
    output_path: Path | str,
    *,
    target_lufs: float = TARGET_LUFS,
    target_tp: float = TRUE_PEAK_DBTP,
    target_lra: float = TARGET_LRA,
    sample_rate: int = OUTPUT_SAMPLE_RATE,
    bitrate: str = MP3_BITRATE,
) -> MasteringResult:
    """音声 wav (bytes) を -16 LUFS 正規化して mp3 で書き出す (FR-102/103).

    1. pass1: 入力ラウドネスを測定
    2. pass2: 測定値で線形 loudnorm + mp3 エンコード
    3. 出力 mp3 を再測定して結果メタデータに格納 (正規化が効いた証跡)
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 入力検証: 不正バイトは MasteringError、0フレーム (T28 全滅 fail-open 産物) は
    # 短い無音に退避して valid mp3 を返す (番組を止めず degrade)。
    frames, in_rate = _wav_frames_rate(audio_wav)
    if frames == 0:
        audio_wav = _short_silence(in_rate or sample_rate)

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.wav"
        src.write_bytes(audio_wav)

        # pass1 測定。有効 wav でも無音等で測定不能なら None に縮退 (raise しない)。
        try:
            stats: LoudnormStats | None = _measure_loudness_path(src)
        except MasteringError:
            stats = None
        flt = _build_loudnorm_filter(
            stats, target_i=target_lufs, target_tp=target_tp, target_lra=target_lra
        )
        # 測定不能時 (flt is None) は loudnorm を通さず素エンコード (無音でも valid mp3)。
        args = ["-y", "-i", str(src)]
        if flt is not None:
            args += ["-af", flt]
        args += ["-ar", str(sample_rate), "-c:a", "libmp3lame", "-b:a", bitrate, str(out)]
        proc = _run_ffmpeg(args)
        if proc.returncode != 0 or not out.exists():
            tail = proc.stderr.strip().splitlines()[-3:]
            raise MasteringError("mp3 エンコード失敗: " + " / ".join(tail))

    # pass3: 出力の実ラウドネス (無音出力は測定不能 → -inf として記録)。
    try:
        verify: LoudnormStats | None = _measure_loudness_path(out)
    except MasteringError:
        verify = None
    return MasteringResult(
        path=str(out),
        target_lufs=target_lufs,
        measured_lufs=verify.input_i if verify is not None else float("-inf"),
        true_peak_dbtp=verify.input_tp if verify is not None else float("-inf"),
        duration_sec=_wav_duration_seconds(audio_wav),
        bitrate=bitrate,
        sample_rate=sample_rate,
    )
