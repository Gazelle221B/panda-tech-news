# T60 — 無内容テンプレ台本の放送防止 (薄記事ペナルティ + テンプレ枠ドロップ, Issue #60)

- 日付: 2026-08-01
- ブランチ: `agent/T60-template-drop-impl`
- 実装者: Claude Code
- 参照: Issue #60

## 背景

実配信で「Hook: 今日は中華圏の AI ニュースを一つ取り上げます…」という無内容なテンプレ台本
(T18 `generate_with_fallback` の最終防衛) が1枠そのまま放送された。根本原因は RSS summary
が13文字しかない薄記事が prescore 上位に選定され、writer が意味のある台本を書けず全リトライ
失敗して T18 テンプレに fail-open したこと。対策は2層 (原因側の抑制 + 結果側のドロップ)。

## 変更内容

### 1. 薄記事ペナルティ (`src/karyu_tech_news/edit/prescore.py`)

- `THIN_SUMMARY_CHARS = 40`: `summary.strip()` がこの文字数未満なら「薄い」とみなす。
- `THIN_SUMMARY_PENALTY = -15`: 薄い候補への減点。既存スケール (キーワードバケツ加点
  10/20/30、Tier ボーナス最大 30) に対し、release バケツ (+10) 単体では相殺しきれない一方、
  urgent バケツ (+30) や Tier1 ボーナスと合わさった強い候補までは単独で足切りしない値として
  選定 (「明確に順位を下げるが単独では足切りにしない」)。値の根拠は docstring に明記。
- `thin_summary_penalty(summary: str | None) -> int`: 新規公開関数。`summary` が `None`
  (RSS 側で欠落) の場合も空文字と同じ「薄い」扱いにする。
- `extract_candidates` のスコア計算式に `+ thin_summary_penalty(summary)` を追加
  (`prescore_text` 自体は title+summary 結合テキストのキーワード走査のみを担うため変更せず、
  summary 単独の薄さ判定は別関数に分離した)。

### 2. テンプレ枠のドロップ (`src/karyu_tech_news/script/runner.py`)

- `MIN_TOPICS = 3`: 番組として成立する最低本数 (show_format の標準は 5 本, `edit/select.py`
  `SELECT_MAX`)。
- `_drop_overflow_templates()`: 生成結果のうち method が `METHOD_TEMPLATE` (T18 fallback)
  のトピックを、**除外しても残りが `MIN_TOPICS` 以上ある場合に限り**放送 (episode markdown /
  ソース一覧 / 番号付け) から除外する。床値を割る場合は何もせず全件を残す (テンプレのまま
  放送。番組を出すこと自体を最優先する fail-open の精神を維持)。除外した各トピックについて
  `item_id` とタイトル先頭 30 字を WARN ログに出す。
- `run_draft()`: `results` (writer 生成 + ルビ抽出後の全件) から `_drop_overflow_templates`
  で `aired_results` / `dropped_results` を分離し、`assemble_episode` には `aired_results`
  のみを渡す (markdown・ソース一覧・番号付け・notices が自動的に除外分を反映)。
  - `insert_script_versions` は従来どおり **`results` 全件** (除外分含む) を渡し、
    script_versions を監査証跡として保持する。
  - `insert_topic_candidates` の `positions` は `aired_results` (放送に残った分のみ) から
    再構築する。除外されたトピックは `judged` には残るため `TopicCandidate` 行自体は
    作られるが、`position` が振られないため `selected=False` になる (`position is not None`
    判定はそのまま)。「採用 = 実際に放送された」という既存 `selected` フィールドの意味論
    (`edit/abtest.py` の採用率評価が前提とする「番組に入ったか」) と整合させる判断。
  - `method_counts` は従来どおり `results` 全件 (除外分含む) から集計する — 「何本 LLM で
    書けたか」という生成試行の監査値として script_versions と同じ母集団を保つため。
  - `DraftRunResult` に `dropped_count: int` を追加。`selected_count` はテンプレ除外後の
    放送本数 (`len(aired_results)`) に意味を変更 (テンプレ除外が発生しない既存シナリオでは
    値は変わらない)。

### 3. `src/karyu_tech_news/script/fallback.py`

- `METHOD_TEMPLATE = "template"` を新規定数として追加し、`generate_with_fallback` の
  `method="template"` をこれに置き換え。runner.py がマジックストリングを重複させず
  テンプレ判定できるようにするための最小限の追加 (値自体は変わらないため既存テストへの
  影響なし)。

### 4. `src/karyu_tech_news/main.py`

- `draft` コマンドの完了サマリー行に `dropped={result.dropped_count}` を追加。

## テスト

### `tests/test_prescore.py` (6 件追加)

- `test_thin_summary_penalty_applies_to_13_char_summary`: 実例どおり 13 字の summary が
  `THIN_SUMMARY_PENALTY` 相当の減点になること。
- `test_thin_summary_penalty_no_penalty_at_40_chars_or_more`: 境界値 (ちょうど 40 字・
  それ以上) で減点なし。
- `test_thin_summary_penalty_applies_below_threshold`: 39 字は減点される (境界の反対側)。
- `test_thin_summary_penalty_none_summary_is_thin`: `None` も薄い扱いで減点。
- `test_thin_summary_penalty_whitespace_only_is_thin`: 空白のみの summary も薄い扱い。
- 既存 `test_extract_candidates_scores_and_sorts` / `test_extract_candidates_handles_null_summary`
  は summary="" (既定) や `None` のため新たにペナルティが乗る。期待値を
  `+ THIN_SUMMARY_PENALTY` へ更新し、後者には「None summary も減点される」ことを検証する
  アサーションを追加した (既存テストへの影響確認)。

### `tests/test_draft_runner.py` (2 件追加 + ヘルパー)

- `_editor_json(n)` / `_writer_forcing_template(target_title)` / `_seed_n_items(session, n)`
  ヘルパーを追加。fake writer は呼び出し順ではなく `user` プロンプト中のタイトル文字列で
  対象 topic を判定するため、`select_topics`/`arrange_arc` の並び替えに依存しない。
- `test_run_draft_drops_template_above_floor`: 5 本中 1 本が template のとき 4 本に除外され、
  markdown・ソース一覧 (`episode.sources`) には出ないが `script_versions` には 5 件全て残る
  こと、`topic_candidates` は除外分が `selected=False` / `position=None` になることを検証。
- `test_run_draft_keeps_template_at_floor`: 3 本中 1 本が template のとき、除外すると
  `MIN_TOPICS` を割るため従来どおり 3 本ともテンプレ込みで残ることを検証。
- 両テストとも `result.dropped_count` (0 または 1) を確認し、main.py サマリー行が参照する
  値がドロップ件数を正しく反映することを (データ層で) 検証した。CLI 出力文字列そのものの
  smoke は既存の `tests/test_cli_1b.py` に実 LLM 呼び出しを伴う draft の統合テストが無く
  (dry-run / エラー系のみ)、本チケットの範囲では runner レベルの検証に留めた。

### T56 ルビ抽出テストへの影響

`test_run_draft_extracts_ruby_and_updates_auto_dict` は変更なしで green (T60 の
テンプレ除外はルビ抽出 (`_extract_ruby_from_results`) の**後**に行われるため、ルビ処理自体は
影響を受けない。除外されるのは T18 テンプレ本文のみであり、テンプレにはインラインルビ
注釈が含まれないため実質的な相互作用もない)。

## 品質ゲート (fresh 実行)

```
$ uv run pytest
629 passed, 11 skipped in 8.84s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 88 source files

$ git diff --check
(出力なし = クリーン)
```

## 仕様から外れた判断・不確かな点

- **`THIN_SUMMARY_PENALTY = -15` の具体的な値**: チケットは「既存スケールに対して明確に
  順位を下げるが単独では足切りにしない程度」とだけ指定し、具体的な数値は実装判断に委ねられて
  いた。バケツ加点 (10/20/30) と Tier ボーナス (最大30) の中間的な値として -15 を選んだ
  (根拠は docstring 参照)。実配信で「まだ薄記事が上位に来る」ようであれば絶対値を上げる
  余地がある。
- **`selected_count` / `TopicCandidate.selected` の意味論変更**: チケットは
  「script_versions への記録自体は除外分も残してよい」とだけ明記し、topic_candidates 側の
  方針は「既存挙動を読んで整合させる」と実装判断に委ねていた。本実装は
  `TopicCandidate.selected` を「編集ゲートで選ばれたか」ではなく「実際に放送されたか」の
  意味で扱うことにした (`edit/abtest.py` の採用率評価が「番組に入ったか」を測る指標として
  意味を持つと判断したため)。この変更で既存の `test_run_draft_full_pipeline` 等が壊れて
  いないことは確認済み (テンプレ除外が発生しないシナリオでは挙動は従来と同一)。
- **`method_counts` は除外分を含めたまま**: 除外後の「放送された生成方法の内訳」ではなく
  「生成を試みた全件の内訳」を維持した。writer の実力 (LLM 生成成功率) を示す監査値として
  script_versions と母集団を揃える方が A/B 評価の一貫性に資すると判断したため。CLI 表示の
  `生成方法: {methods}` は引き続き試行全件ベース、`dropped=N` は別途追加した数値として提示
  する形にした。
- **CLI (`main.py`) の draft コマンド出力文字列そのものの smoke テストは追加していない**:
  既存の `tests/test_cli_1b.py` には実 LLM 呼び出しを伴う draft の統合テストが無く (すべて
  dry-run / APIキー無し / 不正 variant のエラー系)、新規に LLM モックを CLI レベルまで
  通す統合テストを追加するのはスコープ膨張と判断し、`DraftRunResult.dropped_count` が
  正しい値を持つことを runner レベルのテストで担保するに留めた。
