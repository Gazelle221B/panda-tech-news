"""SFX トランジション挿入 (Sprint 2+ Ticket T62, Issue #65).

produce が segment (トピック) ごとに個別合成した wav バイト列のリストを、トピック間
だけに短い SFX (トランジション音) を挟んで 1 本の wav に連結する。イントロ前・最終
トピック後には挿入しない (トピック間のみ)。

依存方向 (`docs/architecture.md` §1, `docs/IMPLEMENTATION_PLAN-2.md` §3 `script → tts →
mix` 一方向): mix 層は tts/script を import しない。本モジュールは wav バイト列のみを
受け取り、`tts/synthesize.py` の内部実装 (`_concat_wav_with_stats`) には依存せず、
同等の単純連結ロジックを本モジュール内に独立して持つ (styleguide §1 Surgical Changes:
レイヤー境界を跨がない)。

設計判断:
- **fail-open**: SFX 素材が無い/欠落、segment が 1 個以下、または ffmpeg 実行自体が
  失敗した場合は SFX なしの単純連結へ縮退する。SFX 音源は Issue #65 スコープB
  (人間試聴・採用) 待ちのため、`sfx.enabled: false` の既定運用でも produce の挙動は
  一切変えない (呼び出し側 main.py が enabled 判定を持つ)。
- SFX 挿入は ffmpeg concat フィルタで行う (`mix/master.py` の ffmpeg 呼び出し流儀を踏襲:
  タイムアウト必須・stderr 末尾を WARN ログに残す)。SFX のサンプルレート/チャンネル数は
  先頭セグメントの形式を基準に `aformat`/`aresample` で自動整合し、`volume={sfx_gain_db}dB`
  で減衰する。同一 SFX ファイルをトピック間の数だけ複数回 `-i` する単純な構成にし、
  filter label の暗黙 fan-out には頼らない。
"""
from __future__ import annotations

import io
import logging
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SFX_GAIN_DB = -6.0  # TTS 音声比の減衰量目安 (Issue #65)
FFMPEG_TIMEOUT_SECONDS = 120.0  # SFX 挿入は完パケマスタリングより短時間で完結する想定
_FALLBACK_SAMPLE_RATE = 48000  # 空入力時の無音 wav 用 (tts/synthesize.py の既定値と同値)


def _silent_wav(sample_rate: int = _FALLBACK_SAMPLE_RATE) -> bytes:
    """0 フレームの有効な wav (16bit/mono). 全滅時も下流が wave.open で落ちないように."""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"")
    return out.getvalue()


def _concat_wav_simple(chunks: list[bytes]) -> bytes:
    """ffmpeg を使わない素の wav 連結 (SFX 無し経路).

    tts/synthesize.py の `_concat_wav_with_stats` と同等のロジック (先頭 chunk の
    パラメータを基準にパラメータ不一致/壊れた chunk を fail-open で skip、有効 chunk
    ゼロなら無音 wav) を mix 層側で独立して持つ (レイヤー境界を跨がないため)。
    """
    params: tuple[int, int, int] | None = None
    frames: list[bytes] = []
    for chunk in chunks:
        try:
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                cur = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
                nframes = reader.getnframes()
                data = reader.readframes(nframes)
        except (wave.Error, EOFError) as exc:
            logger.warning("壊れた segment wav を skip (fail-open): %s", exc)
            continue
        if nframes == 0:
            continue
        if params is None:
            params = cur
        elif cur != params:
            logger.warning("segment wav パラメータ不一致 %s != %s, skip (fail-open)", cur, params)
            continue
        frames.append(data)
    if params is None:
        return _silent_wav()
    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        writer.setnchannels(params[0])
        writer.setsampwidth(params[1])
        writer.setframerate(params[2])
        for data in frames:
            writer.writeframes(data)
    return out.getvalue()


def _wav_format(wav_bytes: bytes) -> tuple[int, int] | None:
    """(channels, sample_rate) を返す. 不正 wav は None."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as reader:
            return reader.getnchannels(), reader.getframerate()
    except (wave.Error, EOFError):
        return None


def _build_ffmpeg_concat(
    seg_paths: list[Path],
    sfx_path: Path,
    out_path: Path,
    *,
    channels: int,
    sample_rate: int,
    sfx_gain_db: float,
) -> list[str]:
    """[seg0, sfx, seg1, sfx, ..., segN-1] を concat する ffmpeg コマンドを組む."""
    layout = "mono" if channels == 1 else "stereo"
    inputs: list[Path] = []
    filters: list[str] = []
    labels: list[str] = []
    for i, seg_path in enumerate(seg_paths):
        idx = len(inputs)
        inputs.append(seg_path)
        label = f"a{idx}"
        filters.append(
            f"[{idx}:a]aformat=sample_rates={sample_rate}:channel_layouts={layout}[{label}]"
        )
        labels.append(label)
        if i < len(seg_paths) - 1:  # トピック間のみ (先頭前・末尾後には入れない)
            idx = len(inputs)
            inputs.append(sfx_path)
            label = f"a{idx}"
            filters.append(
                f"[{idx}:a]volume={sfx_gain_db}dB,aresample={sample_rate},"
                f"aformat=sample_rates={sample_rate}:channel_layouts={layout}[{label}]"
            )
            labels.append(label)

    concat_inputs = "".join(f"[{lbl}]" for lbl in labels)
    filter_complex = ";".join(filters) + f";{concat_inputs}concat=n={len(labels)}:v=0:a=1[out]"

    args = ["-hide_banner", "-nostats", "-y"]
    for p in inputs:
        args += ["-i", str(p)]
    args += [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "pcm_s16le",
        str(out_path),
    ]
    return args


def concat_with_transitions(
    segment_wavs: list[bytes],
    sfx_path: Path | None,
    *,
    sfx_gain_db: float = DEFAULT_SFX_GAIN_DB,
) -> bytes:
    """複数 segment の wav をトピック間 SFX 付きで 1 本に連結する (T62, Issue #65).

    SFX はトピック間のみに挿入する (先頭セグメント前・末尾セグメント後には入れない)。
    `sfx_path` が None/存在しない、または segment が 1 個以下なら SFX なしの単純連結に
    なる (`sfx.enabled: false` の既定運用ではこの分岐のみを通り、挙動は一切変わらない)。
    ffmpeg 未導入・実行失敗・タイムアウトは WARN ログの上で単純連結へ fail-open する。
    """
    if sfx_path is None or not sfx_path.exists() or len(segment_wavs) <= 1:
        return _concat_wav_simple(segment_wavs)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        logger.warning("ffmpeg が見つかりません。SFX なしの単純連結にフォールバック (fail-open)")
        return _concat_wav_simple(segment_wavs)

    fmt = _wav_format(segment_wavs[0])
    if fmt is None:
        logger.warning("先頭 segment wav が不正。SFX なしの単純連結にフォールバック (fail-open)")
        return _concat_wav_simple(segment_wavs)
    channels, sample_rate = fmt

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            seg_paths = []
            for i, wav_bytes in enumerate(segment_wavs):
                p = tmp / f"seg_{i}.wav"
                p.write_bytes(wav_bytes)
                seg_paths.append(p)

            out_path = tmp / "out.wav"
            args = _build_ffmpeg_concat(
                seg_paths,
                sfx_path,
                out_path,
                channels=channels,
                sample_rate=sample_rate,
                sfx_gain_db=sfx_gain_db,
            )
            proc = subprocess.run(
                [ffmpeg, *args],
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT_SECONDS,
                check=False,
            )
            if proc.returncode != 0 or not out_path.exists():
                tail = proc.stderr.strip().splitlines()[-3:]
                raise RuntimeError("ffmpeg concat 失敗: " + " / ".join(tail))
            return out_path.read_bytes()
    except (subprocess.TimeoutExpired, OSError, RuntimeError) as exc:
        logger.warning(
            "SFX 挿入 concat に失敗、SFX なしの単純連結にフォールバック (fail-open): %s", exc
        )
        return _concat_wav_simple(segment_wavs)
