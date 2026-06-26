"""tts.normalize のユニットテスト (Sprint 2 Ticket T26, FR-092). 全て決定的.

固有名詞読み辞書による TTS 発音正規化を検証する。台本本文は LLM がカナ化するが、
fallback テンプレの原題や取りこぼしを TTS 前に機械的に読み仮名へ置換する安全網。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from karyu_tech_news.tts.normalize import (
    load_reading_dict,
    normalize_text,
    prepare_tts_text,
    sanitize_chinese_title_quotes,
    strip_ascii_gloss,
    strip_duplicate_parentheticals,
    strip_invalid_tts_chars,
    strip_link_markup,
    strip_pronunciation_parentheticals,
    strip_script_markup,
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


def test_strip_link_markup_keeps_label_drops_url() -> None:
    out = strip_link_markup("詳しくは[公式資料](https://example.com/a)と https://example.com/b を確認。")
    assert out == "詳しくは公式資料と  を確認。"
    assert "https://" not in out
    assert "](" not in out


def test_strip_link_markup_preserves_text_after_bare_url() -> None:
    assert strip_link_markup("参照: https://example.com/a。次です。") == "参照: 。次です。"
    assert strip_link_markup("参照: https://example.com/a、次です。") == "参照: 、次です。"


def test_strip_invalid_tts_chars_repairs_observed_replacement_char() -> None:
    assert strip_invalid_tts_chars("世界一に返り�きました。") == "世界一に返り咲きました。"
    assert strip_invalid_tts_chars("未知�文字") == "未知文字"


def test_strip_duplicate_parentheticals_removes_exact_duplicate_reading() -> None:
    assert strip_duplicate_parentheticals("バイトダンス（バイトダンス）が発表。") == "バイトダンスが発表。"
    assert strip_duplicate_parentheticals("生成AI（AI）です。") == "生成AIです。"
    assert strip_duplicate_parentheticals("自動運転（レベル4）です。") == "自動運転（レベル4）です。"


def test_strip_pronunciation_parentheticals_keeps_kana_reading() -> None:
    # 原語+カナ読みは TTS で二重読みになるため、カナ読みだけを残す
    assert strip_pronunciation_parentheticals("灵晟（リンション）が首位。") == "リンションが首位。"
    assert strip_pronunciation_parentheticals("FSD（エフエスディー）を評価。") == "エフエスディーを評価。"
    assert strip_pronunciation_parentheticals("生成AI（エーアイ）です。") == "生成エーアイです。"
    assert strip_pronunciation_parentheticals("自動運転（レベル4）です。") == "自動運転（レベル4）です。"


def test_strip_pronunciation_parentheticals_preserves_japanese_prefix() -> None:
    assert strip_pronunciation_parentheticals("中国企業灵晟（リンション）が首位。") == "中国企業リンションが首位。"
    assert (
        strip_pronunciation_parentheticals("半導体企業灵晟（リンション）が発表。")
        == "半導体企業リンションが発表。"
    )


def test_strip_pronunciation_parentheticals_preserves_ascii_prefix() -> None:
    assert (
        strip_pronunciation_parentheticals("Tesla FSD（エフエスディー）を評価。")
        == "Tesla エフエスディーを評価。"
    )
    assert (
        strip_pronunciation_parentheticals("OpenAI FSD（エフエスディー）を評価。")
        == "OpenAI エフエスディーを評価。"
    )


def test_prepare_tts_text_strips_links_and_pronunciation_parenthetical() -> None:
    out = prepare_tts_text(
        "詳しくは[公式資料](https://example.com/a)。灵晟（リンション）が首位。",
        {},
    )
    assert "https://" not in out
    assert "](" not in out
    assert "灵晟" not in out
    assert "リンション" in out


def test_prepare_tts_text_strips_duplicate_parenthetical() -> None:
    assert prepare_tts_text("バイトダンス（バイトダンス）が発表。", {}) == "バイトダンスが発表。"
    assert (
        prepare_tts_text("字节跳动（バイトダンス）が発表。", {"字节跳动": "バイトダンス"})
        == "バイトダンスが発表。"
    )


def test_prepare_tts_text_normalizes_observed_simplified_terms_outside_quotes() -> None:
    d = load_reading_dict(DICT_PATH)
    out = prepare_tts_text(
        "2026年世界人工智能大会で、卓越AI引领者賞(SAIL賞)が発表されました。"
        "聖陽股份（聖陽股份）も話題です。",
        d,
    )
    assert "人工智能" not in out
    assert "引领者" not in out
    assert "SAIL賞" not in out
    assert "聖陽股份" not in out
    assert "世界人工知能大会" in out
    assert "卓越エーアイリーダー賞" in out
    assert "セイル賞" in out
    assert "シェンヤングーフェン" in out


def test_prepare_tts_text_preserves_known_short_chinese_quote_reading() -> None:
    out = prepare_tts_text("「灵晟」が首位。", {"灵晟": "リンション"})
    assert out == "「リンション」が首位。"


# ---------- Markdown マーカー除去 (実音声 smoke で発見) ----------

def test_strip_script_markup_removes_labels() -> None:
    body = (
        "**Hook:** つかみです。\n**Insight:** 意味です。\n**Action:** 行動です。"
    )
    out = strip_script_markup(body)
    assert "**" not in out  # ** が TTS で読み上げられない
    assert "Hook" not in out and "Insight" not in out and "Action" not in out
    assert "つかみです。" in out and "意味です。" in out and "行動です。" in out


def test_strip_script_markup_handles_fullwidth_colon() -> None:
    assert strip_script_markup("**Hook：** あ") == "あ"


def test_strip_script_markup_noop_on_plain_text() -> None:
    assert strip_script_markup("普通の文。") == "普通の文。"


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


# ---------- 中国語原題 quote の発話退避 (T35/T36) ----------

def test_sanitize_chinese_title_in_quotes() -> None:
    # 長い中国語原題は pinyin 羅列として読ませず、日本語の汎用参照に退避する。
    out = sanitize_chinese_title_quotes("「三星电子HBM4」というニュース。")
    assert out == "このニュース。"
    assert "san xing" not in out
    assert "三星" not in out


def test_sanitize_skips_japanese_quote() -> None:
    # かなを含む日本語引用は中国語でないので置換しない (誤置換回避)
    assert sanitize_chinese_title_quotes("「日本語の引用」が話題。") == "「日本語の引用」が話題。"


def test_sanitize_leaves_plain_japanese_untouched() -> None:
    # 「」の無い日本語ナレーション (漢字混在) は一切触らない
    src = "清華大学が空間知能モデルをオープンソース化しました。"
    assert sanitize_chinese_title_quotes(src) == src


def test_sanitize_only_targets_chinese_span() -> None:
    # 同一文に中国語原題と日本語が混在しても、原題のみ退避する。
    out = sanitize_chinese_title_quotes("今日は「豆包发布」を取り上げます。")
    assert out == "今日はこの話題を取り上げます。"
    assert "dou bao" not in out
    assert "发布" not in out


def test_sanitize_drops_long_pinyin_prone_title() -> None:
    # 実 ASR で長い pinyin 羅列は「変な読み」になったため、本文では読ませない。
    out = sanitize_chinese_title_quotes("「刚刚，豆包2.1发布！Agent自己跑18个小时」")
    assert out == "この話題"
    assert "gang gang" not in out
    assert "Agent" not in out
    assert "刚刚" not in out


@pytest.mark.parametrize(
    "jp_quote",
    ["「生成AI」", "「東京大学」", "「人工知能」", "「半導体」", "「国際会議」", "「機械学習」", "「自動運転」"],
)
def test_transliterate_skips_japanese_kanji_only_quote(jp_quote: str) -> None:
    # 漢字のみの日本語引用 (簡体字特有文字を含まない) は退避しない (Codex High 回帰)。
    # かな無し条件だけでは中国語扱いされていた → 簡体字必須条件で防ぐ。
    assert sanitize_chinese_title_quotes(jp_quote) == jp_quote


def test_sanitize_requires_simplified_char() -> None:
    # 簡体字を含む中国語原題は退避される (簡体字必須条件の肯定側)
    assert sanitize_chinese_title_quotes("「电子」") == "この話題"


def test_sanitize_keeps_exact_known_chinese_quote_reading() -> None:
    assert sanitize_chinese_title_quotes("「灵晟」が首位。", {"灵晟": "リンション"}) == "「リンション」が首位。"
