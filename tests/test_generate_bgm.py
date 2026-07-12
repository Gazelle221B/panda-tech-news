"""scripts/generate_bgm.py のテスト (Issue #36, T52 暫定コード生成 BGM).

BGM/ジングル素材のライセンス確定を待たず、stdlib のみの決定的コード生成 BGM で暫定代用
する (ユーザー決定 2026-07-12)。純ロジック (音符/エンベロープ→サンプル変換・正規化・
declick フェード等) のユニットテストと、生成 wav を実際に `mix_bgm` へ通す統合テスト
(RIFF 妥当性・長さ・ループ境界のクリック近似検証) を行う。

`scripts/` はパッケージ化されていないため、importlib でファイルパスから動的 import する。
"""
from __future__ import annotations

import importlib.util
import io
import random
import shutil
import struct
import wave
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _ROOT / "scripts" / "generate_bgm.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_bgm", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bgm = _load_module()


# ---------- 純ロジック: 音符→サンプル変換 ----------


def test_midi_to_hz_a4_is_440() -> None:
    assert bgm.midi_to_hz(69) == pytest.approx(440.0)


def test_midi_to_hz_octave_doubles_frequency() -> None:
    assert bgm.midi_to_hz(81) == pytest.approx(880.0)  # 69+12 = 1オクターブ上


def test_synth_tone_length_matches_duration() -> None:
    samples = bgm.synth_tone(220.0, 0.1, 48000, amplitude=1.0)
    assert len(samples) == int(0.1 * 48000)


def test_synth_tone_starts_and_ends_near_zero_declick_envelope() -> None:
    """個々の音符自体にも前後エンベロープを掛け、密集したアルペジオでもクリックを防ぐ."""
    samples = bgm.synth_tone(220.0, 0.05, 48000, amplitude=1.0)
    assert abs(samples[0]) < 0.05
    assert abs(samples[-1]) < 0.05


def test_synth_tone_stays_within_unit_range() -> None:
    samples = bgm.synth_tone(220.0, 0.2, 48000, amplitude=1.0)
    assert all(-1.0 <= s <= 1.0 for s in samples)


def test_synth_kick_decays_to_near_silence() -> None:
    samples = bgm.synth_kick(0.18, 48000, amplitude=1.0)
    head_peak = max(abs(s) for s in samples[:100])
    tail_peak = max(abs(s) for s in samples[-100:])
    assert tail_peak < head_peak  # ディケイなので末尾は先頭よりずっと小さい


def test_synth_hat_is_deterministic_given_same_rng_seed() -> None:
    a = bgm.synth_hat(0.05, 48000, amplitude=0.25, rng=random.Random(1))
    b = bgm.synth_hat(0.05, 48000, amplitude=0.25, rng=random.Random(1))
    assert a == b


# ---------- 純ロジック: 正規化・declick フェード ----------


def test_normalize_to_peak_dbfs_scales_to_target() -> None:
    buffer = [0.1, -0.3, 0.2, -0.05]
    out = bgm.normalize_to_peak_dbfs(buffer, -6.0)
    peak = max(abs(x) for x in out)
    assert peak == pytest.approx(10 ** (-6.0 / 20.0), rel=1e-6)


def test_normalize_to_peak_dbfs_handles_silence() -> None:
    assert bgm.normalize_to_peak_dbfs([0.0, 0.0], -12.0) == [0.0, 0.0]


def test_apply_declick_fade_zeroes_leading_boundary_sample() -> None:
    buffer = [1.0] * 1000
    out = bgm.apply_declick_fade(buffer, sample_rate=48000, fade_ms=5.0)
    assert out[0] == pytest.approx(0.0, abs=1e-9)
    assert out[-1] == pytest.approx(0.0, abs=1e-9)
    assert out[500] == pytest.approx(1.0)  # フェード区間外 (中間) は無変更


# ---------- 純ロジック: 全体合成・決定性 ----------


def test_build_arrangement_is_deterministic() -> None:
    a = bgm.build_arrangement(bpm=120.0, bars=2, sample_rate=8000, seed=7)
    b = bgm.build_arrangement(bpm=120.0, bars=2, sample_rate=8000, seed=7)
    assert a == b


def test_build_arrangement_length_matches_bars_and_bpm() -> None:
    sample_rate, bars, bpm_value = 8000, 2, 120.0
    buffer = bgm.build_arrangement(bpm=bpm_value, bars=bars, sample_rate=sample_rate, seed=1)
    expected_sec = bars * bgm.BEATS_PER_BAR * (60.0 / bpm_value)
    assert len(buffer) == pytest.approx(expected_sec * sample_rate, abs=sample_rate * 0.01)


def test_build_arrangement_respects_peak_dbfs() -> None:
    buffer = bgm.build_arrangement(bpm=120.0, bars=2, sample_rate=8000, seed=1, peak_dbfs=-6.0)
    peak = max(abs(x) for x in buffer)
    assert peak == pytest.approx(10 ** (-6.0 / 20.0), rel=0.02)


# ---------- 純ロジック: PCM 変換 ----------


def test_samples_to_pcm16_round_trip() -> None:
    pcm = bgm.samples_to_pcm16([0.0, 1.0, -1.0])
    values = struct.unpack("<3h", pcm)
    assert values == (0, 32767, -32767)  # 対称スケーリング (kokoro.py floats_to_wav と同じ流儀)


def test_samples_to_pcm16_clamps_out_of_range() -> None:
    pcm = bgm.samples_to_pcm16([2.0, -2.0])
    values = struct.unpack("<2h", pcm)
    assert values == (32767, -32768)


# ---------- write_wav / CLI ----------


def test_write_wav_creates_valid_riff_container_and_parent_dir(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "bgm.wav"
    bgm.write_wav([0.0, 0.5, -0.5, 0.0], 48000, out)
    assert out.exists()
    with wave.open(str(out), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 48000
        assert w.getnframes() == 4


def test_main_generates_wav_with_expected_duration(tmp_path: Path) -> None:
    out = tmp_path / "generated.wav"
    rc = bgm.main(
        ["--out", str(out), "--bpm", "120", "--bars", "2", "--sample-rate", "8000", "--seed", "3"]
    )
    assert rc == 0
    assert out.exists()
    with wave.open(str(out), "rb") as w:
        assert w.getframerate() == 8000
        expected_sec = 2 * bgm.BEATS_PER_BAR * (60.0 / 120.0)
        actual_sec = w.getnframes() / 8000
        assert actual_sec == pytest.approx(expected_sec, abs=0.01)


# ---------- 統合: 生成 wav を mix_bgm の実経路に通す ----------
#
# pydub は optional extra `tts` のため、この 1 テストだけ関数単位で skipif する
# (モジュール冒頭で importorskip すると、pydub 非依存の純ロジックテストまで
# 巻き込んで skip されてしまうため、test_mix_mixer.py のモジュール全体 skip 流儀は
# あえて踏襲しない)。

_HAS_PYDUB_AND_FFMPEG = importlib.util.find_spec("pydub") is not None and shutil.which("ffmpeg") is not None


def _silence_wav(seconds: float, sample_rate: int = 48000) -> bytes:
    n = int(seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n)
    return buf.getvalue()


@pytest.mark.skipif(
    not _HAS_PYDUB_AND_FFMPEG,
    reason="pydub (optional extra `tts`) または ffmpeg 不在のため実ミックス経路を skip",
)
def test_generated_bgm_is_valid_and_loops_without_click_through_mixer(tmp_path: Path) -> None:
    """生成 wav → mix_bgm の実経路を通し、RIFF 妥当性・長さ・ループ境界の破綻無しを確認する."""
    from pydub import AudioSegment  # 遅延 import (skipif 済みで安全)

    from karyu_tech_news.mix.mixer import mix_bgm

    bgm_path = tmp_path / "generated.wav"
    buffer = bgm.build_arrangement(bpm=120.0, bars=2, sample_rate=48000, seed=11)
    bgm.write_wav(buffer, 48000, bgm_path)

    with wave.open(str(bgm_path), "rb") as w:
        assert w.getnframes() > 0  # RIFF 妥当性 (wave モジュールで読める)

    # ボイス (無音、BGM より長い) へループして敷く経路を通す
    voice = _silence_wav(seconds=8.0)
    out = mix_bgm(voice, bgm_path=bgm_path, bgm_gain_db=0.0, fade_ms=0)
    assert out[:4] == b"RIFF"
    assert out[8:12] == b"WAVE"
    seg = AudioSegment.from_file(io.BytesIO(out), format="wav")
    assert len(seg) == pytest.approx(8000, abs=20)  # ボイス長 (8s) に一致

    # ループが機能していること (中間区間で信号が鳴っている = passthrough でない)
    middle = seg[3000:5000]
    assert middle.rms > 50

    # クリック近似検証: declick フェードにより境界サンプルは0近傍のはずなので、
    # ループ連結境界 (末尾→先頭) の跳躍量が小さいことを確認する。
    boundary_jump = abs(buffer[-1] - buffer[0])
    assert boundary_jump < 0.05
