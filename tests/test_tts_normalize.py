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
    spell_out_residual_ascii_tokens,
    split_markdown_topics,
    strip_ascii_gloss,
    strip_duplicate_parentheticals,
    strip_invalid_tts_chars,
    strip_link_markup,
    strip_markdown_structure,
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


def test_normalize_ascii_terms_require_token_boundary() -> None:
    d = {"AI": "エーアイ", "SAIL賞": "セイル賞", "OpenAI": "オープンエーアイ"}
    assert normalize_text("SAIL賞とAI。OpenAIも対象。", d) == (
        "セイル賞とエーアイ。オープンエーアイも対象。"
    )
    assert normalize_text("SAIL", {"AI": "エーアイ"}) == "SAIL"
    assert normalize_text("OpenAI_API", d) == "OpenAI_API"
    assert normalize_text("GPT-5.6.1", {"GPT-5.6": "ジーピーティー五点六"}) == "GPT-5.6.1"
    assert normalize_text("LLM/RAG", {"LLM": "エルエルエム", "RAG": "ラグ"}) == "エルエルエム/ラグ"
    assert (
        normalize_text("5G+AI", {"5G+": "ファイブジープラス", "AI": "エーアイ"})
        == "ファイブジープラスエーアイ"
    )


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


def test_prepare_tts_text_normalizes_lenovo_simplified_han_variants() -> None:
    # 2026-08-14 の配信欠落再現 (Issue 記載): 台本に簡体字「联想集団」が残存し
    # (読み辞書コベレッジで「残存CJK(簡体字)=1件 [联想集団x1]」と検出)、TTS が
    # 正しく読めず ASR ゲートが mismatch 判定した。联想集团/联想集団/联想 いずれの
    # 表記も読み辞書で「レノボ」へ正規化され、簡体字が出力に残らないことを固定する。
    #
    # codex terra レビュー指摘: 「联」不在 + 「レノボ」在るだけでは、短い「联想」が
    # 「联想集团」の内部で先に部分置換され「レノボ集团/レノボ集団」になる退行 (最長一致
    # 優先の regression) を検出できない (「联」自体は既に消費済みで再検出できないため)。
    # 完全一致で置換後の期待文そのものを固定し、部分置換の残骸が残らないことも明示する。
    d = load_reading_dict(DICT_PATH)
    for variant in ("联想集团", "联想集団", "联想"):
        out = prepare_tts_text(f"{variant}が第1四半期決算で増収増益を発表しました。", d)
        assert out == "レノボが第1四半期決算で増収増益を発表しました。"
        assert "联" not in out
        assert "レノボ集団" not in out
        assert "レノボ集团" not in out


def test_prepare_tts_text_preserves_known_short_chinese_quote_reading() -> None:
    out = prepare_tts_text("「灵晟」が首位。", {"灵晟": "リンション"})
    assert out == "「リンション」が首位。"


def test_prepare_tts_text_normalizes_observed_english_terms() -> None:
    d = load_reading_dict(DICT_PATH)
    out = prepare_tts_text(
        "HAL Daily Briefingです。Claude Code、FSD、LLM、GitHub、HBM4、GPT-5.6、"
        "ISC、A株、AI、5G、5G+、5G+AI、4D、LLM/RAG、Lite/Pro/Maxを確認。",
        d,
    )
    for raw in [
        "HAL Daily Briefing",
        "Claude Code",
        "FSD",
        "LLM",
        "GitHub",
        "HBM4",
        "GPT-5.6",
        "ISC",
        "A株",
        "5G",
        "5G+",
        "5G+AI",
        "4D",
        "LLM/RAG",
        "Lite/Pro/Max",
    ]:
        assert raw not in out
    assert "ハル デイリーブリーフィング" in out
    assert "クロードコード" in out
    assert "エフエスディー" in out
    assert "エルエルエム" in out
    assert "ギットハブ" in out
    assert "エイチビーエムフォー" in out
    assert "ジーピーティー五点六" in out
    assert "アイエスシー" in out
    assert "エー株" in out
    assert "エーアイ" in out
    assert "ファイブジー" in out
    assert "ファイブジープラス" in out
    assert "ファイブジープラスエーアイ" in out
    assert "フォーディー" in out
    assert "エルエルエム/ラグ" in out
    assert "ライト/プロ/マックス" in out


# ---------- ASCII 略語カナ綴りフォールバック (T57, Issue #53) ----------

def test_spell_out_residual_ascii_tokens_converts_known_abbreviations() -> None:
    assert spell_out_residual_ascii_tokens("DOIとISCを確認。") == (
        "ディーオーアイとアイエスシーを確認。"
    )


def test_spell_out_residual_ascii_tokens_skips_lowercase_digit_and_single_char() -> None:
    text = "MoWorldとv1.0.0と5Gと単文字Aを確認。"
    assert spell_out_residual_ascii_tokens(text) == text


def test_spell_out_residual_ascii_tokens_skips_inside_longer_identifiers() -> None:
    # SAIL 単体は境界的に対象だが、より長い識別子や連続大文字の内部では発火しない。
    assert spell_out_residual_ascii_tokens("OpenAI_APIを呼ぶ。") == "OpenAI_APIを呼ぶ。"
    assert spell_out_residual_ascii_tokens("ABCDEFGを確認。") == "ABCDEFGを確認。"


def test_spell_out_residual_ascii_tokens_handles_multiple_tokens_in_sentence() -> None:
    assert spell_out_residual_ascii_tokens("DOIとIPOを発行。") == (
        "ディーオーアイとアイピーオーを発行。"
    )


def test_prepare_tts_text_spells_out_residual_ascii_abbreviations() -> None:
    out = prepare_tts_text("DOIとISCについて。", {})
    assert "DOI" not in out
    assert "ISC" not in out
    assert "ディーオーアイ" in out
    assert "アイエスシー" in out


def test_prepare_tts_text_reading_dict_wins_over_spelling_fallback() -> None:
    # 辞書に載っている語 (AI 等) は辞書の読みが勝ち、一字ずつの綴り読みにならない。
    out = prepare_tts_text("AIが話題。", {"AI": "エーアイ"})
    assert out == "エーアイが話題。"


def test_prepare_tts_text_skips_lowercase_digit_and_single_char_tokens() -> None:
    text = "MoWorldとv1.0.0と5Gと単文字Aを確認。"
    assert prepare_tts_text(text, {}) == text


def test_prepare_tts_text_skips_inside_identifier() -> None:
    assert prepare_tts_text("OpenAI_APIを呼ぶ。", {}) == "OpenAI_APIを呼ぶ。"


def test_prepare_tts_text_dict_term_wins_before_spelling_for_sail() -> None:
    # 「SAIL賞」は辞書エントリで一括変換され、SAIL 単体が先に綴り読みされない。
    d = load_reading_dict(DICT_PATH)
    out = prepare_tts_text("卓越AI引领者賞(SAIL賞)が発表された。", d)
    assert "SAIL" not in out
    assert "セイル賞" in out
    assert "エスエーアイエル" not in out


def test_prepare_tts_text_spells_out_standalone_hal() -> None:
    d = load_reading_dict(DICT_PATH)
    assert prepare_tts_text("HALが解説します。", d) == "ハルが解説します。"


def test_prepare_tts_text_keeps_hal_daily_briefing_dict_entry() -> None:
    # 「HAL」単独エントリを追加しても、長い「HAL Daily Briefing」エントリが
    # 長い term 優先で正しく先に一致する (共存確認)。
    d = load_reading_dict(DICT_PATH)
    out = prepare_tts_text("HAL Daily Briefingへようこそ。", d)
    assert out == "ハル デイリーブリーフィングへようこそ。"


def test_prepare_tts_text_spells_out_multiple_tokens_in_sentence() -> None:
    out = prepare_tts_text("DOIとIPOを発行。", {})
    assert out == "ディーオーアイとアイピーオーを発行。"


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


def test_strip_script_markup_removes_plain_labels() -> None:
    body = "Hook: つかみです。\nInsight：意味です。\nAction: 行動です。"
    out = strip_script_markup(body)
    assert "Hook" not in out and "Insight" not in out and "Action" not in out
    assert "つかみです。" in out and "意味です。" in out and "行動です。" in out


def test_strip_script_markup_removes_list_prefixed_labels() -> None:
    body = "- **Hook:** つかみです。\n1. **Insight:** 意味です。\n+ Action: 行動です。"
    out = strip_script_markup(body)
    assert "Hook" not in out and "Insight" not in out and "Action" not in out
    assert "- " not in out and "1. " not in out and "+ " not in out
    assert "つかみです。" in out and "意味です。" in out and "行動です。" in out


def test_strip_script_markup_preserves_content_action_terms() -> None:
    assert strip_script_markup("GitHub Action: ワークフローを改善。") == (
        "GitHub Action: ワークフローを改善。"
    )
    assert strip_script_markup("Call to Action: 登録導線を改善。") == (
        "Call to Action: 登録導線を改善。"
    )


def test_prepare_tts_text_strips_plain_script_labels() -> None:
    out = prepare_tts_text("Hook: つかみです。Insight: 意味です。Action: 行動です。", {})
    assert "Hook" not in out and "Insight" not in out and "Action" not in out
    assert "つかみです。" in out and "意味です。" in out and "行動です。" in out


def test_strip_script_markup_noop_on_plain_text() -> None:
    assert strip_script_markup("普通の文。") == "普通の文。"


def test_strip_script_markup_removes_multiple_list_prefixes() -> None:
    # T42 Codex 実証: 箇条書き prefix は `?` (最大1回) までしか剥がれず、
    # 二重 prefix ("- -" 等) が素通りしていた。`*` (0回以上) に変更して修正。
    assert strip_script_markup("- - Hook: abc") == "abc"
    assert strip_script_markup("1. - **Insight:** x") == "x"
    # 既存の単一 prefix ケースが非破壊であることも併せて確認。
    body = "- **Hook:** つかみです。\n1. **Insight:** 意味です。\n+ Action: 行動です。"
    assert strip_script_markup(body) == "つかみです。\n意味です。\n行動です。"


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


def test_sanitize_drops_mixed_katakana_chinese_title() -> None:
    out = sanitize_chinese_title_quotes(
        "本日注目の話題です。「モアスレッド：完成MiniMax M3大規模モデル适配」が報じられました。"
    )
    assert out == "本日注目の話題が報じられました。"
    assert "适配" not in out
    assert "MiniMax" not in out


def test_sanitize_cleans_placeholder_topic_repetition() -> None:
    out = sanitize_chinese_title_quotes("「モアスレッド：完成MiniMax M3大規模モデル适配」が話題になっています。")
    assert out == "この話題が注目されています。"


@pytest.mark.parametrize(
    "jp_quote",
    [
        "「生成AI」",
        "「東京大学」",
        "「人工知能」",
        "「半導体」",
        "「国際会議」",
        "「機械学習」",
        "「自動運転」",
        "「国際競争」",
        "「関与」",
        "「付与」",
        "「与党」",
        "「給与」",
        "「貸与」",
    ],
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


def test_sanitize_evacuates_short_simplified_title_missing_signal_char() -> None:
    # T42 Codex 実証: 「竞」が _SIMPLIFIED_HAN 未収録で短い簡体字タイトルが素通りしていた。
    assert sanitize_chinese_title_quotes("「竞争」が話題になっています。") == "この話題が注目されています。"
    assert sanitize_chinese_title_quotes("「竞价排名」というニュース。") == "このニュース。"


@pytest.mark.parametrize(
    "jp_quote",
    ["「競争」", "「生成AI」", "「関与」", "「参考」"],
)
def test_sanitize_new_simplified_signal_chars_preserve_japanese(jp_quote: str) -> None:
    # T42 で追加した簡体字シグナル文字 (态势报线统经说视计讯论读类织页项顶竞) が
    # 日本語新字体 (競争等) を誤検知しないことを確認する (非破壊)。
    assert sanitize_chinese_title_quotes(jp_quote) == jp_quote


# ---------- split_markdown_topics (T62, Issue #65 トピック境界セグメント分割) ----------


def test_split_markdown_topics_no_headings_returns_single_part() -> None:
    # `## ` 見出しが無い旧形式は従来どおり全体 1 パート (produce の後方互換)。
    md = "# タイトル\n生成日時: 2026-08-01 10:00 / LLM profile: A\n\nこんにちは。本日のニュースです。\n"
    result = split_markdown_topics(md)
    assert result == [strip_markdown_structure(md)]
    assert len(result) == 1
    assert "こんにちは" in result[0]


def test_split_markdown_topics_intro_only_no_topics() -> None:
    # トピック無し (見出しゼロ) の最小構成もイントロのみの単一パートになる。
    md = "# 華流テック通信 — HAL Daily Briefing\n\nタイトルコールです。\nオープニングです。\n"
    result = split_markdown_topics(md)
    assert len(result) == 1
    assert "タイトルコールです" in result[0]
    assert "オープニングです" in result[0]
    assert not result[0].lstrip().startswith("#")


def test_split_markdown_topics_multiple_headings_splits_intro_and_each_topic() -> None:
    md = (
        "# 華流テック通信 — HAL Daily Briefing\n"
        "生成日時: 2026-08-01 10:00 / LLM profile: A\n\n"
        "タイトルコールです。\n"
        "オープニングです。\n\n"
        "## 1. トピック1タイトル\n"
        "トピック1本文です。\n\n"
        "## 2. トピック2タイトル\n"
        "トピック2本文です。\n\n"
        "締めの挨拶です。\n\n"
        "---\n"
        "### ソース一覧\n"
        "1. [トピック1タイトル](https://example.com/1)\n"
        "2. [トピック2タイトル](https://example.com/2)\n"
    )
    result = split_markdown_topics(md)
    assert len(result) == 3  # イントロ + トピック2件

    intro, topic1, topic2 = result
    assert "タイトルコールです" in intro
    assert "オープニングです" in intro
    assert "華流テック通信" not in intro  # # 見出し行は除去済み

    assert "トピック1本文です" in topic1
    assert "トピック2" not in topic1  # 次見出し以降は含まない

    assert "トピック2本文です" in topic2
    assert "締めの挨拶です" in topic2  # 末尾トピックは締め挨拶も含む (outro segment は作らない)
    assert "ソース一覧" not in topic2  # レベル3見出しも除去される
    assert "https://" not in topic2  # ソース一覧のリンク行は除去される
    assert "---" not in topic2


def test_split_markdown_topics_drops_empty_sections() -> None:
    # 見出し直後に本文が無いセクション (strip 後に空文字) は除外される。
    md = "# タイトル\nイントロ本文\n\n## 1. 空トピック\n\n## 2. 本文ありトピック\n本文です。\n"
    result = split_markdown_topics(md)
    assert result == ["イントロ本文", "本文です。"]


def test_split_markdown_topics_all_empty_returns_empty_list() -> None:
    # 見出しも無く strip 後に何も残らない入力は空リスト (produce 側の 0 件ゲートに委ねる)。
    assert split_markdown_topics("") == []
    assert split_markdown_topics("# タイトルのみ\n生成日時: 2026-08-01\n") == []
