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
