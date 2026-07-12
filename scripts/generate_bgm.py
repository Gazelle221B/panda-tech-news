"""Algorave 風コード生成 BGM (Issue #36, T52 暫定導入).

BGM/ジングル素材のライセンス確認 ([Issue #36](https://github.com/Gazelle221B/panda-tech-news/issues/36))
が未確定のため、ユーザー決定 (2026-07-12)「Algorave やライブコーディングみたいなコードで
音楽作るやつで一旦代用して」に基づき、**stdlib のみ** (wave/math/random/struct。numpy 等の
新規依存は追加しない, 依存最小 AGENTS §5) でミニマルなループ BGM を決定的に (seed 固定) 合成する。

構成: 120 BPM 前後・8〜16 小節・A minor の簡易コード進行 (i-VI-III-VII) 上のトライアングル波
アルペジオ + 控えめなシンセキック/ハイハット。ループ結合時のクリックを避けるため、先頭・末尾に
短い (5ms) declick フェードを掛けてから書き出す (`mix/mixer.py` の `mix_bgm` は BGM を
バックトゥバックで連結してループさせるため, 内部の連結境界がここでの「ループ境界」に当たる)。

使い方: `uv run python scripts/generate_bgm.py [--out assets/bgm/generated_loop.wav]`

生成物の配置先は `mix/mixer.py` の `find_bgm()` (既定 `assets/bgm/`) が読むパスに合わせる。
`assets/` 配下は `.gitignore` で git 管理外のため、生成 wav 自体はコミットしない
(各環境でこのスクリプトを実行してローカルに用意する運用)。
"""
from __future__ import annotations

import argparse
import math
import random
import struct
import wave
from pathlib import Path

DEFAULT_OUT_PATH = Path("assets/bgm/generated_loop.wav")
DEFAULT_BPM = 120.0
DEFAULT_BARS = 16
DEFAULT_SAMPLE_RATE = 48000  # プロジェクト標準 (mix/master.py OUTPUT_SAMPLE_RATE と同じ, FR-103)
DEFAULT_SEED = 42  # 決定的生成 (同じ引数なら常に同じ wav バイト列になる)
DEFAULT_PEAK_DBFS = -12.0  # トークの邪魔にならない音量目安 (mixer 側で更に -18dB 減衰, T29)
BEATS_PER_BAR = 4
STEPS_PER_BEAT = 4  # 16分音符グリッド (algorave/ライブコーディング風シーケンサー)
DECLICK_FADE_MS = 5.0  # ループ結合境界のクリック防止 (業界標準の1〜10msレンジ)

# A minor の簡易コード進行 (i - VI - III - VII)。ルートの MIDI ノート番号。4小節ごとに切替。
_CHORD_ROOTS_MIDI = (45, 41, 48, 43)  # A2, F2, C3, G2
_MINOR_TRIAD_INTERVALS = (0, 3, 7, 12)  # ルートからの半音数 (root, 短3度, 完全5度, オクターブ)


def midi_to_hz(midi_note: float) -> float:
    """MIDI ノート番号を周波数 (Hz) に変換する (A4=69=440Hz 基準の等平均律)."""
    return float(440.0 * (2.0 ** ((midi_note - 69) / 12.0)))


def _linear_envelope(n: int, attack: int, release: int) -> list[float]:
    """attack サンプルで 0→1、release サンプルで 1→0 にする台形エンベロープ (クリック防止)."""
    if n <= 0:
        return []
    attack = max(0, min(attack, n))
    release = max(0, min(release, n - attack))
    env = [1.0] * n
    for i in range(attack):
        env[i] = i / attack
    for i in range(release):
        env[n - 1 - i] = i / release
    return env


def synth_tone(freq_hz: float, duration_sec: float, sample_rate: int, *, amplitude: float = 1.0) -> list[float]:
    """ナイーブなトライアングル波 1 音 (アルペジオ用)。前後に短いエンベロープでクリックを防ぐ."""
    n = max(1, int(duration_sec * sample_rate))
    attack = max(1, int(sample_rate * 0.003))
    release = max(1, int(sample_rate * 0.005))
    env = _linear_envelope(n, attack, release)
    period = sample_rate / freq_hz if freq_hz > 0 else float(n)
    out = []
    for i in range(n):
        phase = (i % period) / period if period > 0 else 0.0
        triangle = 4 * abs(phase - 0.5) - 1.0  # [-1, 1] のナイーブ三角波
        out.append(triangle * amplitude * env[i])
    return out


def synth_kick(duration_sec: float, sample_rate: int, *, amplitude: float = 1.0) -> list[float]:
    """ピッチが急降下するサイン波バースト (シンプルな合成キック). 位相を連続積分し不連続を避ける."""
    n = max(1, int(duration_sec * sample_rate))
    start_hz, end_hz = 150.0, 45.0
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = start_hz + (end_hz - start_hz) * t
        phase += freq / sample_rate
        decay = math.exp(-6.0 * t)
        out.append(math.sin(2 * math.pi * phase) * amplitude * decay)
    return out


def synth_hat(
    duration_sec: float, sample_rate: int, *, amplitude: float, rng: random.Random
) -> list[float]:
    """短いノイズバースト (簡易ハイハット)。控えめな音量前提、rng で決定的に生成する."""
    n = max(1, int(duration_sec * sample_rate))
    out = []
    for i in range(n):
        t = i / n
        decay = math.exp(-20.0 * t)
        out.append(rng.uniform(-1.0, 1.0) * amplitude * decay)
    return out


def _add_event(buffer: list[float], start_sample: int, event: list[float]) -> None:
    """event を buffer の start_sample 位置に加算合成する (buffer 範囲外は切り詰め)."""
    end = min(len(buffer), start_sample + len(event))
    for i in range(start_sample, end):
        buffer[i] += event[i - start_sample]


def normalize_to_peak_dbfs(buffer: list[float], target_dbfs: float) -> list[float]:
    """buffer 全体のピーク振幅が target_dbfs になるよう線形スケーリングする (無音なら無変更)."""
    peak = max((abs(x) for x in buffer), default=0.0)
    if peak <= 0.0:
        return list(buffer)
    target_amp = 10.0 ** (target_dbfs / 20.0)
    scale = target_amp / peak
    return [x * scale for x in buffer]


def apply_declick_fade(
    buffer: list[float], sample_rate: int, fade_ms: float = DECLICK_FADE_MS
) -> list[float]:
    """先頭・末尾のみ短い線形フェードをかけ、ループ連結時のクリックを防ぐ."""
    n = len(buffer)
    if n < 2:
        return list(buffer)
    fade_samples = min(max(1, int(sample_rate * fade_ms / 1000.0)), n // 2)
    out = list(buffer)
    for i in range(fade_samples):
        gain = i / fade_samples
        out[i] *= gain
        out[n - 1 - i] *= gain
    return out


def build_arrangement(
    *,
    bpm: float = DEFAULT_BPM,
    bars: int = DEFAULT_BARS,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = DEFAULT_SEED,
    peak_dbfs: float = DEFAULT_PEAK_DBFS,
) -> list[float]:
    """Algorave 風ミニマルループを決定的に合成する (同じ引数なら常に同じ波形になる).

    毎ステップ (16分音符) A minor 三和音のアルペジオ、各小節の 1・3 拍目にキック、
    裏拍 16分にハイハットを重ねる。最後に peak_dbfs へ正規化し、declick フェードを掛ける。
    """
    rng = random.Random(seed)
    beat_sec = 60.0 / bpm
    step_sec = beat_sec / STEPS_PER_BEAT
    total_steps = max(1, bars) * BEATS_PER_BAR * STEPS_PER_BEAT
    total_samples = max(1, int(total_steps * step_sec * sample_rate))
    buffer = [0.0] * total_samples

    step_samples = step_sec * sample_rate
    for step in range(total_steps):
        bar = step // (BEATS_PER_BAR * STEPS_PER_BEAT)
        beat_in_bar = (step // STEPS_PER_BEAT) % BEATS_PER_BAR
        sub_in_beat = step % STEPS_PER_BEAT
        start_sample = int(step * step_samples)

        # アルペジオ: 毎ステップ1音。コードは4小節ごとに i-VI-III-VII で切替。
        chord_root = _CHORD_ROOTS_MIDI[(bar // 4) % len(_CHORD_ROOTS_MIDI)]
        interval = _MINOR_TRIAD_INTERVALS[step % len(_MINOR_TRIAD_INTERVALS)]
        note_hz = midi_to_hz(chord_root + interval)
        _add_event(buffer, start_sample, synth_tone(note_hz, step_sec * 0.9, sample_rate, amplitude=0.5))

        # キック: 半々テンポの four-on-the-floor もどき (1・3拍目のみ、控えめ)
        if sub_in_beat == 0 and beat_in_bar in (0, 2):
            _add_event(buffer, start_sample, synth_kick(0.18, sample_rate, amplitude=0.9))

        # ハイハット: 裏拍の16分 (控えめな音量)
        if sub_in_beat in (1, 3):
            _add_event(buffer, start_sample, synth_hat(0.05, sample_rate, amplitude=0.25, rng=rng))

    buffer = normalize_to_peak_dbfs(buffer, peak_dbfs)
    return apply_declick_fade(buffer, sample_rate)


def samples_to_pcm16(buffer: list[float]) -> bytes:
    """float [-1, 1] のサンプル列を 16bit PCM (little-endian, mono) バイト列に変換する."""
    return b"".join(
        struct.pack("<h", max(-32768, min(32767, int(round(x * 32767.0))))) for x in buffer
    )


def write_wav(buffer: list[float], sample_rate: int, path: Path) -> None:
    """mono 16bit PCM wav として書き出す (親ディレクトリが無ければ作成する)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = samples_to_pcm16(buffer)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Algorave 風コード生成 BGM を assets/bgm/ へ書き出す (Issue #36)"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH, help=f"出力 wav パス (既定: {DEFAULT_OUT_PATH})")
    parser.add_argument("--bpm", type=float, default=DEFAULT_BPM, help=f"テンポ (既定: {DEFAULT_BPM})")
    parser.add_argument("--bars", type=int, default=DEFAULT_BARS, help=f"小節数 (既定: {DEFAULT_BARS})")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help=f"サンプルレート (既定: {DEFAULT_SAMPLE_RATE})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"乱数シード (既定: {DEFAULT_SEED}, 決定的生成)")
    parser.add_argument("--peak-dbfs", type=float, default=DEFAULT_PEAK_DBFS, help=f"ピーク音量 dBFS (既定: {DEFAULT_PEAK_DBFS})")
    args = parser.parse_args(argv)

    buffer = build_arrangement(
        bpm=args.bpm,
        bars=args.bars,
        sample_rate=args.sample_rate,
        seed=args.seed,
        peak_dbfs=args.peak_dbfs,
    )
    write_wav(buffer, args.sample_rate, args.out)
    duration_sec = len(buffer) / args.sample_rate
    print(
        f"生成完了: {args.out} ({duration_sec:.1f}s, {args.sample_rate}Hz, "
        f"peak={args.peak_dbfs}dBFS, seed={args.seed})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
