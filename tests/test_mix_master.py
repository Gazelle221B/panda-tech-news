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


def _silence_wav(*, seconds: float = 1.0, sample_rate: int = 48000) -> bytes:
    """無音 wav (測定不能 -inf になる入力. fail-open 縮退テスト用)."""
    n = int(seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


def _zero_frame_wav(*, sample_rate: int = 48000) -> bytes:
    """0フレーム wav (T28 が全合成失敗時に返す fail-open 産物と同型)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"")
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


def test_parse_loudnorm_stats_raises_on_missing_key() -> None:
    # JSON はあるが必須キー (input_i) 欠落 → MasteringError。
    # 別ブロック誤検出時に 0.0 を「測定成功」と誤認し誤正規化するのを防ぐ (Copilot 指摘)。
    with pytest.raises(MasteringError):
        _parse_loudnorm_stats('[loudnorm]\n{"input_tp":"-3.2","input_lra":"5.4"}')


def test_parse_loudnorm_stats_raises_on_broken_json() -> None:
    # JSON ブロック形だが json.loads 失敗 → MasteringError に統一 (例外型をブレさせない)
    with pytest.raises(MasteringError):
        _parse_loudnorm_stats("{not valid json at all}")


# ---------- 純ロジック: loudnorm フィルタ構築 (ffmpeg 不要) ----------


def test_build_filter_two_pass_includes_measured() -> None:
    stats = _parse_loudnorm_stats(_SAMPLE_LOUDNORM_JSON)
    f = _build_loudnorm_filter(stats, target_i=-16.0, target_tp=-1.5, target_lra=11.0)
    assert f is not None  # 測定可能なので 2-pass フィルタ文字列が返る (型を str に絞る)
    assert "loudnorm=" in f
    assert "I=-16.0" in f
    assert "TP=-1.5" in f
    assert "measured_I=-23.45" in f
    assert "measured_thresh=-33.78" in f
    assert "linear=true" in f


def test_build_filter_none_when_unmeasurable() -> None:
    # 測定不能 (None) のときは loudnorm を通さない (素エンコードへ縮退) → None
    assert _build_loudnorm_filter(None, target_i=-16.0, target_tp=-1.5, target_lra=11.0) is None


def test_build_filter_none_for_inf_stats() -> None:
    # input_i=-inf (無音) でも None。dynamic loudnorm を無音に通すと libmp3lame が
    # 落ちるため、素エンコードへ退避させる (Codex 指摘の fail-open 漏れ修正)。
    silent = LoudnormStats(
        input_i=float("-inf"),
        input_tp=float("-inf"),
        input_lra=0.0,
        input_thresh=float("-inf"),
        target_offset=0.0,
    )
    assert _build_loudnorm_filter(silent, target_i=-16.0, target_tp=-1.5, target_lra=11.0) is None


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


@_needs_ffmpeg
def test_master_to_mp3_handles_silence(tmp_path: Path) -> None:
    # 無音 (測定不能) でも fail-open: loudnorm をスキップしクラッシュせず valid mp3
    out = tmp_path / "silent.mp3"
    res = master_to_mp3(_silence_wav(seconds=1.0), out)
    assert out.exists() and out.stat().st_size > 0
    assert res.audio_format == "mp3"


@_needs_ffmpeg
def test_master_to_mp3_handles_zero_frame_wav(tmp_path: Path) -> None:
    # T28 全滅 fail-open 産物 (0フレーム wav) → 短い無音に退避し valid mp3 を返す
    out = tmp_path / "empty.mp3"
    res = master_to_mp3(_zero_frame_wav(), out)
    assert out.exists() and out.stat().st_size > 0
    assert res.audio_format == "mp3"
