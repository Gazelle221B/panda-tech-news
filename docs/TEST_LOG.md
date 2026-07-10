# テストログ

> 参照: [WORKFLOW.md](./WORKFLOW.md) §14, [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
> 更新者: OpenCode (実装担当)
> 役割: 各タスクの実装完了時に **実行コマンドと結果** を残し、Codex レビューの証跡とする。

実行ログ本体は `artifacts/test-results/<task-id>-<date>.log` に保存し、本ファイルにはサマリーのみ追記する。

---

## テンプレ (タスク完了ごとに追記)

```markdown
## T<ID> <タスク名>  (実装者: OpenCode / 日付: YYYY-MM-DD)

### 実行コマンド

\`\`\`bash
pytest tests/test_<...>.py -v --cov=src/karyu_tech_news/<...>
\`\`\`

### 結果サマリー

- passed: N / failed: 0
- coverage: NN%
- artifacts: artifacts/test-results/T<ID>-YYYY-MM-DD.log

### 既知制限

- (あれば箇条書き)

### Codex への引き継ぎポイント

- DESIGN.md §X.Y に対応
- 重点的に見てほしい箇所: <ファイル:行>
```

---

## 履歴

## T42: TTS 読み上げハードニング  (実装: Codex / 日付: 2026-07-02)

### 実行コマンド

```bash
uv run pytest tests/test_tts_normalize.py -q
uv run pytest tests/test_tts_synthesize.py -q
uv run pytest tests/test_tts_normalize.py tests/test_tts_synthesize.py -q
uv run ruff check src/karyu_tech_news/tts/normalize.py tests/test_tts_normalize.py
uv run pytest
uv run ruff check .
uv run mypy src tests
git diff --check
uv run python - <<'PY'
# latest 10 episode_drafts を strip_markdown_structure + prepare_tts_text で検査
PY
```

### 結果サマリー

- `tests/test_tts_normalize.py`: **52 passed**。
- `tests/test_tts_synthesize.py`: **27 passed**。
- focused TTS tests: **81 passed**。
- focused ruff: All checks passed。
- full pytest: **452 passed in 3.23s**。
- full ruff: All checks passed。
- mypy strict: Success, no issues found in 70 source files。
- `git diff --check`: clean。
- 実 DB 検査: 最新 draft #2-#11 の TTS 入力で ASCII word token と `Hook/Insight/Action:` label が 0 件。対象にした raw `HAL Daily Briefing` / `Claude Code` / `FSD` / `LLM` / `GitHub` / `HBM4` / `GPT-5.6` / `ISC` / `A株` / `5G` / `5G+` / `4D` / `适配` / `国资系` / `脳機接口` は残存なし。
- レビュー指摘の追加回帰: `関与` / `付与` / `与党` / `給与` / `貸与` は中国語 quote 退避の対象外として保持。`OpenAI_API` / `GPT-5.6.1` は短い辞書語の部分置換で壊さない。`GitHub Action:` / `Call to Action:` は本文として保持し、台本構造ラベルの `Action:` だけを除去する。`LLM/RAG` / `Lite/Pro/Max` / `5G+AI` は記号区切りでも各語を読みへ置換する。`- **Hook:**` / `1. **Insight:**` / `+ Action:` のような箇条書き label も発話から除去する。

### 既知制限

- 人間聴感の最終判断 (T32) は未実施。今回の完了条件は TTS 入力の客観ハードニングまで。
- 共有漢字だけで構成された未知の中国語タイトルは、従来どおり誤置換回避のため自動退避しない。

### Codex への引き継ぎポイント

- `prepare_tts_text()` が TTS 境界。plain label 除去、ASCII 境界付き読み辞書置換、混在中国語 quote 退避の順序を重点確認。
- `config/reading_dict.yaml` は実 draft に出た英語技術語を優先追加。今後の聴感 QA で継続追記する。

## T42 追加修正: Codex 実証欠陥 2 件 (改称・多重 prefix・簡体字未収録)  (実装: Claude Code / 日付: 2026-07-09)

PR #25 (Sprint 3, T38-T41) との採番衝突により旧称「T38」を **T42** へ改称した上で、Codex 独立レビューで実証された欠陥 2 件を修正。

### 実行コマンド

```bash
uv run pytest tests/test_tts_normalize.py -q
uv run pytest tests/test_tts_normalize.py tests/test_tts_synthesize.py -q
uv run pytest -q
uv run ruff check .
uv run mypy src tests
git diff --check
```

### 結果サマリー

- `tests/test_tts_normalize.py`: **60 passed in 0.04s**。
- `tests/test_tts_normalize.py` + `tests/test_tts_synthesize.py`: **87 passed in 0.17s**。
- full pytest: **458 passed in 2.40s**。
- full ruff: All checks passed。
- mypy strict: Success, no issues found in 70 source files。
- `git diff --check`: clean。

### 修正内容と挙動確認 (修正前後)

- **修正A (`strip_script_markup` の多重 prefix 未除去)**: `_SCRIPT_LABEL_RE` の箇条書き prefix 部分を `(?:...)?` (0または1回) から `(?:...)*` (0回以上) に変更。
  - 修正前: `strip_script_markup('- - Hook: abc')` → `'- abc'` (二重 prefix の1つ目のみ剥がれ、`- ` が素通り)。
  - 修正後: `strip_script_markup('- - Hook: abc')` == `'abc'`、`strip_script_markup('1. - **Insight:** x')` == `'x'`。
  - 非破壊確認: 既存の単一 prefix ケース (`- **Hook:**` / `1. **Insight:**` / `+ Action:`)・`GitHub Action:` / `Call to Action:` の本文保持は回帰テストで維持を確認。
- **修正B (`sanitize_chinese_title_quotes` の短い簡体字タイトル素通り)**: `_SIMPLIFIED_HAN` に `竞` を含む未収録18字 (`态势报线统经说视计讯论读类织页项顶竞`) を追加。各字は日本語新字体と1字ずつ字形比較の上で選定 (例: `竞`≠`競`、`说`≠`説`、`视`≠`視`。`变`は追加前から既に収録済みと判明したため追加不要だった)。
  - 修正前: `sanitize_chinese_title_quotes("「竞争」が話題になっています。")` → 素通り (簡体字シグナルなしと誤判定)。
  - 修正後: `== "この話題が注目されています。"`、`sanitize_chinese_title_quotes("「竞价排名」というニュース。") == "このニュース。"`。
  - 非破壊確認: 「競争」「生成AI」「関与」「参考」等の日本語新字体クォートは新規追加字と字形が異なるため不変であることを回帰テストで確認 (「国際競争」等の既存回帰テストも継続グリーン)。

### 既知制限

- `docker-compose.yml` の healthcheck 修正は本チケットのスコープ外 (T43 として分離、本ブランチでは変更していない)。
- 人間聴感の最終判断 (T32 由来の残課題) は引き続き未実施。

### Codex への引き継ぎポイント

- `_SCRIPT_LABEL_RE` (`src/karyu_tech_news/tts/normalize.py`) の prefix 量指定子と `_SIMPLIFIED_HAN` の追加18字を重点確認。

## T1 + T3(schema): プロジェクト初期化・CLIスケルトン・ソーススキーマ  (実装: autopilot / 日付: 2026-05-30)

### 実行コマンド

```bash
uv sync
uv run python -m karyu_tech_news --help
uv run python -m karyu_tech_news validate-sources
uv run pytest
uv run ruff check src tests
uv run mypy src
```

### 結果サマリー

- CLI `--help`: サブコマンド version / validate-sources / info を表示。
- `validate-sources`: `OK: 11 sources loaded (9 enabled, 2 disabled)`、Tier 5/2/2/0、disabled 2本(jiqizhixin-rss, huxiu-rss)を黄色注記。exit 0。
- pytest: **24 passed** / failed 0 (test_config.py 17 + test_cli.py 7)。
- ruff check: All checks passed (B008 は typer の Option() デフォルト設計のため除外)。
- mypy --strict: Success, no issues in 4 source files。
- `info` は Webhook URL を `(set)/(not set)` のみ表示し秘密値を出さないことをテストで保証。

### 既知制限

- DB・フェッチャ・Discord は未実装 (Ticket #3 以降)。`collect` / `init-db` / `post-summary` は未提供。
- 実行は **uv 必須**。システム python3 は 3.9 で `StrEnum` 非対応 (requires-python >=3.11)。

### 引き継ぎポイント (Ticket #3 フェッチャ)

- `config.SourcesFile.enabled_sources()` を入力に `FetchResult` のリストを返す (design-inheritance §1, §11)。
- fail-open: 1ソース失敗で全体を止めない。例外は FetchResult に包む。
- 検証データは ADOPT 5本(実 entries) + 監視 4本(entries=0 の正常空振り) + disabled 2本 の3状態を最初から扱える。

## T4: RSS/RSSHub 取得モジュール (フェッチャ + 正規化)  (実装: OpenCode / 日付: 2026-05-31)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **48 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 11 source files。

### 実装内容

**新規ファイル**:
- `src/karyu_tech_news/collect/__init__.py` — モジュール初期化
- `src/karyu_tech_news/collect/normalize.py` — RawItem/FetchResult 型定義、item_key 生成 (FR-021)、canonical_url_hash (FR-022)、feedparser entry 正規化
- `src/karyu_tech_news/collect/fetcher.py` — httpx + feedparser 取得、リトライ (FR-013)、タイムアウト (FR-012)、fail-open (FR-060)、RSSHub URL 展開 (ADR-0004)
- `tests/test_normalize.py` — 12 テスト (item_key 優先順、canonical_url_hash 正規化、entry 変換)
- `tests/test_fetcher.py` — 12 テスト (取得成功、リトライ、タイムアウト、bozo 判定、fail-open、RSSHub 展開)

**主要仕様**:
- `generate_item_key()`: external_id → link → sha256(title|published_at|source_id) の優先順 (FR-021)
- `compute_canonical_url_hash()`: scheme/host 小文字化、末尾スラッシュ除去、UTM パラメータ除去、クエリソート (FR-022)
- `fetch_one()`: 単一ソース取得、タイムアウト 30s、リトライ最大 2 回、bozo=1 でも entries>=1 なら採用 (Spike §6)
- fail-open: 例外は `FetchResult(ok=False, error=...)` に包む (styleguide §7, noqa: BLE001)
- `expand_rsshub_url()`: `http://localhost:1200` を `RSSHUB_BASE_URL` で置換 (ADR-0004)

### 既知制限

- DB 層 (store/) は未実装。`collect` CLI コマンドは T8 (runner) 以降で統合。
- feedparser は型スタブなし (`# type: ignore[import-untyped]` で対応)。

### 引き継ぎポイント (Ticket #4 SQLite)

- `RawItem` を `items` テーブルに INSERT。`UNIQUE(source_id, item_key)` で dedupe (FR-031)。
- `FetchResult` の `ok` に基づき `source_health` を更新 (FR-050/051)。
- `collect_runs` に実行ログを記録 (FR-034)。

## T5: SQLite スキーマ + 永続化層  (実装: OpenCode / 日付: 2026-05-31)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **57 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 9)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 15 source files。

### 実装内容

**新規ファイル**:
- `src/karyu_tech_news/store/__init__.py` — モジュール初期化
- `src/karyu_tech_news/store/schema.py` — SQLAlchemy テーブル定義 (sources, items, source_health, collect_runs)
- `src/karyu_tech_news/store/repo.py` — CRUD 関数 (upsert_source, insert_items, update_source_health_*, create/finish_collect_run)
- `tests/test_store.py` — 9 テスト (冪等性、UNIQUE制約、dedupe、source_health 更新、collect_run ライフサイクル)

**変更ファイル**:
- `src/karyu_tech_news/main.py` — `init-db` コマンド追加

**主要仕様**:
- `create_db_engine()`: SQLite エンジン作成 (パスの親ディレクトリ自動作成)
- `init_db()`: スキーマ初期化（冪等、2回実行しても壊れない）
- `upsert_source()`: ソース追加/更新
- `insert_items()`: アイテム追加（UNIQUE制約で自動スキップ、空の item_key は ValueError）
- `update_source_health_success()`: 成功時 consecutive_failures=0 にリセット
- `update_source_health_failure()`: 失敗時 consecutive_failures += 1、last_error 保存
- `create_collect_run()` / `finish_collect_run()`: 収集実行記録の作成と完了

**DESIGN.md §4 準拠**:
- `UNIQUE(source_id, item_key)` 制約 (FR-031)
- `hash` 単体 UNIQUE なし（禁止事項遵守）
- `item_key` 空での INSERT 防止 (ValueError 発生)
- インデックス: `idx_items_canonical_hash`, `idx_items_published`

### 既知制限

- `collect` CLI コマンドは T8 (runner) 以降で統合。
- `post-summary` CLI コマンドは T9 (Discord) で実装。

### 引き継ぎポイント (Ticket #5 dedupe)

- `insert_items()` で既に UNIQUE 制約による dedupe を実装済み。
- Ticket #5 は `store/repo.py` の拡張ではなく、T8 (runner) で `insert_items()` を呼び出す形で統合。

## T5 修正: Codex レビュー指摘対応  (実装: OpenCode / 日付: 2026-06-01)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **60 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 15 source files。

### 修正内容

**High 指摘対応**:
- `src/karyu_tech_news/store/repo.py` — `create_db_engine()` で SQLAlchemy event listener を使い、接続時に `PRAGMA foreign_keys=ON` を実行。外部キー制約を実効化。
- `tests/test_store.py` — 存在しない `source_id` への insert/update が `IntegrityError` を発生させることを確認するテストを 2件追加。

**Medium 指摘対応**:
- `src/karyu_tech_news/store/repo.py` — `finish_collect_run()` で `run.total_sources` と `len(results)` の不一致を検出し、`ValueError` を発生させるように修正。
- `tests/test_store.py` — 不一致時に `ValueError` が発生することを確認するテストを追加。既存の `test_collect_run_lifecycle` を `total_sources=2` に修正。

**Low 指摘対応**:
- `src/karyu_tech_news/store/schema.py` — `idx_items_published` を `text("published_at DESC")` に修正し、設計 SQL と一致させる。
- `src/karyu_tech_news/main.py` — `info` コマンドの Sprint 表示を `1A (Ticket #4 SQLite)` に更新。

### 追加テスト

- `test_insert_items_rejects_orphan_source_id`: 存在しない `source_id` への insert が `IntegrityError` を発生させることを確認。
- `test_update_source_health_rejects_orphan_source_id`: 存在しない `source_id` への source_health 更新が `IntegrityError` を発生させることを確認。
- `test_finish_collect_run_rejects_total_sources_mismatch`: `total_sources` と `len(results)` の不一致時に `ValueError` が発生することを確認。

### DESIGN.md §4 / domain/collection.md §3.1 準拠

- 外部キー制約 `REFERENCES sources(id)` が SQLite 実行時に実効化された。
- `SourceHealth は Source に従属` という不変条件が `IntegrityError` で保証される。

## T6: seen 管理 / dedupe  (実装: OpenCode / 日付: 2026-06-01)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **65 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 16 source files。

### 実装内容

**新規ファイル**:
- `tests/test_dedupe.py` — 5 テスト (同一 source+key の dedupe、異なる source で同一 key は別レコード、同一 source で異なる key は別レコード、バッチ投入時の部分的 dedupe、空バッチ)

**実装方針**:
- `store/repo.py` の拡張は不要。既存の `insert_items()` が既に UNIQUE 制約による dedupe を実装済み。
- Ticket #5 (T6) はテストの拡充に焦点を当て、dedupe の動作をより詳細に検証。

**テストケース**:
- `test_dedupe_same_source_same_key`: 同一 source+key の2回投入で1行のみ存在。
- `test_dedupe_different_source_same_key`: 異なる source で同一 key は別レコードとして保存（クロスソース重複は Sprint 1A では許容）。
- `test_dedupe_same_source_different_keys`: 同一 source で異なる key は別レコードとして保存。
- `test_dedupe_batch_insert_mixed`: バッチ投入時の部分的な重複（一部は新規、一部は既存）。既存アイテムは更新されず、新規アイテムのみ追加。
- `test_dedupe_empty_batch`: 空バッチは0件を返す。

### DESIGN.md §4 / domain/collection.md §3.2 準拠

- `UNIQUE(source_id, item_key)` 制約による dedupe が正常に動作。
- クロスソース重複は Sprint 1A では別レコードとして許容 (FR-041)。
- `item_key` 空での INSERT 防止は `test_insert_items_empty_key_rejected` で既に検証済み。

### 引き継ぎポイント (Ticket #6 source_health)

- `update_source_health_success()` / `update_source_health_failure()` は既に実装済み。
- Ticket #6 (T7) はテストの拡充に焦点を当てる。

## T7: source_health 更新  (実装: OpenCode / 日付: 2026-06-01)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **73 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 17 source files。

### 実装内容

**新規ファイル**:
- `tests/test_health.py` — 8 テスト (初回成功/失敗時のレコード作成、連続失敗後の成功リセット、累積失敗、警告閾値、last_error 更新、タイムスタンプ更新、成功/失敗サイクル)

**実装方針**:
- `store/repo.py` の拡張は不要。既存の `update_source_health_success()` / `update_source_health_failure()` が既に実装済み。
- Ticket #6 (T7) はテストの拡充に焦点を当て、source_health の状態遷移をより詳細に検証。

**テストケース**:
- `test_health_first_success_creates_record`: 初回成功時に source_health レコードが作成され、last_success_at が設定される。
- `test_health_first_failure_creates_record`: 初回失敗時に source_health レコードが作成され、consecutive_failures=1、last_failure_at、last_error が設定される。
- `test_health_success_resets_after_failures`: 連続失敗後に成功すると consecutive_failures が 0 にリセットされ、last_success_at が更新される。
- `test_health_consecutive_failures_accumulate`: 連続失敗で consecutive_failures が累積する（5回）。
- `test_health_warning_threshold`: consecutive_failures が 3 に到達（Discord 警告の閾値）。
- `test_health_last_error_updates`: last_error が最新の error で更新される。
- `test_health_timestamps_update_correctly`: last_success_at と last_failure_at のタイムスタンプが正しく更新される。
- `test_health_success_failure_cycle`: 成功→失敗→成功→失敗のサイクルで正しく状態が遷移する。

### DESIGN.md §4 / domain/collection.md §4.3 準拠

- 成功時: `last_success_at` 更新、`consecutive_failures = 0` にリセット (FR-050)。
- 失敗時: `last_failure_at` 更新、`consecutive_failures += 1`、`last_error` 保存 (FR-051)。
- `consecutive_failures >= 3`: Discord 収集サマリーで⚠️警告表示 (FR-052)。

### 引き継ぎポイント (Ticket #7 collect runner)

- `update_source_health_success()` / `update_source_health_failure()` は `collect/runner.py` で `FetchResult.ok` に基づき呼び出す。
- Ticket #7 (T8) は `fetch_one()` + `insert_items()` + `source_health` 更新を統合し、fail-open を実装。

## T8: collect runner (fail-open 統合)  (実装: OpenCode / 日付: 2026-06-01)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **79 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 6)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 19 source files。

### 実装内容

**新規ファイル**:
- `src/karyu_tech_news/collect/runner.py` — `run_collect()` 関数 (fail-open 統合)
- `tests/test_runner_fail_open.py` — 6 テスト (全成功、1失敗継続、複数失敗、全失敗、空ソース、DB エラー継続)

**実装方針**:
- `run_collect()` は全ソースを順次処理し、各ソースごとに `fetch_one()` → `insert_items()` → `update_source_health_success/failure()` を実行。
- **fail-open**: 各ソースの処理で例外が発生しても、次のソースへ進む。
  - `fetch_one()` は既に fail-open 実装（例外をキャッチして `FetchResult(ok=False)` を返す）。
  - `insert_items()` で DB エラーが発生した場合も、`FetchResult` を `ok=False` に変更して続行。
- `collect_runs` で実行記録を管理（開始時に作成、終了時に完了処理）。

**テストケース**:
- `test_run_collect_all_success`: 全ソースが成功するケース。
- `test_run_collect_one_failure_continues`: 1ソースが失敗しても他のソースが完走する。
- `test_run_collect_multiple_failures`: 複数のソースが失敗しても残りが完走する。
- `test_run_collect_all_fail`: 全ソースが失敗するケース。
- `test_run_collect_empty_sources`: 空のソースリストでも正常に動作する。
- `test_run_collect_db_error_continues`: `insert_items()` で DB エラーが発生しても他のソースが完走する。

### DESIGN.md §2.3 / domain/collection.md §5.3 準拠

- **fail-open (FR-060)**: 1ソースの失敗で全体を止めない。
- **CollectRun 管理**: 収集開始時にレコードを作成、終了時に完了処理。
- **source_health 更新**: `FetchResult.ok` に基づき `update_source_health_success/failure()` を呼び出す。

### 引き継ぎポイント (Ticket #8 Discord Webhook)

- `run_collect()` の戻り値 `CollectRun` を使って、Discord に収集サマリーを投稿。
- Ticket #8 (T9) は `deliver/discord.py` を実装し、`collect_runs` と `source_health` からサマリーを生成。

## T8 修正: Codex レビュー指摘対応  (実装: OpenCode / 日付: 2026-06-01)

### 指摘内容

**High**: `runner.py` のDBエラー処理で `session.rollback()` が欠けており、実SQLiteのIntegrityError発生時にfailed transaction状態で後続処理が失敗する問題。

### 修正内容

- `src/karyu_tech_news/collect/runner.py` — DBエラー処理の先頭で `session.rollback()` を呼び出すように修正。
- `tests/test_runner_fail_open.py` — `insert_items()` をモックしてIntegrityErrorを発生させる回帰テストを追加。

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **80 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 7)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 19 source files。

### 追加テスト

- `test_run_collect_real_sqlite_integrity_error`: `insert_items()` をモックしてIntegrityErrorを発生させ、`session.rollback()` が正しく呼ばれ、後続のソースが処理されることを確認。

## T8 追加修正: Codex 再レビュー指摘対応  (実装: OpenCode / 日付: 2026-06-01)

### 指摘内容

**High**: `runner.py` の line 43 で `total_new_items += new_count` が `session.commit()` 前に実行されている。実DBのflush/commitで失敗するとrollbackされてitemは保存されないが、`total_new_items`だけ増えたままになる。

### 修正内容

- `src/karyu_tech_news/collect/runner.py` — `total_new_items += new_count` を `session.commit()` 成功後に移動。
- `tests/test_runner_fail_open.py` — `session.commit()` をモックして特定の呼び出しで失敗させ、`run.new_items == 保存済みItem件数` を確認する回帰テストを追加。

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **81 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 8)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 19 source files。

### 追加テスト

- `test_run_collect_new_items_matches_persisted_on_commit_failure`: `session.commit()` をモックして特定の呼び出しで失敗させ、`run.new_items` が保存済みItem件数と一致することを確認。

## T9: Discord Webhook サマリー投稿  (実装: OpenCode / 日付: 2026-06-01)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **87 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 8 + test_discord.py 6)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 22 source files。

### 実装内容

**新規ファイル**:
- `src/karyu_tech_news/deliver/__init__.py` — モジュール初期化
- `src/karyu_tech_news/deliver/discord.py` — `format_summary()` と `post_summary()` 関数
- `tests/test_discord.py` — 6 テスト (基本的なサマリー形式、警告表示、Webhook送信成功/失敗、空URL、JST変換)

**実装方針**:
- `format_summary()` は `CollectRun` と `SourceHealth`、`Source`、`Item` から §14.1 形式のサマリーテキストを生成。
  - JST変換: `started_at` を UTC から JST (UTC+9) に変換して表示。
  - 実行時間: `finished_at - started_at` で計算。
  - 警告表示: `consecutive_failures >= 3` のソースを一覧表示。
  - Tier別/カテゴリ別カウント: `Item.fetched_at >= run.started_at` でフィルタリングし、`Source` の `tier` と `category` で集計。
- `post_summary()` は httpx で Webhook に POST。失敗時はログのみで False を返す (fail-open, FR-071)。

**テストケース**:
- `test_format_summary_basic`: 基本的なサマリー形式が正しいことを確認。
- `test_format_summary_with_unhealthy_sources`: `consecutive_failures >= 3` の警告が表示されることを確認。
- `test_post_summary_success`: Webhook送信成功時にTrueを返すことを確認。
- `test_post_summary_failure`: Webhook送信失敗時にFalseを返すことを確認 (fail-open, FR-071)。
- `test_post_summary_empty_url`: Webhook URLが空の場合にFalseを返すことを確認。
- `test_format_summary_jst_conversion`: JST変換が正しく動作することを確認。

### DESIGN.md §3.2 / requirements-v1.0.md §14.1 / FR-070/071/072 準拠

- **FR-070**: Discord Webhook へ収集サマリーを投稿。
- **FR-071**: Webhook 投稿失敗時も収集処理は失敗扱いにしない (fail-open)。
- **FR-072**: Sprint 1A では添付ファイルなし、Markdown本文投稿のみ。
- **§14.1**: 指定されたフォーマット形式に適合 (日時、実行時間、成功/失敗、警告、新規アイテム、Tier別、カテゴリ別)。

### 引き継ぎポイント (Ticket #9 CLI統合)

- `post_summary()` を `main.py` の `collect` コマンドから呼び出す。
- Ticket #9 (T10) は `collect` コマンドに `--post` オプションを追加し、収集後に自動で Discord に投稿する機能を統合。

## T9 修正: Codex レビュー指摘対応  (実装: OpenCode / 日付: 2026-06-01)

### 指摘内容

**High**: `discord.py` の Tier/カテゴリ集計が `Item.fetched_at >= run.started_at` だけで、`run.finished_at` 以前に限定されていない。過去 run のサマリーを作ると、run 終了後に保存された item まで混ざる。

### 修正内容

- `src/karyu_tech_news/deliver/discord.py` — `run.finished_at` がある場合、item 集計条件に `Item.fetched_at <= run.finished_at` を追加。
- `tests/test_discord.py` — run 終了後の item が Tier/カテゴリ集計に入らない回帰テストを追加。

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **88 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 8 + test_discord.py 7)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 22 source files。

### 追加テスト

- `test_format_summary_excludes_items_after_finished_at`: run 終了後に保存された item が Tier/カテゴリ集計に含まれないことを確認。

## T10: CLI統合 (`collect` コマンド)  (実装: OpenCode / 日付: 2026-06-01)

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **97 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 8 + test_discord.py 7 + test_cli_integration.py 9)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 23 source files。

### 実装内容

**変更ファイル**:
- `src/karyu_tech_news/main.py` — `collect` コマンドを追加 (`--post`, `--dry-run` オプション)
- `tests/test_cli_integration.py` — 9 テスト (ヘルプ表示、dry-run、成功/失敗、Discord 投稿成功/失敗/未設定)

**実装方針**:
- `collect` コマンドは `runner.run_collect()` を呼び出し、収集結果を `CollectRun` として保存。
- `--post` オプションで収集後に `discord.format_summary()` と `discord.post_summary()` を統合。
- `--dry-run` オプションで実際の収集・投稿をスキップ。
- ソースを `upsert_source()` でデータベースに登録してから収集を実行。
- fail-open: Discord 投稿失敗時もプロセスを継続。

**テストケース**:
- `test_collect_help`: `collect --help` が正しく表示されることを確認。
- `test_collect_dry_run`: `--dry-run` オプションで収集がスキップされることを確認。
- `test_collect_dry_run_with_post`: `--dry-run --post` で Discord 投稿もスキップされることを確認。
- `test_collect_no_enabled_sources`: 有効なソースがない場合に警告を表示して正常終了することを確認。
- `test_collect_success`: 収集が成功した場合に正しいメッセージが表示されることを確認。
- `test_collect_with_post_success`: `--post` オプションで Discord 投稿が成功することを確認。
- `test_collect_with_post_no_webhook_url`: `DISCORD_WEBHOOK_URL` が未設定の場合に警告を表示することを確認。
- `test_collect_with_post_failure`: Discord 投稿が失敗しても fail-open で継続することを確認。
- `test_collect_with_failures`: 収集で失敗が発生しても正常に完了することを確認。

### DESIGN.md §3.1 / requirements-v1.0.md §11.1 準拠

- **CLI要件**: `python -m karyu_tech_news collect` が完走する。
- **fail-open**: 1ソースの失敗で全体を止めない。
- **Discord 投稿**: `--post` オプションで収集後に自動で投稿。

## T10 修正: Codex レビュー指摘対応  (実装: OpenCode / 日付: 2026-06-01)

### 指摘内容

**High**: `collect --source <id>` が未実装。`DESIGN.md` のCLI契約では `collect [--dry-run] [--source <id>]` ですが、実行すると `No such option: --source` で exit 2 になります。

**Medium**: T10受け入れ条件のDB状態検証が不足。現テストは `run_collect()` をモックしており、「dry-runでDB書き込みなし」「通常実行で `sources/items/source_health/collect_runs` 更新」を実証していません。

### 修正内容

- `src/karyu_tech_news/main.py` — `--source` オプションを追加（複数指定可能）。指定されたソースIDでフィルタリング。
- `tests/test_cli_integration.py` — 4 テスト追加:
  - `test_collect_with_source_option`: `--source` オプションで特定のソースのみ収集
  - `test_collect_with_invalid_source_option`: 存在しないソースIDを指定した場合にエラー
  - `test_collect_dry_run_no_db_write`: dry-run でDB書き込みがないことを確認
  - `test_collect_updates_db_state`: 通常実行で `sources/items/source_health/collect_runs` が更新されることを確認

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **101 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 8 + test_discord.py 7 + test_cli_integration.py 13)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 23 source files。

### 追加テスト

- `test_collect_with_source_option`: `--source` オプションで特定のソースのみ収集することを確認。
- `test_collect_with_invalid_source_option`: 存在しないソースIDを指定した場合にエラーになることを確認。
- `test_collect_dry_run_no_db_write`: dry-run でDB書き込みがないことを確認（`sources/items/collect_runs` がすべて0件）。
- `test_collect_updates_db_state`: 通常実行で `sources/items/source_health/collect_runs` が更新されることを確認（`fetch_one` のみモック、実際のDB書き込みを検証）。

## T10 再レビュー指摘対応  (実装: OpenCode / 日付: 2026-06-02)

### 指摘内容

**High**: `--source` で複数指定時、一部が未知IDまたはdisabled IDでも残りがあればexit 0で進む。指定されたIDを黙って捨てるのは運用上危険。未一致IDが1件でもあればexit 1にするべき。

### 修正内容

- `src/karyu_tech_news/main.py` — `source_ids` 指定時、全てのIDがenabled sourcesに存在することを検証。未一致ID（未知またはdisabled）があれば、それらをリストアップしてexit 1。
- `tests/test_cli_integration.py` — 3 テスト追加:
  - `test_collect_with_partial_invalid_sources`: 複数のsource_idsを指定し、その一部が無効なIDの場合にexit 1になることを確認
  - `test_collect_with_disabled_source`: disabledのsource_idを指定した場合にexit 1になることを確認
  - `test_collect_with_multiple_valid_sources`: 全てのsource_idsが有効な場合に正常に動作することを確認
- `tests/test_cli_integration.py` — 既存テスト更新:
  - `test_collect_with_invalid_source_option`: エラーメッセージを新しい実装に合わせて更新
- `tests/test_cli_integration.py` — フィクスチャ更新:
  - `temp_sources_file`: disabled-sourceを追加

### 実行コマンド

```bash
uv run pytest -v
uv run ruff check .
uv run mypy src tests
```

### 結果サマリー

- pytest: **104 passed** / failed 0 (test_cli.py 8 + test_config.py 16 + test_normalize.py 12 + test_fetcher.py 12 + test_store.py 12 + test_dedupe.py 5 + test_health.py 8 + test_runner_fail_open.py 8 + test_discord.py 7 + test_cli_integration.py 16)。
- ruff check: All checks passed。
- mypy --strict: Success, no issues found in 23 source files。

### 追加テスト

- `test_collect_with_partial_invalid_sources`: 複数のsource_idsを指定し、その一部が無効なIDの場合にexit 1になることを確認。
- `test_collect_with_disabled_source`: disabledのsource_idを指定した場合にexit 1になることを確認。
- `test_collect_with_multiple_valid_sources`: 全てのsource_idsが有効な場合に正常に動作することを確認。

## Ticket #11 (T11): 3日連続稼働観察 (手動運用)

### 目的
Sprint 1A で実装した収集基盤全体が、実際のソースに対して連続して動作し、エラー時も正しくフェイルオープンとして機能するか、および Discord へのサマリー投稿が正常に行われるかを3日間にわたり手動（または定期）実行で確認する。

### 実行コマンド（例）
```bash
uv run python -m karyu_tech_news collect --post
```

### 稼働記録

| 日付 (YYYY-MM-DD) | 実行時刻 (JST) | 取得ソース数 | 新規件数 | Discord 投稿 | エラー・特記事項 |
|---|---|---|---|---|---|
| Day 1: 2026-06-02 | 09:52 | 9/9 成功 | 4 | 未投稿※(webhook未設定。`format_summary` 出力はプレビュー確認済) | dedup正常(36Krのみ4新着、他8本0new)。zhipu-glm 301→`zai-org/GLM-4` 自動追従。fail-open発火なし(全成功) |
| Day 2: 2026-06-03 | 22:03 | 9/9 成功 | 58 | ✅ 投稿成功 (HTTP 204) | 初の Discord 実配信。fail-open発火なし。13.5秒。Tier2:30/Tier3:28、AI:38/Tech:20 |
| Day 3: 2026-06-04 | 00:39 | 9/9 成功 | 1 | ✅ 投稿成功 (HTTP 204) | fail-open発火なし。12.3秒。Tier2/AI 1件。**3日連続達成** |

※ 3日間の安定稼働が確認できた時点で Sprint 1A は完全終了となり、Sprint 1B（LLM統合）へ進行可能となります。

### Day 1 観察結果 (2026-06-02 09:52 JST)

- **収集**: 9/9 ソース成功、4 新規アイテム (36Kr Newsflash の速報、Tier2/Tech)。実行 3.5 秒。
- **dedup 実証**: 既存8ソースは 0 new (前回 collect と同一アイテムを `UNIQUE(source_id, item_key)` で重複排除)。
- **耐障害性**: zhipu-glm は GitHub の 301 リダイレクト (`THUDM`→`zai-org/GLM-4`) を httpx が自動追従し成功。実 fail-open の発火は今回なし (全ソース成功)。
- **Discord**: webhook 未設定のため未投稿。`format_summary` の出力 (要件 §14.1 形式) はプレビューで検証済。実投稿は `.env` に `DISCORD_WEBHOOK_URL` を設定し `collect --post` で実施する。
- **品質ゲート (fresh)**: pytest 104 passed / ruff clean / mypy strict clean。

投稿プレビュー (`--post` で送信される本文):

```
📰 華流テック通信 - 収集レポート
日時: 2026-06-02 09:52 JST
実行時間: 3.5秒
✅ 成功: 9/9 ソース
❌ 失敗: 0/9 ソース
📥 新規アイテム: 4件
Tier別:
- Tier2 ニュース: 4件
カテゴリ別:
- Tech: 4
```

### Day 2 観察結果 (2026-06-03 22:03 JST)

- **収集**: 9/9 ソース成功、**58 新規アイテム** (前回から約36時間で 36Kr 速報・掘金トレンドが蓄積)。実行 13.5 秒。
- **Discord 実配信成功**: `collect --post` → HTTP **204 No Content**。要件 §14.1 形式のサマリーが Webhook に到達 (本プロジェクト初の実配信)。
- **内訳**: Tier2 ニュース 30 / Tier3 コミュニティ 28、カテゴリ AI 38 / Tech 20。
- **耐障害性**: fail-open 発火なし (全9成功)。2日連続で全ソース取得成功。

投稿サマリー (Discord 到達):

```
📰 華流テック通信 - 収集レポート
日時: 2026-06-03 22:03 JST
実行時間: 13.5秒
✅ 成功: 9/9 ソース
❌ 失敗: 0/9 ソース
📥 新規アイテム: 58件
Tier別:
- Tier2 ニュース: 30件
- Tier3 コミュニティ: 28件
カテゴリ別:
- AI: 38
- Tech: 20
```

### Day 3 観察結果 (2026-06-04 00:39 JST)

- **収集**: 9/9 ソース成功、1 新規アイテム (Tier2/AI)。実行 12.3 秒。
- **dedup 正常**: 前回 (Day 2) から数時間のため新着は1件のみ。`UNIQUE(source_id, item_key)` が安定動作。
- **Discord 実配信成功**: `collect --post` → HTTP **204 No Content** (2日連続の実配信)。
- **耐障害性**: fail-open 発火なし (全9成功)。**3日連続で全ソース取得成功**。

投稿サマリー (Discord 到達):

```
📰 華流テック通信 - 収集レポート
日時: 2026-06-04 00:39 JST
実行時間: 12.3秒
✅ 成功: 9/9 ソース
❌ 失敗: 0/9 ソース
📥 新規アイテム: 1件
Tier別:
- Tier2 ニュース: 1件
カテゴリ別:
- AI: 1
```

## Ticket #11 (T11) 完了 — 3日連続稼働 達成 (2026-06-04)

| 観点 | 結果 | 要件 §15.1 DoD |
|---|---|---|
| 3日連続稼働 | ✅ 06-02 / 06-03 / 06-04 すべて完走 | 「3日連続で動作する」 |
| ソース取得 | ✅ 全日 9/9 成功 (11本中9有効) | 「10本前後を取得できる」 |
| fail-open | ✅ 全日発火なし。例外時の継続は `test_runner_fail_open.py` で担保 | 「一部失敗しても止まらない」 |
| dedup | ✅ 実 DB で実証 (新着 Day1=4 / Day2=58 / Day3=1、再実行で重複増加なし) | 「2回 collect で重複登録されない」 |
| source_health | ✅ 9 ソース分の health を記録・更新 | 「source_health が更新される」 |
| Discord 配信 | ✅ Day2/Day3 で HTTP 204 実配信、Day1 はプレビュー検証 | 「Discord にサマリーが届く」 |

**結論: Sprint 1A の全 DoD を満たし、Sprint 1A は完全終了。次は Sprint 1B (LLM編集・台本生成)。**

---

# Sprint 1B 実装ログ

## Ticket T12 — LLM profile ローダ + provider 抽象 (2026-06-10)

> ブランチ: `agent/T12-impl` (最新 main `965f37d` から分岐)。実装: Claude Code。
> 実 API 呼び出しなし — T13 (接続確認 smoke) は人間ブロッカー解消後 (IMPLEMENTATION_PLAN-1B §6)。

1. `tests/test_llm_profile.py` (17件) → verify: スキーマ検証 (label/base_url/temperature/max_tokens)・label 重複拒否・ab_test 参照整合・A/B/C 役割解決・実 `config/llm_profiles.yaml` 結合テストが緑
2. `tests/test_llm_client.py` (13件) → verify: chat リクエスト契約 (body/headers/timeout)・json_mode・ollama think=false・リトライ (MAX_RETRIES=2)・API キー非漏洩・reasoning_content フォールバック・不正応答の LLMError 化が緑
3. 新規モジュール: `src/karyu_tech_news/llm/profile.py` (ローダ + ResolvedRoles) / `llm/client.py` (OpenAI 互換クライアント)

実行結果 (fresh):

```
uv run pytest -q          → 134 passed
uv run ruff check .       → All checks passed!
uv run mypy src tests     → Success: no issues found in 28 source files
```

## Ticket T14 — 候補抽出 + ローカル事前スコア (2026-06-10)

1. `tests/test_prescore.py` (15件) → verify: キーワード辞書 (緊急+30/規制+20/リリース+10、バケツ1回加点)・Tier ボーナス・lookback フィルタ・prescore 降順 + 新着優先・上限 40 件キャップ・NULL summary 耐性が緑
2. 新規モジュール: `src/karyu_tech_news/edit/prescore.py` (`ScoredCandidate` / `prescore_text` / `extract_candidates`)
3. キーワードは中華圏向けに再設計 (漏洞/监管/发布 系 + 日英少数) — design-inheritance §4.1/§14

実行結果 (fresh): pytest **149 passed** / ruff clean / mypy strict clean (31 files)

## Ticket T15 — LLM 編集判定 (2026-06-10)

1. `tests/test_judge.py` (16件) → verify: JSON 頑健抽出 (素直な loads → fence 除去 → 最外 `{}`)・スキーマ検証 (score 0-100 / tone enum)・プロンプト切り詰め (title 180/summary 420 文字)・corroboration (canonical_url_hash クロスソース一致)・temp=0 + json_mode 呼び出し・未知 index スキップが緑
2. `llm/client.py` に temperature 上書き引数追加 (+1 テスト)。`ScoredCandidate` に canonical_url_hash 追加 (corroboration 用)
3. 新規モジュール: `src/karyu_tech_news/edit/judge.py` (`Tone` / `JudgedTopic` / `judge_topics`)。採点=LLM、裏取り集計=決定的コードの分離を維持

実行結果 (fresh): pytest **165 passed** / ruff clean / mypy strict clean (33 files)

## Ticket T16 — 多様性キャップ選定 + アーク配置 (2026-06-10)

1. `tests/test_select_arc.py` (16件) → verify: 編集ゲート (Tier3/4 は独立2ソース必須)・llm_score 順・ソース/カテゴリキャップ各2・4パス緩和充填 (単一ソースのみの日でも番組が出る)・最大5本・三幕構成 (hard_negative 先頭 / constructive 中盤 / bright 末尾、bright 不在時 constructive 締め)・入力非破壊が緑
2. 新規モジュール: `edit/select.py` (`select_topics`) + `edit/arc.py` (`arrange_arc`)。**LLM 不使用・全て決定的コード** (design-inheritance §4.3/§5)

実行結果 (fresh): pytest **181 passed** / ruff clean / mypy strict clean (36 files)

## Ticket T17 — Markdown 台本生成 (2026-06-11)

1. `tests/test_script_generate.py` (16件) → verify: 文字数カウント (空白除くコードポイント)・writer プロンプト契約 (Hook/Insight/Action・300字・カナ化・転載禁止・Tier4 噂指示)・プレーンテキスト生成 (json_mode 不使用)・検証 (セクション欠落/300字超過/URL混入/禁止表現/噂明示)・エピソード組み立て (Markdown・ソース一覧・注意事項・推定尺・暫定挨拶) が緑
2. 新規モジュール: `script/generate.py` (`build_writer_prompts` / `generate_topic_script` / `validate_topic_script` / `assemble_episode` / `EpisodeScript`)
3. LLM=プレーンテキスト台本のみ、検証と組み立て=決定的コード (IMPLEMENTATION_PLAN-1B §8)。出典 URL は本文に入れずソース一覧へ (design-inheritance §8)

実行結果 (fresh): pytest **197 passed** / ruff clean / mypy strict clean (39 files)

## Ticket T18 — fallback 二重防御 (2026-06-11)

1. `tests/test_fallback.py` (10件) → verify: 全テンプレ 4 パターンが契約適合・パターン別文面・Tier4 噂明示込み・乱択・長文タイトル切り詰め・LLM 1回目成功 ("llm")・違反フィードバック付き再生成 ("llm_retry")・連続違反でテンプレ ("template")・LLMError 時もテンプレで継続・Tier4 噂明示の強制が緑
2. 新規モジュール: `script/fallback.py` (`fallback_topic_script` / `generate_with_fallback` / `TopicScriptResult`)
3. method/violations は T20 (A/B/C 修正回数ログ) の入力。fallback で「LLM が崩れた日も番組が出る」を担保 (design-inheritance §7)

実行結果 (fresh): pytest **207 passed** / ruff clean / mypy strict clean (41 files)

## Ticket T19 — Sprint 1B 新テーブル + 永続化 (2026-06-11)

1. `tests/test_store_1b.py` (7件) → verify: init_db で 4 新テーブル作成 (冪等)・episode_drafts 保存 (variant/markdown/notices)・topic_candidates の selected/position 記録・llm_runs の成功/失敗/json_stable 記録・script_versions の method/attempts 記録が緑
2. `store/schema.py` に `EpisodeDraft` / `TopicCandidate` / `LLMRun` / `ScriptVersion` 追加 (要件 §12.5、FK は episode_drafts/items へ)
3. `store/repo.py` に `create_episode_draft` / `insert_topic_candidates` / `record_llm_run` / `insert_script_versions` 追加。値オブジェクト import は collect.normalize の既存前例に倣う

実行結果 (fresh): pytest **214 passed** / ruff clean / mypy strict clean (42 files)

## Ticket T20 — A/B/C 比較ログ集計 (evaluate) (2026-06-11)

1. `tests/test_abtest.py` (4件) → verify: variant 別集計 (採用率 2/4=50%・LLM 呼び出し/失敗・tokens 合算・json_stable 率・method 内訳・平均 attempts)・editor 実行なし variant の json_stable=None・空 DB・日本語サマリー整形が緑
2. 新規モジュール: `edit/abtest.py` (`VariantStats` / `evaluate_variants` / `format_evaluation`)。読み上げ自然さ・AI 要約臭は人間評価と明記 (ADR-0005)

実行結果 (fresh): pytest **218 passed** / ruff clean / mypy strict clean (44 files)

## Ticket T21 — CLI draft / evaluate + Discord 台本投稿 (2026-06-11)

1. `tests/test_discord_script.py` (8件) → verify: 2000字チャンク分割 (行境界優先・超過行はコードポイント強制分割・内容無欠損)・post_markdown の複数投稿・失敗時 False (fail-open)・空 URL/空文の拒否が緑
2. `tests/test_draft_runner.py` (4件) → verify: 候補ゼロで None・フルパイプライン (DB に episode_drafts/topic_candidates(selected+position)/script_versions/llm_runs(editor+writer, tokens, json_stable) が揃う)・editor JSON 崩壊時の neutral fallback (json_stable=False 記録で番組続行)・writer 全違反時の全テンプレ化が緑
3. `tests/test_cli_1b.py` (5件) → verify: draft --help・--dry-run (LLM 不使用)・API キー未設定 exit 1 (案内付き)・未知 variant exit 1・evaluate 空 DB が緑
4. **実 DB スモーク**: `draft --dry-run --lookback-hours 240` → 候補 40 件 (上限キャップ動作)、prescore 序列 (70/50...)、variant A 解決 (editor=mimo, writer=deepseek) を実データで確認。`evaluate` → 「draft なし」表示
5. `main.py` に `draft` / `evaluate` コマンド追加、info の Sprint 表示を 1B に更新。AGENTS.md の §2/§3.4/§4/§6 を実態同期

実行結果 (fresh): pytest **235 passed** / ruff clean / mypy strict clean (48 files)

### Sprint 1B 実装まとめ (T12〜T21)

| 層 | モジュール | 役割 |
|---|---|---|
| llm/ | profile.py / client.py | A/B/C 設定切替・OpenAI 互換クライアント (T12) |
| edit/ | prescore.py / judge.py / select.py / arc.py / abtest.py | 事前スコア→LLM判定→ゲート+多様性選定→三幕配置→評価集計 (T14-T16, T20) |
| script/ | generate.py / fallback.py / runner.py | 台本契約+検証→二重防御→draft 統合 (T17, T18, T21) |
| store/ | schema.py / repo.py (拡張) | 1B 4テーブル永続化 (T19) |
| deliver/ | discord.py (拡張) | 台本チャンク投稿 (T21) |

**残**: T13 (実 API 接続 smoke — 人間の API 契約・課金判断待ち。解消後は .env にキー設定のみで `draft` 実行可能) → T22 (3日間品質観察)。

### カバレッジ (2026-06-11, `uv run --with pytest-cov pytest --cov=karyu_tech_news`)

TOTAL **96%** (1323 stmts / 58 miss)。DoD 80% を充足。1B 新規モジュールは 93〜100% (prescore/select/arc/abtest/fallback/generate/profile/repo/schema = 100%)。

## Sprint 1B E2E 検証 #1 — LLM 全断時の fail-open 実証 (2026-06-11)

> ローカル Ollama (`local-ollama` 互換 profile, variant L) + 実 DB コピー (`/tmp/karyu-e2e.db`) で `draft` を実行。
> Homebrew 版 Ollama 0.30.7 の パッケージング不全 (llama-server 欠落) により **全 LLM 呼び出しが HTTP 500** という、偶然ながら理想的な「LLM 全断の日」の実地試験になった。

結果: **番組は完全な形で出力された** (設計どおり)。

- editor 3 回リトライ→失敗 → **neutral 判定フォールバック** 発動 (`editor JSON 安定: no`)
- writer 各トピック 2 試行→失敗 → **テンプレ fallback** 発動 (`template=5`、4 パターン乱択で文面が単調にならないことも確認)
- 出力 Markdown: タイトル/生成日時/profile、オープニング、トピック5本 (Hook/Insight/Action 構造維持)、クロージング、ソース一覧5件 — 要件 §14.2 の全項目
- `evaluate --db-path /tmp/karyu-e2e.db`: 採用率 12% (5/40)、修正回数 平均3.0 (template=5)、LLM 呼び出し2回/失敗2、JSON 安定性 0% — **失敗が観測データとして正しく記録される**ことを実証
- 検証で気づいた改善候補 (Ticket 外、人間判断待ちへ): タイトルが短い GitHub リリース (例「v1.0.0」) は見出しにソース名を併記したい

確認コマンド: `uv run karyu draft --profiles /tmp/karyu-e2e-profiles.yaml --variant L --db-path /tmp/karyu-e2e.db --lookback-hours 240`

### E2E 検証 #2 (ハッピーパス) の状態 — 環境起因で保留

ローカル LLM 正常系の E2E (qwen3:0.6b) も試行したが、Homebrew formula 版 Ollama 0.30.7 は llama-server 欠落 (MLX のみ同梱)、公式アプリ版 (`brew install --cask ollama-app` 導入済み) は **GUI 初回起動の対話承認が必要**でヘッドレスでは未完。人間が Ollama.app を一度起動すれば、以下で正常系 E2E を再開できる (コード変更不要):

```bash
ollama pull qwen3:0.6b   # 取得済み
uv run karyu draft --profiles /tmp/karyu-e2e-profiles.yaml --variant L --db-path /tmp/karyu-e2e.db --lookback-hours 240
```

なお実 API (MiMo/DeepSeek) の正常系は T13 の本来のスコープであり、本検証はその先行リハーサルという位置づけ。

## E2E 発見バグ修正 — reasoning フィールドのフォールバック (2026-06-11)

ローカル E2E (Ollama 0.30.7 + qwen3:0.6b) の実測で、OpenAI 互換応答の思考出力が `reasoning_content` ではなく **`reasoning`** フィールドに入ることを確認 (設計継承 §9「多数フィールドを順に試す」の正当性を実証)。`llm/client.py` のフォールバック連鎖を `content → reasoning_content → reasoning` に拡張、回帰テスト追加。

実行結果 (fresh): pytest **236 passed** / ruff clean / mypy strict clean

## Sprint 1B E2E 検証 #2 — ローカル実 LLM ハッピーパス成功 (2026-06-11)

> Ollama (公式アプリ版) + qwen3:0.6b (コンテキスト16k、ポート11500の検証用サーバ) + 実 DB コピーで `draft` を再実行。

結果: **Draft #2 生成完了: 候補 40 → 採用 5 本 (生成方法: llm=5, editor JSON 安定: no)**

- **writer LLM が 5 本全てを生成** (テンプレ 0)。全本文が Hook/Insight/Action 構造・300字以内・URL 混入なし・禁止表現なしの検証を通過
- editor は 1/40 件しか判定を返さず → **今回実装した neutral 充填が発動** (`judged 1/40` → `neutral fill for 39`) し番組成立。0.6b に 40 件一括判定は荷が重い (本番 MiMo/DeepSeek の評価ポイント)
- `evaluate` 集計 (2 回分): 採用率 12% (10/80)、修正回数 平均 2.0 (llm=5/template=5)、コスト prompt 9,724 / completion 1,636 tokens、JSON 安定性 0% — **全断日と正常日が同じ評価軸で比較可能**なことを実証
- E2E が今日発見・修正させた実改善 2 件: (1) `reasoning` フィールドフォールバック、(2) 部分的判定欠落の neutral 充填
- 0.6b 品質所感 (人間評価の参考): 構造契約は満たすが固有名詞の誤りと日中混在あり。実運用モデル (DeepSeek/MiMo) では大幅改善見込み

**結論: 収集 (実データ) → 候補抽出 → LLM 判定 → ゲート/アーク → LLM 台本生成 → 検証 → 組み立て → 永続化 → 集計 の全行程が実 LLM で完走。Sprint 1B パイプラインは本番 API キー投入を残すのみ。**

## Sprint 1B 運用リハーサル Day 0 — §13.2 日次フローを本日の実データで完走 (2026-06-11)

> 要件 §13.2 (collect → draft → Discord 台本投稿 → 翌朝人間確認) を、ローカル LLM (variant L) で初めて通しで実運用。

1. `docker compose up -d rsshub` → RSSHub 起動
2. `collect --post` → **9/9 ソース成功・70 新着**・Discord 収集サマリー **HTTP 204**
3. `draft --variant L --lookback-hours 30 --post` → **候補 40 → 採用 5 本 (llm=5)**・**Discord に台本初配信成功**
   - editor カバレッジ 38/40 (neutral 充填 2 件のみ)。当日ニュース (GPT-5.6 / Claude Mythos 5 等) が選定された
   - 採用 5 本の検証 (Hook/Insight/Action・300字・URL なし・禁止表現なし) 全通過
4. **人間確認待ち**: Discord に届いた台本 (variant L = ローカル検証版) を読み、「音声化する価値」評価の練習台として利用可

### 発見・修正したセキュリティ問題

`collect --post` 実行ログで **httpx INFO ログが Discord Webhook URL (トークン込み) をコンソールへ出力**していることを発見 (T11 期間から存在した既存問題、要件 §9.5 違反)。`setup_logging` で httpx ロガーを WARNING に抑制 + 回帰テスト追加。**トークンはローカルコンソールにのみ出ており、リポジトリへの混入はない** (grep 確認済み)。露出が気になる場合は Webhook の再発行 (Discord 側でワンクリック) を推奨。

実行結果 (fresh): pytest **238 passed** / ruff clean / mypy strict clean

---

## Ticket T13 — MiMo/DeepSeek 実 API 接続 smoke 完了 (2026-06-12)

> 人間ブロッカー (API 契約・課金) 解消 — ユーザーが `.env` に DEEPSEEK_API_KEY / MIMO_API_KEY を設定。

| profile | 確定 endpoint | 確定 model | 結果 |
|---|---|---|---|
| deepseek | `https://api.deepseek.com/v1` (変更なし) | エイリアス `deepseek-chat` → 実体 **deepseek-v4-flash** | ✅ 疎通 (20+1 tokens) |
| mimo | **`https://api.xiaomimimo.com/v1`** (プレースホルダ `api-inference.xiaomi.com` は DNS 不在 → 公式 platform.xiaomimimo.com ドキュメントで確定し config 修正) | `mimo-v2.5-pro` (公式記載どおり) | ✅ 疎通 (27+36 tokens、Bearer 認証で通過) |

- smoke は自前 `LLMClient` をそのまま使用 (クライアント実装の本番互換も同時に実証)。キー値は出力・記録していない
- OpenRouter フォールバックは未契約のまま保留 (主系 2 つが疎通したため不要)

## Ticket T22 — 台本品質観察 Day 1 (2026-06-12, variant A 本番初配信)

`draft --variant A --post` (editor=MiMo, writer=DeepSeek) を実行:

- **Draft #2: 候補 40 → 採用 5 本 (生成方法: llm_retry=5, editor JSON 安定: yes)** → **Discord 配信成功**
- **editor (MiMo)**: 40/40 候補を一発 JSON 判定 (neutral 充填ゼロ)。**JSON 安定性 100%**
- **writer (DeepSeek)**: 全 5 本が初回違反 → フィードバック再生成 1 回で契約適合 (`llm_retry=5`)。初回違反の主因は要観察 (300字超過の可能性大 — T22 で傾向を見てプロンプト調整判断)
- **品質所見 (Day 1)**: カナ化+初出原語併記が仕様どおり (例: アントロピック (Anthropic))、Insight が日本リスナー視点、三幕構成成立。「音声化する価値」評価は人間の Discord 確認待ち
- **コスト実測**: 1 エピソード = prompt 13,966 + completion 2,572 tokens (約16.5k)。月22営業日でも要件 §9.7 予算 (1,500-3,000円) に対し大幅な余裕
- evaluate による A vs L 比較が初めて成立 (JSON 安定性 100% vs 0% — ADR-0005 の評価軸が実データで機能)

残: T22 Day 2 / Day 3 (翌日以降の `collect --post` → `draft --variant A --post`)

## Ticket T22 — 台本品質観察 Day 2 (2026-06-13 16:58 JST, variant A)

> 注: 06-13 07:47 のスケジュール自動実行は発火したが TEST_LOG 記録・コミットを残さず途中失敗 (旧セッション環境要因の可能性)。Day 2 観察窓は当日であるため、オーケストレーターが [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) §2 決定木 行#3 に従い手動完走させた。

`collect --post` → `draft --variant A --post` → `evaluate` を実行:

- **collect: 7/9 ソース成功・30 新着・Discord HTTP 投稿成功**。Docker (colima) 停止により juejin 2 ソース (RSSHub 依存) が Connection refused → **fail-open 完璧動作** (残 7 ソースで完走・Discord 着弾)。§3.3 の実地実証
- **draft: 候補 30 → 採用 5 本・Discord 投稿成功**。生成方法 `llm_retry=1, template=4`、**editor JSON 安定: yes**
- **⚠ 品質変動 (Day 1 比)**: writer (DeepSeek) が **5 本中 4 本で template fallback** に落ちた (Day 1 は llm=5/template=0)。topic 5 (脳機接口) のみ豊かな LLM 洞察が生成され、1-4 はテンプレ定型文 (「本日注目の話題です」「詳細は引き続き確認中ですが」)。**editor (MiMo) は引き続き安定**だが **writer (DeepSeek) の生成成否が日によって大きく振れる**ことが判明 — これは T22 が検出すべき最重要観察。原因候補: DeepSeek の応答品質変動 / レート制限 / 当日候補の性質。Day 3 で再現性を確認し、再現するなら writer プロンプト調整 or fallback 閾値の人間判断へ
- **evaluate (案 A 累計 2 回)**: 採用率 14% (10/70)、修正 平均 2.4 回 (llm_retry=6, template=4)、コスト prompt 22,532 + completion 5,804 tokens (LLM 4 回・失敗 0)、**JSON 安定性 100%**
- **コスト**: 2 エピソード累計 約 28k tokens。要件 §9.7 予算 (月 1,500-3,000円) に対し大幅な余裕を維持
- **環境メモ**: Docker (colima) 未起動のため Tier3 掘金が取得不可。Day 3 で掘金も観察したい場合は `colima start` → `docker compose up -d rsshub` が必要 (任意 — 直接ソース 7 本で番組は成立)

- **真因診断 (Day 2、`data/state.db` の llm_runs/script_versions 解析)**: template 落ち 4 本は writer LLM 呼び出し成功 (`ok=1`、API エラー無し) かつ `attempts=3` まで `validate_topic_script` の **「300 字超過 (空白除く)」検証に通らず** fallback。成功 1 本は空白除き ≤300 字。**= DeepSeek が `TOPIC_CHAR_LIMIT=300` を超える長さで書き、再生成 3 回でも縮められないのが真因** (API/editor の問題ではない)。対処案と「観察汚染を避けるため T22 後に修正」の方針は PROJECT_STATE「人間判断待ち」に記録。

残: T22 Day 3 (06-14、3 日総括 + DoD 更新 + Sprint 1B 完了 PR)。**Day 3 で writer の template fallback 率を必ず確認** (Day 1=0/5, Day 2=4/5 の振れの再現性)

## Ticket T22 — 台本品質観察 Day 3 (2026-06-14 19:02 JST, variant A) + 3日間総括

> 注: 06-14 07:47 のスケジュール自動実行も (Day 2 同様) 記録・コミットを残さず失敗。**スケジュール機構自体がこの多段 git コミット作業には不安定**と確定 (堅牢化プロンプトでも改善せず → 失敗原因はプロンプトでなく scheduled-session 環境)。Day 3 はオーケストレーターが手動完走 (今回は `colima start` で RSSHub も起動しフル 9 ソース観察)。

`collect --post` → `draft --variant A --post` → `evaluate` を実行:

- **collect: 9/9 ソース成功・53 新着・Discord 投稿成功**。掘金 (juejin) 2 ソース復活でフル稼働。
- **draft: 候補 40 → 採用 5 本・Discord 投稿成功**。生成方法 **`template=5` (llm=0)**、**editor JSON 安定: yes**。
- **⚠ writer fallback の悪化トレンド確定 (T22 最重要結論)**: template 率が **Day1 0/5 → Day2 4/5 → Day3 5/5** と単調悪化し、Day 3 は**全トピックがテンプレ定型文**。DB 診断 (llm_runs/script_versions): writer 呼び出しは成功 (`ok=1`, completion 2,518 tokens, エラー無し) だが全 5 本 `attempts=3` まで「300 字超過 (空白除く)」検証に通らず fallback。**= DeepSeek が冗長で `TOPIC_CHAR_LIMIT=300` を一貫して超過し、再生成フィードバックでも縮められない**。間欠的でなく**構造的**な品質問題と確定。editor (MiMo) は 3 日とも JSON 100% 安定で問題なし。
- **⚠ NEW 発見 — エピソード内 同一記事重複**: ソース一覧の #2/#3 が同一 URL (`juejin.cn/post/7650451521307770923`)。`juejin-ai-category` と `juejin-trending-ai-weekly` が同一記事を別 `source_id` で保持 → `UNIQUE(source_id,item_key)` では別レコード → **選定が canonical URL 横断で重複排除していない**ため同一エピソードに 2 回採用。Day 2 は juejin ダウンで顕在化せず、Day 3 のフル観察で発見。
- **evaluate (案 A 累計 3 回)**: 採用率 14% (15/110)、修正 平均 2.6 回 (**llm_retry=6, template=9**)、コスト prompt 36,497 + completion 9,179 tokens (LLM 6 回・失敗 0)、**JSON 安定性 100%**。

### T22 3日間総括 (結論)

| 評価軸 | 結論 |
|---|---|
| パイプライン完走 | ✅ 3 日とも collect→draft→evaluate→Discord 配信が完走 (Discord 6/6 投稿成功) |
| fail-open | ✅ Day 2 (juejin ダウン) でも 7/9 ソースで番組成立・配信 — §3.3 実証 |
| editor (MiMo) | ✅ **本番品質**。3 日とも候補全件を一発 JSON 判定、安定性 100%、neutral 充填ゼロ〜僅少 |
| writer (DeepSeek) | ❌ **本番品質に未達**。300 字上限を一貫超過し template 率 0→80→100% と悪化。variant A の writer は現状のままでは「音声化する価値」を安定して満たさない |
| dedup | ⚠ ソース内は ✅ だが **canonical URL 横断の重複排除が欠落** (Day 3 発見) |
| コスト | ✅ 3 エピソード累計 ~46k tokens。要件 §9.7 (月 1,500-3,000円) に対し大幅余裕 |
| 「音声化する価値」 | △ editor 判定は良好だが、writer のテンプレ落ちにより Day2/3 の台本は定型文中心で価値水準に未達。**writer 修正が前提条件** |

**総合判定**: Sprint 1B の**インフラ DoD (3-5本選定/Markdown台本/ソース一覧/A-B-C記録/Discord投稿/fail-open) は全て達成**。一方、**コンテンツ品質 DoD「音声化する価値に近い」は writer (DeepSeek) の 300字超過問題により未達**。T22 観察は設計意図どおり**実運用でしか出ない 2 defects を捕捉**した (= 観察フェーズの成功)。

**次アクション (この観察から導かれる修正)**:
1. **writer 300字遵守** (確定根因): writer プロンプトに明示的な字数バジェット (上限より厳しめ) + 再生成フィードバックに現在文字数/超過分を含める。低リスク・コスト不変・設計保存の修正。
2. **canonical URL 横断 dedup**: 選定段階で同一正規化 URL のトピックを 1 本に統合。
3. (人間判断) 上記 1 で不十分なら writer モデル差し替え or `TOPIC_CHAR_LIMIT` 緩和 (TTS 尺・コストに影響)。

---

## Ticket T24 — 実音声 smoke (2026-06-17, Kokoro ONNX 実機合成)

> 人間が `uv sync --extra tts` で kokoro-onnx 導入 + Kokoro モデル DL を許可 (Irodori も実機で動作可と確認)。これで T24 の人間環境ブロッカーが解消 → **実音声を初生成** (T13 の音声版)。

- **環境**: Kokoro モデル `kokoro-v1.0.onnx` (325MB) + `voices-v1.0.bin` (28MB) を `~/.cache/karyu-tts/` に DL。`KOKORO_MODEL_PATH`/`KOKORO_VOICES_PATH` で指定。Mac でローカル ONNX 推論 (GPU/課金不要)。
- **単体 smoke**: `select_engine('kokoro')` → 「こんにちは。華流テック通信、本日の…」を合成 → **820KB / 24kHz / 17.1s の有効 wav**。アダプタ (`tts/kokoro.py`) + エンジン抽象が実機で動作。
- **フルパイプライン smoke**: 構造化(T25)→読み仮名正規化(T26)→絵文字注釈(T27, kokoro は emoji 非対応でゲート off)→文分割+実合成+wav結合(T28) → **1 エピソード実音声 4MB / 73-84s**。T23-T28 全鎖が実エンジンで動作。
- **⚠ 実音声 smoke で発見した defect (修正済み)**: 台本本文の Markdown マーカー `**Hook:**`/`**Insight:**`/`**Action:**` を TTS が「アスタリスク…」と読み上げていた (モック駆動では出ない欠陥)。→ `tts/normalize.strip_script_markup` を追加し合成前に除去。修正後、尺 83.8s→73.1s に短縮 (マーカー読み上げ分が消失)・回帰テスト追加。
- **⚠ T32 観察項目 (要調整)**: 修正後も 73s は ~140 字に対し長すぎ (話速が遅い)。`SynthesisRequest.speed` 引き上げ or 声/lang 設定の調整を T32 聴感観察で詰める。
- **Irodori アダプタ (ADR-0006 主軸) を実装**: `tts/irodori.py` (OpenAI 互換 `POST /v1/audio/speech` を httpx で叩く、絵文字スタイル制御対応・emoji_style=True)。`select_engine('irodori-tts-v3')` で config primary_engine と一致。実サーバ smoke は `uv run python -m irodori_openai_tts --port 8088` 起動後に実施 (人間環境)。ユニットは httpx モックで契約固定。
- **生成 wav は `data/episodes/` (git 管理外)**。pytest 325 / ruff / mypy strict (63 files) 緑。

---

## Ticket T30 — ラウドネス正規化 + mp3 完パケ (2026-06-17, autopilot インライン)

FR-102/103 のマスタリング層 `mix/master.py`。ffmpeg `loudnorm` (EBU R128) 2-pass で
-16 LUFS へ正規化し mp3 192kbps/48kHz で書き出す。**計画の T29(BGM)→T30 順を判断で逆転**し、
BGM 素材 (人間ゲート §6) を待たずに「素の音声→完パケ mp3」のエンドツーエンドを開通。

**目標駆動の検証手順** (`命令 → verify`):
1. 純ロジック (loudnorm JSON パース・フィルタ構築) を ffmpeg 非依存で実装 → verify: `pytest tests/test_mix_master.py -k "parse or build"` 緑 (4 件)。
2. ffmpeg 統合で実 mp3 生成・正規化 → verify: tone wav を master し `measured_lufs ≈ -16 ±1.5` / 出力が mp3 / 48kHz をアサート (ffmpeg 不在は skipif で除外)。
3. 測定不能 (無音 -inf / 0フレーム) のとき **loudnorm をスキップし素エンコードに縮退** (真の fail-open, Codex 指摘で修正) → verify: `_build_loudnorm_filter` が None を返し、無音 wav・0フレーム wav (→短い無音退避) が valid mp3 になる統合テスト。不正バイトは `MasteringError` で区別。
4. E2E 実 smoke (実エピソード wav): `master_to_mp3(episode_smoke2.wav)` →
   - 入力: **-20.17 LUFS** / TP -3.66 dBTP (配信には静かすぎる素の音声)
   - 完パケ: **-16.30 LUFS** (目標 -16.0, 誤差 0.3 LU) / TP **-1.71 dBTP** (≤ -1.5 ceiling)
   - 尺 73.1s / 192k / 48kHz / **1.7MB** (Discord 25MB 添付上限内 → T31 配信方法判断の材料)

**依存最小の判断 (§5)**: ffmpeg `loudnorm` 単体で測定+正規化+mp3化が完結するため **pydub を足さない**
(pydub が要るのは T29 の BGM 時間軸合成)。

**Codex 独立レビュー**: 初回 FAIL (High1: 測定不能/無音/0フレーム時の fail-open が不完全で
libmp3lame assertion crash) → 修正 (上記 step 3) → 再レビューで実 ffmpeg/ffprobe 検証し **PASS**。
**Antigravity QA PASS** (無音/0フレーム/実音声を実際に master_to_mp3 へ投入)。

**ゲート (fresh 実行)**: `pytest` **324 passed** / `ruff check .` クリーン / `mypy src tests` strict
**Success (64 files)**。生成 mp3/wav は `data/episodes/` (git 管理外)。

---

## Ticket T29 + T31 — 完パケ自律パイプライン (2026-06-18, autopilot インライン)

人間の3決定 (#17 にスタック実装 / 配信=Discord 添付 / BGM=素材非依存) を受けて実装。

**T29 `mix/mixer.py` (素材非依存)**:
- `assets/bgm/` に素材があれば pydub で全編に -18dB BGM + 前後フェード、無ければ **passthrough**。
- pydub 未導入・デコード失敗も fail-open (音声のみ返す)。素材ライセンス (人間ゲート §6) を待たずコードを通せる。

**T31 produce / 永続化 / 配信**:
- `audio_versions` テーブル (engine/duration/lufs/bitrate/sample_rate/path、lufs は無音時 NULL) + `insert_audio_version` / `get_latest_episode_draft`。
- `deliver.post_audio`: mp3 を Discord に multipart 添付。25MB 超はメッセージに degrade。fail-open + 秘密非漏洩。
- CLI `produce`: 保存済み台本 → 構造化 (markdown 1 segment) → 文単位合成 → BGMミックス → -16LUFS+mp3 → audio_versions 記録 → (Discord 添付)。`--engine`(既定=config tts.primary_engine) `--dry-run` `--out-dir` `--bgm-dir`。

**⚠ 実 produce smoke で発見した回帰 (修正済)**: `synthesize_script` が声 ID を `"hal"` 固定 → kokoro (声=`jf_alpha`) で全文「Voice hal not found」と fail-open し **無音 mp3**。mock/irodori は `"hal"` を持つため決定的テストでは緑だった。→ エンジン既定声 (`engine.voices()[0].id`) フォールバックで修正・回帰テスト追加。

**実 produce E2E smoke (kokoro, 実 draft id=5)**: 1838字 → **643秒 (10.7分) / 192k / 48kHz / -16.3 LUFS / 15.4MB** の実音声完パケ mp3 (Discord 25MB 内)。**⚠ T32 観察項目**: 10.7分は話速が遅い (`speed` 調整は聴感判断で別途)。

**Codex 独立レビュー**: 初回 FAIL → High (produce が config primary_engine を `voice` 誤読、実構造は `tts` ブロック = FR-090 違反、常に kokoro fallback) + Medium (post_audio 秘密非漏洩テスト不足) → 修正 (tts ブロック読込 + config 駆動回帰テスト + caplog 秘密テスト) → 再レビュー **PASS**。**Antigravity QA PASS** (gates 再実行 + 差分レビュー 5 観点)。

**ゲート (fresh)**: `pytest` **363 passed** / `ruff check .` クリーン / `mypy src tests` strict **Success (68 files)**。生成 mp3/wav は `data/episodes/` (git 管理外)。

---

## Ticket T33 / T33+ / T34 — 日次自動配信 + 絵文字制御 + 600M VoiceDesign 本採用 (2026-06-23〜24, autopilot インライン, PR #22)

**T33 日次自動配信 + launchd**: `scripts/daily_pipeline.sh` (collect→draft→produce→Discord を fail-open 順次 + Irodori サーバ存命管理 + mkdir 原子ロック + PID 再利用ガード) + `scripts/launchd/com.karyu.daily-pipeline.plist` (2026-06-24/25/26 06:30 ピン)。`tts/irodori.py` timeout 120→300s + env `IRODORI_TIMEOUT` 上書き (参照音声の遅い1文の ReadTimeout 欠落対策、test 3種)。
- ライブ実証 (6/23 09:48, 500M): collect 5s / draft 52s / produce 9分、3点 Discord 配信成功、文欠落0、episode_6 192.7s/-16.3LUFS。

**T33+ 絵文字スタイル制御の修復**: 従来 annotate 層 (T27) が produce で未呼出=死コードだった根因を修正。`synthesize_script` に `emoji_mapping` を追加し**文単位**で tone 別絵文字挿入 (`capabilities.emoji_style` ゲート、後方互換、test 3種)。`hal_persona.yaml` を Irodori 公式45絵文字語彙へ remap (語彙外 `bright ☺️→😊` 等修正) + `neutral→📖`。

**T34 600M VoiceDesign + caption (エンジン非依存)**: `SynthesisRequest.caption` + `Capabilities.voice_design` (engine.py)、`IrodoriTTSEngine` の caption 送出 (irodori.py、env `IRODORI_CAPTION` 上書き可、test 4種)、`synthesize_script` の caption 文単位配線 (voice_design ゲート、test 2種)、produce が `hal_persona.tts.caption` を渡す。外部 server (別リポジトリ): `app.py` caption plumbing / `.env` checkpoint 600M / `irodori-tts` eaf74d6 更新 (use_speaker_condition 対応、silentcipher ウォーターマーク付与)。

**ゲート (fresh, 6/24)**: `pytest` **380 passed** / `ruff check .` クリーン / `mypy src tests` strict **Success (68 files)** / `bash -n scripts/daily_pipeline.sh` + `shellcheck` クリーン / `plutil -lint` plist **OK**。
**実 E2E 証跡**: (1) 600M server caption smoke = HTTP 200 / 7.04s 音声 / valid 48kHz wav。(2) 実 produce (draft 6, 600M+caption+絵文字) = サーバ22文合成・**文欠落0**・236.6s/192k/48kHz/**-16.2 LUFS** 完パケ (audio_versions id=6)。
**レビュー/QA**: **Codex 独立レビュー PASS** (Critical0/High0/Medium2/Low1、Medium=PROJECT_STATE/TEST_LOG 同期 → 本追記で解消)。**Antigravity QA 合格** (§3 NG 抵触なし・回帰なし・整合性 OK、Low=README/AGENTS テスト数 drift → 同期)。
**⚠ shell/plist の自動テストは無し (Codex Low)**: `bash -n` + `shellcheck` + `plutil -lint` の静的検証で代替。将来変更時は本ログの手順を再実行する。
**⚠ 既知の運用リスク (QA)**: Mac スリープ中 launchd 不発火 (`pmset repeat wake` で回避) / produce 失敗時の Discord 通知なし (ログのみ、T36 で解消) / collect 0件日は前日 draft 再配信 / 6/26 後 launchd 撤去要 / **draft の中国語見出し埋め込みで TTS が崩す content 課題 (LLM writer プロンプト改善が中期対策)**。

**Copilot PR レビュー対応 (6/24, fb7bef4)**: PR #22 上の 5 指摘を全対応・全 thread resolve 済み。(1) `_resolve_timeout` が `float(nan)/(inf)` を弾くよう `math.isfinite` ガード追加 (nan は `<=0` をすり抜け・inf は無限 timeout = 無人ジョブ安全性バグ)・test に nan/inf/-inf 追加 → **pytest 383 passed**。(2) サーバを `--host 127.0.0.1` バインド + `.env` `IRODORI_HOST=127.0.0.1` で LAN 露出回避 (サーバ再起動で localhost-only 確認)。(3) `daily_pipeline.sh` のパスを env 上書き可 + スクリプト位置/`$HOME`/`PATH` 解決でポータビリティ確保。(4) plist の `ProgramArguments` を `$HOME` 経由でユーザー名非依存化 + 編集要箇所明記。ruff / mypy strict 68 / bash -n + shellcheck / plutil 再確認済み。

**T35 — 初の無人自動配信 (6/24 06:30) で発覚した 2 件を修正 (PR #22, `c7182e5`)**: ① **無音バグ**: launchd 実走ログ (`data/logs/launchd_pipeline.out.log` + `daily_20260624_063000.log`) で collect/draft 成功・**produce が rc=1 失敗 = 音声欠落**を確認。根因は launchd の bare PATH に Homebrew が無く `ffmpeg が見つかりません` でマスタリング失敗。対話実行は PATH に `/opt/homebrew/bin` があり常に成功していたため未検出 (= 無人実行特有の env バグ)。`daily_pipeline.sh` PATH に Homebrew 追加で修正。② **中国語翻字**: `transliterate_chinese_titles` を追加 (「」内が漢字あり・かな無し = 中国語原題のみ pinyin 化)。実 Hook smoke: `「三星电子HBM4芯片…」` → `「san xing dian zi HBM4 xin pian …」`、日本語引用/ナレーションは不変。**ゲート**: `pytest 387 passed` / ruff / mypy strict 68 files / bash -n + shellcheck OK。draft 7 再 produce で 600M+caption+翻字の実音声を確認 (DoD 証跡)。launchd 撤去は `/schedule` (`uninstall-daily-pipeline-launchd`, 6/27 07:00 JST) に登録。

**T35 Codex 2 ラウンド独立レビュー対応 (`1fb38ed` 他)**: (R1 High) 翻字 heuristic が「漢字あり・かな無し」だけでは**漢字のみの日本語引用 (生成AI/東京大学/人工知能 等) も pinyin 化**する誤検出を、**簡体字特有文字 (`_SIMPLIFIED_HAN`: 电/问/选/发 等、日本語新字体と字形が異なる字) を含む span のみ翻字**へ強化して解消。誤翻字防止 7 ケース + fail-open テスト追加。(R1 Medium) `pypinyin` を core→optional extra `tts` へ移動 (+mypy override+plan 追記)。(R2 High) 「肯定系翻字テストが標準 `uv run pytest` で extra 非導入だと落ちる」依存/ゲート不整合を、`pypinyin` を **dev group にも追加** + 肯定系テストに `pytest.importorskip("pypinyin")` で解消 (runtime は extra のまま最小)。**最終ゲート: `pytest 396 passed` / ruff / mypy strict 68 files / bash -n + shellcheck**。draft 7 再 produce = 275.4s / -16.3 LUFS / 文欠落0 (audio_versions id=7)。

---

## Ticket T36 — 音声品質ハードニング (2026-06-24, autopilot / branch `agent/T36-audio-quality-impl`)

ユーザー報告「途中で途切れる・読めていない・変な読み」を受け、実生成ログ/DB/音声ファイルを再調査。

**根因 1: 中国語 quote 処理と読み辞書の順序バグ**:
- T35 では `transliterate_chinese_titles` を入れたが、`synthesize_script` が先に `normalize_text(reading_dict)` を実行していた。
- 例: `「刚刚，豆包2.1发布！...」` に読み辞書が `豆包→ドウバオ` を混ぜる → quote 内にカナが入る → 後段の「かな有りなら日本語」ガードが働き、中国語原題の大半が TTS に残る。
- 修正: `prepare_tts_text` を追加し、`strip_script_markup`/`strip_ascii_gloss` → **中国語 quote 発話退避** → 読み辞書 → 残存 quote 発話退避の順に統一。
- 追加修正: 当初は pinyin へ翻字したが、実音声 ASR で長い pinyin 羅列そのものが異物読みになることを確認。長い中国語原題 quote は `この話題` へ退避し、読み辞書に完全一致する短い固有名詞 (`灵晟` など) だけカナ読みを残す。これにより `pypinyin` 依存を削除。
- 実DB draft #11 再構成: `今日は「刚刚，豆包2.1发布！...」を取り上げます。` 系の長い中国語 quote は `今日はこの話題を取り上げます。` へ退避し、raw `刚刚`/`发布` と pinyin 羅列は残らない。

**根因 2: 合成欠落が produce から見えない**:
- 既存 `synthesize_script` は文単位 TTSError を warning で skip して完走するが、戻り値に skip 数がなく、produce は文欠落を成功と区別できなかった。
- 修正: `SynthesisResult` に `attempted_sentences` / `synthesized_sentences` / `skipped_sentences` を追加。`synthesize_script` は文単位では fail-open で最後まで試すが、produce 境界では `skipped_sentences > 0` を不完全音声として fail-fast し、mp3 生成・DB 記録・Discord 投稿を中止する。合成成功文が 0 件、TTS 合成 wav が実質無音、または実運用尺 (>=5s) で post-encode LUFS が測定不能な場合も同様に中止する。

**根因 3: repeated produce が過去 mp3 証跡を上書き**:
- 既存 output path は `data/episodes/episode_<draft_id>.mp3` 固定で、同一 draft 再 produce が過去ファイルを上書きして `audio_versions` の複数行が同じ現物を指していた。
- 修正: `episode_<draft_id>_<UTC timestamp>.mp3` に変更し、各 produce 実行のファイル証跡を分離。

**根因 4: 原語 + カナ読み / URL が TTS 入力に残りうる**:
- 実DB draft #8/#9 で `灵晟（リンション）` が TTS 入力に残り、原語とカナ読みを二重に読む可能性を確認。
- 修正: `strip_pronunciation_parentheticals` で `原語（カナ読み）` をカナ読みだけに整理し、`strip_link_markup` で inline Markdown link と bare URL を TTS 入力から除去。誤置換防止として、置換対象は ASCII/数字または簡体字特有文字を含む headword に限定し、日本語説明括弧 (`自動運転（レベル4）`) は残す。`生成AI（エーアイ）` は `生成エーアイ` として前置の日本語を削らない。Code review High 3件 (bare URL が後続日本語まで削る / `中国企業灵晟（リンション）` の前置語を削る / `Tesla FSD（エフエスディー）` の前置語を削る) は、句読点を越えない URL regex と headword 末尾置換で修正。
- 追加辞書: `灵晟` / `ling cheng` → `リンション`。実DB再構成で raw `灵晟` / pinyin `ling cheng` が残らず `リンション` に揃うことを確認。

**根因 5: TTS wav の途中無音を BGM が覆い隠しうる**:
- 「途中で途切れる」系の不良は、BGM ミックス後や mp3 化後だけ見ると検出しにくい。
- 修正: `tts/quality.py` に `analyze_wav_signal` を追加し、BGM ミックス前の TTS wav でデジタル無音と最大連続無音秒数を計測。produce は 3.0 秒以上の無音区間を検出したら mp3 生成前に fail-fast。
- Architect WATCH 対応: 当初の 3.5 秒許容 / 4.0 秒 fail 境界を実データ再確認後に締め、2.5 秒ギャップは通し、3.0 秒ギャップは fail-fast する境界テストへ更新。成功時の CLI 出力に `max_silence=<秒>` を含め、T32/日次観察で実データを記録できるようにした。
- 追加修正: 全体では 3.0 秒未満でも、1 文だけ短い無音 wav を返すと「読めていない」まま通り得るため、`synthesize_script` が各文の返却 wav を `analyze_wav_signal` で確認するようにした。0フレーム/壊れた wav/デジタル無音/実質無音 chunk は結合前に skip し、`skipped_sentences` に加算する。
- 追加修正 2: クリック音や単発ノイズだけの chunk は `has_pcm_signal=True` になり得るため、`analyze_wav_signal` に `active_ratio` を追加。0.2 秒以上の文 chunk で有音 window が 10% 未満、かつ有音時間も 0.15 秒未満なら「有音率の低い wav」として skip し、短いノイズを「読めた音声」と誤判定しない。有音率だけでは長い前後無音を含む短い実発話も落とし得るため、絶対有音時間を併用する。

**根因 6: writer 出力に Unicode replacement character (`�`) が混入しうる**:
- 2026-06-25 実運用 draft #10 で `返り�きました` を確認。日本語TTSが置換文字を記号として読むと「変なの読んだ」音声になる。
- 修正: `validate_topic_script` が `�` を本文契約違反として検出し、将来の writer 出力は再生成/fallback に回る。既存 draft の produce では `prepare_tts_text` が観測済み `返り�き` を `返り咲き` に補修し、残存 `�` は除去して読ませない。

**根因 7: post-encode clipping 余裕を produce が gate していない**:
- `master_to_mp3` は true peak を測定しているが、produce は LUFS 測定不能だけを fail-fast にしていた。mp3 の true peak が高すぎると、配信側再エンコードや再生環境でクリップ/歪みの原因になる。
- 修正: 実運用尺 (>=5s) の完パケで true peak が測定不能、または -1.0 dBTP を超える場合、mp3 を削除して DB/Discord へ進めない。成功出力には `tp=<dBTP>` を含める。

**根因 8: 品質ゲート fail-fast を日次運用で見逃しうる**:
- `produce` が品質ゲートで fail-fast しても `daily_pipeline.sh` は fail-open でログだけ残し、最終 exit 0 で終わる。Architect delta review で「音声配信ゼロを見逃す」運用 WATCH と判定。
- 修正: `run_step` が rc を返すようにし、`produce` 失敗時のみ `notify_failure` を呼ぶ。通知は既存の `post_summary` を使い、`DISCORD_ERROR_WEBHOOK_URL` があれば優先、未指定なら `DISCORD_WEBHOOK_URL` に送る。bash 側で Webhook URL を表示しない。通知と Irodori cleanup 後は `produce` の rc をスクリプト全体の rc として返し、launchd/外部監視が品質ゲート失敗を success 扱いしないようにした。

**根因 9: pinyin 原題そのものが日本語番組音声として破綻しうる**:
- OpenAI API キーが無く `transcribe` skill は使えなかったため、ローカルの MLX Whisper ASR で 6/26 実配信 `episode_11_20260625T213100335574Z.mp3` を検証。
- baseline の日次配信 mp3 は TTS 入力との類似度 0.837 相当で、pinyin 原題が `ガン` / `インギニア` / `アイチテイ` などに崩れて認識された。
- 中国語原題 quote を `この話題` へ退避した dry-run mp3 は類似度 0.893 相当まで改善し、pinyin artifact は消失。`pypinyin` は不要になったため `pyproject.toml` / `uv.lock` から削除した。

**根因 10: 絵文字スタイル注釈が実音声に異物読みを混ぜる**:
- T34/T33+ の絵文字注釈あり dry-run は 276.3s / -16.3 LUFS / 3 秒以上無音なしまで機械ゲート上は正常だったが、ASR では `カイニーズ` / `ご作作` / `短短` / `イースム` / `課題の大ステム` など、台本にない異物句が残った。
- 同じ draft #11 を絵文字注釈なし persona で dry-run すると、220.6s / -16.2 LUFS / `tp=-1.8 dBTP` / `max_silence=2.0s` / 3 秒以上無音なし。ASR 類似度は 0.951 相当まで改善し、既知 artifact ヒットは 0。
- 修正: `load_emoji_annotation` は `tts.emoji_annotation_enabled: true` を明示した persona だけ mapping を返す。`config/hal_persona.yaml` は `emoji_annotation_enabled: false` を production 既定とし、再採用は ASR + 聴感再検証を条件にする。

**目標駆動の検証手順**:
1. 中国語 quote の順序バグを固定 → verify: `test_synthesize_sanitizes_chinese_title_before_reading_dict` が、`豆包` 読み辞書があっても長い中国語原題 quote を `この話題` へ退避し、raw 簡体字・pinyin 羅列・`ドウバオ` 混入を残さないことを確認。
2. 中国語原題の発話退避を固定 → verify: `test_sanitize_replaces_chinese_title_with_topic_placeholder` / `test_sanitize_drops_long_pinyin_prone_title` が、長い中国語 quote を `この話題` へ置換し、読み辞書完全一致の短い固有名詞だけカナ読みへ残すことを確認。
3. 合成欠落の可観測性を固定 → verify: flaky engine test で attempted=2 / synthesized=1 / skipped=1、mixed-rate/0-frame chunk は concat 後に skipped として数え、all-fail test で synthesized=0 / skipped=1。
4. 全滅無音成功防止を固定 → verify: zero-frame engine で `produce` が `TTS 合成で欠落文があります 2/2 文` により rc=1 となり、mp3 を生成しない。
5. デジタル無音成功防止を固定 → verify: 非ゼロフレームだが PCM が全て 0 の engine で `produce` が `TTS 合成で欠落文があります 2/2 文` により rc=1 となり、BGM/マスタリング前に mp3 を生成しない。
6. LUFS 証跡欠落の成功防止を固定 → verify: master 後の duration が 5.0s かつ `measured_lufs=-inf` の場合、`LUFS を測定できません` により rc=1 となり、mp3 と audio_versions 行を残さない。
7. output 証跡分離を固定 → verify: 同一 draft を 2 回 produce して `audio_versions.path` が 2 つとも異なり、両ファイルが存在。
8. TTS 入力 QA を固定 → verify: inline Markdown link / bare URL は読ませず、`灵晟（リンション）` / `「灵晟」` は `リンション` に正規化される。URL 後続文 (`https://example.com/a。次です。`)、日本語前置語 (`中国企業灵晟（リンション）`)、ASCII 前置語 (`Tesla FSD（エフエスディー）`) は削らない。
9. TTS 出力 QA を固定 → verify: `analyze_wav_signal` がデジタル無音と 4.5 秒無音ギャップを検出し、produce は 3.0 秒無音ギャップで `無音区間` エラーにより mp3 を生成しない。一方で 2.5 秒ギャップは通し、成功出力に `max_silence=2.5s` を含める。
10. 置換文字混入を固定 → verify: `validate_topic_script` が `�` を拒否し、`strip_invalid_tts_chars` が `返り�きました` を `返り咲きました` へ補修、未知の `�` を除去する。
11. post-encode clipping 余裕を固定 → verify: fake master が true peak -0.4 dBTP を返す実運用尺音声で produce が `true peak が高すぎます` により rc=1 となり、mp3 と audio_versions 行を残さない。
12. produce 失敗通知と外部監視向け rc を固定 → verify: fake `uv` + ローカル health server smoke で collect/draft 成功・produce rc=7 のとき、`notify_failure` が呼ばれ `produce 失敗通知: 処理完了` が日次ログに残り、cleanup 後にスクリプト全体も rc=7 で終了する。
13. 文単位の無音 chunk 欠落を固定 → verify: `test_synthesize_script_counts_silent_chunk_as_skipped` が 2 文中 1 文だけ無音 wav を返す engine で attempted=2 / synthesized=1 / skipped=1 となり、結合 wav には有音 chunk だけが残ることを確認。produce 境界では skipped が 1 件でも不完全音声として fail-fast し、mp3 を生成しない。
14. クリック音だけの chunk 誤通過を固定 → verify: `test_analyze_wav_signal_measures_sparse_click_as_low_activity` が 1 サンプルだけ有音の 1 秒 wav を `active_ratio=0.05` と測定し、`test_synthesize_script_counts_sparse_click_chunk_as_skipped` が 2 文中 1 文だけクリック音 chunk の engine で attempted=2 / synthesized=1 / skipped=1 となることを確認。
15. 短い実発話の誤 skip を防止 → verify: `test_synthesize_script_keeps_short_speech_with_padding` が、3 秒 chunk 中 0.2 秒だけ有音の短い実発話を `active_ratio < 0.1` でも kept として扱い、attempted=2 / synthesized=2 / skipped=0 となることを確認。
16. 部分欠落配信を防止 → verify: `test_produce_partial_synthesis_exits_without_mp3` が、2 文中 1 文だけ無音 skipped の engine で `TTS 合成で欠落文があります 1/2 文` により rc=1 となり、mp3 を生成しないことを確認。
17. 重複読み括弧を固定 → verify: `test_strip_duplicate_parentheticals_removes_exact_duplicate_reading` と `test_prepare_tts_text_strips_duplicate_parenthetical` が、`バイトダンス（バイトダンス）` および `字节跳动（バイトダンス）` + 読み辞書後の `バイトダンス（バイトダンス）` を `バイトダンス` へ整理することを確認。
18. template fallback の原題読み上げを廃止 → verify: `test_fallback_does_not_embed_raw_title_in_spoken_body` が、fallback 本文に raw 中国語 title (`刚刚...`) を含めず category ベースの日本語 Hook に落とすことを確認。出典タイトルは Markdown 見出し/ソース一覧に残し、TTS では読ませない。
19. pinyin 依存削除を固定 → verify: `uv lock` で `pypinyin v0.55.0` が lock から削除され、標準テストが pinyin 依存なしで通ることを確認。
20. 絵文字注釈の production 既定無効を固定 → verify: `test_load_emoji_annotation_defaults_off_for_persona` が既定 persona で `{}` を返し、`test_load_emoji_annotation_requires_explicit_opt_in` が明示 opt-in のみ mapping を返すことを確認。
21. ASR の客観改善を確認 → verify: draft #11 の Irodori dry-run を「中国語原題退避 + 絵文字注釈なし」で生成し、220.6s / -16.2 LUFS / `tp=-1.8 dBTP` / `max_silence=2.0s` / 3 秒以上無音なし、ASR 類似度 0.951 相当、既知 artifact ヒット 0 を確認。

**TTS chunk gate (fresh)**: `uv run pytest tests/test_tts_quality.py tests/test_tts_synthesize.py` → **39 passed in 0.37s**。

**対象ゲート (fresh)**: `uv run pytest tests/test_script_generate.py tests/test_tts_quality.py tests/test_tts_normalize.py tests/test_tts_synthesize.py tests/test_produce_pipeline.py` → **129 passed in 0.84s**。

**ASR delta 対象ゲート (fresh)**: `uv run pytest tests/test_tts_annotate.py tests/test_tts_normalize.py tests/test_tts_synthesize.py tests/test_fallback.py` → **87 passed in 0.28s**。

**通知補助込み対象ゲート (fresh)**: `uv run pytest tests/test_script_generate.py tests/test_tts_quality.py tests/test_tts_normalize.py tests/test_tts_synthesize.py tests/test_produce_pipeline.py tests/test_discord.py tests/test_discord_script.py` → **147 passed in 0.88s**。

**全体ゲート (fresh)**:
- `uv run pytest` → **438 passed in 2.93s**
- `uv run ruff check .` → **All checks passed**
- `uv run mypy src tests` → **Success: no issues found in 70 source files**
- `uv lock --check` → **OK (Resolved 65 packages)**
- `bash -n scripts/daily_pipeline.sh` + `shellcheck scripts/daily_pipeline.sh` → **clean**
- `plutil -lint scripts/launchd/com.karyu.daily-pipeline.plist` → **OK**
- `git diff --check` → **clean**

**実データ QA (2026-06-25 追加)**:
- `data/state.db` の最新 draft #6-#10 に `strip_markdown_structure` + `prepare_tts_text` を適用。発話入力に URL / Markdown link / `原語（カナ読み）` パターンは残らず、`灵晟` / `ling cheng` も残らないことを確認。draft #7-#10 は `リンション` へ正規化済み。draft #10 の `返り�きました` は `返り咲きました` に補修され、`�` は残らない。
- 2026-06-26 03:42 JST 追加確認: draft #10 の TTS 入力は 31 文 / 1203 文字で、従来 `バイトダンス（バイトダンス）がドウバオ2.1をリリースしました。` となっていた文が `バイトダンスがドウバオ2.1をリリースしました。` に整理され、`contains_duplicate=False` を確認。
- 簡体字候補として残った文字は draft #6=`争参` / #7=`参` / #8=`争参担` / #9=`争` / #10=`争参`。`競争` / `参考` / `担う` など日本語文脈のみで、中国語原題の未処理残存ではないことを文脈確認。
- 2026-06-25 実運用 Irodori produce は `data/logs/daily_20260625_063004.log` で `episode_10_20260624T213100466311Z.mp3` 生成成功 (340.6s / -16.2 LUFS / `max_silence=2.3s`)。`ffprobe` は 340.6s / 8,175,789 bytes。`ffmpeg ... silencedetect=n=-45dB:d=4` で 4 秒以上の無音イベントは出力されず。追加で `silencedetect=n=-45dB:d=1.5` を当てると 1.5〜2.4 秒の自然な間はあるが、3.0 秒 fail-fast 閾値を超える無音はない。
- 2026-06-26 03:12 JST 再測定: 同 mp3 は `silencedetect=n=-45dB:d=3` でも 3 秒以上の無音イベントなし。`loudnorm` は input -16.24 LUFS / -1.75 dBTP / LRA 6.90 で、T36 の -16 LUFS / true peak 余裕条件を満たす。
- 2026-06-26 03:42 JST 時点では 6/26 の日次 log/episode は未生成 (06:30 launchd 前)。現行 T36 コード + 重複括弧除去で実 Irodori dry-run produce を再実行し、`episode_10_20260625T184522399308Z.mp3` を生成成功 (337.8s / -16.2 LUFS / `tp=-1.8 dBTP` / `max_silence=2.9s`)。`[DRY RUN] DB 記録・Discord 投稿はスキップ` を確認。`ffprobe` は 337.84s / 8,109,549 bytes。`silencedetect=n=-45dB:d=3` で 3 秒以上の無音イベントなし。`silencedetect=n=-45dB:d=1.5` は 1.5〜2.17 秒の自然な間のみ。`loudnorm` 再測定は input -16.25 LUFS / -1.75 dBTP / LRA 7.20。
- 2026-06-26 06:30 JST launchd 実行: `data/logs/daily_20260626_063002.log` で collect 9/9 sources・52 new、draft #11、produce 成功、Discord mp3 投稿成功を確認。完パケ `episode_11_20260625T213100335574Z.mp3` は 316.8s / -16.3 LUFS / `tp=-1.8 dBTP` / `max_silence=2.6s`。DB `audio_versions` id=10 / draft_id=11 / lufs=-16.26 / path 記録済み。`ffprobe` は 316.80s / 7,604,397 bytes。`silencedetect=n=-45dB:d=3` で 3 秒以上の無音イベントなし。`silencedetect=n=-45dB:d=1.5` は最長 2.70 秒の自然な間のみ。`loudnorm` 再測定は input -16.26 LUFS / -1.76 dBTP / LRA 7.10。draft #11 の TTS 入力再構成は 1174 文字 / 25 文、URL / Markdown link / `�` / 重複括弧なし。簡体字候補は `参考` / `競争` など日本語文脈のみ。
- 2026-06-26 追加修正後の入力 QA: 読み辞書で `世界人工智能大会` / `引领者` / `SAIL賞` / `聖陽股份` を日本語・カナ読みへ正規化。draft #11 再構成で `人工智能` / `引领者` / `聖陽股份` / `SAIL賞` は残らず、`世界人工知能大会` / `卓越エーアイリーダー賞(セイル賞)` / `シェンヤングーフェン` へ変換されることを確認。template fallback は future draft で raw title を発話本文に入れない。
- ASR 確認 (2026-06-26): OpenAI API キーなしでも実行できるローカル MLX Whisper で draft #11 を検証。日次配信 mp3 は類似度 0.837 相当で pinyin artifact (`ガン` / `インギニア` / `アイチテイ`) を確認。中国語原題 quote を `この話題` へ退避した dry-run は類似度 0.893 相当で pinyin artifact 消失。さらに絵文字注釈なし persona の dry-run は `episode_11_20260626T004141167976Z.mp3` (220.6s / -16.2 LUFS / `tp=-1.8 dBTP` / `max_silence=2.0s`) となり、ASR 類似度 0.951 相当、既知 artifact ヒット 0、3 秒以上無音なし。発音・抑揚・固有名詞の自然さの最終判断は T32 の人間試聴が残る。
- 置換文字修正後の dry-run 再 produce: `uv run python -m karyu_tech_news produce --draft-id 10 --dry-run --engine irodori-tts-v3 --db-path data/state.db --bgm-dir assets/bgm --out-dir data/episodes` → `episode_10_20260625T005025587701Z.mp3` 生成成功 (340.2s / -16.3 LUFS / `max_silence=2.2s`)。`[DRY RUN] DB 記録・Discord 投稿はスキップ` を確認。`ffprobe` は 340.24s / 8,167,149 bytes。`silencedetect=n=-45dB:d=4` で 4 秒以上の無音イベントなし。追加 `silencedetect=n=-45dB:d=1.5` でも最長は約2.1秒。`loudnorm` 再測定は -16.26 LUFS / -1.75 dBTP、`volumedetect` は max_volume -1.8 dB。TTS 入力再構成でも `返り咲きました` あり、`返り�きました` / `�` 残存なし。これは BGM 後の補助確認であり、T36 本体の品質ゲートは produce 内で BGM 前 TTS wav に対して `max_silence`、post-encode mp3 に対して LUFS / true peak を測る。
- daily pipeline 通知 smoke: fake `uv` が collect/draft=0・produce=7 を返す環境で `scripts/daily_pipeline.sh` を実行し、script rc=7、`UV:run python - produce 7 <log>`、`WARNING: produce 失敗 (rc=7)`、`produce 失敗通知: 処理完了`、`日次パイプライン終了 (rc=7` を確認。これにより collect/draft は従来どおり fail-open で進めつつ、最終 produce の品質ゲート失敗は Discord 通知 + 非 0 終了で外部監視へ伝えられる。

**独立レビュー反映**:
- Code review (入力正規化 + concat 欠落検出まで): APPROVE with LOW。Kokoro 運用メモの `fail-open=無音mp3` が T36 後の fail-fast 契約と矛盾していたため、非 0 終了しうる説明へ修正。
- Architecture review: 初回 WATCH。実運用尺で `measured_lufs=-inf` を成功扱いする証跡リスクを、duration >= 5.0s の LUFS 測定不能 fail-fast と `AudioVersion.lufs` コメント更新で解消。無音ギャップ検出追加後の WATCH (当初 4.0s 閾値の境界/観察不足) は、最終的に 2.5s pass / 3.0s fail テストと `max_silence` 出力で解消し、最終 CLEAR。
- Code review (無音ギャップ検出 delta): サブエージェントへ最終確認を依頼したが長時間応答せず shutdown。main agent self-review と fresh gate は clean だが、PR 前には最新差分全体で独立 reviewer lane を再実行すること。
- Code review (最新 full diff, 2026-06-25): code-reviewer lane COMMENT with LOW 2件。① all-silent produce guard は ffmpeg 前に fail-fast するため不要な `skipif(not _HAS_FFMPEG)` を削除。② `analyze_wav_signal` の PCM 形式 coverage として 8/16/24/32-bit mono + 16-bit stereo の signal/silence 検出を追加。修正後 gate: `tests/test_tts_quality.py tests/test_produce_pipeline.py` → 40 passed、対象セット 120 passed、全体 426 passed、ruff/mypy/diff-check clean。再確認で **APPROVE**。Architecture lane は full diff と U+FFFD delta と LOW 修正後 delta のすべてで **CLEAR**。true peak gate 追加分も architecture delta **CLEAR** / code-reviewer delta **APPROVE** (Files reviewed 4, CRITICAL/HIGH/MEDIUM/LOW 0)。Autopilot code loop は clean。
- Code review (3.0s threshold + daily pipeline notification delta): code-reviewer lane **APPROVE** (CRITICAL/HIGH/MEDIUM/LOW 0)。architecture lane は initially WATCH (produce fail-fast を daily pipeline がログのみで見逃す運用リスク) → `daily_pipeline.sh` の produce 失敗通知追加後に **CLEAR**。残懸念は Discord 通知自体の best-effort 失敗時はログ止まりになる点のみで、既存 fail-open 契約と一致。
- Code review (partial synthesis delta): code-reviewer lane **APPROVE** (CRITICAL/HIGH/MEDIUM/LOW 0)。architecture lane は **WATCH**: `skipped_sentences > 0` が stderr 警告だけで、20文中15文欠落のような不完全 mp3 が投稿され得る。対応: produce 境界で `skipped_sentences > 0` を fail-fast に変更し、日次 pipeline の produce 失敗通知へ接続。`test_produce_partial_synthesis_exits_without_mp3` を追加。follow-up architecture は **CLEAR**。follow-up code-review は LOW 1件 (古い fail-open 説明) → main.py docstring / TEST_LOG / IMPLEMENTATION_PLAN-2 を更新後 **APPROVE**。
- Code review (latest full diff + duplicate-parenthetical delta, 2026-06-26): native subagent 2 レーンは使用上限で起動失敗したため CLI-backed review に代替。`codex review --uncommitted -c model_reasoning_effort=high` → **No discrete correctness, security, or maintainability bugs**。別途 `codex exec` architecture review → **Architectural Status: CLEAR**。非ブロッキング注意は (1) untracked `tts/quality.py` / `tests/test_tts_quality.py` を PR 前に含めること、(2) PROJECT_STATE review state の重複括弧 delta 待ち表現を更新すること。本追記で (2) は解消。
- Code review (fallback title removal + reading_dict delta, 2026-06-26): native subagent tool は「明示的 subagent 依頼時のみ」の制約があるため、CLI-backed review で最終確認。`codex review --uncommitted -c model_reasoning_effort=high` → **No actionable correctness issues**、対象/全体 pytest・ruff・mypy・bash syntax・diff whitespace checks も review 側で clean。別途 `codex exec` architecture review → **Architectural Status: CLEAR**。残リスクは ASR/人間聴感未実施と、本文 quote に共有漢字のみの中国語タイトルが残った場合は簡体字特有文字ベースの翻字対象外になり得る点。
- Code review (ASR delta + daily pipeline rc, 2026-06-26): staged full diff で `codex review --uncommitted -c model_reasoning_effort=high` を再実行し、**No actionable defects**。レビュアー側でも changed test subset / full `pytest` / `ruff` / `mypy` が green。別途 `codex exec` architecture review はコード境界・TTS 正規化順・日次 pipeline rc 伝播を妥当と確認し、初回は TEST_LOG/PROJECT_STATE の古い日次 pipeline rc と pytest 件数の記録だけ **WATCH** とした。記録修正後の follow-up architecture review は **Architectural Status: CLEAR** / Required actions none。

## 2026-06-29 — T37 agentic workflow research hardening

**対象**: プロダクトコード変更なし。agentic / multi-agent 最新知見を [agentic-workflow-research-2026.md](./agentic-workflow-research-2026.md) に集約し、`AGENTS.md` / `README.md` / `docs/WORKFLOW.md` / `docs/ORCHESTRATION_RUNBOOK.md` / `docs/PROJECT_STATE.md` / `prompts/review.md` / `prompts/qa.md` へ反映。

**URL到達性確認**:
- Anthropic Building effective agents: HTTP 200
- OpenAI practical guide to building agents: curl は HTTP 403 (公式ページのアクセス制限、404ではない)
- arXiv 2503.13657 MAST: HTTP 200
- Cognition Don't Build Multi-Agents / Multi-Agents working: HTTP 200 / 200
- arXiv 2405.15793 SWE-agent: HTTP 200
- arXiv 2604.07821 cooperation failure: HTTP 200
- arXiv 2605.01133 MAS safety: HTTP 200

**静的整合チェック**:
- `wc -l AGENTS.md` → **299** (300行以内)
- stale表現検索 (`merge 待ち` / `pytest **380` / `現状 242` / `agent/T22` など、現役文書対象) → no matches
- `git diff --check` → clean

**全体ゲート (fresh)**:
- `uv run pytest` → **438 passed in 3.02s**
- `uv run ruff check .` → **All checks passed**
- `uv run mypy src tests` → **Success: no issues found in 70 source files**
- `git diff --check` → **clean**

## 2026-06-29 — PR #24 review comment response

**対応したコメント**:
- README Quick start の `produce --dry-run` が `uv sync` だけで動くように見える点を修正。`uv sync --extra tts` と `--extra tts + TTS 設定` を明示。
- ORCHESTRATION_RUNBOOK の日次運用ループが全ステップ fail-open に読める点を修正。`collect` / `draft` は fail-open、`produce` は品質ゲート失敗時に通知 + 非 0 終了、`evaluate` は配信ループ外の任意観察手順と明記。

**全体ゲート (fresh)**:
- `uv run pytest` → **438 passed in 2.68s**
- `uv run ruff check .` → **All checks passed**
- `uv run mypy src tests` → **Success: no issues found in 70 source files**
- `git diff --check` → **clean**

## T44/T47 — 恒常スケジューラ再導入 + state.db バックアップ (2026-07-09)

- **T44 (恒常日次配信スケジューラ)**: 3日限定 Month+Day ピンから平日 (月〜金) 06:30 発火の Weekday 方式へ plist を変更。`install.sh` / `uninstall.sh` を新設 (`__HOME__` プレースホルダを実 $HOME へ展開して `~/Library/LaunchAgents` へ配置、冪等、plutil lint 込み)。
- **T47 (state.db バックアップ)**: `daily_pipeline.sh` の collect 前に `sqlite3 .backup` によるオンライン整合バックアップを挿入 (fail-open、7世代ローテーション、`data/backups/`)。実 state.db (17M) で `.backup` → `PRAGMA integrity_check`=ok・全9テーブル保持を確認。
- 検証: `plutil -lint` OK、展開後 plist も lint OK、`bash -n` 全 OK、`shellcheck scripts/daily_pipeline.sh scripts/launchd/*.sh` clean。

## T48 mixer 実 BGM ミックス経路テスト追加 (実装者: Claude Code / 日付: 2026-07-10)

**背景**: `src/karyu_tech_news/mix/mixer.py` の実 BGM オーバーレイ経路 (pydub でループ/フェード/overlay/export する本体、49-68 行) が passthrough (素材なし) 経路しかテストされておらず、カバレッジ 46%。BGM 素材投入時に本番で初めて走る未検証コードだった。

**追加**: `tests/test_mix_mixer.py` (新規)。`pytest.importorskip("pydub")` で optional extra `tts` 未導入環境を自動 skip する流儀は `tests/test_mix_master.py` の ffmpeg skipif に合わせた。ダミー wav (無音ナレーション / 正弦波 BGM) を `tmp_path` に生成し実ミックス経路を検証:
- 出力長がナレーション長に一致 (BGM 長に引きずられない)
- 出力が正しい RIFF/WAVE コンテナ
- BGM (2秒) がナレーション (6秒) より短い → 全編ループして敷かれる (中間区間の RMS で信号存在を確認)
- BGM (5秒) がナレーション (1秒) より長い → 切り詰め
- 前後フェード (端の RMS が中間より小さい)
- `bgm_gain_db` が実際に音量を減衰させる (-18dB ≈ 振幅比 0.126、理論値と比較検証)
- 非無音ナレーションへの overlay で波形が passthrough と変化する
- fail-open 分岐: BGM 0フレーム / pydub ImportError (`builtins.__import__` を monkeypatch で強制) / デコード失敗 (壊れた音声) — いずれも `mix_bgm` が例外を投げず音声のみ返すことを確認

**発見バグ (最小修正済み)**: `mix_bgm(fade_ms=0)` (フェード無効化のつもりの呼び出し) が pydub 内部の `fade_in(0)`/`fade_out(0)` で `TypeError: unsupported operand type(s) for -: 'NoneType' and 'int'` を送出し、fail-open で BGM がまるごと passthrough (無音扱い) に縮退することを発見。現行 `main.py` の呼び出しは `fade_ms` を上書きしないため本番導線には未到達だが、公開関数のシグネチャ上は妥当な呼び出しのため `mixer.py` に `if fade_ms > 0:` ガードを追加 (fade_ms<=0 のときはフェードをスキップして BGM 自体は正常に敷く)。

**カバレッジ (mixer.py, fresh 実測)**:
- Before (T48 着手前, `uv run --with pytest-cov pytest tests/ --cov=karyu_tech_news.mix.mixer`): **46%** (missing 49-68, 実ミックス経路まるごと)
- After (同コマンド, pydub 導入下): **100%** (0 missing)
- タスク指定コマンド `uv run --with pytest-cov pytest tests/test_mix*.py --cov=karyu_tech_news.mix.mixer --cov-report=term-missing -q` (glob が `test_mix*.py` のみを対象とし、`find_bgm` 系テストが `test_produce_pipeline.py` にあるため対象外) では **87%** (missing 30-33, 48 = `find_bgm` 本体 / `bgm_path=None` passthrough 行)。

**全体ゲート (fresh)**:
- `uv run pytest` → **458 passed, 1 skipped in 2.03s** (pydub 未導入のベース環境では `test_mix_mixer.py` が importorskip で 1 モジュールとして skip)
- `uv run --with pydub --with audioop-lts pytest tests/test_mix_mixer.py tests/test_produce_pipeline.py tests/test_mix_master.py -q` → **61 passed** (pydub 導入下で実ミックス経路含め全緑)
- `uv run ruff check .` → **All checks passed**
- `uv run mypy src tests` → **Success: no issues found in 71 source files**
- `git diff --check` → **clean**
