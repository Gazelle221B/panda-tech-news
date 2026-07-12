"""video.render のユニットテスト (Sprint 3 T38, FR-110/111/112).

- 純ロジック (filter_complex / ffmpeg 引数構築) は ffmpeg 無しで完全テスト。
- 実 ffmpeg 依存の統合テストは小さなトーン mp3 で、ffmpeg 不在環境では skip。
"""
from __future__ import annotations

import io
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from karyu_tech_news.video.render import (
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    VideoRenderError,
    build_ffmpeg_args,
    build_filter_complex,
    render_video,
)

_HAS_FFMPEG = shutil.which("ffmpeg") is not None
_needs_ffmpeg = pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")


def _tone_wav(*, seconds: float = 1.0, sample_rate: int = 48000) -> bytes:
    n = int(seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            val = int(0.3 * 32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _tone_mp3(tmp_path: Path, *, seconds: float = 1.0) -> Path:
    """統合テスト用の短い mp3 (ffmpeg で wav から変換)."""
    src = tmp_path / "tone.wav"
    src.write_bytes(_tone_wav(seconds=seconds))
    dst = tmp_path / "tone.mp3"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-b:a", "128k", str(dst)],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return dst


def _tiny_png(path: Path) -> Path:
    """小さな単色 PNG (ffmpeg で生成。統合テスト専用 = _needs_ffmpeg 前提)."""
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=64x64:d=1",
            "-frames:v",
            "1",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return path


# ---- 純ロジック: filter_complex ----


def test_filter_complex_with_logo_centers_over_canvas() -> None:
    flt = build_filter_complex(has_logo=True)
    assert f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease" in flt
    assert "overlay=(W-w)/2:(H-h)/2" in flt  # FR-110: ロゴ中央配置
    assert "[2:a]showwaves=" in flt  # ロゴあり時の音声は入力 2
    assert "format=yuv420p" in flt  # FR-112: YouTube 互換ピクセルフォーマット
    assert "-loop" not in flt


def test_filter_complex_without_logo_uses_plain_background() -> None:
    flt = build_filter_complex(has_logo=False)
    assert "scale=" not in flt  # lavfi color はキャンバスサイズで生成済み
    assert "[1:a]showwaves=" in flt  # ロゴなし時の音声は入力 1
    assert "shortest=1" in flt  # 音声尺で終える


# ---- 純ロジック: ffmpeg 引数 ----


def test_build_args_with_logo_adds_image_input(tmp_path: Path) -> None:
    args = build_ffmpeg_args(
        tmp_path / "a.mp3", tmp_path / "o.mp4", logo_path=tmp_path / "logo.png"
    )
    # 壊れた画像でのパーサ無限ループ (ffmpeg hang) を避けるため -loop は使わない
    assert "-loop" not in args
    assert "lavfi" in args  # ベースは常に color ソース
    assert str(tmp_path / "logo.png") in args
    assert args[args.index("-map", args.index("-map") + 1) :][:2] == ["-map", "2:a"]
    assert "-shortest" in args
    assert str(tmp_path / "o.mp4") == args[-1]
    assert "libx264" in args
    assert "aac" in args


def test_build_args_without_logo_uses_lavfi_color(tmp_path: Path) -> None:
    args = build_ffmpeg_args(tmp_path / "a.mp3", tmp_path / "o.mp4", logo_path=None)
    assert "lavfi" in args
    joined = " ".join(args)
    assert f"color=c=0x1A1A2E:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={VIDEO_FPS}" in joined
    assert "1:a" in args  # ロゴなし時の音声 map


# ---- エラー経路 ----


def test_render_missing_audio_raises(tmp_path: Path) -> None:
    with pytest.raises(VideoRenderError, match="入力音声"):
        render_video(tmp_path / "none.mp3", tmp_path / "o.mp4")


# ---- 統合 (実 ffmpeg) ----


@_needs_ffmpeg
def test_render_video_without_logo(tmp_path: Path) -> None:
    mp3 = _tone_mp3(tmp_path)
    result = render_video(mp3, tmp_path / "out" / "ep.mp4")
    out = Path(result.path)
    assert out.exists()
    assert result.size_bytes > 0
    assert result.used_logo is False
    assert (result.width, result.height) == (VIDEO_WIDTH, VIDEO_HEIGHT)


@_needs_ffmpeg
def test_render_video_with_logo(tmp_path: Path) -> None:
    mp3 = _tone_mp3(tmp_path)
    logo = _tiny_png(tmp_path / "logo.png")
    result = render_video(mp3, tmp_path / "ep.mp4", logo_path=logo)
    assert Path(result.path).exists()
    assert result.used_logo is True


@_needs_ffmpeg
def test_render_video_missing_logo_degrades(tmp_path: Path) -> None:
    """ロゴ素材が無い日は単色背景に縮退して配信を止めない (素材ゲート fail-open)."""
    mp3 = _tone_mp3(tmp_path)
    result = render_video(mp3, tmp_path / "ep.mp4", logo_path=tmp_path / "ghost.png")
    assert Path(result.path).exists()
    assert result.used_logo is False


@_needs_ffmpeg
def test_render_video_broken_audio_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"not an mp3")
    with pytest.raises(VideoRenderError, match="エンコード失敗"):
        render_video(bad, tmp_path / "ep.mp4")


@_needs_ffmpeg
def test_render_video_broken_logo_fails_fast(tmp_path: Path) -> None:
    """壊れたロゴ画像はハングせず即エラーになる (旧 -loop 方式の 900s ハング回帰防止)."""
    import time

    mp3 = _tone_mp3(tmp_path)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)  # 不正な PNG
    start = time.monotonic()
    with pytest.raises(VideoRenderError, match="エンコード失敗"):
        render_video(mp3, tmp_path / "ep.mp4", logo_path=broken)
    assert time.monotonic() - start < 60.0
