"""TTS wav signal quality checks."""
from __future__ import annotations

import io
import wave

import pytest

from karyu_tech_news.tts.quality import analyze_wav_signal


def _sample_bytes(sample_width: int, *, loud: bool) -> bytes:
    if sample_width == 1:
        return b"\xff" if loud else b"\x80"
    if sample_width == 2:
        return (32767 if loud else 0).to_bytes(2, "little", signed=True)
    if sample_width == 3:
        return (8388607 if loud else 0).to_bytes(3, "little", signed=True)
    if sample_width == 4:
        return (2147483647 if loud else 0).to_bytes(4, "little", signed=True)
    raise ValueError(f"unsupported sample_width={sample_width}")


def _pcm_frames(
    n_frames: int,
    *,
    sample_width: int = 2,
    channels: int = 1,
    loud: bool,
) -> bytes:
    return _sample_bytes(sample_width, loud=loud) * channels * n_frames


def _wav_from_chunks(
    chunks: list[bytes],
    *,
    sample_rate: int = 1000,
    sample_width: int = 2,
    channels: int = 1,
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        for chunk in chunks:
            w.writeframes(chunk)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("sample_width", "channels"),
    [(1, 1), (2, 1), (3, 1), (4, 1), (2, 2)],
)
def test_analyze_wav_signal_detects_digital_silence(
    sample_width: int,
    channels: int,
) -> None:
    wav = _wav_from_chunks(
        [_pcm_frames(1000, sample_width=sample_width, channels=channels, loud=False)],
        sample_width=sample_width,
        channels=channels,
    )
    stats = analyze_wav_signal(wav)
    assert stats.valid_wav is True
    assert stats.has_pcm_signal is False
    assert stats.max_silence_sec == pytest.approx(1.0)
    assert stats.active_ratio == 0.0


@pytest.mark.parametrize(
    ("sample_width", "channels"),
    [(1, 1), (2, 1), (3, 1), (4, 1), (2, 2)],
)
def test_analyze_wav_signal_detects_signal_across_pcm_formats(
    sample_width: int,
    channels: int,
) -> None:
    wav = _wav_from_chunks(
        [_pcm_frames(1000, sample_width=sample_width, channels=channels, loud=True)],
        sample_width=sample_width,
        channels=channels,
    )
    stats = analyze_wav_signal(wav)
    assert stats.valid_wav is True
    assert stats.has_pcm_signal is True
    assert stats.max_silence_sec == 0.0
    assert stats.active_ratio == pytest.approx(1.0)


def test_analyze_wav_signal_measures_long_silence_gap() -> None:
    loud = _pcm_frames(1000, loud=True)
    silent = _pcm_frames(4500, loud=False)
    wav = _wav_from_chunks([loud, silent, loud])
    stats = analyze_wav_signal(wav)
    assert stats.has_pcm_signal is True
    assert stats.duration_sec == 6.5
    assert 4.4 <= stats.max_silence_sec <= 4.6
    assert stats.active_ratio == pytest.approx(2.0 / 6.5, rel=0.05)


def test_analyze_wav_signal_measures_sparse_click_as_low_activity() -> None:
    click = _pcm_frames(1, loud=True)
    silence = _pcm_frames(999, loud=False)
    wav = _wav_from_chunks([click, silence], sample_rate=1000)
    stats = analyze_wav_signal(wav)
    assert stats.has_pcm_signal is True
    assert stats.duration_sec == 1.0
    assert stats.active_ratio == pytest.approx(0.05)
