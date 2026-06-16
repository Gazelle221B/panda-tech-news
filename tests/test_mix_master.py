"""mix.master のユニットテスト (Sprint 2 Ticket T30, FR-102/103).

設計方針 (IMPLEMENTATION_PLAN-2 §5):
- 純ロジック (loudnorm JSON パース・フィルタ文字列構築) は ffmpeg 無しで完全テスト。
- 実 ffmpeg 依存の統合テストは小さなフィクスチャ wav で、ffmpeg 不在環境では skip。
"""
from __future__ import annotations

import io
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from karyu_tech_news.mix.master import (
    MP3_BITRATE,
    OUTPUT_SAMPLE_RATE,
    TARGET_LUFS,
    LoudnormStats,
    MasteringError,
    MasteringResult,
    _build_loudnorm_filter,
    _parse_loudnorm_stats,
    master_to_mp3,
    measure_loudness,
)

_HAS_FFMPEG = shutil.which("ffmpeg") is not None
_needs_ffmpeg = pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")


def _tone_wav(
    *, seconds: float = 2.0, freq: float = 440.0, sample_rate: int = 48000, amp: float = 0.3
) -> bytes:
    """信号入りの 16bit/mono wav (ラウドネス測定が有限値になるよう正弦波)."""
    n = int(seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            val = int(amp * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))
    return buf.getvalue()


# loudnorm pass1 の典型的な stderr 末尾 (print_format=json)
_SAMPLE_LOUDNORM_JSON = """
[Parsed_loudnorm_0 @ 0x600000]
{
	"input_i" : "-23.45",
	"input_tp" : "-3.20",
	"input_lra" : "5.40",
	"input_thresh" : "-33.78",
	"output_i" : "-16.02",
	"output_tp" : "-1.51",
	"output_lra" : "5.30",
	"output_thresh" : "-26.40",
	"normalization_type" : "dynamic",
	"target_offset" : "0.12"
}
"""


# ---------- 純ロジック: loudnorm JSON パース (ffmpeg 不要) ----------


def test_parse_loudnorm_stats_extracts_floats() -> None:
    stats = _parse_loudnorm_stats(_SAMPLE_LOUDNORM_JSON)
    assert isinstance(stats, LoudnormStats)
    assert stats.input_i == pytest.approx(-23.45)
    assert stats.input_tp == pytest.approx(-3.20)
    assert stats.input_lra == pytest.approx(5.40)
    assert stats.input_thresh == pytest.approx(-33.78)
    assert stats.target_offset == pytest.approx(0.12)


def test_parse_loudnorm_stats_raises_without_json() -> None:
    with pytest.raises(MasteringError):
        _parse_loudnorm_stats("ffmpeg がエラーで JSON を出さなかった")


def test_parse_loudnorm_stats_handles_inf_silence() -> None:
    # 無音入力では input_i が -inf になり得る (測定不能)
    silent_json = _SAMPLE_LOUDNORM_JSON.replace('"-23.45"', '"-inf"')
    stats = _parse_loudnorm_stats(silent_json)
    assert math.isinf(stats.input_i)


# ---------- 純ロジック: loudnorm フィルタ構築 (ffmpeg 不要) ----------


def test_build_filter_two_pass_includes_measured() -> None:
    stats = _parse_loudnorm_stats(_SAMPLE_LOUDNORM_JSON)
    f = _build_loudnorm_filter(stats, target_i=-16.0, target_tp=-1.5, target_lra=11.0)
    assert "loudnorm=" in f
    assert "I=-16.0" in f
    assert "TP=-1.5" in f
    assert "measured_I=-23.45" in f
    assert "measured_thresh=-33.78" in f
    assert "linear=true" in f


def test_build_filter_dynamic_when_unmeasurable() -> None:
    # 測定不能 (None or 非有限) のときは measured_* を付けない単一パス (dynamic)
    f = _build_loudnorm_filter(None, target_i=-16.0, target_tp=-1.5, target_lra=11.0)
    assert "loudnorm=" in f
    assert "I=-16.0" in f
    assert "measured_I" not in f


# ---------- ffmpeg 統合 (skip 可) ----------


@_needs_ffmpeg
def test_measure_loudness_finite_for_tone() -> None:
    stats = measure_loudness(_tone_wav())
    assert math.isfinite(stats.input_i)
    assert stats.input_i < 0  # LUFS は負


@_needs_ffmpeg
def test_master_to_mp3_produces_normalized_file(tmp_path: Path) -> None:
    out = tmp_path / "episode.mp3"
    result = master_to_mp3(_tone_wav(), out)
    assert isinstance(result, MasteringResult)
    assert out.exists() and out.stat().st_size > 0
    assert result.audio_format == "mp3"
    assert result.bitrate == MP3_BITRATE
    assert result.sample_rate == OUTPUT_SAMPLE_RATE
    # 出力は実際に target 付近へ正規化されている (±1.5 LU の実務許容)
    assert result.measured_lufs == pytest.approx(TARGET_LUFS, abs=1.5)
    assert result.duration_sec == pytest.approx(2.0, abs=0.2)


@_needs_ffmpeg
def test_master_to_mp3_is_actually_mp3(tmp_path: Path) -> None:
    out = tmp_path / "e.mp3"
    master_to_mp3(_tone_wav(seconds=1.0), out)
    head = out.read_bytes()[:3]
    # MP3: ID3 タグ or フレーム同期ワード 0xFFEx
    assert head[:3] == b"ID3" or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)


@_needs_ffmpeg
def test_master_to_mp3_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "episodes" / "2026-06-17" / "ep.mp3"
    master_to_mp3(_tone_wav(seconds=1.0), out)
    assert out.exists()


@_needs_ffmpeg
def test_master_to_mp3_raises_on_invalid_audio(tmp_path: Path) -> None:
    with pytest.raises(MasteringError):
        master_to_mp3(b"not a wav at all", tmp_path / "x.mp3")
