# T61 — 薄記事の本文フェッチによる素材強化 (Issue #61)

- 日付: 2026-08-01
- ブランチ: `agent/T61-article-enrich-impl`
- 実装者: Claude Code
- 参照: Issue #61 (T60 の対策の続き)

## 背景

T60 (Issue #60) で薄い summary (40字未満) 候補への減点とテンプレ枠ドロップを入れたが、
これは「薄記事を選ばれにくくする / 選ばれても放送しない」という対症療法であり、根本的な
素材不足は解消していない。採用候補上位に薄記事しか無い日は依然として writer が意味のある
台本を書けない。本チケットは薄記事のうち prescore 上位のものだけ記事本文ページを直接
フェッチし、editor 判定・writer 生成の素材そのものを補強する。

## 変更内容

### 1. 記事本文取得 (`src/karyu_tech_news/collect/article.py`, 新規)

- `fetch_article_text(url: str, *, timeout: float = 30.0) -> str | None`: 記事ページを
  httpx で GET し、`trafilatura.extract()` で本文を抽出する。`collect/fetcher.py` の
  UA (`karyu-tech-news/0.1`)・タイムアウト 30 秒・リトライ 2 回の流儀を踏襲。
- 失敗系はすべて fail-open で `None` を返す (fetcher.py の `fetch_one` と異なり例外は
  投げない): HTTP エラー・タイムアウト (リトライ尽きた後 WARN ログ)、trafilatura 抽出が
  `None`、抽出できても `MIN_EXTRACTED_CHARS = 100` 文字未満。
- 非 HTML ページは個別の content-type 判定を設けず、trafilatura.extract の失敗
  (`None` 返却) に委ねる設計にした (下記「仕様から外れた判断」参照)。
- `import trafilatura` は関数内の遅延 import にし、未導入でも `collect` モジュール自体の
  import は壊さない (`tts/kokoro.py` の `kokoro_onnx` 遅延 import と同じ流儀)。

### 2. 素材強化の編成 (`src/karyu_tech_news/edit/enrich.py`, 新規)

- `enrich_thin_candidates(candidates, *, top_k=15, max_fetch=5) -> list[ScoredCandidate]`:
  prescore 降順の上位 `top_k` 件のうち、`prescore.thin_summary_penalty()` が発火する
  (= T60 の薄記事判定と同じ条件) 候補だけを対象に、先頭から最大 `max_fetch` 件まで
  `fetch_article_text` を呼ぶ。
- フェッチ成功 (本文 `MIN_FETCHED_CHARS = 100` 文字以上) した候補は、`summary` を本文冒頭
  `ENRICHED_SUMMARY_CHARS = 600` 文字に置換し、`prescore` から `THIN_SUMMARY_PENALTY`
  (-15) 分を引き戻した新しい `ScoredCandidate` を `model_copy(update=...)` で作る。
  文字列の切り詰めは Python `str` (コードポイント) 単位のスライス (`text[:600]`) であり、
  バイト単位切り詰めではない (`design-inheritance-tc-newsflow.md` §6 / AGENTS.md §3.2)。
- フェッチ対象外 (top_k 外 / 薄くない / max_fetch 超過) の候補と、フェッチ失敗・本文不足の
  候補は元の `ScoredCandidate` インスタンスをそのまま返す (fail-open、元リストは非破壊)。
- 置換が発生した候補は `item_id` と取得字数を `logger.info` で記録する。
- DB の `items` テーブルは一切変更しない。取得した本文は `run_draft` 実行中のメモリ内
  (`candidates` リストのローカル変数) でのみ使われ、永続化されない (要件 §9.6 法務:
  記事本文の転載禁止、要約素材としてのみ利用)。

### 3. 配線 (`src/karyu_tech_news/script/runner.py`)

- `run_draft()` の `extract_candidates()` 呼び出し (候補ゼロの早期 return 判定の直後) と
  `corroboration_counts()` (editor 判定の直前) の間に `candidates = enrich_thin_candidates(candidates)`
  を1行追加。editor 判定 (`_judge_with_neutral_fallback`) も writer 生成
  (`generate_with_fallback`) も、この後段で使う `candidates`/`arranged` 経由で補強済み
  summary の恩恵を受ける。
- モジュール docstring の fail-open 一覧に本チケットの項目を追記。

## テスト

### 新規: `tests/test_article.py` (7件)

`collect.article` を httpx / trafilatura をモックしてユニットテスト。

- 成功 (本文抽出・置換される)
- HTTP エラー (`httpx.HTTPStatusError`) → `None`、リトライ回数確認
- タイムアウト → `None`、リトライ回数確認
- trafilatura 抽出が `None` → `None`
- 抽出本文が `MIN_EXTRACTED_CHARS` 未満 → `None`
- 抽出本文がちょうど `MIN_EXTRACTED_CHARS` 文字 → 採用される (境界値)
- trafilatura 未導入 (`sys.modules["trafilatura"] = None` で `ImportError` をシミュレート)
  → `None` (遅延 import が壊れても collect モジュール自体は壊れないことの確認)

### 新規: `tests/test_enrich.py` (9件)

`edit.enrich` を `fetch_article_text` をモックしてユニットテスト。

- 薄い候補が置換され、summary が本文に、score が `THIN_SUMMARY_PENALTY` 分戻ることを確認
- 600字切り詰めがコードポイント単位であること (多バイト文字「中」を700字用意し
  `len(summary) == 600` かつ内容が正しく切られていることを確認)
- 厚い candidate (summary が `THIN_SUMMARY_CHARS` 以上) は `fetch_article_text` が
  呼ばれないこと
- `top_k` 外の候補はフェッチされないこと (`top_k=2` で3件中2件のみ呼ばれることを確認)
- `max_fetch` 上限で呼び出し回数が頭打ちになること (4件中2件のみ呼ばれ、残り2件は元のまま)
- フェッチ失敗 (`None`) は元の candidate のまま
- フェッチ成功でも本文が短すぎる場合は元の candidate のまま
- 元のリスト・元の `ScoredCandidate` インスタンスが変更されない (非破壊) こと
- 空リスト入力で空リストを返し、フェッチも呼ばれないこと

### 更新: `tests/test_draft_runner.py`

- **autouse フィクスチャ `_no_real_article_fetch` を追加**: `run_draft` に
  `enrich_thin_candidates` を配線したことで、既存テスト (`_seed_items` は薄い
  `summary=""` をシードしている) がそのままだと実 HTTP フェッチを試みてしまう。
  `karyu_tech_news.edit.enrich.fetch_article_text` を既定で `None` 返却にパッチする
  autouse fixture を追加し、実ネットワークアクセスを防ぎつつ fail-open で候補が
  元のまま = 既存テストの前提・アサーションを一切変えないようにした。
- **新規テスト `test_run_draft_calls_enrich_before_editor_judge`**: `enrich_thin_candidates`
  と `corroboration_counts` (editor 判定の直前に呼ばれる関数) をそれぞれ呼び出し順を
  記録するフェイクに差し替え、`enrich` → `corroboration_counts` の順で呼ばれることを検証。

## 品質ゲート (fresh 実行)

```
$ uv run pytest
646 passed, 11 skipped in 8.51s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 92 source files

$ uv lock --check
Resolved 114 packages (差分なし)

$ git diff --check
(出力なし = クリーン)
```

## `trafilatura` 追加による依存差分の概要

`uv add trafilatura` (通常依存、`pyproject.toml` の `[project.dependencies]` に
`trafilatura>=2.2.0` を追加。optional extra ではない — チケットの記述通り、収集した
本文は draft 実行中のみ使うコア機能であり `tts`/`qa-asr` のような重量級・任意機能とは
性質が異なると判断)。`uv.lock` は 235 行追加。連鎖的に入った主な依存: `lxml` /
`lxml-html-clean` (HTML パース)、`courlan` / `htmldate` / `justext` (trafilatura の
本文抽出補助)、`dateparser`、`babel`。mypy strict は追加の `[[tool.mypy.overrides]]`
無しで通過した (trafilatura が型情報を同梱しているため、pydub/kokoro-onnx/whisper の
ような `ignore_missing_imports` override は不要だった)。

## 仕様から外れた判断・不確かな点

- **薄さ判定の実装**: チケット文面は「T60 の `thin_summary_penalty` が発火する条件 =
  `prescore.py` の `THIN_SUMMARY_CHARS` を import して判定」としていたが、実装では
  `THIN_SUMMARY_CHARS` を直接 import して閾値比較を再実装するのではなく、既存の
  `thin_summary_penalty()` 関数をそのまま呼んで戻り値が非ゼロかで判定した。理由は
  閾値比較ロジック (strip 後の文字数比較、`None` の扱い) の重複を避け、T60 側の定義が
  唯一の真実の源であり続けるようにするため。判定条件そのものはチケットの意図
  (「thin_summary_penalty が発火する候補」) と完全に一致する。
- **非 HTML ページの扱い**: チケット文面は「失敗 (HTTP エラー・タイムアウト・非 HTML) は
  None」と3つを並列に挙げていたが、実装では非 HTML 用の content-type 判定を別途設けず、
  trafilatura.extract が非 HTML 入力に対して自然に `None` を返す挙動に委ねた。
  content-type ヘッダの信頼性 (誤設定されている RSSHub 経由サイト等) よりも、実際に
  パースできるかどうかで判定する方が fail-open の趣旨に合うと判断した。
- **`MIN_FETCHED_CHARS` (enrich.py) と `MIN_EXTRACTED_CHARS` (article.py) の二重定義**:
  同じ 100 文字という値を2箇所で持つ (article.py は「抽出結果を採用するか」、enrich.py は
  「置換に足るか」という別レイヤーの判断のため、意図的に定数を分離した。article.py 側の
  ゲートを通れば enrich.py 側のゲートは実質的に常に通るが、collect 層の戻り値を edit 層が
  無条件に信頼しない防御的な二重チェックとして残した)。
- **`enrich_thin_candidates` の `max_fetch` はフェッチ「試行」回数の上限**: 成功件数では
  なく `fetch_article_text` の呼び出し回数そのものを上限とした (フェッチ失敗が続いても
  無制限にリトライして予算を超過しないため)。チケット文面「最大 max_fetch 件」はこちらの
  解釈が自然だと判断した。
- **enrich の挿入位置**: `run_draft` 内で `extract_candidates` の早期 return (`if not
  candidates: return None`) の**後**、`corroboration_counts` の**前**に置いた。
  `corroboration_counts` は `canonical_url_hash` のみを見て summary を参照しないため
  enrich の前後どちらでも結果は変わらないが、チケット文面「extract_candidates の直後・
  editor judge の前」により忠実な位置として corroboration_counts の前を選んだ。
