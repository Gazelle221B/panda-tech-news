# T57 — 残存 ASCII 略語のカナ綴りフォールバック (Issue #53)

- 日付: 2026-07-31
- ブランチ: `agent/T57-ascii-fallback-impl`
- 実装者: Claude Code
- 参照: [Issue #53](https://github.com/Gazelle221B/panda-tech-news/issues/53)

## 背景

実エピソード検証で、読み辞書 (`config/reading_dict.yaml`) に未登録だった「HAL」が TTS で
不明瞭な発話になった。辞書の手編集は事後対応にしかならないため、辞書に無い ASCII 略語が
生のまま TTS に到達する事故を構造的に塞ぐ最終安全網が必要だった。

## 変更内容

### 1. `src/karyu_tech_news/tts/normalize.py`

- `_ASCII_LETTER_KANA`: 英字 1 文字 → カナの固定マップ (A→エー 〜 Z→ゼット、指示された
  対応表どおり)。
- `_ASCII_ABBREVIATION_RE`: `(?<![A-Za-z0-9._\-])[A-Z]{2,5}(?![A-Za-z0-9._\-])`。
  既存 `_reading_term_pattern` と同じ境界思想を流用し、前後が `[A-Za-z0-9._\-]` なら
  発火しない (識別子内部を壊さない)。
- `spell_out_residual_ascii_tokens()`: 上記正規表現にマッチした「純アルファベット全大文字
  2〜5 文字」トークンを 1 文字ずつカナへ変換する。小文字混在 (MoWorld 等)・数字混在
  (5G, M3, HBM4 等)・1 文字トークンは、文字クラス自体 (`[A-Z]`) と境界条件により自然に
  対象外となる (追加の除外ロジック不要)。これら 3 種は本関数の担当外で、別チケット T56 の
  LLM ルビ生成が担当する分担であることを docstring に明記した。
- `prepare_tts_text()`: 最終段 (読み辞書適用・中国語原題退避の後) で
  `spell_out_residual_ascii_tokens()` を呼ぶよう変更。辞書が常に優先されるパイプライン順序を
  維持した。

### 2. `config/reading_dict.yaml`

- `english` カテゴリに `HAL: ハル` を追加 (GPU と HBM4 の間、アルファベット順の位置)。
  既存の `HAL Daily Briefing` エントリとは、`normalize_text()` が `sorted(key=len,
  reverse=True)` で長い term を先に試すため、単一正規表現の中で安全に共存する
  (「HAL Daily Briefing」が「HAL」より先に一致)。

### 3. テスト (`tests/test_tts_normalize.py`)

`spell_out_residual_ascii_tokens` を直接叩くテストと、`prepare_tts_text` 経由でパイプライン
全体を通すテストの両方を追加 (計 12 件):

- `spell_out_residual_ascii_tokens` 単体: 既知略語の綴り読み化 (DOI, ISC)、小文字/数字混在/
  1 文字トークンの不変、`OpenAI_API` のような識別子内部・7 文字連続大文字の内部での非発火、
  文中複数トークンの同時変換。
- `prepare_tts_text` 経由: 空辞書での綴り読みフォールバック、読み辞書エントリがフォールバック
  に優先すること (`AI` 等)、`MoWorld`/`v1.0.0`/`5G`/単文字 `A` の不変、`OpenAI_API` の不変、
  実辞書ロードで `SAIL賞` が辞書優先で一括変換され `SAIL` 単体の綴り読みが先に発火しないこと、
  単独 `HAL` → `ハル`、`HAL Daily Briefing` → `ハル デイリーブリーフィング` (辞書エントリの
  共存確認)、文中複数トークンの同時変換。

## 既存テストへの追随修正

`tests/test_tts_synthesize.py::test_synthesize_script_fail_open_on_sentence_error` が
新フォールバックにより red 化した。このテストはモック TTS エンジンの例外トリガーとして
「BOOM」という任意の全大文字文字列を使っていたが、`synthesize_script` 内部で
`prepare_tts_text` を通すため「BOOM」(2〜5 文字の全大文字トークン) が新フォールバックで
「ビーオーオーエム」に変換され、`if "BOOM" in req.text` が不成立になっていた。
テストの意図 (1 文の合成失敗で番組を止めない fail-open 確認) 自体は本チケットと無関係なため、
トリガー文字列を小文字の `"boom"` に変更し (全大文字 2〜5 文字のみが対象のフォールバックの
影響を受けない)、コメントで理由を明記した。無関係なリファクタは含めていない。

## 品質ゲート (fresh 実行)

```
$ uv run pytest
575 passed, 11 skipped in 9.17s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 84 source files

$ git diff --check
(出力なし = クリーン)
```

## 保守側に倒した判断

- **境界条件の除外ロジックを持たせず正規表現の文字クラスに委ねた**: 小文字混在・数字混在・
  1 文字トークンの除外は、`[A-Z]{2,5}` という文字クラス自体 (小文字・数字を含まない) と
  `_reading_term_pattern` 由来の境界条件 (前後が英数字・`.`・`_`・`-` なら非発火) だけで
  漏れなく満たされることを確認した (`HBM4` は末尾の `4` が境界クラスに含まれるため
  `HBM` 部分だけの発火が起きない、`5G` は大文字ランが 1 文字のため対象外、等)。追加の
  条件分岐を書くより、既存パターンとの一貫性と正確性を優先した。
- **6 文字以上の連続大文字ランは対象外 (仕様に明記は無いが自然な帰結)**: 正規表現の
  前後境界チェックにより、6 文字以上の連続大文字ランはどの部分文字列を取っても左右いずれかの
  境界チェックに失敗し、一切変換されない (`ABCDEFG` のようなケースをテストで固定)。仕様書には
  明記されていなかったが、「2〜5 文字のトークン」という指示と整合する自然な副作用として
  受け入れた。
- **`tests/test_tts_synthesize.py` の追随修正**: 指示のスコープ外だが、本チケットの変更が
  直接の原因で red 化した既存テストのため、Surgical Changes (AGENTS.md §12.3) の原則に沿って
  トリガー文字列のみを最小修正した (関数シグネチャやアサーションの意図は無変更)。
