"""SFX トランジション挿入 (Sprint 2+ Ticket T62, Issue #65).

produce が segment (トピック) ごとに個別合成した wav バイト列のリストを、
`[opening?, seg0, transition, seg1, transition, ..., segN-1, ending?]` の順に SFX を
挟んで 1 本の wav に連結する。transition はトピック間のみに挿入する (先頭セグメント前・
最終セグメント後には入れない)。opening/ending はセグメント数に関わらず先頭前・末尾後に
それぞれ独立して挿入できる。

依存方向 (`docs/architecture.md` §1, `docs/IMPLEMENTATION_PLAN-2.md` §3 `script → tts →
mix` 一方向): mix 層は tts/script を import しない。本モジュールは wav バイト列のみを
受け取り、`tts/synthesize.py` の内部実装 (`_concat_wav_with_stats`) には依存せず、
同等の単純連結ロジックを本モジュール内に独立して持つ (styleguide §1 Surgical Changes:
レイヤー境界を跨がない)。

設計判断:
- **fail-open (種類ごとに独立)**: opening/transition/ending はそれぞれ個別に「未指定
  (None) / ファイル欠落」を判定し、欠落したものだけを挿入せずスキップする (他の2種が
  有効なら通常どおり挿入される)。SFX 素材が全て無い、または ffmpeg 実行自体が失敗した
  場合は SFX なしの単純連結へ縮退する。`sfx.enabled: false` の既定運用でも produce の
  挙動は一切変えない (呼び出し側 main.py が enabled 判定を持つ)。
- SFX 挿入は ffmpeg concat フィルタで行う (`mix/master.py` の ffmpeg 呼び出し流儀を踏襲:
  タイムアウト必須・stderr 末尾を WARN ログに残す)。SFX のサンプルレート/チャンネル数は
  先頭セグメントの形式を基準に `aformat`/`aresample` で自動整合し、種類別のゲイン
  (`{transition,opening,ending}_gain_db`) を適用する。同一 SFX ファイルを挿入箇所の数
  だけ複数回 `-i` する単純な構成にし、filter label の暗黙 fan-out には頼らない。
"""
from __future__ import annotations

import io
import logging
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# 種類別ゲイン既定値 (Issue #65, 2026-08-01 プロダクトオーナー選定音源の実測に基づく目安)。
# 後段の BGM ミックス + loudnorm が全体のラウドネスを揃えるため、ここでは TTS 音声との
# 相対バランスのみを担保する。
DEFAULT_TRANSITION_GAIN_DB = -6.0
DEFAULT_OPENING_GAIN_DB = -3.0
DEFAULT_ENDING_GAIN_DB = -3.0

FFMPEG_TIMEOUT_SECONDS = 120.0  # SFX 挿入は完パケマスタリングより短時間で完結する想定
_FALLBACK_SAMPLE_RATE = 48000  # 空入力時の無音 wav 用 (tts/synthesize.py の既定値と同値)


@dataclass(frozen=True)
class _SfxPiece:
    """挿入対象の SFX 1件 (ファイルパス + 適用ゲイン)."""

    path: Path
    gain_db: float


def _resolve_sfx(path: Path | None, gain_db: float) -> _SfxPiece | None:
    """path が None/欠落なら None (fail-open, その種類だけ挿入しない)."""
    if path is None or not path.exists():
        return None
    return _SfxPiece(path=path, gain_db=gain_db)


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
    out_path: Path,
    *,
    opening: _SfxPiece | None,
    transition: _SfxPiece | None,
    ending: _SfxPiece | None,
    channels: int,
    sample_rate: int,
) -> list[str]:
    """[opening?, seg0, transition, seg1, ..., segN-1, ending?] を concat する ffmpeg コマンドを組む."""
    layout = "mono" if channels == 1 else "stereo"
    inputs: list[Path] = []
    filters: list[str] = []
    labels: list[str] = []

    def _add(path: Path, *, gain_db: float | None) -> None:
        idx = len(inputs)
        inputs.append(path)
        label = f"a{idx}"
        if gain_db is None:  # segment (TTS 音声) はゲイン調整しない
            filters.append(
                f"[{idx}:a]aformat=sample_rates={sample_rate}:channel_layouts={layout}[{label}]"
            )
        else:
            filters.append(
                f"[{idx}:a]volume={gain_db}dB,aresample={sample_rate},"
                f"aformat=sample_rates={sample_rate}:channel_layouts={layout}[{label}]"
            )
        labels.append(label)

    if opening is not None:
        _add(opening.path, gain_db=opening.gain_db)
    for i, seg_path in enumerate(seg_paths):
        _add(seg_path, gain_db=None)
        if transition is not None and i < len(seg_paths) - 1:  # トピック間のみ
            _add(transition.path, gain_db=transition.gain_db)
    if ending is not None:
        _add(ending.path, gain_db=ending.gain_db)

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
    *,
    transition_path: Path | None = None,
    opening_path: Path | None = None,
    ending_path: Path | None = None,
    transition_gain_db: float = DEFAULT_TRANSITION_GAIN_DB,
    opening_gain_db: float = DEFAULT_OPENING_GAIN_DB,
    ending_gain_db: float = DEFAULT_ENDING_GAIN_DB,
) -> bytes:
    """複数 segment の wav を opening/transition/ending SFX 付きで 1 本に連結する (T62, Issue #65).

    出力順は `[opening?, seg0, transition, seg1, transition, ..., segN-1, ending?]`。
    transition はトピック間のみに挿入する (先頭セグメント前・最終セグメント後には入れない)。
    opening/ending はセグメント数に関わらず独立して先頭前・末尾後に挿入できる。

    各 `*_path` は None/存在しない場合に個別に fail-open する (その種類だけ挿入しない)。
    3種すべて未指定・欠落なら SFX なしの単純連結になる (`sfx.enabled: false` の既定運用
    ではこの分岐のみを通り、挙動は一切変わらない)。ffmpeg 未導入・実行失敗・タイムアウトも
    WARN ログの上で単純連結へ fail-open する。
    """
    opening = _resolve_sfx(opening_path, opening_gain_db)
    transition = _resolve_sfx(transition_path, transition_gain_db)
    ending = _resolve_sfx(ending_path, ending_gain_db)

    if not segment_wavs:
        return _concat_wav_simple(segment_wavs)
    if opening is None and ending is None and (transition is None or len(segment_wavs) <= 1):
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
                out_path,
                opening=opening,
                transition=transition,
                ending=ending,
                channels=channels,
                sample_rate=sample_rate,
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
