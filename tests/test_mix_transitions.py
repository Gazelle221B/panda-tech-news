"""mix.transitions のユニットテスト (Sprint 2+ Ticket T62, Issue #65).

SFX 無し単純連結 (常時テスト可) と ffmpeg 依存の実 SFX 挿入経路 (`shutil.which("ffmpeg")`
不在なら skip、`tests/test_mix_master.py` の流儀を踏襲) の両方を検証する。ffmpeg 失敗系は
`subprocess.run` をモックし、実 ffmpeg の有無に関わらず fail-open 経路を検証する。
"""
from __future__ import annotations

import io
import logging
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from karyu_tech_news.mix.transitions import concat_with_transitions

_HAS_FFMPEG = shutil.which("ffmpeg") is not None
_needs_ffmpeg = pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg 不在")


def _tone_wav(
    *, seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 48000, amp: float = 0.6
) -> bytes:
    """信号入りの 16bit/mono wav (SFX ダミー素材・信号確認用)."""
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
    n = int(seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


def _wav_duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        return r.getnframes() / r.getframerate() if r.getframerate() else 0.0


def _wav_params(wav_bytes: bytes) -> tuple[int, int, int, int]:
    """(nchannels, sampwidth, framerate, nframes)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        return r.getnchannels(), r.getsampwidth(), r.getframerate(), r.getnframes()


def _rms_window(wav_bytes: bytes, start_sec: float, end_sec: float) -> float:
    """[start_sec, end_sec) の 16bit PCM サンプルの RMS を返す (無音判別用)."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        rate = r.getframerate()
        r.setpos(max(0, int(start_sec * rate)))
        n = max(0, int((end_sec - start_sec) * rate))
        raw = r.readframes(n)
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


# ---------- SFX 無し単純連結 (ffmpeg 不要, 常時実行) ----------


def test_concat_single_segment_ignores_sfx_path(tmp_path: Path) -> None:
    """segment が 1 個なら sfx_path があっても SFX なし単純連結になる."""
    seg = _tone_wav(seconds=1.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=0.5, freq=880.0))

    out = concat_with_transitions([seg], sfx_path)
    assert _wav_params(out) == _wav_params(seg)
    assert _wav_duration_seconds(out) == pytest.approx(1.0, abs=1e-6)


def test_concat_none_sfx_path_is_simple_concat(tmp_path: Path) -> None:
    seg0 = _tone_wav(seconds=1.0)
    seg1 = _tone_wav(seconds=2.0, freq=880.0)
    out = concat_with_transitions([seg0, seg1], None)
    assert _wav_duration_seconds(out) == pytest.approx(3.0, abs=1e-6)


def test_concat_missing_sfx_file_is_simple_concat(tmp_path: Path) -> None:
    seg0 = _tone_wav(seconds=1.0)
    seg1 = _tone_wav(seconds=1.0, freq=880.0)
    out = concat_with_transitions([seg0, seg1], tmp_path / "missing.wav")
    assert _wav_duration_seconds(out) == pytest.approx(2.0, abs=1e-6)


def test_concat_empty_segment_list_returns_valid_silent_wav() -> None:
    out = concat_with_transitions([], None)
    # 空入力でも wave.open で読める有効な wav (0 フレーム) を返す (下流が壊れないように)。
    assert _wav_params(out)[3] == 0


def test_concat_simple_skips_corrupt_and_mismatched_chunks(caplog: pytest.LogCaptureFixture) -> None:
    good = _tone_wav(seconds=1.0, sample_rate=48000)
    mismatched_rate = _tone_wav(seconds=1.0, sample_rate=24000)
    corrupt = b"not a wav at all"
    with caplog.at_level(logging.WARNING):
        out = concat_with_transitions([good, mismatched_rate, corrupt], None)
    # 先頭 chunk (48000Hz) のみ採用され、パラメータ不一致とデコード不能は skip される。
    assert _wav_duration_seconds(out) == pytest.approx(1.0, abs=1e-6)
    assert "パラメータ不一致" in caplog.text
    assert "壊れた segment wav" in caplog.text


# ---------- fail-open (ffmpeg 呼び出しをモック, 実 ffmpeg 不要) ----------


def test_concat_ffmpeg_missing_falls_back_to_simple_concat(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    seg0 = _tone_wav(seconds=1.0)
    seg1 = _tone_wav(seconds=1.0, freq=880.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=0.5))

    with (
        patch("karyu_tech_news.mix.transitions.shutil.which", return_value=None),
        caplog.at_level(logging.WARNING),
    ):
        out = concat_with_transitions([seg0, seg1], sfx_path)
    assert "ffmpeg が見つかりません" in caplog.text
    # フォールバックは SFX なし単純連結 (SFX の 0.5s は含まれない)
    assert _wav_duration_seconds(out) == pytest.approx(2.0, abs=1e-6)


def test_concat_ffmpeg_nonzero_exit_falls_back_to_simple_concat(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    seg0 = _tone_wav(seconds=1.0)
    seg1 = _tone_wav(seconds=1.0, freq=880.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=0.5))

    fake_proc = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="boom\nffmpeg error detail"
    )
    with (
        patch("karyu_tech_news.mix.transitions.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("karyu_tech_news.mix.transitions.subprocess.run", return_value=fake_proc),
        caplog.at_level(logging.WARNING),
    ):
        out = concat_with_transitions([seg0, seg1], sfx_path)
    assert "SFX 挿入 concat に失敗" in caplog.text
    assert _wav_duration_seconds(out) == pytest.approx(2.0, abs=1e-6)


def test_concat_ffmpeg_timeout_falls_back_to_simple_concat(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    seg0 = _tone_wav(seconds=1.0)
    seg1 = _tone_wav(seconds=1.0, freq=880.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=0.5))

    with (
        patch("karyu_tech_news.mix.transitions.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch(
            "karyu_tech_news.mix.transitions.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120.0),
        ),
        caplog.at_level(logging.WARNING),
    ):
        out = concat_with_transitions([seg0, seg1], sfx_path)
    assert "SFX 挿入 concat に失敗" in caplog.text
    assert _wav_duration_seconds(out) == pytest.approx(2.0, abs=1e-6)


def test_concat_corrupt_first_segment_falls_back_before_invoking_ffmpeg(
    tmp_path: Path,
) -> None:
    """先頭 segment が不正 wav だと形式判定できず ffmpeg を呼ばずにフォールバックする."""
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=0.5))
    with (
        patch("karyu_tech_news.mix.transitions.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("karyu_tech_news.mix.transitions.subprocess.run") as run,
    ):
        out = concat_with_transitions([b"not a wav", _tone_wav(seconds=1.0)], sfx_path)
    run.assert_not_called()
    assert _wav_duration_seconds(out) == pytest.approx(1.0, abs=1e-6)  # 壊れた1本目は skip


# ---------- 実 ffmpeg 統合 (skip 可) ----------


@_needs_ffmpeg
def test_concat_with_transitions_inserts_sfx_between_topics_only(tmp_path: Path) -> None:
    """SFX はトピック間のみに挿入され、先頭前・末尾後には入らない."""
    seg0 = _silence_wav(seconds=2.0)
    seg1 = _silence_wav(seconds=2.0)
    seg2 = _silence_wav(seconds=2.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=1.0, freq=880.0, amp=0.8))

    out = concat_with_transitions([seg0, seg1, seg2], sfx_path, sfx_gain_db=0.0)

    # 3 segment (2s) + 2 SFX 挿入 (1s) = 8s
    assert _wav_duration_seconds(out) == pytest.approx(8.0, abs=0.2)

    # segment 区間 (無音) は静か、SFX 挿入区間 (2.0-3.0s, 5.0-6.0s) は信号あり。
    assert _rms_window(out, 0.2, 1.8) < 200
    assert _rms_window(out, 2.2, 2.8) > 3000
    assert _rms_window(out, 3.2, 4.8) < 200
    assert _rms_window(out, 5.2, 5.8) > 3000
    assert _rms_window(out, 6.2, 7.8) < 200


@_needs_ffmpeg
def test_concat_with_transitions_applies_gain(tmp_path: Path) -> None:
    seg0 = _silence_wav(seconds=1.0)
    seg1 = _silence_wav(seconds=1.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=1.0, freq=880.0, amp=0.8))

    loud = concat_with_transitions([seg0, seg1], sfx_path, sfx_gain_db=0.0)
    quiet = concat_with_transitions([seg0, seg1], sfx_path, sfx_gain_db=-18.0)

    loud_rms = _rms_window(loud, 1.2, 1.8)
    quiet_rms = _rms_window(quiet, 1.2, 1.8)
    assert loud_rms > 1000
    ratio = quiet_rms / loud_rms
    assert ratio == pytest.approx(10 ** (-18 / 20), rel=0.2)


@_needs_ffmpeg
def test_concat_with_transitions_produces_valid_wav_container(tmp_path: Path) -> None:
    seg0 = _silence_wav(seconds=1.0)
    seg1 = _silence_wav(seconds=1.0)
    sfx_path = tmp_path / "sfx.wav"
    sfx_path.write_bytes(_tone_wav(seconds=0.5))

    out = concat_with_transitions([seg0, seg1], sfx_path)
    assert out[:4] == b"RIFF"
    assert out[8:12] == b"WAVE"
