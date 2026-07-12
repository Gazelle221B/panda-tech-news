"""波形動画生成 (Sprint 3 Ticket T38, FR-110/111/112).

完パケ mp3 (T30/T31 の audio_versions 産物) を入力に、番組ロゴの静止画 (FR-110) と
ffmpeg showwaves の簡易波形 (FR-111) を重ねた YouTube 投稿用 mp4 (FR-112) を生成する。

設計判断 (IMPLEMENTATION_PLAN-3 §3.1):
- **依存最小 (AGENTS §5)**: ffmpeg 単発呼び出しで完結する。moviepy/pillow は足さない。
  T30 マスタリングが既に ffmpeg を必須にしているため、新しい実行環境要求は増えない。
- **ロゴ素材はフェイルオープン**: `assets/logo.png` は人間ゲート (素材調達) のため、
  無ければ単色背景に縮退して配信経路を止めない (BGM 素材と同じ扱い, T29)。
- **`-loop 1` の静止画無限ループ入力は使わない**: 壊れた画像を渡すと ffmpeg の
  パーサが同じデータを再解析し続けバッファ枯渇までハングする (実 ffmpeg 8.1 で
  900s タイムアウトを観測)。代わりにベースを常に lavfi color (無限・堅牢) とし、
  ロゴは単一フレーム入力を overlay (既定 repeatlast=1) で静止表示する。
  この構成なら不正画像は数十 ms で fail-fast する。
- **純ロジック分離**: filter_complex 文字列と ffmpeg 引数の構築は純関数にし、
  ffmpeg 不在環境でも大半をテスト可能にする (mix/master.py と同じ流儀)。
- ffmpeg 呼び出しには必ずタイムアウトを付ける (AGENTS §3.3 の精神)。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

VIDEO_WIDTH = 1280  # 720p: 静止画 + 波形にフル HD は過剰で、エンコード時間を抑える
VIDEO_HEIGHT = 720
VIDEO_FPS = 30
WAVE_HEIGHT = 200  # 画面下部の波形帯の高さ (px)
WAVE_BOTTOM_MARGIN = 40  # 波形帯の下マージン (px)
BG_COLOR = "0x1A1A2E"  # ロゴ余白/縮退時の背景 (深紺 — 番組トーンに合わせた暫定値)
WAVE_COLOR = "0x7FD4FF"  # 波形色 (シアン系)
VIDEO_PRESET = "veryfast"  # 静止画背景なので速度優先で十分な画質が出る
VIDEO_CRF = "23"
AUDIO_BITRATE = "192k"  # FR-103 の音声ビットレートを踏襲
AUDIO_SAMPLE_RATE = 48000
FFMPEG_TIMEOUT_SECONDS = 900.0  # 数分のエピソード + 低速マシンの余裕

_MAX_STDERR_LINES = 3


class VideoRenderError(Exception):
    """動画生成 (ffmpeg 実行・出力検証) の失敗."""


class VideoRenderResult(BaseModel):
    """生成した mp4 のメタデータ (video_versions 永続化 T40 の証跡)."""

    path: str
    width: int
    height: int
    fps: int
    size_bytes: int
    used_logo: bool  # False = ロゴ素材無しで単色背景に縮退した


def _ensure_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise VideoRenderError("ffmpeg が見つかりません (T38 動画生成に必須)")
    return ffmpeg


def build_filter_complex(
    *,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = VIDEO_FPS,
    wave_height: int = WAVE_HEIGHT,
    wave_bottom_margin: int = WAVE_BOTTOM_MARGIN,
    wave_color: str = WAVE_COLOR,
    has_logo: bool,
) -> str:
    """ffmpeg filter_complex 文字列を組む (純関数).

    - 入力 0 = lavfi color 背景 (常時)。ロゴありなら入力 1 = ロゴ画像、最後の入力 = 音声。
    - ロゴはアスペクト比を保ってキャンバスに収め、中央配置で overlay する (FR-110)。
      単一フレームでも overlay 既定の repeatlast=1 で静止表示が続く。
    - showwaves の帯を下部にオーバーレイ (FR-111)。`shortest=1` で音声尺に合わせて終える。
    """
    audio_idx = 2 if has_logo else 1
    parts: list[str] = []
    if has_logo:
        parts.append(
            f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease[logo]"
        )
        parts.append("[0:v][logo]overlay=(W-w)/2:(H-h)/2[bg0]")
        parts.append("[bg0]setsar=1[bg]")
    else:
        parts.append("[0:v]setsar=1[bg]")
    parts.append(
        f"[{audio_idx}:a]showwaves=s={width}x{wave_height}:mode=cline"
        f":colors={wave_color}:rate={fps}[wave]"
    )
    parts.append(
        f"[bg][wave]overlay=0:H-h-{wave_bottom_margin}:shortest=1,format=yuv420p[v]"
    )
    return ";".join(parts)


def build_ffmpeg_args(
    audio_path: Path,
    output_path: Path,
    *,
    logo_path: Path | None,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = VIDEO_FPS,
) -> list[str]:
    """ffmpeg 引数リストを組む (純関数。先頭の ffmpeg バイナリ名は含まない)."""
    inputs = ["-f", "lavfi", "-i", f"color=c={BG_COLOR}:s={width}x{height}:r={fps}"]
    if logo_path is not None:
        inputs += ["-i", str(logo_path)]
    audio_idx = 2 if logo_path is not None else 1
    flt = build_filter_complex(
        width=width, height=height, fps=fps, has_logo=logo_path is not None
    )
    return [
        "-y",
        *inputs,
        "-i",
        str(audio_path),
        "-filter_complex",
        flt,
        "-map",
        "[v]",
        "-map",
        f"{audio_idx}:a",
        "-c:v",
        "libx264",
        "-preset",
        VIDEO_PRESET,
        "-crf",
        VIDEO_CRF,
        "-c:a",
        "aac",
        "-b:a",
        AUDIO_BITRATE,
        "-ar",
        str(AUDIO_SAMPLE_RATE),
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def render_video(
    audio_path: Path | str,
    output_path: Path | str,
    *,
    logo_path: Path | str | None = None,
) -> VideoRenderResult:
    """完パケ mp3 から波形動画 mp4 を生成する (FR-110/111/112).

    ロゴ画像が指定されないか存在しない場合は単色背景に縮退する (fail-open)。
    ffmpeg の失敗・出力欠落・空出力は VideoRenderError に正規化する (fail-fast)。
    """
    src = Path(audio_path)
    if not src.exists():
        raise VideoRenderError(f"入力音声が見つかりません: {src.name}")
    logo: Path | None = Path(logo_path) if logo_path is not None else None
    if logo is not None and not logo.exists():
        logo = None  # 素材待ちでも経路を止めない (IMPLEMENTATION_PLAN-3 §3.1)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = _ensure_ffmpeg()
    args = build_ffmpeg_args(src, out, logo_path=logo)
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", *args],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoRenderError(f"ffmpeg タイムアウト ({FFMPEG_TIMEOUT_SECONDS}s)") from exc

    if proc.returncode != 0 or not out.exists():
        tail = proc.stderr.strip().splitlines()[-_MAX_STDERR_LINES:]
        raise VideoRenderError("mp4 エンコード失敗: " + " / ".join(tail))
    size = out.stat().st_size
    if size == 0:
        out.unlink(missing_ok=True)
        raise VideoRenderError("mp4 出力が空です (ffmpeg は成功を報告したが 0 バイト)")

    return VideoRenderResult(
        path=str(out),
        width=VIDEO_WIDTH,
        height=VIDEO_HEIGHT,
        fps=VIDEO_FPS,
        size_bytes=size,
        used_logo=logo is not None,
    )
