"""BGM/ジングル仮ミックス (Sprint 2 Ticket T29).

T28 が結合した音声 wav に BGM を時間軸で重ねる。**素材非依存**に設計し、
`assets/bgm/` に素材が無ければ音声をそのまま返す (passthrough)。素材があるときだけ
pydub で全編に低音量 BGM を敷く (仮ミックス)。素材ライセンス選定 (人間ゲート §6) を
待たずにコードを通せるようにし、素材は後から追加すればミックスが有効になる。

設計判断:
- **fail-open**: pydub 未導入や BGM 読み込み失敗でも番組を止めず音声のみ返す。
- pydub は optional extra `tts`。mixer 内で遅延 import し、未導入環境でも passthrough。
- 仮ミックスは「全編に -18dB の BGM を敷き、前後を短くフェード」のみ (サイドチェイン
  ダッキング等は将来の精緻化)。サンプルレート差は pydub が吸収する。
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_BGM_DIR = Path("assets/bgm")
DEFAULT_BGM_GAIN_DB = -18.0  # 声を主役にするための BGM 減衰量
DEFAULT_FADE_MS = 1500  # 前後フェード (唐突な開始/終了を避ける)
_BGM_SUFFIXES = (".mp3", ".wav", ".ogg", ".m4a", ".flac")


def find_bgm(bgm_dir: Path = DEFAULT_BGM_DIR) -> Path | None:
    """BGM ディレクトリの最初の音源を返す (無ければ None). 素材非依存運用の入口."""
    if not bgm_dir.is_dir():
        return None
    candidates = sorted(p for p in bgm_dir.iterdir() if p.suffix.lower() in _BGM_SUFFIXES)
    return candidates[0] if candidates else None


def mix_bgm(
    voice_wav: bytes,
    *,
    bgm_path: Path | None = None,
    bgm_gain_db: float = DEFAULT_BGM_GAIN_DB,
    fade_ms: int = DEFAULT_FADE_MS,
) -> bytes:
    """音声 wav に BGM を敷いた wav を返す. 素材が無ければ入力をそのまま返す (passthrough).

    fail-open: pydub 未導入・素材読み込み失敗でも音声のみを返し、番組を止めない。
    """
    if bgm_path is None or not bgm_path.exists():
        return voice_wav  # 素材なし → 素通し (素材非依存)
    try:
        from pydub import AudioSegment  # 遅延 import (optional extra `tts`)
    except ImportError:
        logger.warning("pydub 未導入のため BGM をスキップ (passthrough): %s", bgm_path.name)
        return voice_wav
    try:
        voice = AudioSegment.from_file(io.BytesIO(voice_wav), format="wav")
        bgm = AudioSegment.from_file(bgm_path)
        if len(bgm) == 0:
            return voice_wav
        bgm = bgm + bgm_gain_db  # dB 加算 = 減衰 (負値)
        loops = len(voice) // len(bgm) + 1
        bed = (bgm * loops)[: len(voice)].fade_in(fade_ms).fade_out(fade_ms)
        mixed = voice.overlay(bed)
        out = io.BytesIO()
        mixed.export(out, format="wav")
        return out.getvalue()
    except Exception as exc:  # ffmpeg/デコード失敗等は fail-open で音声のみ返す
        logger.warning("BGM ミックス失敗 (passthrough, fail-open): %s", exc)
        return voice_wav
