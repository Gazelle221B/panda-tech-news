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
