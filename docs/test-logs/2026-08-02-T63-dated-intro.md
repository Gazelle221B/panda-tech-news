# T63 — イントロ挨拶に当日日付を組み込む (Issue #69)

- 日付: 2026-08-02
- ブランチ: `agent/T63-dated-intro-impl`
- 実装者: Claude Code
- 参照: Issue #69 (プロダクトオーナー指示 2026-08-02)

## 背景

現行イントロ「華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。キャスターの
HALです。…」に当日日付 (JST) を組み込み、ニュース番組らしさを出す。フレーズ管理は T54 で
確定済みの `config/show_format.yaml` `phrases` → `script/generate.py::load_show_phrases`
という設計 (fail-open) を踏襲する。

## 調査で判明した点: フレーズ組み立て経路が2箇所ある

`load_show_phrases` を呼んでイントロ文 (タイトルコール+オープニング) を組み立てるコードは
2箇所存在する:

1. `script/generate.py::assemble_episode` — draft の markdown (Discord 投稿・DB 保存)。
2. `script/structure.py::build_structured_script` — 構造化台本 (TTS 音声合成の segment 化)。

さらに実際の `produce` コマンド (`main.py`) は `build_structured_script` を直接呼ばず、DB に
保存された `draft.markdown` を `tts/normalize.py::split_markdown_topics` で `## ` 見出し単位に
再分割して合成している。つまり **`assemble_episode` が生成する markdown の内容がそのまま実際の
放送音声の発話テキストになる** ため、日付置換を `assemble_episode` だけに入れれば実運用の
`produce` には反映される。一方 `build_structured_script` は現状 main.py から直接呼ばれておらず
テスト専用に見えるが、将来使われた場合に日付なしのまま音声化される不整合を残さないため、
**両方に同じ配線を入れた** (詳細は「仕様から外れた判断」参照)。

## 変更内容

### 1. 日付整形・プレースホルダ置換 (`src/karyu_tech_news/script/generate.py`)

- `format_broadcast_date(now: datetime) -> str`: `now` を JST へ変換し「8月2日、土曜日」形式
  (年なし、月日はゼロ埋めしない、曜日は「◯曜日」まで) で返す。JST オフセットは
  `deliver/discord.py::format_summary` と同じ固定 `timezone(timedelta(hours=9))` を使用
  (Windows 実行環境で zoneinfo が追加の tzdata パッケージを要する問題を避けるため、既存踏襲)。
  naive datetime (tzinfo 無し) は同ファイルの防御的方針にならい UTC とみなして変換する。
- `apply_date_placeholder(phrases: ShowPhrases, date_str: str) -> ShowPhrases`: `title_call` /
  `opening` / `closing` の3フィールドすべてに対し `str.replace("{date}", date_str)` を適用する。
  `str.replace` は対象が無ければ何もしないため、プレースホルダを含まない旧フレーズ (カスタム
  config・移行前) も例外なくそのまま素通しする fail-open 契約になる。
- `assemble_episode` で `load_show_phrases` の直後に
  `phrases = apply_date_placeholder(phrases, format_broadcast_date(generated_at))` を追加。

### 2. TTS 側の配線 (`src/karyu_tech_news/script/structure.py`)

- `build_structured_script` にも同じ2行 (`apply_date_placeholder` + `format_broadcast_date`) を
  追加し、`load_show_phrases` 直後に適用。intro segment の発話テキストにも日付が入る。

### 3. 設定 (`config/show_format.yaml`)

- `phrases.opening` の冒頭に `{date}。` を追加:
  `"{date}。キャスターのHALです。支度の手を止めずに、今朝の中華圏テック、要点だけボクと一緒に
  追いかけましょう。"`
- コメントで `{date}` の置換元・fail-open 契約を明記。

### 4. ドキュメントの整合 (コード非参照, 説明用)

- `config/hal_persona.yaml` `phrases` (show_format.yaml のドキュメント用ミラー、コード未参照)
  の `opening` にも同じ `{date}` プレースホルダを反映し、ミラーとしての一致を保った。
- `docs/hal-persona.md` §4 オープニング挨拶の項に、T63 での日付組み込み方針 (プレースホルダ
  方式・JST・置換元関数) を追記。

## 挿入結果の実例

`generated_at = 2026-06-11 07:00 UTC` (JST 2026-06-11 16:00, 木曜日) での `assemble_episode`
出力 (markdown 冒頭抜粋):

```
華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。
6月11日、木曜日。キャスターのHALです。支度の手を止めずに、今朝の中華圏テック、要点だけボクと一緒に追いかけましょう。
```

## テスト

### 新規: `tests/test_script_generate.py` (+11件)

- `format_broadcast_date`: 二桁月日 (ゼロ埋めなし確認)・一桁月日・年を含まないこと・naive
  datetime を UTC とみなす防御的変換・UTC 15:00 (=JST 0:00) を跨ぐ日付繰り上げ境界
  (`8月1日、土曜日` → `8月2日、日曜日`)・月〜日の全曜日の日本語表記。
- `apply_date_placeholder`: 3フィールド全てへの置換・プレースホルダ無し旧フレーズの fail-open
  素通し (無変化)。
- `assemble_episode` 統合: 実 markdown に `format_broadcast_date(generated_at)` の文字列が
  含まれること、`generated_at` を変えると markdown 内の日付も追随すること (ハードコードで
  ないことの証明)。

既存 `test_load_show_phrases_reads_real_show_format_yaml` は、実 config の `opening` が
`{date}` プレースホルダを含む生の値を返すよう変わったため、期待値を
`phrases.opening.startswith("{date}。キャスターのHALです。")` に更新した (`load_show_phrases`
自体は日付置換をしない責務分離のため意図した変更)。他の `load_show_phrases` / `assemble_episode`
系の既存テストは全て部分一致 (`in`) ベースのアサーションだったため無改修のまま緑を維持。

### 更新: `tests/test_draft_runner.py` (+2 assertion)

`test_run_draft_full_pipeline` に、`now=NOW` (2026-06-11 07:00 UTC → JST 木曜日) 由来の
「6月11日、木曜日」が `result.episode.markdown` および DB 保存済み `draft.markdown` の両方に
含まれることを確認するアサーションを追加 (draft 統合テストでの markdown 冒頭反映確認、DoD)。

### 更新: `tests/test_script_structure.py` (+1件)

`test_intro_segment_includes_broadcast_date`: `build_structured_script` の intro segment
テキストにも日付が反映されること (TTS 側の反映漏れ防止)。既存
`test_intro_segment_carries_title_call_and_opening` は部分一致ベースのため無改修で緑。

## 品質ゲート (fresh 実行)

```
$ uv run pytest -q
689 passed, 11 skipped in 17.80s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 94 source files

$ git diff --check
(出力なし = クリーン)
```

## 仕様から外れた判断・不確かな点

- **`build_structured_script` (structure.py) にも同じ配線を追加した**: チケット指示は
  「script/generate.py (assemble_episode?) がそれをどう組み込むか」を読むよう示しており、主眼は
  `assemble_episode` だった。しかし調査の結果、`load_show_phrases` を呼んでイントロ文を組み立てる
  コードパスが `generate.py` と `structure.py` の2箇所に存在すると判明した。実運用の `produce`
  は `assemble_episode` が書いた markdown を再分割する経路のため `assemble_episode` だけの修正で
  実際の放送には十分反映されるが、`structure.py::build_structured_script` を放置すると「同じ目的の
  イントロ組み立てロジックが2箇所にあり、一方だけ日付が入る」という一貫性の無い状態が残る
  (将来 `build_structured_script` が実際に配線された場合、日付なしのまま音声化される潜在バグにも
  なる)。日付整形・置換ロジックを `generate.py` に集約し、`structure.py` からは再利用する形
  (2行の呼び出し追加のみ) にしたため、変更範囲は最小に抑えられている。
- **`apply_date_placeholder` は3フィールド全てに置換を適用**: 挿入位置の推奨は「opening 冒頭」
  のみだったが、`title_call` / `closing` にも同じプレースホルダ機構を適用できるようにした
  (置換対象の `{date}` が無ければ何もしないため、現状 `title_call`/`closing` の文言は無変化)。
  DoD の「プレースホルダ置換 (あり/なし旧フレーズ fail-open)」というテスト要求が特定フィールドに
  限定されていなかったこと、および「フレーズ文言は config で編集可能なまま保つ」という指針から、
  将来 config 側だけでタイトルコールやクロージングにも日付を足したくなった場合にコード変更が
  不要になるよう、汎用的な実装にした。
- **JST オフセットは `zoneinfo` ではなく固定 `timezone(timedelta(hours=9))`**: `deliver/discord.py`
  が既にこの方式を採用しており (`JST = timezone(timedelta(hours=9))`)、Windows 実行環境では
  `zoneinfo` が IANA tzdata を同梱していないため追加パッケージが必要になる。既存コードとの一貫性・
  依存追加回避を優先し、同じ固定オフセット方式を踏襲した。
- **`config/hal_persona.yaml` のドキュメント用ミラーも更新**: コードからは未参照だが、
  「show_format.yaml のミラー」と明記されたファイルであり、ここだけ古い文言のまま放置すると
  ドキュメントとして誤解を招くと判断し、同じ `{date}` プレースホルダを反映した (実質ドキュメント
  更新のみ、コード動作に影響なし)。
