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
