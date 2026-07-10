"""mix.mixer の実 BGM ミックス経路 (T29) のユニットテスト (T48).

BGM 素材はライセンス人間ゲート待ちで `assets/bgm/` に不在のため、これまでは
passthrough (素材なし) 経路しかテストされていなかった (`tests/test_produce_pipeline.py`)。
本ファイルは pydub が導入されている環境限定で、ダミー wav を BGM 素材として渡し、
`mix_bgm` の実ミックス経路 (ループ・切り詰め・フェード・overlay・export) を検証する。

pydub は optional extra `tts` のため、未導入環境では ``importorskip`` で自動 skip する
(`tests/test_mix_master.py` の ffmpeg skipif と同じ流儀: 依存が無い環境を壊さない)。
"""
from __future__ import annotations

import io
import logging
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from karyu_tech_news.mix.mixer import mix_bgm

pytest.importorskip("pydub")
from pydub import AudioSegment  # noqa: E402  (importorskip 後の遅延 import)

if shutil.which("ffmpeg") is None:
    pytest.skip(
        "ffmpeg 不在 (pydub の実ミックス経路は ffmpeg に依存するため skip)",
        allow_module_level=True,
    )


def _tone_wav(
    *, seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 48000, amp: float = 0.5
) -> bytes:
    """信号入りの 16bit/mono wav (BGM ダミー素材・信号確認用)."""
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
    """無音 wav (ナレーション役. BGM の寄与だけを分離して観測するため無音にする)."""
    n = int(seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


def _zero_frame_wav(*, sample_rate: int = 48000) -> bytes:
    """0フレーム wav (BGM 素材が空扱いされるケースの再現用)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"")
    return buf.getvalue()


def _decode(wav_bytes: bytes) -> AudioSegment:
    return AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")


# ---------- 実ミックス経路 (BGM 素材あり) ----------


def test_mix_bgm_output_matches_voice_duration(tmp_path: Path) -> None:
    """出力長はナレーション長に一致する (BGM 長に引きずられない)."""
    voice = _silence_wav(seconds=6.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=2.0, freq=220.0))

    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=500)
    seg = _decode(out)
    assert len(seg) == pytest.approx(len(_decode(voice)), abs=20)


def test_mix_bgm_produces_valid_wav_container(tmp_path: Path) -> None:
    """export(format="wav") が正しい RIFF/WAVE コンテナを返す."""
    voice = _silence_wav(seconds=2.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=1.0))

    out = mix_bgm(voice, bgm_path=bgm_path)
    assert out[:4] == b"RIFF"
    assert out[8:12] == b"WAVE"


def test_mix_bgm_loops_short_bgm_across_full_voice(tmp_path: Path) -> None:
    """BGM (2秒) がナレーション (6秒) よりも短い場合、全編にループして敷かれる."""
    voice = _silence_wav(seconds=6.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=2.0, freq=220.0, amp=0.8))

    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=500)
    seg = _decode(out)
    # フェード区間 (先頭・末尾 500ms) を避けた中間区間 (2.5s-4.5s) は
    # BGM がループし続けていれば十分な RMS を持つ (信号が変化=passthrough でない)。
    middle = seg[2500:4500]
    assert middle.rms > 1000  # 無音ナレーションのみなら rms は 0 に近いはず


def test_mix_bgm_truncates_bgm_longer_than_voice(tmp_path: Path) -> None:
    """BGM (5秒) がナレーション (1秒) より長い場合、ナレーション長へ切り詰められる."""
    voice = _silence_wav(seconds=1.0)
    bgm_path = tmp_path / "long_bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=5.0, freq=220.0, amp=0.8))

    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=100)
    seg = _decode(out)
    assert len(seg) == pytest.approx(1000, abs=20)  # 5000ms ではなく 1000ms


def test_mix_bgm_applies_fade_in_and_out(tmp_path: Path) -> None:
    """前後がフェードされ、端の RMS が中間より小さい (唐突な開始/終了を避ける)."""
    voice = _silence_wav(seconds=6.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=1.0, freq=220.0, amp=0.8))

    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=1000)
    seg = _decode(out)
    head = seg[0:200]
    middle = seg[2500:3500]
    tail = seg[-200:]
    assert 0 < head.rms < middle.rms  # 先頭はフェード中 (無音ではないが弱い)
    assert 0 < tail.rms < middle.rms  # 末尾も同様にフェードアウト
    assert middle.rms > 1000  # 中間はフェードの影響を受けずしっかり鳴っている


def test_mix_bgm_fade_zero_disables_fade_without_crashing(tmp_path: Path) -> None:
    """fade_ms=0 (フェード無効化) でも BGM 自体は正常に敷かれる.

    (T48 で発見: pydub の fade_in(0)/fade_out(0) は内部で
    TypeError (None - int) を送出し、修正前は fail-open で BGM が
    まるごと passthrough に縮退していた。)
    """
    voice = _silence_wav(seconds=4.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=2.0, freq=220.0, amp=0.8))

    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=0)
    seg = _decode(out)
    assert len(seg) == pytest.approx(len(_decode(voice)), abs=20)
    assert seg[1500:2500].rms > 1000  # BGM が実際に敷かれている (passthrough でない)


def test_mix_bgm_gain_db_attenuates_bgm_level(tmp_path: Path) -> None:
    """bgm_gain_db が実際に BGM の音量を減衰させる (-18dB ≈ 振幅 0.126 倍)."""
    voice = _silence_wav(seconds=4.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=2.0, freq=220.0, amp=0.8))

    loud = _decode(mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=0))
    quiet = _decode(mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=-18.0, fade_ms=0))

    loud_rms = loud[1500:2500].rms
    quiet_rms = quiet[1500:2500].rms
    assert loud_rms > 1000
    ratio = quiet_rms / loud_rms
    assert ratio == pytest.approx(10 ** (-18 / 20), rel=0.15)  # -18dB の理論減衰比に近い


def test_mix_bgm_overlays_onto_nonsilent_voice(tmp_path: Path) -> None:
    """ナレーションに信号がある場合でも BGM 重畳後は元の声のみと波形が変わる."""
    voice = _tone_wav(seconds=3.0, freq=440.0, amp=0.3)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=1.0, freq=220.0, amp=0.8))

    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=200)
    assert out != voice  # passthrough なら bytes は完全一致するはず


# ---------- fail-open 分岐 (素材あり・失敗系) ----------


def test_mix_bgm_zero_length_bgm_is_passthrough(tmp_path: Path) -> None:
    """BGM が0フレーム (実質空) にデコードされた場合は素通し."""
    voice = _silence_wav(seconds=1.0)
    bgm_path = tmp_path / "empty.wav"
    bgm_path.write_bytes(_zero_frame_wav())

    assert mix_bgm(voice, bgm_path=bgm_path) == voice


def test_mix_bgm_import_error_is_passthrough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """pydub 未導入 (ImportError) を模擬し、fail-open で音声のみ返すことを確認."""
    import builtins

    voice = _silence_wav(seconds=1.0)
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=1.0))

    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pydub":
            raise ImportError("forced (T48 test)")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with caplog.at_level(logging.WARNING):
        out = mix_bgm(voice, bgm_path=bgm_path)
    assert out == voice
    assert "pydub 未導入" in caplog.text


def test_mix_bgm_decode_failure_is_passthrough(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """壊れた音声 (デコード失敗) でも例外を投げず音声をそのまま返す (fail-open)."""
    invalid_voice = b"not a wav at all"
    bgm_path = tmp_path / "bgm.wav"
    bgm_path.write_bytes(_tone_wav(seconds=1.0))

    with caplog.at_level(logging.WARNING):
        out = mix_bgm(invalid_voice, bgm_path=bgm_path)
    assert out == invalid_voice
    assert "BGM ミックス失敗" in caplog.text
