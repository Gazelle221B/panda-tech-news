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


# 台本本文の Markdown 構造マーカー (**Hook:** / **Insight:** / **Action:**) を除去する用。
# Discord 表示には必要だが TTS では「アスタリスク アスタリスク フック コロン」と読み上げて
# しまうため、合成前に落とす (実音声 smoke で発見, architecture §4 の script→tts 境界)。
_SCRIPT_LABEL_RE = re.compile(r"\*\*\s*(?:Hook|Insight|Action)\s*[:：]\s*\*\*\s*")


def strip_script_markup(text: str) -> str:
    """TTS 前に台本の Markdown マーカーを除去する (ラベルと残存 ** を落とす)."""
    return _SCRIPT_LABEL_RE.sub("", text).replace("**", "")


# 台本 Markdown の見出し行 (`# / ##`) と生成メタ行を除去する用。見出しは番組タイトルや
# **中国語原文の記事タイトル** で朗読対象でなく (要件 §9.6 中国メディア本文朗読禁止・
# editorial-policy §1/§10)、Kokoro 等が中国語を遅く誤読し尺も膨らむ。生成日時/LLM profile
# のビルドメタも発話しない。保存済み台本 markdown を produce で合成する経路で使う。
_MD_HEADER_RE = re.compile(r"^[ \t]*#{1,6}[ \t].*$", re.MULTILINE)
_MD_META_RE = re.compile(r"^[ \t]*生成日時[:：].*$", re.MULTILINE)


def strip_markdown_structure(text: str) -> str:
    """TTS 前に Markdown 見出し行・生成メタ行を除去し本文ナレーションのみ残す.

    見出し (`# 華流テック通信...` / `## 1. 智谱：...`) は番組タイトルや中国語原文の記事
    タイトルで発話対象でない (要件 §9.6・editorial-policy §1/§10)。生成日時/LLM profile の
    メタも読まない。Hook/Insight/Action の日本語ナレーションのみ残す (produce 経路で使用)。
    """
    text = _MD_HEADER_RE.sub("", text)
    text = _MD_META_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


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
