"""tts.normalize のユニットテスト (Sprint 2 Ticket T26, FR-092). 全て決定的.

固有名詞読み辞書による TTS 発音正規化を検証する。台本本文は LLM がカナ化するが、
fallback テンプレの原題や取りこぼしを TTS 前に機械的に読み仮名へ置換する安全網。
"""
from __future__ import annotations

from pathlib import Path

from karyu_tech_news.tts.normalize import (
    load_reading_dict,
    normalize_text,
    strip_ascii_gloss,
)

DICT_PATH = Path("config/reading_dict.yaml")


def test_normalize_replaces_known_term() -> None:
    text = normalize_text("小米の新モデル", {"小米": "シャオミ"})
    assert text == "シャオミの新モデル"


def test_normalize_prefers_longest_match() -> None:
    # 「小米版」が「小米」より優先される (部分置換で壊さない)
    d = {"小米": "シャオミ", "小米版": "シャオミバン"}
    assert normalize_text("小米版Claude", d) == "シャオミバンClaude"


def test_normalize_no_double_replacement() -> None:
    # 読みの中に別の用語が含まれても再置換しない (1パス)
    d = {"A社": "B社の系列", "B社": "ビーシャ"}
    # A社 → "B社の系列" に置換後、その中の "B社" は再置換されない
    assert normalize_text("A社", d) == "B社の系列"


def test_normalize_unknown_text_unchanged() -> None:
    assert normalize_text("未知の語", {"小米": "シャオミ"}) == "未知の語"


def test_normalize_empty_dict_unchanged() -> None:
    assert normalize_text("そのまま", {}) == "そのまま"


def test_normalize_multiple_terms() -> None:
    d = {"小米": "シャオミ", "華為": "ファーウェイ"}
    assert normalize_text("小米と華為", d) == "シャオミとファーウェイ"


# ---------- ASCII 原語グロス除去 ----------

def test_strip_ascii_gloss_removes_paren_original() -> None:
    assert strip_ascii_gloss("ディープシーク (DeepSeek)") == "ディープシーク"


def test_strip_ascii_gloss_handles_fullwidth_parens() -> None:
    assert strip_ascii_gloss("ジーフー（Zhipu AI）") == "ジーフー"


def test_strip_ascii_gloss_keeps_japanese_parens() -> None:
    # 中身が日本語の括弧 (意味的補足) は残す
    assert strip_ascii_gloss("脳機接口（ブレイン）") == "脳機接口（ブレイン）"


# ---------- 辞書ロード ----------

def test_load_reading_dict_flattens_categories() -> None:
    d = load_reading_dict(DICT_PATH)
    assert isinstance(d, dict)
    assert d  # 非空
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())
    assert all(k and v for k, v in d.items())  # 空キー/空値なし


def test_load_reading_dict_usable_for_normalize() -> None:
    d = load_reading_dict(DICT_PATH)
    term, reading = next(iter(d.items()))
    assert normalize_text(term, d) == reading


def test_load_reading_dict_excludes_null_and_blank(tmp_path: Path) -> None:
    # YAML の null / 空白キー・値を除外 (Copilot 指摘: 'None' 文字列化・空白キー化を防ぐ)
    p = tmp_path / "rd.yaml"
    p.write_text(
        "companies:\n  小米: シャオミ\n  空値: null\n  '   ': トリム\n  華為: '  '\n",
        encoding="utf-8",
    )
    assert load_reading_dict(p) == {"小米": "シャオミ"}
