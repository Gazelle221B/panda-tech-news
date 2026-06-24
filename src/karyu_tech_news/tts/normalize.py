"""読み仮名辞書 + テキスト正規化 (Sprint 2 Ticket T26, FR-092).

ADR-0006: Irodori-TTS v3 は漢字読み精度が弱い (公式明記)。中国企業名/モデル名/
メディア名/専門用語のカナ読みを `config/reading_dict.yaml` で制御し、TTS 合成前に
機械的に置換する。台本本文は LLM がカナ化するが、fallback テンプレの原題や
取りこぼしに対する安全網として機能する。
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
    pattern = re.compile("|".join(re.escape(t) for t in terms))
    return pattern.sub(lambda m: reading_dict[m.group(0)], text)


# 中国語原題の翻字 (T35): fallback テンプレの Hook は原題を「<中国語>」で埋め込む
# (例: 「三星电子HBM4芯片推出四个月销售额突破10亿美元」というニュース...)。
# 日本語特化 TTS (Irodori v3) は簡体字を誤読/崩す (文字化け) ため、漢字を pinyin に
# 翻字して読めるようにする。見出し/ソース一覧は strip_markdown_structure で除去済みなので、
# ここで対象になるのは本文の「」引用に残った原題のみ。
# 検出: 「」内に漢字があり・日本語かな無し・かつ**簡体字特有文字**を含む span = 中国語原題。
# かな無しだけでは漢字のみの日本語引用 (生成AI / 東京大学 / 人工知能 等) も誤翻字するため
# (Codex High 指摘)、日本語新字体/繁体字と字形が異なる簡体字を 1 つ以上含むことを必須にする。
# precision 優先: 共有字のみの稀な中国語原題は取りこぼす (従来通り素のまま) が、正しい日本語は壊さない。
_HAN_RE = re.compile(r"[㐀-䶿一-鿿]")
_KANA_RE = re.compile(r"[぀-ヿ]")
_QUOTED_RE = re.compile(r"「([^」]*)」")
# 簡体字特有 (日本語新字体と字形が異なる) 高頻度文字。中国語原題の確証に使う。
# 共有字 (国 学 会 体 来 万 数 医 区 等 = 日本語新字体と同形) は意図的に除外。
_SIMPLIFIED_HAN = frozenset(
    "电发东车书长门问题马龙风飞见现实战应产优传总处复币录据网罗联获营认让设证识护击损银难"
    "验销额亿灵续闻监构该场选开关间时这过还进远边转较钟际团图价习张划评试语资业务员观规严"
    "众货质购贸费软轻输载连运钱铁错队阶险顺顾频颗颜驱鸟鸡齐齿龟丰临举义乐乡买争亚仅从仓伟"
    "伤伦伪侧侨偿厂历压县参双变叠号叶团圆园块坚执扩扫担拥据摆术机权条标树桥检欢残职"
)


def _han_to_pinyin(text: str) -> str:
    """漢字を声調なし pinyin (空白区切り) へ。非漢字 (Latin/数字/記号) はそのまま保持.

    pypinyin 未導入時は fail-open で原文を返す (依存に含むが防御的に)。
    """
    try:
        from pypinyin import Style, lazy_pinyin
    except ImportError:  # pragma: no cover
        logger.warning("pypinyin 未導入 — 中国語翻字をスキップ")
        return text
    return " ".join(lazy_pinyin(text, style=Style.NORMAL))


def transliterate_chinese_titles(text: str) -> str:
    """「」内が中国語 (漢字あり・かななし) の span を pinyin に翻字する (TTS 前処理).

    日本語混在の引用やナレーションは対象外。Latin/数字/記号は保持。
    """

    def _repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        is_chinese_title = (
            _HAN_RE.search(inner) is not None
            and _KANA_RE.search(inner) is None
            and any(ch in _SIMPLIFIED_HAN for ch in inner)
        )
        if is_chinese_title:
            return f"「{_han_to_pinyin(inner)}」"
        return m.group(0)

    return _QUOTED_RE.sub(_repl, text)
