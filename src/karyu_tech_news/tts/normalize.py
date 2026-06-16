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
                if term is None or reading is None:
                    continue  # YAML null は除外 ('None' 文字列化を防ぐ, Copilot 指摘)
                term_s, reading_s = str(term).strip(), str(reading).strip()
                if term_s and reading_s:  # strip 後の空文字も落とす
                    flat[term_s] = reading_s
    return flat


# 「カナ (原語)」表記の原語グロスを除去する用 (半角/全角括弧 + ASCII 中身)。
# 台本は読みやすさのため「ディープシーク (DeepSeek)」と書くが、TTS では原語を
# 読み上げない & 読み辞書で二重読みになるため、合成前に括弧グロスを落とす
# (Codex レビュー指摘)。中身が日本語の括弧 (意味的補足) は残す。
_ASCII_GLOSS_RE = re.compile(r"\s*[（(][ -~]+[）)]")


def strip_ascii_gloss(text: str) -> str:
    """「カナ (原語)」の ASCII 原語グロスを除去する (TTS 入力前処理)."""
    return _ASCII_GLOSS_RE.sub("", text)


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
