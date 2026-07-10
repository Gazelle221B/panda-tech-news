"""読み仮名辞書 + テキスト正規化 (Sprint 2 Ticket T26, FR-092).

ADR-0006: Irodori-TTS v3 は漢字読み精度が弱い (公式明記)。中国企業名/モデル名/
メディア名/専門用語のカナ読みを `config/reading_dict.yaml` で制御し、TTS 合成前に
機械的に置換する。台本本文は LLM がカナ化するが、fallback テンプレの原題や
取りこぼしに対する安全網として機能する。長い中国語原題は pinyin で読ませず、
発話本文では日本語の汎用参照へ退避する。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


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


# inline Markdown link / bare URL は表示専用情報。TTS では URL や括弧記号を読まない。
_MD_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:https?://|mailto:)[^)]+\)")
_URL_RE = re.compile(r"https?://[^\s<>\]）)」』】。、，！？]+")
_REPLACEMENT_CHAR_REPAIRS = {
    "返り�き": "返り咲き",  # 2026-06-25 実 draft #10 で観測。記号読みを避け意味も補修。
}
_DUPLICATE_PAREN_RE = re.compile(
    r"(?P<term>[A-Za-z0-9._+/\-぀-ヿ㐀-鿿]{1,40})[（(](?P=term)[）)]"
)


def strip_link_markup(text: str) -> str:
    """TTS 前に inline Markdown link と bare URL を除去する."""
    text = _MD_INLINE_LINK_RE.sub(r"\1", text)
    return _URL_RE.sub("", text)


def strip_invalid_tts_chars(text: str) -> str:
    """TTS が記号名として読んでしまう壊れた文字を除去・補修する."""
    for broken, repaired in _REPLACEMENT_CHAR_REPAIRS.items():
        text = text.replace(broken, repaired)
    return text.replace("\ufffd", "")


def strip_duplicate_parentheticals(text: str) -> str:
    """`バイトダンス（バイトダンス）` のような完全重複括弧を除去する."""
    return _DUPLICATE_PAREN_RE.sub(r"\g<term>", text)


# 「原語（カナ読み）」形式は原語を読ませずカナ読みだけを残す。
# 例: 灵晟（リンション） -> リンション、FSD（エフエスディー） -> エフエスディー。
_PRONUNCIATION_PAREN_RE = re.compile(
    r"(?P<term>"
    r"[A-Za-z0-9][A-Za-z0-9 ._+/\-]{0,40}"
    r"|"
    r"[㐀-䶿一-鿿]{1,40}"
    r")"
    r"[（(](?P<reading>[^）)]*[぀-ヿ][^）)]*)[）)]"
)


def strip_pronunciation_parentheticals(
    text: str,
    headwords: set[str] | None = None,
) -> str:
    """「原語（カナ読み）」からカナ読みだけを残す (二重読み防止)."""

    def _repl(m: re.Match[str]) -> str:
        term = m.group("term")
        if any(ch.isascii() and ch.isalnum() for ch in term):
            prefix, sep, _headword = term.rpartition(" ")
            return f"{prefix}{sep}{m.group('reading')}" if sep else m.group("reading")
        simplified_positions = [i for i, ch in enumerate(term) if ch in _SIMPLIFIED_HAN]
        if not simplified_positions:
            return m.group(0)
        if headwords:
            candidates = [
                word for word in headwords if term.endswith(word) and any(ch in _SIMPLIFIED_HAN for ch in word)
            ]
            if candidates:
                headword = max(candidates, key=len)
                return term[: -len(headword)] + m.group("reading")
        return term[: simplified_positions[0]] + m.group("reading")

    return _PRONUNCIATION_PAREN_RE.sub(_repl, text)


# 台本本文の Markdown 構造マーカー (**Hook:** / **Insight:** / **Action:**) を除去する用。
# Discord 表示には必要だが TTS では「アスタリスク アスタリスク フック コロン」と読み上げて
# しまうため、合成前に落とす (実音声 smoke で発見, architecture §4 の script→tts 境界)。
# 箇条書き prefix ((?:[-*+]|\d+[.)]) [ \t]+) は `*` で 0 回以上許容する (T42 Codex 指摘:
# `- - Hook: abc` のような二重 prefix が `?` (最大1回) では剥がれず素通りしていた)。
_SCRIPT_LABEL_RE = re.compile(
    r"(?:^|(?<=[\n。！？!?]))[ \t]*(?:(?:[-*+]|\d+[.)])[ \t]+)*"
    r"(?:\*\*\s*)?(?:Hook|Insight|Action)\s*[:：]\s*(?:\*\*)?\s*"
)


def strip_script_markup(text: str) -> str:
    """TTS 前に台本の Markdown マーカーを除去する (ラベルと残存 ** を落とす)."""
    return _SCRIPT_LABEL_RE.sub("", text).replace("**", "")


# 台本 Markdown の見出し行 (`# / ##`) と生成メタ行を除去する用。見出しは番組タイトルや
# **中国語原文の記事タイトル** で朗読対象でなく (要件 §9.6 中国メディア本文朗読禁止・
# editorial-policy §1/§10)、Kokoro 等が中国語を遅く誤読し尺も膨らむ。生成日時/LLM profile
# のビルドメタも発話しない。保存済み台本 markdown を produce で合成する経路で使う。
_MD_HEADER_RE = re.compile(r"^[ \t]*#{1,6}[ \t].*$", re.MULTILINE)
_MD_META_RE = re.compile(r"^[ \t]*生成日時[:：].*$", re.MULTILINE)
# ソース一覧の Markdown リンク行 (`1. [中国語原文タイトル](https://...)`)。原文タイトル+URL は
# 発話対象でない (出典は Discord の視覚表示に残す)。番号/箇条書き付きの単独リンク行のみ対象。
_MD_LINK_LINE_RE = re.compile(
    r"^[ \t]*(?:[-*]|\d+[.)])?[ \t]*\[[^\]]*\]\([^)]*\)[ \t]*$", re.MULTILINE
)
# 水平線 (`---` / `***` / `___`)。装飾でナレーションでなく、Kokoro が記号を読むため除去。
_MD_HR_RE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.MULTILINE)


def strip_markdown_structure(text: str) -> str:
    """TTS 前に Markdown 見出し行・生成メタ行・ソース一覧リンク行を除去する.

    見出し (`# 華流テック通信...` / `## 1. 智谱：...`) は番組タイトルや中国語原文の記事
    タイトル、ソース一覧 (`1. [原文](URL)`) は出典で、いずれも発話対象でない (要件 §9.6
    中国メディア本文朗読禁止・editorial-policy §1/§10、URL も読まない)。生成日時/LLM profile
    のメタも読まない。Hook/Insight/Action の日本語ナレーションのみ残す (produce 経路で使用)。
    """
    text = _MD_HEADER_RE.sub("", text)
    text = _MD_META_RE.sub("", text)
    text = _MD_LINK_LINE_RE.sub("", text)
    text = _MD_HR_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def normalize_text(text: str, reading_dict: dict[str, str]) -> str:
    """text 中の既知用語を読み仮名へ置換する (TTS 発音用).

    - **最長一致優先**: 長い用語を先に当て、部分置換で壊さない。
    - **1 パス置換**: 置換後の読みに含まれる別用語を再置換しない。
    """
    if not text or not reading_dict:
        return text
    terms = sorted(reading_dict, key=len, reverse=True)
    pattern = re.compile("|".join(_reading_term_pattern(t) for t in terms))
    return pattern.sub(lambda m: reading_dict[m.group(0)], text)


def _reading_term_pattern(term: str) -> str:
    """辞書 term 用 regex。ASCII 語は長い識別子の内部で部分一致させない."""
    escaped = re.escape(term)
    if any(ch.isascii() and ch.isalnum() for ch in term):
        right_boundary = r"[._\-]" if term.endswith("+") else r"[A-Za-z0-9._\-]"
        return rf"(?<![A-Za-z0-9._\-]){escaped}(?!{right_boundary})"
    return escaped


# 中国語原題の発話退避 (T35/T36): かつては本文の「<中国語原題>」を pinyin へ
# 翻字していたが、実 ASR で長い pinyin 羅列そのものが「変な読み」に聞こえることを確認。
# 見出し/ソース一覧は strip_markdown_structure で除去済みなので、本文 quote に残った
# 中国語原題は発話本文では「この話題」へ置換する。原題は Markdown 側に視覚情報として残る。
# 検出: 「」内に漢字があり・ひらがな無し・かつ**簡体字シグナル文字**を含む span = 中国語原題。
# ひらがな無しだけでは漢字のみの日本語引用 (生成AI / 東京大学 / 人工知能 等) も誤翻字するため
# (Codex High 指摘)、日本語新字体/繁体字と字形が異なる簡体字を 1 つ以上含むことを必須にする。
# カタカナは中国企業名の日本語表記と中国語原題が混ざる quote にも出るため、保護条件にしない。
# precision 優先: 共有字のみの稀な中国語原題は取りこぼす (従来通り素のまま) が、正しい日本語は壊さない。
_HAN_RE = re.compile(r"[㐀-䶿一-鿿]")
_HIRAGANA_RE = re.compile(r"[ぁ-ゟ]")
_QUOTED_RE = re.compile(r"「([^」]*)」")
# 簡体字特有 (日本語新字体と字形が異なる) 高頻度文字。中国語原題の確証に使う。
# 共有字 (国 学 会 体 来 万 数 医 区 等 = 日本語新字体と同形) は意図的に除外。
_SIMPLIFIED_HAN = frozenset(
    "电发东车书长门问题马龙风飞见现实战应产优传总处复币录据网罗联获营认让设证识护击损银难"
    "验销额亿灵续闻监构该场选开关间时这过还进远边转较钟际团图价习张划评试语资业务员观规严"
    "众货质购贸费软轻输载连运钱铁错队阶险顺顾频颗颜驱鸟鸡齐齿龟丰临举义乐乡买争亚仅从仓伟"
    "伤伦伪侧侨偿厂历压县参双变叠号叶团圆园块坚执扩扫担拥据摆术机权条标树桥检欢残职"
    # T42 Codex 実証: 短い簡体字タイトル (例:「竞争」) が未収録で素通りしていた。
    # 各字を日本語新字体と 1 字ずつ字形比較し、明確に異なるもののみ追加 (同形字は含めない)。
    "态势报线统经说视计讯论读类织页项顶竞"
)
# 公開名 (T46 Copilot レビュー: coverage.py が非公開シンボルに直接依存していた)。
# 後方互換のため旧名 `_CHINESE_TITLE_SIGNAL_HAN` もエイリアスとして維持する。
CHINESE_TITLE_SIGNAL_HAN = (_SIMPLIFIED_HAN | frozenset("刚个办兴广责问让适级头为")) - frozenset(
    "参争与"
)
_CHINESE_TITLE_SIGNAL_HAN = CHINESE_TITLE_SIGNAL_HAN
CHINESE_TITLE_PLACEHOLDER = "この話題"


def _is_chinese_title_quote(text: str) -> bool:
    return (
        _HAN_RE.search(text) is not None
        and _HIRAGANA_RE.search(text) is None
        and any(ch in _CHINESE_TITLE_SIGNAL_HAN for ch in text)
    )


def _cleanup_chinese_title_placeholder_context(text: str) -> str:
    """置換後に不自然になる定型文を発話向けに整える."""
    text = text.replace(f"{CHINESE_TITLE_PLACEHOLDER}というニュース", "このニュース")
    text = text.replace(f"{CHINESE_TITLE_PLACEHOLDER}が話題になっています", "この話題が注目されています")
    text = text.replace(
        f"本日注目の話題です。{CHINESE_TITLE_PLACEHOLDER}が報じられました。",
        "本日注目の話題が報じられました。",
    )
    return text


def sanitize_chinese_title_quotes(
    text: str,
    reading_dict: dict[str, str] | None = None,
) -> str:
    """「」内の中国語原題を TTS 発話向けに退避する.

    - 既知の短い固有名詞が quote 全体なら読み辞書の読みを残す。
    - 長い中国語原題は pinyin 羅列にせず `この話題` へ置換する。
    - 日本語混在の引用やナレーションは対象外。
    """

    def _repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if _is_chinese_title_quote(inner):
            if reading_dict and inner in reading_dict:
                return f"「{reading_dict[inner]}」"
            return CHINESE_TITLE_PLACEHOLDER
        return m.group(0)

    return _cleanup_chinese_title_placeholder_context(_QUOTED_RE.sub(_repl, text))


def transliterate_chinese_titles(text: str) -> str:
    """後方互換名: 現在は pinyin 翻字ではなく中国語原題 quote の発話退避を行う."""
    return sanitize_chinese_title_quotes(text)


def prepare_tts_text(text: str, reading_dict: dict[str, str]) -> str:
    """TTS 入力用に台本文字列を正規化する.

    順序が品質に直結する。中国語原題 quote は、読み辞書が `豆包` → `ドウバオ`
    のようなカナを混ぜる前に退避する。カナ混入後だと日本語保護ガードが働き、
    中国語原題が TTS に残ってしまう。
    """
    cleaned = strip_script_markup(text)
    cleaned = strip_invalid_tts_chars(cleaned)
    cleaned = strip_duplicate_parentheticals(cleaned)
    cleaned = strip_link_markup(cleaned)
    cleaned = strip_ascii_gloss(cleaned)
    cleaned = strip_pronunciation_parentheticals(cleaned, set(reading_dict))
    translated_first = sanitize_chinese_title_quotes(cleaned, reading_dict)
    normalized = normalize_text(translated_first, reading_dict)
    normalized = strip_duplicate_parentheticals(normalized)
    # 読み辞書に載っていない簡体字 title がまだ残る場合の保険。通常は no-op。
    return sanitize_chinese_title_quotes(normalized, reading_dict)
