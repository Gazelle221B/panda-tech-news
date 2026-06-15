"""読み仮名辞書 + テキスト正規化 (Sprint 2 Ticket T26, FR-092).

ADR-0006: Irodori-TTS v3 は漢字読み精度が弱い (公式明記)。中国企業名/モデル名/
メディア名/専門用語のカナ読みを `config/reading_dict.yaml` で制御し、TTS 合成前に
機械的に置換する。台本本文は LLM がカナ化するが、fallback テンプレの原題や
取りこぼしに対する安全網として機能する。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def load_reading_dict(path: Path) -> dict[str, str]:
    """YAML (カテゴリ別) を {term: reading} のフラット辞書へ統合する.

    空 term / 空 reading は除外する (置換が無意味かつ正規表現を壊すため)。
    """
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    flat: dict[str, str] = {}
    if isinstance(raw, dict):
        for category in raw.values():
            if not isinstance(category, dict):
                continue
            for term, reading in category.items():
                term_s, reading_s = str(term), str(reading)
                if term_s and reading_s:
                    flat[term_s] = reading_s
    return flat


def normalize_text(text: str, reading_dict: dict[str, str]) -> str:
    """text 中の既知用語を読み仮名へ置換する (TTS 発音用).

    - **最長一致優先**: 長い用語を先に当て、部分置換で壊さない。
    - **1 パス置換**: 置換後の読みに含まれる別用語を再置換しない。
    """
    if not text or not reading_dict:
        return text
    terms = sorted(reading_dict, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(t) for t in terms))
    return pattern.sub(lambda m: reading_dict[m.group(0)], text)
