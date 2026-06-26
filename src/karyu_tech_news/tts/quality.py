"""TTS wav の機械的品質チェック.

produce 境界で「音声として成立しているか」を見るための軽量検査。
BGM を混ぜる前の TTS wav に対して使い、BGM が無音ギャップを覆い隠すのを避ける。
"""
from __future__ import annotations

import io
import sys
import wave
from array import array
from dataclasses import dataclass


@dataclass(frozen=True)
class WavSignalStats:
    """TTS wav の信号状態."""

    valid_wav: bool
    duration_sec: float
    has_pcm_signal: bool
    max_silence_sec: float
    active_ratio: float


def _peak_ratio(fragment: bytes, sample_width: int) -> float:
    if not fragment:
        return 0.0
    if sample_width == 1:
        peak = max(abs(byte - 128) for byte in fragment)
        return peak / 128.0
    if sample_width == 2:
        samples = array("h")
        samples.frombytes(fragment[: len(fragment) - (len(fragment) % 2)])
        if sys.byteorder != "little":
            samples.byteswap()
        peak = max((abs(sample) for sample in samples), default=0)
        return peak / 32768.0
    if sample_width == 4:
        samples = array("i")
        samples.frombytes(fragment[: len(fragment) - (len(fragment) % 4)])
        if sys.byteorder != "little":
            samples.byteswap()
        peak = max((abs(sample) for sample in samples), default=0)
        return peak / 2147483648.0
    if sample_width == 3:
        peak = 0
        usable = len(fragment) - (len(fragment) % 3)
        for i in range(0, usable, 3):
            sample = int.from_bytes(fragment[i : i + 3], "little", signed=True)
            peak = max(peak, abs(sample))
        return peak / 8388608.0
    return 1.0 if any(byte != 0 for byte in fragment) else 0.0


def analyze_wav_signal(
    audio_wav: bytes,
    *,
    silence_threshold_ratio: float = 0.01,
    window_sec: float = 0.05,
) -> WavSignalStats:
    """wav の最大連続無音時間と信号有無を計測する.

    `has_pcm_signal` は完全なデジタル無音を検出するため、0 でないサンプルがあれば真。
    `max_silence_sec` はノイズ床を考慮し、window の peak が閾値以下なら無音として数える。
    """
    try:
        with wave.open(io.BytesIO(audio_wav), "rb") as reader:
            channels = max(1, reader.getnchannels())
            sample_width = reader.getsampwidth()
            frame_rate = reader.getframerate()
            frame_count = reader.getnframes()
            frames = reader.readframes(frame_count)
    except (wave.Error, EOFError):
        return WavSignalStats(
            valid_wav=False,
            duration_sec=0.0,
            has_pcm_signal=False,
            max_silence_sec=0.0,
            active_ratio=0.0,
        )

    duration_sec = frame_count / frame_rate if frame_rate else 0.0
    if frame_count <= 0 or frame_rate <= 0 or sample_width <= 0:
        return WavSignalStats(
            valid_wav=True,
            duration_sec=duration_sec,
            has_pcm_signal=False,
            max_silence_sec=duration_sec,
            active_ratio=0.0,
        )

    frame_size = channels * sample_width
    window_frames = max(1, int(frame_rate * window_sec))
    window_bytes = max(frame_size, window_frames * frame_size)
    max_silence_sec = 0.0
    current_silence_sec = 0.0
    active_sec = 0.0
    has_pcm_signal = False

    for offset in range(0, len(frames), window_bytes):
        fragment = frames[offset : offset + window_bytes]
        peak = _peak_ratio(fragment, sample_width)
        fragment_frames = len(fragment) // frame_size
        fragment_sec = fragment_frames / frame_rate
        if peak > 0.0:
            has_pcm_signal = True
        if peak <= silence_threshold_ratio:
            current_silence_sec += fragment_sec
            max_silence_sec = max(max_silence_sec, current_silence_sec)
        else:
            active_sec += fragment_sec
            current_silence_sec = 0.0

    return WavSignalStats(
        valid_wav=True,
        duration_sec=duration_sec,
        has_pcm_signal=has_pcm_signal,
        max_silence_sec=max_silence_sec,
        active_ratio=active_sec / duration_sec if duration_sec else 0.0,
    )
