"""読み辞書カバレッジ観測 (T46, 可観測性).

`config/reading_dict.yaml` は新語が出るたび人手追記が必要で、未収録語がどれだけ
素通りしているかを定量化する手段がなかった。本モジュールは `prepare_tts_text()`
適用前後のテキスト差分から、読み上げ困難なまま残存したトークン (未変換 ASCII
単語 / 簡体字シグナルを含む残存 CJK トークン) を抽出し、レポート化する。

**観測専用**: 辞書の自動追記・自動翻字・テキストの書き換えは一切行わない
(読み取り専用の後付け)。`normalize.py` の処理順序・内部呼び出しグラフには
依存せず、公開関数 `prepare_tts_text()` を素通しでもう一度呼ぶだけの
ブラックボックス diff で完結させる (normalize.py の内部実装変更に強くする)。
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from karyu_tech_news.tts.normalize import _CHINESE_TITLE_SIGNAL_HAN, prepare_tts_text

# 残存 ASCII 単語トークン: 英字 2 文字以上で始まり、英数字が続いてよい。
# 前後を英数字境界で挟まれない (長い識別子の内部を拾わない) ことを要求する。
_ASCII_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2,}[A-Za-z0-9]*(?![A-Za-z0-9])")

# CJK (漢字) の連続run。normalize.py の _HAN_RE と同じ Unicode 範囲を使う
# (Unicode ブロック定義そのものであり normalize.py の内部処理には依存しない)。
_HAN_RUN_RE = re.compile(r"[㐀-䶿一-鿿]+")


@dataclass(frozen=True)
class TokenCount:
    """トークンと出現回数."""

    token: str
    count: int


@dataclass(frozen=True)
class CoverageReport:
    """TTS 前処理後に残存する読み上げ困難トークンの観測結果."""

    ascii_residual_count: int
    ascii_top_tokens: tuple[TokenCount, ...]
    cjk_residual_count: int
    cjk_top_tokens: tuple[TokenCount, ...]
    candidate_count: int
    converted_count: int

    @property
    def dict_hit_rate(self) -> float | None:
        """候補語のうち prepare_tts_text で変換された割合 (候補 0 件なら None)."""
        if self.candidate_count == 0:
            return None
        return self.converted_count / self.candidate_count


def _cjk_simplified_tokens(text: str) -> list[str]:
    """簡体字シグナル文字を 1 文字以上含む漢字連続 run を抽出する.

    `_CHINESE_TITLE_SIGNAL_HAN` (normalize.py が中国語原題 quote 検出用に精度調整
    した集合) を再利用する。日本語新字体と同形の共有字 (参/争/与 等) を含まないため、
    正しい日本語の漢字熟語を誤検出しない (normalize.py 側の precision-first 方針を継承)。
    """
    return [
        tok for tok in _HAN_RUN_RE.findall(text) if any(ch in _CHINESE_TITLE_SIGNAL_HAN for ch in tok)
    ]


def _candidate_tokens(text: str) -> Counter[str]:
    """観測対象トークン (ASCII 単語 + 簡体字シグナル CJK) を出現数付きで数える."""
    counts: Counter[str] = Counter(_ASCII_TOKEN_RE.findall(text))
    counts.update(_cjk_simplified_tokens(text))
    return counts


def analyze_coverage(
    raw_text: str,
    reading_dict: dict[str, str],
    *,
    top_n: int = 10,
) -> CoverageReport:
    """`prepare_tts_text()` 適用前後の差分から辞書カバレッジを観測する.

    - `raw_text`: TTS 前処理にかける前の (合成対象) テキスト。
    - `reading_dict`: `load_reading_dict()` で読み込んだフラット辞書。
    - 候補語 (`raw_text` 中の ASCII 単語 / 簡体字シグナル CJK トークン) のうち、
      `prepare_tts_text()` 適用後のテキストに同じ文字列が残っていなければ
      「変換された」とみなす。dict 置換以外の前処理 (URL 除去等) による
      消失も広義の「変換」として数える (診断目的であり、厳密な dict 単体の
      ヒット率ではなく "算出可能な範囲" の近似値)。
    """
    prepared = prepare_tts_text(raw_text, reading_dict)

    dict_keys = set(reading_dict)
    ascii_residual = Counter(
        tok for tok in _ASCII_TOKEN_RE.findall(prepared) if tok not in dict_keys
    )
    cjk_residual = Counter(_cjk_simplified_tokens(prepared))

    raw_candidates = _candidate_tokens(raw_text)
    prepared_tokens = _candidate_tokens(prepared)

    candidate_count = sum(raw_candidates.values())
    residual_count = sum(
        min(count, prepared_tokens.get(token, 0)) for token, count in raw_candidates.items()
    )
    converted_count = candidate_count - residual_count

    return CoverageReport(
        ascii_residual_count=sum(ascii_residual.values()),
        ascii_top_tokens=tuple(TokenCount(t, c) for t, c in ascii_residual.most_common(top_n)),
        cjk_residual_count=sum(cjk_residual.values()),
        cjk_top_tokens=tuple(TokenCount(t, c) for t, c in cjk_residual.most_common(top_n)),
        candidate_count=candidate_count,
        converted_count=converted_count,
    )


def format_coverage_summary(report: CoverageReport) -> str:
    """CLI 出力向けにレポートを 1 ブロックの文字列へ整形する."""
    hit_rate = report.dict_hit_rate
    hit_rate_str = f"{hit_rate:.1%}" if hit_rate is not None else "N/A (候補0件)"
    ascii_top = ", ".join(f"{t.token}x{t.count}" for t in report.ascii_top_tokens) or "-"
    cjk_top = ", ".join(f"{t.token}x{t.count}" for t in report.cjk_top_tokens) or "-"
    return (
        "読み辞書カバレッジ: "
        f"辞書ヒット率={hit_rate_str} (候補{report.candidate_count}/変換{report.converted_count}), "
        f"残存ASCII={report.ascii_residual_count}件 [{ascii_top}], "
        f"残存CJK(簡体字)={report.cjk_residual_count}件 [{cjk_top}]"
    )
