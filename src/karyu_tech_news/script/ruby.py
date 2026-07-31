"""台本 LLM のインラインルビ注釈パーサ + 自動読み辞書 I/O (Sprint T56, Issue #52).

読み辞書 (`config/reading_dict.yaml`) の手動追記を不要にする恒久機構。writer LLM に
`[[表記|カナ読み]]` の形式で読みをインライン出力させ (`script/generate.py` のプロンプト)、
本モジュールで本文から抽出・除去したうえで自動読み辞書 (`data/reading_dict.auto.yaml`)
へキャッシュする (`script/runner.py` から呼ぶ)。produce 側 (`main.py`) は手動辞書と
二層マージし、手動辞書を常に優先する (手動が最終確認済みの読みのため)。

配置: `script` 層 (`tts/` ではない)。`config` 以外の `karyu_tech_news.*` に依存しない
独立ユーティリティであり、利用者 (`script/runner.py`) と同じ層に置くことで
`docs/architecture.md` §1 の逆向き依存禁止 (script は tts を import しない) を満たす。
produce (CLI/main.py) からの参照は上位層→下位層の順方向であり問題ない。

fail-open: 抽出・保存・読込のいずれの失敗も draft 生成/TTS 合成全体を落とさない。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from karyu_tech_news.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

DEFAULT_AUTO_READING_DICT_PATH = PROJECT_ROOT / "data" / "reading_dict.auto.yaml"

# [[表記|カナ読み]] 形式。表記・読みに `[` `]` `|` 改行を含めない (これらを含む/入れ子/
# 閉じ忘れは fail-open で素通しする対象であり、そもそもマッチさせない)。
_RUBY_RE = re.compile(r"\[\[([^\[\]|\n]*)\|([^\[\]|\n]*)\]\]")


def extract_ruby(text: str) -> tuple[str, dict[str, str]]:
    """本文中の `[[表記|カナ読み]]` を抽出し、本文からは表記だけを残す.

    - malformed (表記/読みが空、閉じ忘れ、入れ子、改行混入) は変換せず素通しする
      (fail-open。壊れた記法をそのまま本文に残す方が、誤って本文を壊すより安全)。
    - 表記・読みの前後空白は strip する。
    - 同一表記が複数回出た場合は最初の読みを採用する。
    """
    mapping: dict[str, str] = {}

    def _repl(m: re.Match[str]) -> str:
        surface = m.group(1).strip()
        reading = m.group(2).strip()
        if not surface or not reading:
            return m.group(0)  # malformed (空表記/空読み) は素通し
        if surface not in mapping:
            mapping[surface] = reading
        return surface

    cleaned = _RUBY_RE.sub(_repl, text)
    return cleaned, mapping


def load_auto_readings(path: Path) -> dict[str, str]:
    """自動読み辞書 (フラット YAML `表記: カナ`) を読む.

    ファイル不在・YAML 破損・非マッピング型は空 dict にフォールバックする
    (fail-open, WARN ログ)。
    """
    if not path.exists():
        return {}
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        logger.warning("auto reading dict load failed, fail-open to empty: %s: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        logger.warning("auto reading dict is not a mapping, fail-open to empty: %s", path)
        return {}
    flat: dict[str, str] = {}
    for term, reading in raw.items():
        if term is None or reading is None:
            continue  # YAML null は除外 (tts.normalize.load_reading_dict と同じ扱い)
        term_s, reading_s = str(term).strip(), str(reading).strip()
        if term_s and reading_s:
            flat[term_s] = reading_s
    return flat


def append_auto_readings(path: Path, mapping: dict[str, str]) -> None:
    """新出の表記だけを自動読み辞書へ追記保存する (既存キーは上書きしない).

    ファイル形式は `config/reading_dict.yaml` と同じ「表記: カナ」のフラット YAML
    (カテゴリ階層は持たない)。親ディレクトリが無ければ作成する。読み書き失敗は
    例外を投げず WARN ログに留める (fail-open。辞書 I/O 障害で draft 生成全体を
    落とさない)。
    """
    if not mapping:
        return
    try:
        existing = load_auto_readings(path)
        new_terms = {k: v for k, v in mapping.items() if k not in existing}
        if not new_terms:
            return
        merged = {**existing, **new_terms}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(merged, allow_unicode=True, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("auto reading dict append failed, fail-open: %s: %s", path, exc)
