# レビュー報告

> 基準: [DESIGN.md](./DESIGN.md), [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
> 作成者: Codex (専任レビュアー / GPT codex系 high reasoning)
> 役割: WORKFLOW §14 に基づき、実装に **関与しない** 立場で品質ゲートを判定する。

実装者 (OpenCode) と同じ context で動かないこと。レビューは必ず「ファイル / 行 / テスト結果」に紐付ける。**証跡欄なしの PASS は無効**。

---

## テンプレ (タスクごとに追記)

```markdown
## T<ID> <タスク名>  (レビュー日: YYYY-MM-DD)

### 総合判定: PASS / FAIL

### 確認した証跡 (必須)

- 確認したファイル:
  - src/karyu_tech_news/<...>.py
  - tests/test_<...>.py
- 根拠とした差分/行:
  - <file>:LXX-YY (UNIQUE制約の付与)
  - <file>:LXX-YY (item_key 生成の優先順)
- 実行/確認したテスト:
  - `pytest tests/test_<...>.py -v` → all passed (TEST_LOG.md 該当エントリ参照)
- DESIGN.md との対応:
  - §4.1 を §store.repo に対応、§4 のスキーマ完全一致を確認

### 設計適合性

- DESIGN.md §<N.M> との乖離: 無 / 有 (詳細)
- 禁止事項 §7 の遵守: hash 単体 UNIQUE 不在 / .env 未commit / fail-open 実装あり

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | | | 必須修正 |
| High | | | 必須修正 |
| Medium | | | 許容 or Issue化 |
| Low | | | 任意 |

### セキュリティ / 並行性

- secret 漏洩: なし
- SQL injection 可能性: なし (SQLAlchemy パラメータバインド)
- 並行更新: Sprint 1A は単一プロセス前提 → リスク低

### テスト不足

- (必要なら追記)
```

---

## 履歴

(レビュー完了に応じて追記)

## T1 + T3(schema) プロジェクト初期化・CLIスケルトン・ソーススキーマ  (レビュー日: 2026-05-30)

### 総合判定: PASS

### 確認した証跡 (必須)

- 確認したファイル:
  - `pyproject.toml`
  - `.env.example`
  - `.gitignore`
  - `config/sources.yaml`
  - `src/karyu_tech_news/__init__.py`
  - `src/karyu_tech_news/__main__.py`
  - `src/karyu_tech_news/config.py`
  - `src/karyu_tech_news/main.py`
  - `tests/test_config.py`
  - `tests/test_cli.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
- 根拠とした差分/行:
  - `pyproject.toml:4-18` — 配布名 `panda-tech-news`、Python 3.11+、Sprint 1A の許可依存のみ。
  - `pyproject.toml:29-37` — console script `karyu` と src-layout wheel 対象。
  - `.env.example:4-16` — Sprint 1A 必須設定とログ設定のサンプル。秘密値は空。
  - `.gitignore:1-14` — `.env`、DB、生成データを git 管理外にする設定。
  - `config/sources.yaml:8-109` — 11ソース定義、9 enabled / 2 disabled、Cookie不要ルートのみ。
  - `src/karyu_tech_news/config.py:18-41` — `SourceTier` / `SourceCategory` の定義。
  - `src/karyu_tech_news/config.py:44-67` — `SourceConfig` の id / URL / tier / category 検証。
  - `src/karyu_tech_news/config.py:70-92` — `SourcesFile` の id 重複禁止、`enabled_sources()`、`by_tier()`。
  - `src/karyu_tech_news/config.py:95-138` — `Settings` と `.env` ロード。
  - `src/karyu_tech_news/main.py:61-140` — `validate-sources` の検証、集計、disabled 注記。
  - `src/karyu_tech_news/main.py:143-160` — `info` は Webhook URL を set/not set のみ表示。
  - `tests/test_config.py:23-139` — schema、重複 id、URL、実 `sources.yaml`、settings のテスト。
  - `tests/test_cli.py:14-80` — CLI help、validate 成功/失敗、secret mask のテスト。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news --help` → `version` / `validate-sources` / `info` を表示。
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest` → `24 passed in 0.14s`。
  - `uv run ruff check src tests` → `All checks passed!`。
  - `uv run mypy src` → `Success: no issues found in 4 source files`。
  - `docs/TEST_LOG.md` の T1 + T3(schema) 履歴と一致。
- DESIGN.md との対応:
  - §1 設計方針: Python 3.11+ 単一、Sprint 1A 許可依存に適合。
  - §3.1 CLI: `--help`、`validate-sources`、`version`、`info` の現段階実装に適合。
  - §3.2 内部モジュール境界: 現状は config / CLI のみで、collect/store/deliver への逆向き依存なし。
  - §7 禁止事項: `.env` 未管理、LLM/TTS/動画/YouTube/Playwright/Cookie必須ルート混入なし。

### 設計適合性

- DESIGN.md §1 / §3 / §7 との乖離: 無。
- Sprint 1A スコープ外コード混入: 無。
- `config/llm_profiles.yaml` は Sprint 1B 以降用の設定ファイルのみで、collect パイプラインからは参照されていないため ADR-0002 の境界内。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。`.env.example` は空値のみ、`info` は Webhook URL を `(set)/(not set)` でマスク。
- SQL injection 可能性: 該当なし。DB 層は未実装。
- 並行更新: 該当なし。収集・永続化層は未実装で、Sprint 1A の単一プロセス前提に反していない。

### テスト不足

- T1 + T3(schema) 範囲では追加必須テストなし。
- `collect` / `init-db` / `post-summary` は未実装であり、次タスク T4/T5/T9 以降でそれぞれテスト対象にする。

## T4 RSS/RSSHub 取得モジュール (フェッチャ + 正規化)  (レビュー日: 2026-05-31)

### 総合判定: PASS

Critical / High 指摘なし。T4 の実装範囲は DESIGN.md / IMPLEMENTATION_PLAN.md に適合しており、次工程 Ticket #4 (SQLite スキーマ + 永続化層) へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/collect/__init__.py`
  - `src/karyu_tech_news/collect/normalize.py`
  - `src/karyu_tech_news/collect/fetcher.py`
  - `tests/test_normalize.py`
  - `tests/test_fetcher.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/architecture.md`
  - `docs/domain/collection.md`
  - `docs/styleguide.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/collect/normalize.py:13-35` — DESIGN.md §3.3 と一致する `RawItem` / `FetchResult` 型。
  - `src/karyu_tech_news/collect/normalize.py:42-59` — `canonical_url_hash` の正規化と sha256 生成。
  - `src/karyu_tech_news/collect/normalize.py:62-76` — `item_key` 生成順 `external_id` → `link` → `sha256(title|published_at|source_id)`。
  - `src/karyu_tech_news/collect/normalize.py:107-150` — feedparser entry の `RawItem` 正規化、空 `item_key` 防止。
  - `src/karyu_tech_news/collect/fetcher.py:16-18` — User-Agent / 30秒 timeout / 最大2回 retry の定数。
  - `src/karyu_tech_news/collect/fetcher.py:21-26` — ADR-0004 に基づく RSSHub base URL 展開。
  - `src/karyu_tech_news/collect/fetcher.py:29-46` — httpx GET、明示 User-Agent、timeout、redirect、retry。
  - `src/karyu_tech_news/collect/fetcher.py:49-73` — bozo=1 かつ entries=0 のみ失敗扱い、entries ありは採用。
  - `src/karyu_tech_news/collect/fetcher.py:76-93` — 例外を `FetchResult(ok=False, error=...)` に包む fail-open。
  - `tests/test_normalize.py:13-99` — item_key 優先順、canonical hash、entry 正規化、FetchResult モデルの単体テスト。
  - `tests/test_fetcher.py:47-221` — RSSHub 展開、RSS/Atom 成功、bozo、timeout/retry、fail-open、User-Agent/timeout 定数の単体テスト。
  - `docs/TEST_LOG.md:75-116` — T4 実装内容・検証結果・Ticket #4 引き継ぎ。
  - `docs/PROJECT_STATE.md:8-28` — Ticket #3 完了、Ticket #4 次対象への状態更新。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest` → `48 passed in 0.20s`。
  - `uv run pytest --collect-only -q` → `test_cli.py: 8`, `test_config.py: 16`, `test_fetcher.py: 12`, `test_normalize.py: 12`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 11 source files`。
- DESIGN.md との対応:
  - §1: Python 3.11+ / feedparser + httpx / fail-open / Sprint 1A の外部依存最小化に適合。
  - §3.2: `collect` から `deliver` への逆向き依存なし。`store` も未導入で境界違反なし。
  - §3.3: `RawItem` / `FetchResult` の主要フィールドに適合。
  - §4.1: `item_key` 生成順に適合。
  - §4.2: canonical URL hash を保持用に生成。
  - §6: bozo 誤検知、timeout、retry の緩和策を実装。
  - §7: LLM/TTS/動画/YouTube/Playwright/Cookie必須ルートの混入なし。

### 設計適合性

- DESIGN.md §1 / §3.2 / §3.3 / §4.1 / §4.2 / §6 / §7 との重大な乖離: 無。
- Architecture status: CLEAR。`collect` レイヤーは `config` と正規化型に閉じており、`store` / `deliver` への逆向き依存や Sprint 1A 越境はない。
- `source_health` / `collect_runs` / `collect` CLI 統合は Ticket #4 以降の責務であり、T4 の未実装事項としては妥当。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | `src/karyu_tech_news/collect/fetcher.py:49-73` / `src/karyu_tech_news/collect/fetcher.py:76-83` | 成功時の `duration_ms` は `_parse_feed()` 内で計測されるため、HTTP GET と retry 待ち時間を含まない。`FetchResult` は「1ソース取得の所要時間」を包む値なので、将来メトリクスに使う場合に実態より短く見える。 | Ticket #4 以降で `FetchResult.duration_ms` を健全性/ログに使う前に、`fetch_one()` の開始時刻から成功/失敗の両方で計測する形へ寄せる。 |
| Low | `README.md:13-15` / `AGENTS.md:21-23` | `PROJECT_STATE.md` と `TEST_LOG.md` は T4 完了に更新済みだが、README と AGENTS のステータス欄はまだ Ticket #3 が次アクションのまま。トップレベル案内として将来エージェントを迷わせる可能性がある。 | コミット前または Ticket #4 着手前の docs cleanup で、Ticket #3 完了・次 Ticket #4 に同期する。 |

### セキュリティ / 並行性

- secret 漏洩: なし。Webhook URL 等の秘密値は T4 実装に含まれていない。
- SSRF / 任意 URL リスク: T4 は `SourceConfig` の固定 `sources.yaml` を入力とする内部バッチ処理であり、ユーザー入力 URL を直接受けない。Sprint 1A の運用前提では許容。
- SQL injection 可能性: 該当なし。DB 層は未実装。
- 並行更新: 該当なし。T4 は取得・正規化のみで SQLite 書き込みなし。
- fail-open: 取得例外は `FetchResult(ok=False, error=...)` に変換され、単一ソース失敗で呼び出し元を例外終了させない。

### テスト不足

- T4 範囲の必須テスト (feedparser モック、timeout、retry、bozo=1+entries 採用、fail-open、RSSHub URL 展開) は存在し、全パス。
- `duration_ms` が HTTP 待ち時間を含むことを固定するテストは未追加。Low 指摘として Ticket #4 以降のログ/健全性実装前に補うのが望ましい。
- RSSHub 実インスタンス疎通はローカル環境依存のため未実施。IMPLEMENTATION_PLAN の Integration Test では CI スキップ可・ローカルのみの扱いであり、T4 unit review のブロッカーではない。

## T5 SQLite スキーマ + 永続化層  (レビュー日: 2026-06-01)

### 総合判定: FAIL

High 指摘 1 件。`sources` への参照整合性が実際の SQLite 実行時に守られておらず、DESIGN.md §4 / domain/collection.md §3.1 の不変条件を満たしていない。修正後に再レビューが必要。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/store/__init__.py`
  - `src/karyu_tech_news/store/schema.py`
  - `src/karyu_tech_news/store/repo.py`
  - `src/karyu_tech_news/main.py`
  - `tests/test_store.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/domain/collection.md`
  - `docs/architecture.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/store/schema.py:25-45` — `sources` テーブルと `SourceHealth` relationship。
  - `src/karyu_tech_news/store/schema.py:47-69` — `items` テーブル、`UNIQUE(source_id, item_key)`、canonical/published indexes。
  - `src/karyu_tech_news/store/schema.py:72-83` — `source_health` テーブル、`source_id` 外部キー。
  - `src/karyu_tech_news/store/schema.py:86-98` — `collect_runs` テーブル。
  - `src/karyu_tech_news/store/repo.py:22-32` — SQLite engine 作成と `create_all()` 初期化。
  - `src/karyu_tech_news/store/repo.py:35-58` — `upsert_source()`。
  - `src/karyu_tech_news/store/repo.py:61-90` — `insert_items()` と空 `item_key` 防止。
  - `src/karyu_tech_news/store/repo.py:93-115` — `source_health` 成功/失敗更新。
  - `src/karyu_tech_news/store/repo.py:118-146` — `collect_runs` 作成/完了。
  - `src/karyu_tech_news/main.py:163-183` — `init-db` CLI。
  - `tests/test_store.py:45-224` — schema 冪等性、source upsert、dedupe、source_health、collect_run の 9 テスト。
  - `docs/TEST_LOG.md:118-168` — T5 実装内容・検証結果・引き継ぎ。
  - `docs/PROJECT_STATE.md:8-29` — Ticket #4 完了状態への更新。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest` → `57 passed in 0.44s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 15 source files`。
  - `uv run python -m karyu_tech_news init-db --db-path <tmp>/state.db` を 2 回実行 → 2 回とも成功、DB ファイル作成を確認。
  - 追加確認: 存在しない `source_id` の `RawItem` を `insert_items()` し、同じく存在しない `source_id` で `update_source_health_failure()` 後に `commit()` → `orphan_insert_count=1`, `committed_orphan_rows=yes`。
- DESIGN.md との対応:
  - §4 のテーブル構造、`UNIQUE(source_id, item_key)`、`hash` 単体 UNIQUE 禁止、index 名は概ね適合。
  - §4 の `REFERENCES sources(id)` と domain/collection.md §3.1 の「SourceHealth は Source に従属」は、SQLite 実行時の外部キー enforcement が無効なため未達。
  - §7 の Sprint 1A 越境、`.env` 混入、LLM/TTS/動画/YouTube/Playwright/Cookie 必須ルート混入はなし。

### 設計適合性

- DESIGN.md §4 の schema 形状は概ね実装されているが、SQLite の外部キー enforcement が有効化されていないため参照整合性の実効性に欠ける。
- Architecture status: BLOCK。`store` は `collect.normalize.RawItem` / `FetchResult` を import しており `architecture.md` の表では store の import 許可が config のみになっている。ただし DESIGN.md §3.2 では collect が store を import してよいという片方向依存だけを明示しており、T5 では型受け渡しのための実務上の結合として許容可能。ブロック理由は import 境界ではなく DB 参照整合性。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/store/repo.py:22-25` / `src/karyu_tech_news/store/repo.py:61-90` / `src/karyu_tech_news/store/repo.py:93-115` | SQLite では `PRAGMA foreign_keys=ON` を接続ごとに有効化しない限り `ForeignKey("sources.id")` が実際には enforcement されない。現状、存在しない `source_id` の item と source_health が commit できる。これは DESIGN.md §4 の `REFERENCES sources(id)` と domain/collection.md §3.1「SourceHealth は Source に従属」に反する。 | `create_db_engine()` で SQLAlchemy event listener により接続時 `PRAGMA foreign_keys=ON` を設定し、存在しない source への item/source_health commit が `IntegrityError` になるテストを追加する。必要なら `insert_items()` / `update_source_health_*()` 側でも source 存在チェックまたは runner での source upsert 順序を固定する。 |
| Medium | `src/karyu_tech_news/store/repo.py:118-146` / `tests/test_store.py:207-224` | `finish_collect_run()` は `run.total_sources` と `len(results)` の不一致を検出せず、実行記録が実処理数と食い違う状態を保存できる。domain/collection.md §3.3 は「集計値は実際の処理結果と一致する」と定義している。 | `finish_collect_run()` で `total_sources = len(results)` に更新するか、不一致時に `ValueError` にする。どちらかをテストで固定する。 |
| Low | `src/karyu_tech_news/store/schema.py:54` | DESIGN.md §4 の SQL 例は `idx_items_published ON items(published_at DESC)` だが、実装は通常の ascending index。現時点では機能不具合ではないが、最新記事順クエリの意図とズレる。 | 必要なら `Index("idx_items_published", Item.published_at.desc())` 相当に寄せる。少なくとも設計上「DESC は例示であり昇順 index で十分」なら文書側を明確化する。 |
| Low | `src/karyu_tech_news/main.py:148` | `info` コマンドの Sprint 表示がまだ `Ticket #1 + #2 schema` のまま。T5 の実装完了状態とユーザー向け CLI 表示がズレている。 | `Sprint phase: 1A` のようなチケット非依存表現へ変更するか、現在の完了チケットに同期する。 |

### セキュリティ / 並行性

- secret 漏洩: なし。
- SQL injection: SQLAlchemy ORM / expression API 利用で直接文字列連結 SQL はなし。
- SQLite integrity: High 指摘の通り、外部キー enforcement が無効なため orphan row を防げない。
- 並行更新: Sprint 1A は単一プロセス前提。`insert_items()` の事前 SELECT → INSERT は並行 collect では race しうるが、architecture.md §1.1 で並行 collect は非ゴールのためブロッカーではない。

### テスト不足

- `PRAGMA foreign_keys=ON` と外部キー違反時の `IntegrityError` テストが不足。
- `finish_collect_run()` の集計整合性テストが不足。
- `init-db` CLI の冪等性は手動確認済みだが、CLI レベルの自動テストは未追加。現時点では repo/schema の unit test で最低限は満たす。

## T5 SQLite スキーマ + 永続化層 再レビュー  (レビュー日: 2026-06-01)

### 総合判定: PASS

初回レビューの High / Medium / Low 指摘はすべて対応済み。Critical / High / Medium 指摘なし。Ticket #4 (T5) は次工程 Antigravity QA へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/store/schema.py`
  - `src/karyu_tech_news/store/repo.py`
  - `src/karyu_tech_news/main.py`
  - `tests/test_store.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
- 初回レビュー指摘への対応:
  - High: `src/karyu_tech_news/store/repo.py:22-33` — SQLAlchemy `connect` event で `PRAGMA foreign_keys=ON` を設定。
  - High: `tests/test_store.py:227-255` — orphan item / orphan source_health が `IntegrityError` になるテストを追加。
  - Medium: `src/karyu_tech_news/store/repo.py:141-153` — `run.total_sources` と `len(results)` の不一致時に `ValueError`。
  - Medium: `tests/test_store.py:257-265` — total_sources 不一致の回帰テストを追加。
  - Low: `src/karyu_tech_news/store/schema.py:55` — `idx_items_published` を `published_at DESC` で作成。
  - Low: `src/karyu_tech_news/main.py:143-160` — `info` の Sprint 表示を Ticket #4 SQLite に同期。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest` → `60 passed in 0.37s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 15 source files`。
  - `uv run python -m karyu_tech_news init-db --db-path <tmp>/state.db` を 2 回実行 → 2 回とも成功、DB ファイル作成を確認。
  - 追加確認: 存在しない `source_id` の item / source_health commit → `orphan_item=blocked`, `orphan_health=blocked`。
  - 追加確認: `sqlite_master` の `idx_items_published` DDL → `CREATE INDEX idx_items_published ON items (published_at DESC)`。
  - `uv run python -m karyu_tech_news info` → `Sprint phase: 1A (Ticket #4 SQLite)`。

### 設計適合性

- DESIGN.md §4 の `REFERENCES sources(id)` は SQLite 実行時にも enforcement されるようになった。
- domain/collection.md §3.1 の「SourceHealth は Source に従属」は外部キー制約で保証される。
- domain/collection.md §3.3 の collect_run 集計整合性は `total_sources` 不一致の `ValueError` で保護された。
- Architecture status: CLEAR。初回レビューの BLOCK 理由は解消済み。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。
- SQL injection: SQLAlchemy ORM / expression API 利用で直接文字列連結 SQL なし。
- SQLite integrity: orphan item / source_health は `IntegrityError` で拒否されることを確認済み。
- 並行更新: Sprint 1A は単一プロセス前提。`UNIQUE(source_id, item_key)` による最終防衛は維持されている。

### テスト不足

- T5 再レビュー範囲では追加必須テストなし。
- `init-db` CLI の冪等性は手動確認済み。CLI 自動テストは将来の CLI integration ticket で扱う。

## T6 seen 管理 / dedupe  (レビュー日: 2026-06-01)

### 総合判定: PASS

Critical / High / Medium / Low 指摘なし。Ticket #5 (T6) は、既存 `insert_items()` の dedupe 仕様を追加テストで固定する範囲として DESIGN.md / domain/collection.md に適合している。次工程 Antigravity QA へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `tests/test_dedupe.py`
  - `src/karyu_tech_news/store/repo.py`
  - `src/karyu_tech_news/store/schema.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/domain/collection.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/store/schema.py:52-60` — `UNIQUE(source_id, item_key)` と `source_id` / `item_key` の非 NULL 定義。
  - `src/karyu_tech_news/store/repo.py:69-98` — `insert_items()` が既存 `(source_id, item_key)` を検索し、既存 item を更新せず新規のみ追加。
  - `tests/test_dedupe.py:62-83` — 同一 source + 同一 key の再投入で 1 行に留まる。
  - `tests/test_dedupe.py:86-121` — 異なる source の同一 key は別レコードとして保存される。
  - `tests/test_dedupe.py:124-154` — 同一 source の異なる key は別レコードとして保存される。
  - `tests/test_dedupe.py:157-205` — バッチ内で既存 item と新規 item が混在しても、新規のみ追加し既存 item は更新しない。
  - `tests/test_dedupe.py:208-213` — 空バッチは 0 件を返す。
  - `docs/TEST_LOG.md:210-252` — T6 実装内容・検証結果・引き継ぎ。
  - `docs/PROJECT_STATE.md:28-69` — Ticket #5 完了状態への更新。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_dedupe.py -q` → `5 passed`。
  - `uv run pytest --collect-only -q` → `test_dedupe.py: 5` を含む合計 65 tests。
  - `uv run pytest` → `65 passed in 0.39s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 16 source files`。
  - 追加確認: 同一バッチ内に同じ source + key が 2 件ある場合も `same_batch_count=1`, `same_batch_rows=1` で既存仕様どおり dedupe される。

### 設計適合性

- DESIGN.md §4 の `UNIQUE(source_id, item_key)` による source 内 dedupe に適合。
- domain/collection.md §3.2 の「クロスソース重複は 1A では別レコードとして許容」に適合。
- `hash` 単体 UNIQUE は追加されていない。
- Architecture status: CLEAR。T6 は既存 store 層の仕様固定テストであり、新規レイヤーや逆向き依存はない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。テストデータのみ。
- SQL injection: 該当なし。既存 SQLAlchemy query の仕様固定テスト。
- 並行更新: Sprint 1A は単一プロセス前提。`UNIQUE(source_id, item_key)` による最終防衛は維持されている。

### テスト不足

- T6 範囲では追加必須テストなし。
- `insert_items()` の同一バッチ内重複は手元で追加確認済み。必要なら将来の回帰テストとして `tests/test_dedupe.py` に固定してもよいが、今回の PASS 条件ではブロッカーではない。

## T7 source_health 更新  (レビュー日: 2026-06-01)

### 総合判定: PASS

Critical / High / Medium / Low 指摘なし。Ticket #6 (T7) は、既存 `update_source_health_success()` / `update_source_health_failure()` の状態遷移を追加テストで固定する範囲として DESIGN.md / domain/collection.md に適合している。次工程 Antigravity QA へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `tests/test_health.py`
  - `src/karyu_tech_news/store/repo.py`
  - `src/karyu_tech_news/store/schema.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/domain/collection.md`
  - `docs/requirements-v1.0.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/store/schema.py:73-84` — `source_health` が `source_id` 主キー / `sources.id` 外部キーと健全性カラムを持つ。
  - `src/karyu_tech_news/store/repo.py:101-110` — 成功時に `last_success_at` を更新し、`consecutive_failures` と直近エラー状態をリセット。
  - `src/karyu_tech_news/store/repo.py:113-123` — 失敗時に `last_failure_at`、`consecutive_failures + 1`、`last_error` を更新。
  - `tests/test_health.py:54-65` — 初回成功時のレコード作成と成功状態を検証。
  - `tests/test_health.py:68-79` — 初回失敗時のレコード作成と失敗状態を検証。
  - `tests/test_health.py:82-105` — 連続失敗後の成功リセットを検証。
  - `tests/test_health.py:108-128` — 連続失敗の累積と警告閾値到達を検証。
  - `tests/test_health.py:131-169` — `last_error` と成功/失敗タイムスタンプ更新を検証。
  - `tests/test_health.py:172-196` — 成功→失敗→成功→失敗の状態遷移サイクルを検証。
  - `docs/TEST_LOG.md:254-298` — T7 実装内容・検証結果・T8 への引き継ぎ。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_health.py -q` → `8 passed`。
  - `uv run pytest --collect-only -q` → `test_health.py: 8` を含む合計 73 tests。
  - `uv run pytest` → `73 passed in 0.82s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 17 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "<<<<<<<|=======|>>>>>>>" .` → conflict marker なし。

### 設計適合性

- requirements-v1.0.md FR-050 の「成功時 `last_success_at` 更新、`consecutive_failures=0`」に適合。
- requirements-v1.0.md FR-051 の「失敗時 `last_failure_at` 更新、`consecutive_failures += 1`、`last_error` 保存」に適合。
- requirements-v1.0.md FR-052 / domain/collection.md §5.1 の `consecutive_failures >= 3` 警告閾値をテストで固定している。
- SourceHealth は Source に従属する設計を維持しており、外部キー enforcement は T5 再レビュー済み。
- Architecture status: CLEAR。T7 は既存 store 層の仕様固定テストであり、新規依存や Sprint 1A スコープ外実装はない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。テストデータのみ。
- SQL injection: 該当なし。既存 SQLAlchemy ORM 更新関数の仕様固定テスト。
- SQLite integrity: `SourceHealth` の orphan 拒否は既存 `tests/test_store.py` と T5 再レビューで確認済み。
- 並行更新: Sprint 1A は単一プロセス前提。複数 collect の同時更新は非ゴールであり、今回のブロッカーではない。

### テスト不足

- T7 範囲では追加必須テストなし。
- `FetchResult.ok` に基づく実際の `source_health` 呼び分けは Ticket #7 (T8) collect runner 側で検証する。

## T8 collect runner (fail-open 統合)  (レビュー日: 2026-06-01)

### 総合判定: FAIL

High 指摘 1 件。通常の品質ゲートは通っているが、実際の SQLAlchemy DB エラー時に `run_collect()` が停止し、後続ソースへ進めない。Ticket #7 (T8) の中核である fail-open 要件 (FR-060) に反するため、修正後に再レビューが必要。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/collect/runner.py`
  - `tests/test_runner_fail_open.py`
  - `src/karyu_tech_news/collect/fetcher.py`
  - `src/karyu_tech_news/store/repo.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/domain/collection.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/requirements-v1.0.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/collect/runner.py:24-73` — `run_collect()` が `fetch_one()` → `insert_items()` → `source_health` 更新 → `finish_collect_run()` を統合。
  - `src/karyu_tech_news/collect/runner.py:41-63` — DB エラーを捕捉して失敗 `FetchResult` に変換しようとしているが、SQLAlchemy の failed transaction を rollback していない。
  - `tests/test_runner_fail_open.py:244-287` — DB エラー継続テストは `insert_items()` を通常 `Exception` でモックしており、実 DB flush/commit 失敗後の `PendingRollbackError` を検出できない。
  - `docs/architecture.md:87-106` — 1 ソースの例外でループを抜けてはならない。
  - `docs/IMPLEMENTATION_PLAN.md:51-53` — T8 は 1 ソース例外でも他ソース完走 / `collect_runs` 追加が合格条件。
  - `docs/requirements-v1.0.md:515-519` — FR-060: 1 つのソース取得が失敗してもパイプライン全体を止めない。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_runner_fail_open.py -q` → `6 passed`。
  - `uv run pytest` → `79 passed in 0.68s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 19 source files`。
  - 追加再現: 実 SQLite の外部キー違反を `insert_items()` commit で発生させると、`run_collect()` は `PendingRollbackError` を投げて停止。`fetch_one()` 呼び出しは 2 回で止まり、3 ソース目へ進まない。

### 設計適合性

- `fetch_one()` 由来の `FetchResult(ok=False)` については fail-open できている。
- `insert_items()` が通常例外を投げるモックケースについては fail-open できている。
- しかし、実 DB flush/commit 失敗時は SQLAlchemy `Session` が rollback 必須状態になり、次の `update_source_health_failure()` / `session.commit()` が `PendingRollbackError` で失敗する。
- Architecture status: BLOCK。T8 の中核要件である「1ソースの例外でループを抜けない」が、実 DB エラーで破れる。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/collect/runner.py:53-56` / `tests/test_runner_fail_open.py:252-264` | DB エラー捕捉後に `session.rollback()` せず同じ `Session` で `update_source_health_failure()` と `commit()` を実行している。実際の `IntegrityError` などでは Session が failed transaction 状態になり、`PendingRollbackError` で runner 全体が停止する。現行テストは `insert_items()` を通常例外でモックしているため、この失敗を検出できない。 | `except` ブロックの先頭で `session.rollback()` してから source_health failure を記録する。さらに、実 SQLite で commit 時の `IntegrityError` を起こす回帰テストを追加し、該当ソースは failed、後続ソースは処理継続、`collect_runs.finished_at` が埋まることを確認する。 |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。テストデータのみ。
- SQL injection: SQLAlchemy ORM / expression API 利用で直接文字列連結 SQL なし。
- DB 整合性: 外部キー enforcement 自体は T5 で有効化済み。ただし、その enforcement による実エラーを runner が fail-open 処理できていない。
- 並行更新: Sprint 1A は単一プロセス前提。今回のブロッカーは並行性ではなくトランザクション復旧。

### テスト不足

- 実 DB の flush/commit 失敗を使った fail-open 回帰テストが不足。
- `fetch_one()` 自体が予期せず例外を投げた場合の runner レベル保護は未検証。ただし現在の `fetch_one()` は内部で例外を `FetchResult(ok=False)` に包むため、High 指摘の対象は DB エラー復旧に限定する。

## T8 collect runner (fail-open 統合) 再レビュー  (レビュー日: 2026-06-01)

### 総合判定: FAIL

前回 High 指摘のうち、DB エラー後に `session.rollback()` して後続ソースへ進む点は改善済み。ただし、実 DB の flush/commit 失敗では `insert_items()` が返した件数を commit 前に `total_new_items` へ加算しているため、rollback された未保存 item まで `collect_runs.new_items` に含まれる。`new_items` は Persisted のみを数える設計であり、収集サマリーの基礎データが誤るため修正が必要。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/collect/runner.py`
  - `tests/test_runner_fail_open.py`
  - `src/karyu_tech_news/store/repo.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/domain/collection.md`
  - `docs/IMPLEMENTATION_PLAN.md`
- 修正確認:
  - `src/karyu_tech_news/collect/runner.py:53-57` — DB エラー捕捉時に `session.rollback()` が追加された。
  - `tests/test_runner_fail_open.py:290-343` — `IntegrityError` 相当の回帰テストが追加された。
- 追加再現:
  - 実 SQLite の外部キー違反を `insert_items()` 後の flush で発生させると、`run_collect()` は停止せず 3 ソース目まで処理する。
  - 同じ再現で実際に保存された `items` は 2 件だが、`collect_runs.new_items` は 3 になる。
  - 再現出力: `run 2 1 3 3 True`, `fetch_calls 3`, `items 2`。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_runner_fail_open.py -q` → `7 passed`。
  - `uv run pytest` → `80 passed in 0.82s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 19 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- fail-open の「停止しない」は修正済み。
- しかし domain/collection.md §5.2 は `collect_runs.new_items` を Persisted のみと定義している。rollback された failed source の item を `new_items` に含めるのは設計不適合。
- domain/collection.md §3.3 の「集計値は実際の処理結果と一致する」にも反する。
- Architecture status: BLOCK。runner は完走するが、collect_run 集計が実保存状態と食い違う。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/collect/runner.py:43-46` / `src/karyu_tech_news/collect/runner.py:53-64` / `tests/test_runner_fail_open.py:290-343` | `total_new_items += new_count` が commit 前に実行される。`insert_items()` が pending item を追加して戻った後、`update_source_health_success()` の autoflush や `session.commit()` で実 DB エラーが起きると、その item は rollback されるが `total_new_items` だけ増えたままになる。追加テストは `insert_items()` をモックして `IntegrityError` を投げるため、実 DB の flush 失敗後に `new_items` が過大計上されるケースを検出できない。 | `total_new_items` への加算を `session.commit()` 成功後に移動する、または失敗時に当該 `new_count` を加算しない構造にする。回帰テストはモック例外だけでなく、実 SQLite の FK/UNIQUE などで flush/commit 失敗を起こし、保存済み `Item` 件数と `run.new_items` が一致することを確認する。 |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。テストデータのみ。
- SQL injection: SQLAlchemy ORM / expression API 利用で直接文字列連結 SQL なし。
- DB 整合性: 実 DB エラー時の transaction 復旧は改善済み。ただし collect_run 集計の整合性が未解消。
- 並行更新: Sprint 1A は単一プロセス前提。今回のブロッカーは並行性ではなく集計整合性。

### テスト不足

- 実 SQLite の flush/commit 失敗で `run.new_items` が保存済み item 件数と一致することを確認する回帰テストが不足。
- 追加された `test_run_collect_real_sqlite_integrity_error` は名前とコメントに「実SQLite」とあるが、実際には `insert_items()` をモックしているため、今回の過大計上を検出できない。

## T8 collect runner (fail-open 統合) 再々レビュー  (レビュー日: 2026-06-01)

### 総合判定: PASS

前回までの High 指摘は解消済み。実 DB エラー時も runner は後続ソースへ進み、`collect_runs.new_items` は保存済み Item 件数と一致する。Critical / High / Medium / Low 指摘なし。Ticket #7 (T8) は次工程 Antigravity QA へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/collect/runner.py`
  - `tests/test_runner_fail_open.py`
  - `src/karyu_tech_news/store/repo.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/domain/collection.md`
  - `docs/IMPLEMENTATION_PLAN.md`
- 修正確認:
  - `src/karyu_tech_news/collect/runner.py:43-46` — `total_new_items += new_count` が `session.commit()` 成功後に移動した。
  - `src/karyu_tech_news/collect/runner.py:53-57` — DB エラー捕捉時に `session.rollback()` してから source_health failure を記録する。
  - `tests/test_runner_fail_open.py:346-391` — commit 失敗時に `run.new_items` が保存済み Item 件数と一致する回帰テストを追加。
- 追加再現:
  - 実 SQLite の外部キー違反を `insert_items()` 後の flush で発生させても、`run_collect()` は 3 ソース目まで処理する。
  - 同じ再現で `collect_runs.new_items` は 2、保存済み `items` も 2。
  - 再現出力: `run 2 1 3 2 True`, `fetch_calls 3`, `items 2`。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_runner_fail_open.py -q` → `8 passed`。
  - `uv run pytest` → `81 passed in 1.06s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 19 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- requirements-v1.0.md FR-060 の「1つのソース取得が失敗しても、パイプライン全体を止めない」に適合。
- domain/collection.md §5.2 の「Deduped は新規としてカウントしない / `collect_runs.new_items` は Persisted のみ加算」に適合。
- domain/collection.md §3.3 の「集計値は実際の処理結果と一致する」を満たす。
- Architecture status: CLEAR。runner は `fetch_one()` / `insert_items()` / `source_health` / `collect_runs` を最小統合しており、Sprint 1A スコープ外依存はない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。テストデータのみ。
- SQL injection: SQLAlchemy ORM / expression API 利用で直接文字列連結 SQL なし。
- DB 整合性: 実 DB エラー時の rollback と collect_run 集計整合性を確認済み。
- 並行更新: Sprint 1A は単一プロセス前提。`insert_items()` の SELECT → INSERT 競合は非ゴール。

### テスト不足

- T8 範囲では追加必須テストなし。
- CLI `collect` への結合は Ticket #10、Discord サマリー連携は Ticket #8/T9 で扱う。

## T9 Discord Webhook サマリー投稿  (レビュー日: 2026-06-01)

### 総合判定: FAIL

High 指摘 1 件。`post_summary()` の fail-open と Webhook 本文投稿は概ね要件に沿っているが、`format_summary()` の Tier/カテゴリ集計が対象 `CollectRun` の終了時刻で上限を切っていない。そのため、過去 run を指定してサマリーを作ると、後続 run の item まで混ざり、`new_items` と Tier/カテゴリ内訳が食い違う。Discord サマリーは T9 の主成果物なので、修正後に再レビューが必要。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/deliver/discord.py`
  - `src/karyu_tech_news/deliver/__init__.py`
  - `tests/test_discord.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/requirements-v1.0.md`
  - `docs/show-format.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/DESIGN.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/deliver/discord.py:19-74` — `format_summary()` が Discord 収集サマリー本文を生成。
  - `src/karyu_tech_news/deliver/discord.py:49-51` — item 集計が `Item.fetched_at >= run.started_at` のみで、`run.finished_at` 以前に限定していない。
  - `src/karyu_tech_news/deliver/discord.py:77-94` — `post_summary()` は HTTP POST 失敗時に例外を外へ出さず `False` を返す。
  - `tests/test_discord.py:62-115` — 基本サマリー形式を検証。
  - `tests/test_discord.py:118-146` — `consecutive_failures >= 3` の警告表示を検証。
  - `tests/test_discord.py:149-179` — Webhook 成功/失敗/空 URL を検証。
  - `tests/test_discord.py:182-208` — JST 変換を検証。
  - `docs/requirements-v1.0.md:529-539` — FR-070/071/072。
  - `docs/requirements-v1.0.md:946-968` / `docs/show-format.md:83-105` — Sprint 1A サマリー形式。
- 追加再現:
  - run1: `new_items=1`, `finished_at=started+10秒`。
  - run1 終了後に同一 source の item を 1 件追加。
  - `format_summary(session, run1)` の出力は `📥 新規アイテム: 1件` なのに、`Tier1 公式: 2件` / `AI: 2` となる。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_discord.py -q` → `6 passed`。
  - `uv run pytest` → `87 passed in 0.84s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 22 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- FR-070: Webhook 投稿関数は実装済み。
- FR-071: HTTP 例外/失敗時に外へ例外を出さない fail-open は満たしている。
- FR-072: 添付なし、Markdown 本文のみの投稿で適合。
- ただし DESIGN.md §3.1 には `post-summary [--run-id <id>]` があり、`format_summary(session, run)` は引数の `CollectRun` に閉じたサマリーを返す必要がある。現在は run 終了後の item を含めるため、過去 run のサマリーが不正確。
- Architecture status: BLOCK。投稿の主データであるサマリー集計が run 境界を守れていない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/deliver/discord.py:49-51` / `tests/test_discord.py:62-115` | Tier/カテゴリ集計が `Item.fetched_at >= run.started_at` のみで、`run.finished_at` 以前に限定されていない。過去 run のサマリーを生成すると、後続 run で保存された item も集計され、`new_items` と内訳が不一致になる。 | `run.finished_at` がある場合は `Item.fetched_at <= run.finished_at` も条件に入れる。回帰テストとして、対象 run 終了後に別 item を追加しても Tier/カテゴリ集計に含まれないこと、少なくとも `new_items` と内訳が食い違わないことを確認する。 |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。Webhook URL は引数で受け取り、テスト URL のみ。
- SQL injection: SQLAlchemy expression API 利用で直接文字列連結 SQL なし。
- Webhook fail-open: `httpx.post()` / `raise_for_status()` の例外を捕捉して `False` を返す。
- 並行性: Sprint 1A は単一プロセス前提。今回のブロッカーは並行性ではなく run 境界の集計条件。

### テスト不足

- 対象 run 終了後の item が Tier/カテゴリ集計に混ざらないことを確認するテストが不足。
- HTTP 4xx/5xx の `raise_for_status()` 例外テストは未追加だが、実装上は `except` で `False` になるため、今回のブロッカーではない。

## T9 Discord Webhook サマリー投稿 再レビュー  (レビュー日: 2026-06-01)

### 総合判定: PASS

前回 High 指摘は解消済み。`format_summary()` は対象 `CollectRun` の `started_at` 以降かつ `finished_at` 以前の item のみを Tier/カテゴリ集計に含めるようになり、過去 run のサマリーに後続 item が混ざらない。Critical / High / Medium / Low 指摘なし。Ticket #8 (T9) は次工程 Antigravity QA へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/deliver/discord.py`
  - `src/karyu_tech_news/deliver/__init__.py`
  - `tests/test_discord.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/requirements-v1.0.md`
  - `docs/show-format.md`
  - `docs/IMPLEMENTATION_PLAN.md`
- 修正確認:
  - `src/karyu_tech_news/deliver/discord.py:49-52` — item 集計条件に `Item.fetched_at <= run.finished_at` が追加された。
  - `tests/test_discord.py:211-253` — run 終了後に保存された item が Tier/カテゴリ集計に含まれない回帰テストを追加。
- 追加再現:
  - run1: `new_items=1`, `finished_at=started+10秒`。
  - run1 終了後に同一 source の item を 1 件追加。
  - `format_summary(session, run1)` は `📥 新規アイテム: 1件`, `Tier1 公式: 1件`, `AI: 1` を出力し、後続 item を混ぜない。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_discord.py -q` → `7 passed`。
  - `uv run pytest` → `88 passed in 0.87s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 22 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- FR-070: Discord Webhook への収集サマリー投稿関数がある。
- FR-071: Webhook 投稿失敗時も例外を外へ出さず `False` を返す fail-open 挙動。
- FR-072: 添付なし、Markdown 本文投稿のみ。
- requirements-v1.0.md §14.1 / show-format.md §7 の Sprint 1A サマリー形式に適合。
- Architecture status: CLEAR。`deliver` は `store` を読み取るだけで、逆向き依存や Sprint 1A スコープ外実装はない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。Webhook URL は引数で受け取り、テスト URL のみ。
- SQL injection: SQLAlchemy expression API 利用で直接文字列連結 SQL なし。
- Webhook fail-open: `httpx.post()` / `raise_for_status()` の例外を捕捉して `False` を返す。
- 並行性: Sprint 1A は単一プロセス前提。T9 範囲で追加ブロッカーなし。

### テスト不足

- T9 範囲では追加必須テストなし。
- `post-summary` CLI / `collect --post` への結合は Ticket #9 (T10) で扱う。

## T10 CLI統合 (`collect` コマンド) 独立レビュー  (レビュー日: 2026-06-02)

### 総合判定: FAIL

`collect` コマンドは追加され、`--dry-run` / `--post` と Discord 投稿の fail-open は基本的に動く。ただし DESIGN.md §3.1 の公開CLI契約にある `collect [--dry-run] [--source <id>]` の `--source` が未実装で、指定実行すると Typer が `No such option: --source` で終了する。T10はCLI統合タスクであり、公開インターフェース欠落のため次工程 Antigravity QA へは進めない。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/main.py`
  - `tests/test_cli_integration.py`
  - `src/karyu_tech_news/config.py`
  - `src/karyu_tech_news/collect/runner.py`
  - `docs/DESIGN.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
- 根拠とした差分/行:
  - `src/karyu_tech_news/main.py:186-214` — `collect` のオプションに `--sources`, `--db-path`, `--post`, `--dry-run` はあるが `--source` がない。
  - `src/karyu_tech_news/main.py:240-261` — 有効ソース全件を対象にし、単一 source id で絞り込む経路がない。
  - `tests/test_cli_integration.py:60-65` — help テストは `--post` / `--dry-run` のみ確認し、`--source` を確認していない。
  - `tests/test_cli_integration.py:124-147` — 成功系は `run_collect()` をモックして出力だけ検証しており、通常実行で `items` / `source_health` / `collect_runs` が更新されることを確認していない。
  - `docs/DESIGN.md:37-42` — CLI契約に `collect [--dry-run] [--source <id>]` が明記されている。
  - `docs/IMPLEMENTATION_PLAN.md:53-55` — T10テスト方針は「ドライランでDB書き込みなし / 通常実行で全テーブル更新」。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news collect --help` → `--source` なし。
  - `uv run python -m karyu_tech_news collect --source test-source --dry-run` → exit 2、`No such option: --source`。
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run pytest tests/test_cli_integration.py -q` → `9 passed`。
  - `uv run pytest` → `97 passed in 1.05s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 23 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- `collect` コマンド追加、`--post` による Discord サマリー投稿、Webhook 失敗時の fail-open は概ね適合。
- `DISCORD_WEBHOOK_URL` / `RSSHUB_BASE_URL` の設定読み込みは `Settings` と整合している。
- ただし DESIGN.md §3.1 の `--source <id>` が欠落しており、CLI公開契約を満たしていない。
- Architecture status: BLOCK。CLI統合タスクの公開オプションが欠落している。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/main.py:186-214` / `docs/DESIGN.md:37-42` | `collect` コマンドに設計上必須の `--source <id>` がない。単一ソースだけを収集する運用・デバッグ経路が使えず、`collect --source test-source --dry-run` は exit 2 になる。 | `source_id: str | None = typer.Option(None, "--source", help=...)` を追加し、有効ソースを指定IDに絞り込む。存在しないIDまたは disabled のID指定時は分かるエラーで exit 1。`--dry-run` と通常実行の両方で、対象ソースが1件に絞られるテストを追加する。 |
| Medium | `tests/test_cli_integration.py:68-147` / `docs/IMPLEMENTATION_PLAN.md:53-55` | T10の受け入れテスト方針である「dry-runでDB書き込みなし / 通常実行で全テーブル更新」が実証されていない。現テストはdry-run後のDB状態を見ず、通常成功系は `run_collect()` をモックしているため、`collect` CLIから実際に `sources` / `items` / `source_health` / `collect_runs` が更新されることを保証しない。 | dry-run後に `sources` / `items` / `source_health` / `collect_runs` が0件のまま、通常実行では `fetch_one` 相当をモックして実 runner を通し、4テーブルが期待通り更新される統合テストを追加する。 |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。`info` は Webhook URL を set/not set 表示に留めている。
- SQL injection: CLI入力の `db_path` はSQLiteファイルパスとして渡され、SQL文字列連結は見当たらない。
- Webhook fail-open: `post_summary()` の `False` を警告表示に留め、収集完了自体は失敗扱いにしていない。
- 並行性: Sprint 1A は単一プロセス前提。今回のブロッカーは並行性ではなくCLI契約欠落。

### テスト不足

- `collect --source <id>` の help表示、dry-run、通常実行、未知ID、disabled ID のテストが不足。
- dry-runがDBへ何も書かないことのDB状態検証が不足。
- CLIから実 runner 経由で `items` / `source_health` / `collect_runs` まで更新される統合テストが不足。

## T10 CLI統合 (`collect` コマンド) 再レビュー  (レビュー日: 2026-06-02)

### 総合判定: FAIL

前回指摘のうち `--source` オプション追加とDB更新の統合テスト追加は確認できた。ただし実装が「複数指定可能」を掲げた状態で、指定IDの一部が未知または disabled の場合に、そのIDを黙って無視して残りの有効ソースだけで成功終了する。CLIで明示指定したソースが収集されなかったことを検知できず、運用・デバッグ用途の `--source` として危険な挙動のため、T10はまだ次工程 Antigravity QA へ進めない。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/main.py`
  - `tests/test_cli_integration.py`
  - `docs/DESIGN.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
- 修正確認:
  - `src/karyu_tech_news/main.py:203-207` — `--source` オプションが追加され、複数指定可能になった。
  - `src/karyu_tech_news/main.py:250-258` — `source_ids` 指定時に enabled ソースへフィルタする。
  - `tests/test_cli_integration.py:280-324` — `--source` の単一指定と単一未知IDのテストを追加。
  - `tests/test_cli_integration.py:327-353` — dry-run 後に `sources` / `items` / `collect_runs` が0件であることを確認。
  - `tests/test_cli_integration.py:356-411` — `fetch_one` のみモックして実 runner 経由のDB更新を確認。
- 追加再現:
  - `uv run python -m karyu_tech_news collect --source qbitai-feed --source nonexistent-source --dry-run` → exit 0、`qbitai-feed` のみ表示。
  - `uv run python -m karyu_tech_news collect --source qbitai-feed --source jiqizhixin-rss --dry-run` → exit 0、disabled の `jiqizhixin-rss` を無視して `qbitai-feed` のみ表示。
  - `uv run python -m karyu_tech_news collect --source nonexistent-source --dry-run` → exit 1。単独未知IDはエラーになる。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news collect --help` → `--source` 表示あり。
  - `uv run pytest tests/test_cli_integration.py -q` → `13 passed`。
  - `uv run pytest` → `101 passed in 1.06s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 23 source files`。
  - `git ls-files -u` + `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → unmerged file / conflict marker なし。

### 設計適合性

- DESIGN.md §3.1 の `collect [--dry-run] [--source <id>]` は、単一ID指定では実装された。
- T10テスト方針の「通常実行で全テーブル更新」は、`fetch_one` のみモックして実DB更新を確認するテストにより改善された。
- ただし現在のCLIは `--source` を複数指定可能と明示しており、複数指定時に未知ID/disabled IDを黙って無視する。指定したソースだけを収集するというCLI契約に対して部分成功が不可視になる。
- Architecture status: BLOCK。明示指定された入力の一部を黙って捨てる挙動は、運用時の誤収集・誤検証につながる。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/main.py:250-258` / `tests/test_cli_integration.py:280-324` | `--source` 複数指定時、指定IDの一部が未知または disabled でも、少なくとも1件 enabled に一致すれば exit 0 で進む。例: `--source qbitai-feed --source nonexistent-source --dry-run` が成功し、未知IDを無視する。 | `source_ids` が指定された場合は、指定ID集合と enabled ID集合を突合し、未一致IDが1件でもあれば exit 1 で明示する。disabled ID も「指定されたが enabled ではない」ためエラーに含める。回帰テストとして valid+unknown、valid+disabled の混在指定が失敗することを追加する。 |
| Medium | `tests/test_cli_integration.py:327-353` | dry-run のDB未書き込み確認が `sources` / `items` / `collect_runs` のみで、前回要求した `source_health` が未確認。実装上は作成されないはずだが、受け入れ条件の証跡として不足している。 | dry-runテストで `source_health` も0件であることを確認する。 |
| Low | `tests/test_cli_integration.py:60-65` | helpテストが `--source` 表示を確認していない。実CLIでは表示されているが、公開オプションの回帰検知として弱い。 | `test_collect_help` に `assert "--source" in result.output` を追加する。 |

### セキュリティ / 並行性

- secret 漏洩: なし。Webhook URL は出力されず set/not set または投稿結果のみ。
- SQL injection: SQLAlchemy API と固定クエリを使っており、ユーザー入力をSQL文字列に連結していない。
- Webhook fail-open: T10範囲では維持されている。
- 並行性: Sprint 1A は単一プロセス前提。今回のブロッカーは並行性ではなくCLI入力検証。

### テスト不足

- `--source` 複数指定で valid+unknown が失敗するテストが不足。
- `--source` 複数指定で valid+disabled が失敗するテストが不足。
- dry-run の `source_health` 未書き込み確認が不足。

## T10 CLI統合 (`collect` コマンド) 再々レビュー  (レビュー日: 2026-06-02)

### 総合判定: PASS

前回 High 指摘は解消済み。`--source` 複数指定時に未知IDまたは disabled ID が1件でも含まれる場合は exit 1 で明示エラーになり、有効IDのみの場合は dry-run / collect 対象が期待通り絞り込まれる。T10のCLI統合は次工程 Antigravity QA へ進行可能。

### 確認した証跡 (必須)

- 確認したファイル:
  - `src/karyu_tech_news/main.py`
  - `tests/test_cli_integration.py`
  - `docs/TEST_LOG.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/IMPLEMENTATION_PLAN.md`
- 修正確認:
  - `src/karyu_tech_news/main.py:250-260` — `source_ids` 指定時、enabled ID集合と突合し、未一致IDを `Invalid or disabled source IDs` として exit 1 にする。
  - `tests/test_cli_integration.py:334-352` — valid+unknown の混在指定が exit 1 になることを確認。
  - `tests/test_cli_integration.py:355-371` — disabled source 指定が exit 1 になることを確認。
  - `tests/test_cli_integration.py:374-399` — valid source の複数指定が正常に動作することを確認。
  - `tests/test_cli_integration.py:430-485` — `fetch_one` のみモックし、実 runner 経由で `sources` / `items` / `source_health` / `collect_runs` が更新されることを確認。
- 追加再現:
  - `uv run python -m karyu_tech_news collect --source qbitai-feed --dry-run` → exit 0、`qbitai-feed` のみ表示。
  - `uv run python -m karyu_tech_news collect --source qbitai-feed --source nonexistent-source --dry-run` → exit 1、`Invalid or disabled source IDs: nonexistent-source`。
  - `uv run python -m karyu_tech_news collect --source qbitai-feed --source jiqizhixin-rss --dry-run` → exit 1、`Invalid or disabled source IDs: jiqizhixin-rss`。
- 実行/確認したテスト:
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `uv run python -m karyu_tech_news collect --help` → `--source` 表示あり。
  - `uv run pytest tests/test_cli_integration.py -q` → `16 passed`。
  - `uv run pytest` → `104 passed in 0.99s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 23 source files`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- DESIGN.md §3.1 の `collect [--dry-run] [--source <id>]` に適合。
- IMPLEMENTATION_PLAN.md のT10テスト方針のうち、dry-runスキップと通常実行での主要4テーブル更新を確認済み。
- Webhook投稿失敗時は警告表示に留まり、収集完了を失敗扱いしない fail-open を維持。
- Architecture status: CLEAR。公開CLI契約、fail-open境界、DB更新経路に追加ブロッカーなし。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。Webhook URLはCLI出力に露出しない。
- SQL injection: ユーザー入力をSQL文字列へ連結していない。
- Webhook fail-open: `post_summary()` 失敗時も警告のみで継続する。
- 並行性: Sprint 1A は単一プロセス前提。T10範囲で新規ブロッカーなし。

### テスト不足

- T10範囲で追加必須テストなし。

## ドキュメント同期 + CLIテスト分離修正レビュー  (レビュー日: 2026-06-03)

### 総合判定: PASS

T1-T10完了 / T11観察中の実態に合わせたドキュメント同期と、`tests/test_cli_integration.py` の `.env` 由来 Webhook 再投入を防ぐ hermetic 修正を確認した。実 `.env` に `DISCORD_WEBHOOK_URL` がある条件でも、対象テストは空文字固定で「Webhook未設定」経路を正しく検証できる。Critical / High / Medium / Low 指摘なし。merge 前レビュー要件は満たした。

### 確認した証跡 (必須)

- 確認したファイル:
  - `AGENTS.md`
  - `README.md`
  - `docs/commit-rules.md`
  - `docs/PROJECT_STATE.md`
  - `docs/TEST_LOG.md`
  - `src/karyu_tech_news/main.py`
  - `tests/test_cli_integration.py`
- 根拠とした差分/行:
  - `tests/test_cli_integration.py:176-181` — `DISCORD_WEBHOOK_URL` を削除ではなく空文字に固定し、`load_dotenv(override=False)` による実 `.env` 再投入を防ぐ。
  - `src/karyu_tech_news/main.py:1-4` / `src/karyu_tech_news/main.py:145-148` — module docstring と `info` 表示を Sprint 1A T1-T10完了 / T11観察中へ更新。ロジック変更なし。
  - `AGENTS.md` / `README.md` / `docs/commit-rules.md` — 現在のCLI・テスト数・T11進行状況へ同期。
  - `docs/TEST_LOG.md` — T11 Day 1 / Day 2 観察結果と fresh gate 証跡を追記。
  - `docs/PROJECT_STATE.md` — T11進行、ドキュメント同期、テスト分離修正を改訂履歴へ追記。
- 実行/確認したテスト:
  - `uv run pytest` → `104 passed in 1.49s`。
  - `uv run ruff check .` → `All checks passed!`。
  - `uv run mypy src tests` → `Success: no issues found in 23 source files`。
  - `uv run python -m karyu_tech_news validate-sources` → `OK: 11 sources loaded (9 enabled, 2 disabled)`。
  - `wc -l AGENTS.md` → `287 AGENTS.md`。
  - `git check-ignore -v .env` → `.gitignore:2:.env .env`。
  - `git ls-files -u` → unmerged file なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" .` → conflict marker なし。

### 設計適合性

- WORKFLOW §11 の「テストコード変更はCodex独立レビュー」の要求に適合。
- `DISCORD_WEBHOOK_URL` の実値は `.env` に残しても gitignore 対象であり、テスト出力・CLI情報表示にも漏洩しない。
- 現在状態のドキュメントは T1-T10完了、CLI 5コマンド、pytest 104、T11 Day 2/3完了に概ね同期している。
- `docs/TEST_LOG.md` の過去履歴に残る `post-summary` 表記は当時の予定・未実装記録であり、現在状態のドリフトとは扱わない。
- Architecture status: CLEAR。実装ロジック・運用手順・テスト分離に追加ブロッカーなし。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret 漏洩: なし。`.env` は gitignore 対象で、テスト修正は空文字固定のみ。
- テスト分離: `monkeypatch.setenv("DISCORD_WEBHOOK_URL", "")` により、実 `.env` の Webhook 値に依存しない。
- 並行性: ドキュメント同期とテスト環境変数修正のみ。並行実行に関する新規リスクなし。

### テスト不足

- 今回範囲で追加必須テストなし。

## Sprint 1B T12-T21 PR #10 独立レビュー  (レビュー日: 2026-06-12 / レビュアー: Codex)

### 総合判定: FAIL

Sprint 1B の LLM profile、編集判定、選定/アーク、台本生成、fallback、永続化、CLI `draft`/`evaluate` の主要パスは設計と概ね整合し、指定の fresh 品質ゲート (`pytest` / `ruff` / `mypy`) は通過した。ただし Discord Webhook の HTTP ステータスエラー時に、失敗ログへ Webhook URL のトークン部分が出る経路が残っている。要件 §9.5 / DESIGN.md §6 の Webhook URL 漏洩リスクに抵触するため、Critical 1 件として PR #10 は merge 不可。

### 確認した証跡 (必須)

- 確認したファイル:
  - `AGENTS.md`
  - `README.md`
  - `docs/DESIGN.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/IMPLEMENTATION_PLAN-1B.md`
  - `docs/PROJECT_STATE.md`
  - `docs/TEST_LOG.md`
  - `docs/design-inheritance-tc-newsflow.md`
  - `docs/editorial-policy.md`
  - `docs/hal-persona.md`
  - `docs/show-format.md`
  - `docs/adr/ADR-0005-llm-roles-ab-test.md`
  - `config/llm_profiles.yaml`
  - `config/show_format.yaml`
  - `.gitignore`
  - `pyproject.toml`
  - `src/karyu_tech_news/collect/normalize.py`
  - `src/karyu_tech_news/collect/runner.py`
  - `src/karyu_tech_news/deliver/discord.py`
  - `src/karyu_tech_news/edit/abtest.py`
  - `src/karyu_tech_news/edit/arc.py`
  - `src/karyu_tech_news/edit/judge.py`
  - `src/karyu_tech_news/edit/prescore.py`
  - `src/karyu_tech_news/edit/select.py`
  - `src/karyu_tech_news/llm/client.py`
  - `src/karyu_tech_news/llm/profile.py`
  - `src/karyu_tech_news/main.py`
  - `src/karyu_tech_news/script/fallback.py`
  - `src/karyu_tech_news/script/generate.py`
  - `src/karyu_tech_news/script/runner.py`
  - `src/karyu_tech_news/store/repo.py`
  - `src/karyu_tech_news/store/schema.py`
  - `tests/test_abtest.py`
  - `tests/test_cli_1b.py`
  - `tests/test_discord.py`
  - `tests/test_discord_script.py`
  - `tests/test_draft_runner.py`
  - `tests/test_fallback.py`
  - `tests/test_judge.py`
  - `tests/test_llm_client.py`
  - `tests/test_llm_profile.py`
  - `tests/test_prescore.py`
  - `tests/test_script_generate.py`
  - `tests/test_select_arc.py`
  - `tests/test_store_1b.py`
- レビュー対象差分:
  - `git diff --name-status origin/main...HEAD` → 35 ファイル (Sprint 1B T12-T21 + レビュー対応)。
  - `git rev-parse --abbrev-ref HEAD` → `agent/T12-impl`。
  - `git merge-base origin/main HEAD` / `git rev-parse origin/main` → `965f37d548f92ff87c3bb5f077fba746f033ec0f`。
  - `git rev-parse HEAD` → `ab4239ee291dcd43dfd42e597bd559287ffe31aa`。
- 根拠とした差分/行:
  - `AGENTS.md:21-24` — Sprint 1B T12-T21 実装済み、T13/T22 は人間ブロッカー後という現在地。
  - `AGENTS.md:34-49` — `.env` commit 禁止、`item_key`/UNIQUE、fail-open、Sprint 1B の禁止スコープ。
  - `AGENTS.md:80-83` — PR 前品質ゲート (`uv run pytest` / `ruff` / `mypy`)。
  - `docs/DESIGN.md:17-19` / `docs/DESIGN.md:88-147` — SQLite 永続化、`UNIQUE(source_id,item_key)`、FR-021 `item_key` 生成順、空 `item_key` 禁止。
  - `docs/DESIGN.md:171-181` / `docs/DESIGN.md:196-197` — Webhook URL 漏洩防止、Webhook fail-open、法務・秘密管理。
  - `docs/DESIGN.md:204-207` — Sprint 1B は LLM 編集・Markdown 台本まで、TTS/配信系は後続。
  - `docs/IMPLEMENTATION_PLAN.md:49-54` / `docs/IMPLEMENTATION_PLAN.md:79-84` — 1A 回帰対象の dedupe/source_health/fail-open/Webhook テスト条件。
  - `docs/IMPLEMENTATION_PLAN-1B.md:10-20` — Sprint 1B DoD (3-5本、Markdown台本、ソース一覧、A/B/C 記録、Discord 投稿)。
  - `docs/IMPLEMENTATION_PLAN-1B.md:52-75` — T12-T21 タスク分解と LLM モック方針。
  - `docs/IMPLEMENTATION_PLAN-1B.md:86-92` — LLM に JSON と台本を同時生成させない、決定的配置、fallback、TTS/音声/動画/YouTube 禁止。
  - `docs/design-inheritance-tc-newsflow.md:19-25` — LLMProfile 抽象と環境変数名のみ保持。
  - `docs/design-inheritance-tc-newsflow.md:39-60` / `docs/design-inheritance-tc-newsflow.md:65-85` — 事前スコア、LLM判定、決定的アーク、多様性キャップ、fallback。
  - `docs/design-inheritance-tc-newsflow.md:73-79` / `docs/design-inheritance-tc-newsflow.md:89-100` — str/rune 単位切り詰め、Hook/Insight/Action、URLは最終出力本文に入れない。
  - `docs/editorial-policy.md:6-10` / `docs/editorial-policy.md:31-40` / `docs/editorial-policy.md:79-91` — ナショナリズム表現禁止、Tier3/4 の扱い、本文転載禁止。
  - `docs/hal-persona.md:25-49` — HAL の表現ガイド、暫定オープニング/クロージング、噂明示。
  - `docs/show-format.md:14-18` / `docs/show-format.md:60-69` / `docs/show-format.md:107-116` — 3-5本、Hook/Insight/Action、Discord 台本投稿項目。
  - `config/llm_profiles.yaml:9-55` — 実キーではなく `api_key_env` と A/B/C mapping を保持。
  - `src/karyu_tech_news/collect/normalize.py:62-76` / `src/karyu_tech_news/collect/normalize.py:119-129` — `external_id` → `link` → `sha256(title|published_at|source_id)` の順で `item_key` を生成し空値を拒否。
  - `src/karyu_tech_news/store/schema.py:51-56` — `items` は `UniqueConstraint("source_id","item_key")` のみ。`hash` 単体 UNIQUE なし。
  - `src/karyu_tech_news/store/repo.py:76-105` — insert 直前の空 `item_key` 拒否と同一 `(source_id,item_key)` dedupe。
  - `src/karyu_tech_news/store/repo.py:108-130` — source_health は成功で `consecutive_failures=0` / `last_error=None`、失敗で +1 / `last_error` 保存。
  - `src/karyu_tech_news/collect/runner.py:42-79` — 1ソース fetch/DB 失敗時も後続ソースへ進み、run を完了する fail-open。
  - `src/karyu_tech_news/llm/profile.py:31-117` / `src/karyu_tech_news/llm/client.py:40-53` — profile 検証、A/B/C 役割解決、API key は環境変数から解決し未設定時は環境変数名のみ表示。
  - `src/karyu_tech_news/llm/client.py:78-100` / `src/karyu_tech_news/llm/client.py:102-151` — OpenAI 互換 chat、JSON mode、Ollama `think=false`、timeout/retry、`reasoning_content`/`reasoning` fallback。
  - `src/karyu_tech_news/edit/prescore.py:22-49` / `src/karyu_tech_news/edit/prescore.py:78-120` — 候補上限40、Tierボーナス、lookback 抽出、コードポイント単位データ。
  - `src/karyu_tech_news/edit/judge.py:124-154` / `src/karyu_tech_news/edit/judge.py:157-214` — editor は JSON 判定のみ、temp=0、corroboration は決定的コード。
  - `src/karyu_tech_news/edit/select.py:30-69` — Tier3/4 の独立2ソースゲート、最大5本、多様性キャップ4パス。
  - `src/karyu_tech_news/edit/arc.py:23-51` — 三幕アーク配置は決定的コード。
  - `src/karyu_tech_news/script/generate.py:59-125` / `src/karyu_tech_news/script/generate.py:128-182` — writer はプレーンテキスト、Hook/Insight/Action・300字・URL/禁止表現・噂明示の検証、ソース一覧つき Markdown 組み立て。
  - `src/karyu_tech_news/script/fallback.py:86-137` — writer 違反/LLMError 時の再生成→テンプレ fallback。
  - `src/karyu_tech_news/script/runner.py:103-132` / `src/karyu_tech_news/script/runner.py:135-224` — editor JSON 崩壊/部分欠落時の neutral fallback、永続化、A/B/C ログ保存。
  - `src/karyu_tech_news/deliver/discord.py:79-96` — `post_summary()` は fail-open で `False` を返すが、HTTPStatusError の文字列をログに出す。
  - `src/karyu_tech_news/deliver/discord.py:124-141` — `post_markdown()` は台本をチャンク投稿し、同じ `post_summary()` 失敗ログ経路を使う。
  - `src/karyu_tech_news/main.py:31-40` — `httpx` INFO ログは抑止済みだが、アプリ側 `logger.exception(... %s, exc)` の URL 混入は別経路。
  - `tests/test_discord.py:166-173` — Webhook 失敗時の戻り値はあるが、HTTPStatusError ログに URL が出ないことは未検証。
  - `tests/test_cli_1b.py:57-64` — `httpx` INFO 抑止の回帰テストのみ。
  - `tests/test_script_generate.py:123-131` — ラベル込み300字境界の回帰テスト。
  - `tests/test_draft_runner.py:159-200` — editor 部分欠落/JSON崩壊時の neutral fallback。
  - `tests/test_fallback.py:124-149` — writer 違反/LLMError/Tier4 噂明示の fallback。
- 実行/確認したテスト:
  - `uv run pytest` → サンドボックスの `~/.cache/uv` 書き込み不可で起動前失敗 (`Operation not permitted`)。コード失敗ではない。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run pytest` → `239 passed in 1.06s`。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run ruff check .` → `All checks passed!`。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run mypy src tests` → `Success: no issues found in 48 source files`。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run --with pytest-cov pytest --cov=karyu_tech_news` → ネットワーク制限で `pytest-cov` 取得不可 (`Failed to fetch: https://pypi.org/simple/pytest-cov/`)。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run python -c 'import pytest_cov'` → `ModuleNotFoundError`。現在環境に `pytest-cov` なし。
  - coverage は fresh 再測定できなかったため、直近証跡 `docs/TEST_LOG.md:807-809` の `TOTAL 96%` を参照。DoD 80% は既存証跡上充足。
  - `git diff --check origin/main...HEAD` → 出力なし (whitespace error なし)。
  - `git ls-files -u` → 出力なし (unmerged file なし)。
  - `rg -n '^(<<<<<<<|=======|>>>>>>>)' --glob '!docs/REVIEW_REPORT.md' .` → 出力なし (実コンフリクトマーカーなし)。
  - `git ls-files .env data/state.db artifacts | sort` → 出力なし。ローカル `.env` / `data/state.db` は存在するが未追跡。
  - `git check-ignore -v .env data/state.db` → `.gitignore:2:.env` / `.gitignore:7:data/`。
  - secret scan (長さつき `sk-`、GitHub token、Discord webhook URL、実 API env 代入を `docs/REVIEW_REPORT.md` と `uv.lock` 除外で検索) → 出力なし。
  - スコープ外 import 検索 (`playwright` / `moviepy` / `pydub` / `youtube` / `googleapiclient` / `TTSEngine` 等) → コード import なし。`config/show_format.yaml` の既存 audio/video 仕様は今回差分なし。
  - HTTP timeout 検索 → collect `httpx.get(... timeout=TIMEOUT_SECONDS)`、Discord `httpx.post(... timeout=10.0)`、LLM `httpx.post(... timeout=TIMEOUT_SECONDS)` を確認。
  - Webhook status error 再現: `httpx.Response(401, request=Request("POST", "https://discord.com/api/webhooks/123/SECRET_TOKEN")).raise_for_status()` → 例外文字列に `https://discord.com/api/webhooks/123/SECRET_TOKEN` が含まれることを確認。

### DESIGN.md / 1B 計画との対応

- 収集系リグレッション:
  - FR-021 `item_key` 生成順は `src/karyu_tech_news/collect/normalize.py:62-76` で維持。
  - FR-031 `UNIQUE(source_id,item_key)` は `src/karyu_tech_news/store/schema.py:51-56` で維持。`hash` 単体 UNIQUE はなし。
  - source_health 成功/失敗更新は `src/karyu_tech_news/store/repo.py:108-130` と `tests/test_health.py:54-196` で確認。
  - 1ソース失敗/DB失敗時の fail-open は `src/karyu_tech_news/collect/runner.py:42-79` と `tests/test_runner_fail_open.py:122-160` / `tests/test_runner_fail_open.py:244-391` で確認。
  - Webhook 失敗で run 自体を fail させない挙動は `src/karyu_tech_news/main.py:291-305` / `src/karyu_tech_news/main.py:427-439`、`tests/test_discord.py:166-173`、`tests/test_discord_script.py:57-64` で確認。
- Sprint 1B 実装:
  - T12: LLM profile / OpenAI 互換 client は `src/karyu_tech_news/llm/profile.py:31-117` / `src/karyu_tech_news/llm/client.py:56-151`、テストは `tests/test_llm_profile.py:145-163` / `tests/test_llm_client.py:83-274`。
  - T14-T16: 事前スコア、編集判定、多様性キャップ、アーク配置は `src/karyu_tech_news/edit/*.py` と `tests/test_prescore.py:125-181` / `tests/test_judge.py:192-232` / `tests/test_select_arc.py:47-189`。
  - T17-T18: Hook/Insight/Action 台本、検証、fallback は `src/karyu_tech_news/script/generate.py:59-182` / `src/karyu_tech_news/script/fallback.py:86-137` と `tests/test_script_generate.py:71-206` / `tests/test_fallback.py:57-149`。
  - T19-T20: 1B 4テーブルと evaluate は `src/karyu_tech_news/store/schema.py:102-176` / `src/karyu_tech_news/store/repo.py:172-265` / `src/karyu_tech_news/edit/abtest.py:41-130` と `tests/test_store_1b.py:112-238` / `tests/test_abtest.py`。
  - T21: CLI `draft` / `evaluate` と Discord 台本投稿は `src/karyu_tech_news/main.py:308-462` / `src/karyu_tech_news/deliver/discord.py:99-141` と `tests/test_cli_1b.py:14-64` / `tests/test_discord_script.py` / `tests/test_draft_runner.py`。
- コンテンツ/番組整合:
  - `docs/editorial-policy.md:79-91` の禁止表現、本文転載禁止、噂明示は `src/karyu_tech_news/script/generate.py:64-125` と `tests/test_script_generate.py:140-157` で最低限の決定的チェックあり。
  - `docs/hal-persona.md:42-49` の暫定挨拶は `src/karyu_tech_news/script/generate.py:25-28` / `tests/test_script_generate.py:182-184` と整合。
  - `docs/show-format.md:107-116` の Discord 台本投稿項目は `src/karyu_tech_news/script/generate.py:146-168` で概ね組み立て済み。
- スコープ外混入:
  - Sprint 1B では LLM は解禁済み。TTS / 音声処理 / 動画 / YouTube / Playwright / Cookie 必須ルートのコード import / CLI 実装は見当たらない。
  - `config/show_format.yaml:49-59` の audio/video 定義は将来仕様として既存管理されており、今回差分ではない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | `src/karyu_tech_news/deliver/discord.py:91-95` / `src/karyu_tech_news/deliver/discord.py:124-141` / `src/karyu_tech_news/main.py:38-40` / `tests/test_discord.py:166-173` / `tests/test_cli_1b.py:57-64` | Discord が 4xx/5xx を返すと `resp.raise_for_status()` が生成する `HTTPStatusError` の文字列に Webhook URL 全体が含まれる。`post_summary()` は `logger.exception("Discord Webhook post failed: %s", exc)` でその文字列をログ出力するため、`DISCORD_WEBHOOK_URL` のトークンが再びローカルログへ漏れる。今回 `httpx` INFO ログ抑止は入ったが、アプリ側の例外ログ経路は別で残っている。`post_markdown()` も `post_summary()` を呼ぶため、Sprint 1B の台本投稿失敗時にも同じ漏洩が起きる。要件 §9.5 / DESIGN.md §6 の Webhook URL 漏洩リスク、および AGENTS.md §3.1 の秘密管理に抵触。 | Webhook 投稿失敗ログでは `exc` の文字列をそのまま出さず、HTTP status code / exception class / sanitized host 程度に限定する。`httpx.HTTPStatusError` は `exc.response.status_code` を記録し、URL は出さない。回帰テストとして `raise_for_status()` 由来の `HTTPStatusError` を発生させ、`caplog.text` に Webhook token / URL が含まれないことを `post_summary()` と `post_markdown()` の両方で追加する。必要なら既に露出した Discord Webhook は再発行する。 |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性

- secret commit: `git ls-files .env data/state.db artifacts` は空。`.env` と `data/state.db` はローカルに存在するが `.gitignore` 対象 (`.gitignore:2`, `.gitignore:7`)。
- secret 直書き: 長さつき token パターン検索では実キーらしき値なし。`tests/test_llm_client.py` の `sk-test-123` / `sk-secret-value` は短いテスト用ダミー。
- secret ログ: Critical 指摘のとおり、HTTPStatusError 経路で Discord Webhook URL がログへ出る。
- SQL injection: 本番コードの raw SQL は SQLite `PRAGMA foreign_keys=ON` の固定文字列のみ。DB 読み書きは SQLAlchemy の `select()` / ORM を使用し、ユーザー入力を SQL 文字列へ連結していない。
- HTTP timeout: collect / Discord / LLM の httpx 呼び出しはいずれも timeout 指定あり。
- 並行性: DESIGN.md §6 は Sprint 1A 単一プロセス前提。今回差分は複数プロセス同時 draft の排他を導入していないが、Sprint 1B の明示要件ではなく、今回の merge blocker ではない。
- スコープ外: TTS / 音声処理 / 動画 / YouTube 投稿 / Playwright / Cookie 必須ルートの import や実行経路はなし。

### テスト不足

- `post_summary()` / `post_markdown()` の HTTPStatusError 失敗ログに Webhook URL や token が含まれないことを検証する `caplog` 回帰テストが不足。
- fresh coverage はサンドボックスのネットワーク制限により再測定不可。`docs/TEST_LOG.md:807-809` の 96% 証跡は確認したが、今回レビュー時点の coverage 再計測は未実施。

### PR コメント案

PR #10 は FAIL です。主機能・品質ゲートは通っていますが、Discord Webhook が 4xx/5xx を返した場合に `post_summary()` の `logger.exception(... %s, exc)` が `HTTPStatusError` の URL 文字列を出し、Webhook token をログへ漏らします。`httpx` INFO ログ抑止だけではこの経路は塞げていません。失敗ログは status code / exception class のみにサニタイズし、`caplog` で token 非露出を `post_summary()` と `post_markdown()` の両方に追加してください。

## Discord Webhook 例外ログ漏洩修正 再レビュー (レビュー日: 2026-06-12 / レビュアー: Codex)

### 総合判定: PASS

前回 Critical 指摘「Discord Webhook 4xx/5xx 時に `post_summary()` の `logger.exception` が `HTTPStatusError` の URL 文字列、つまり Webhook token をログ出力する」は、コミット `818f88e` で解消されている。`post_summary()` は HTTP status error を status code のみ、その他例外を例外型名のみで記録し、`post_markdown()` は投稿ごとに同じ `post_summary()` 経路へ集約されるため、台本投稿側にも同じサニタイズが適用される。Critical/High 指摘はない。

### 確認した証跡 (必須)

- 確認したファイル:
  - `prompts/review.md`
  - `docs/DESIGN.md`
  - `docs/PROJECT_STATE.md`
  - `docs/TEST_LOG.md`
  - `docs/REVIEW_REPORT.md`
  - `src/karyu_tech_news/deliver/discord.py`
  - `src/karyu_tech_news/main.py`
  - `tests/test_discord.py`
  - `tests/test_discord_script.py`
- レビュー対象差分:
  - `git show --stat --oneline --decorate 818f88e` → `818f88e (HEAD -> agent/T12-impl, origin/agent/T12-impl) fix: Webhook 例外ログのトークン露出を遮断 (Codex レビュー Critical 対応)`。対象は `src/karyu_tech_news/deliver/discord.py` / `tests/test_discord_script.py` / 前回 FAIL の `docs/REVIEW_REPORT.md`。
  - `git show 818f88e -- src/karyu_tech_news/deliver/discord.py tests/test_discord_script.py` → `logger.exception("... %s", exc)` を削除し、`httpx.HTTPStatusError` 専用の status code ログと汎用例外の型名ログへ変更。回帰テスト 3 件を追加。
  - `git status --short --branch` → `## agent/T12-impl...origin/agent/T12-impl`。
- 根拠とした差分/行:
  - `src/karyu_tech_news/deliver/discord.py:79-102` — `post_summary()` は空 URL では固定文言のみ、HTTPStatusError では `exc.response.status_code` のみ、その他例外では `type(exc).__name__` のみをログ出力する。`logger.exception` / `exc_info=True` は使っていない。
  - `src/karyu_tech_news/deliver/discord.py:130-147` — `post_markdown()` は空 URL/空本文では固定文言だけを警告し、実投稿の失敗は全て `post_summary()` に委譲する。ここにも URL や例外文字列を直接ログ出力する経路はない。
  - `src/karyu_tech_news/main.py:291-305` / `src/karyu_tech_news/main.py:427-439` — `collect --post` / `draft --post` は Discord 失敗時に fail-open の CLI 警告のみを出し、Webhook URL を表示しない。
  - `tests/test_discord_script.py:81-92` — Webhook token を含む `HTTPStatusError` テストデータを作る helper。
  - `tests/test_discord_script.py:95-107` — `post_summary()` の HTTP 500 経路で token / Webhook URL が `caplog.text` に出ず、status code のみ残ることを固定。
  - `tests/test_discord_script.py:109-119` — `post_summary()` の接続系例外で token が `caplog.text` に出ず、例外型名のみ残ることを固定。
  - `tests/test_discord_script.py:122-132` — `post_markdown()` の HTTP 429 経路で token / Webhook URL が `caplog.text` に出ないことを固定。
  - `tests/test_discord.py:166-173` — 既存の Webhook 失敗時 `False` 返却 (FR-071 fail-open) 回帰。
  - `docs/DESIGN.md:171-181` / `docs/DESIGN.md:194-196` — Webhook URL 漏洩リスク、Webhook fail-open、秘密管理の設計基準。
  - `docs/DESIGN.md:204-207` — Sprint 1B は LLM 編集・Markdown 台本までで、TTS/配信系の越境なし。
  - `docs/TEST_LOG.md:785-793` — T21 の台本投稿実装と既存テスト証跡。
  - `docs/TEST_LOG.md:807-809` — 直近 coverage 96% 証跡。
- 実行/確認したテスト:
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run pytest tests/test_discord_script.py -q` → exit 0、`........... [100%]` (11 tests)。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run pytest` → `242 passed in 0.99s`。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run ruff check .` → `All checks passed!`。
  - `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run mypy src tests` → `Success: no issues found in 48 source files`。
  - `rg -n "logger\\.exception|exc_info=True|HTTPStatusError|post_summary\\(|post_markdown\\(|httpx\\.post\\(" src tests` → Discord 投稿経路に `logger.exception` / `exc_info=True` なし。`post_markdown()` は `post_summary()` への委譲のみ。
  - `git diff --check` → 出力なし。
  - `git ls-files -u` → 出力なし。
  - `rg -n "^(<<<<<<<|=======|>>>>>>>)" . --glob '!docs/REVIEW_REPORT.md'` → 出力なし。
  - `git ls-files .env data/state.db artifacts && rg -n "discord\\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]{20,}|DISCORD_WEBHOOK_URL=.*https://|sk-[A-Za-z0-9]{20,}" . --glob '!uv.lock' --glob '!docs/REVIEW_REPORT.md' --glob '!tests/test_discord_script.py'` → 出力なし。

### DESIGN.md / 指摘対応との対応

- DESIGN.md §6 / §8 の秘密管理に対し、Webhook URL の値そのものや `HTTPStatusError` の例外文字列をログへ渡さない実装になっている。
- DESIGN.md §7 の FR-071 fail-open に対し、`post_summary()` は失敗時も例外を外へ投げず `False` を返し、`main.py` 側も処理継続の警告に留める。
- traceback 出力をやめた点は妥当。今回の秘密漏洩は例外文字列と traceback 経由の URL 露出が原因であり、運用上必要な診断情報は HTTP status code または exception class で足りる。詳細調査が必要な場合も token 入り URL をログに出すべきではない。
- Sprint 1B のスコープ越境はなし。修正範囲は Discord 例外ログとその回帰テストに限定されている。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | なし | なし | なし |
| Low | なし | なし | なし |

### セキュリティ / 副作用

- secret ログ: `post_summary()` の HTTPStatusError / 汎用例外、`post_markdown()` の委譲経路、CLI 側の失敗表示を確認し、token / Webhook URL がログへ出る経路は見当たらない。
- secret commit: `.env` / `data/state.db` / `artifacts` は追跡されておらず、今回検索した token パターンも検出なし。
- 新たな漏洩経路: `logger.exception` と `exc_info=True` は Discord 投稿経路に存在しない。`httpx` の URL 文字列を含む例外をそのまま `%s` に渡す経路も見当たらない。
- 副作用: `post_summary()` の戻り値契約は維持され、既存の `post_markdown()` fail-open テストも含めて `tests/test_discord_script.py` が全件 green。診断粒度は下がるが、秘密保護を優先する判断として適切。

### テスト不足

- 今回範囲で追加必須テストなし。`post_markdown()` の汎用接続例外は直接の専用テストではなく `post_summary()` の接続系例外テストと `post_markdown()` の委譲構造で担保されているが、同じコード経路であり merge blocker ではない。

## 2026-06-12: Sprint 2 実装計画ドラフト (IMPLEMENTATION_PLAN-2.md) レビュー (レビュー日: 2026-06-12 / レビュアー: Codex)

### 総合判定: PASS

Critical 0 / High 0 / Medium 1 / Low 1。`docs/IMPLEMENTATION_PLAN-2.md` は ADR-0006、完パケ・パイプライン、要件 §8.10-8.11 / §15.3、roadmap Sprint 2 節と大筋で整合している。Sprint 1B 期間中は文書準備に留め、TTS コード導入を禁止し、T22 完了・Sprint 1B 完了 PR の人間マージ・人間 Go の 3 条件を着手ゲートとして明記しているため、AGENTS.md §3.4 の Sprint 越境禁止も守れる書き方になっている。

### 確認した証跡 (必須)

- 確認したファイル:
  - `AGENTS.md`
  - `prompts/review.md`
  - `docs/PROJECT_STATE.md`
  - `docs/DESIGN.md`
  - `docs/IMPLEMENTATION_PLAN-2.md`
  - `docs/REVIEW_REPORT.md`
  - `docs/adr/ADR-0006-tts-irodori-abstraction.md`
  - `docs/architecture-podcast-station.md`
  - `docs/requirements-v1.0.md`
  - `docs/roadmap.md`
  - `docs/hal-persona.md`
  - `docs/show-format.md`
  - `config/hal_persona.yaml`
  - `config/show_format.yaml`
  - `.gitignore`
- レビュー対象:
  - `git branch --show-current` → `agent/T22-impl`。
  - `git status --short` → レビュー開始時点で出力なし (作業ツリー clean)。
  - `git ls-files docs/IMPLEMENTATION_PLAN-2.md ...` → 対象ドキュメントと根拠ドキュメントは追跡済み。
- 根拠とした差分/行:
  - `docs/IMPLEMENTATION_PLAN-2.md:3-4` — Sprint 2 計画は準備ドキュメントであり、T22 完了 / 1B 完了 PR 人間マージ / 人間 Go の 3 条件成立後のみ実装着手、Sprint 1B 中の TTS コード導入なし。
  - `docs/IMPLEMENTATION_PLAN-2.md:10-16` — Sprint 2 DoD は `TTSEngine`、Irodori 接続、構造化台本 JSON、読み仮名辞書、BGM/ジングル、-16 LUFS、mp3 192kbps/48kHz、Discord 投稿、3日観察。
  - `docs/IMPLEMENTATION_PLAN-2.md:20-29` — 設計所在を ADR-0006 / architecture §4 / requirements §8.10-8.11 / hal persona / editorial policy に集約。
  - `docs/IMPLEMENTATION_PLAN-2.md:33-46` — 追加レイヤーは `script -> tts -> mix` の一方向、`tts` は `edit` / `llm` を参照しない。新依存は roadmap 既定の `pydub` + `ffmpeg` に限定。
  - `docs/IMPLEMENTATION_PLAN-2.md:51-62` — T23〜T32 は `TTSEngine` / Irodori smoke / structure / reading dict / emoji annotation / sentence synthesis / mix / master / persistence+CLI+Discord / 3日観察に分解され、依存循環なし。
  - `docs/IMPLEMENTATION_PLAN-2.md:64-68` — モック駆動、決定的コード厚め、ffmpeg 小フィクスチャ、str 単位文分割テスト方針。
  - `docs/IMPLEMENTATION_PLAN-2.md:70-80` — 人間判断待ちと着手ゲート。ただし §6 と §7.2 のブロッカー粒度に Medium 指摘あり。
  - `docs/IMPLEMENTATION_PLAN-2.md:82-88` — Sprint 2 固有 NG: 無断声クローン禁止、動画/YouTube 禁止、LLM に JSON と台本を同時生成させない、TTS 文単位 fail-open、バイト切り詰め禁止、生成音声ファイル commit 禁止。
  - `docs/adr/ADR-0006-tts-irodori-abstraction.md:11-16` — Irodori 主軸、`TTSEngine` 抽象化、HAL 人格の TTS 非依存、VoiceDesign -> Speaker Inversion は検証項目。
  - `docs/adr/ADR-0006-tts-irodori-abstraction.md:27-45` — Irodori の弱点対策として読み仮名辞書、絵文字制御、抽象化層で代替エンジン退避。
  - `docs/adr/ADR-0006-tts-irodori-abstraction.md:56-60` — Sprint 2 で `tts/engine.py` + `tts/irodori.py`、Sprint 1A/1B では TTS 実装なし。
  - `docs/architecture-podcast-station.md:58-76` — 7層パイプラインで Sprint 2 は `tts` / `mix`、Sprint 3 は `render` / `publish`。
  - `docs/architecture-podcast-station.md:78-94` — script -> tts 境界の構造化 JSON、LLM に JSON と日本語コピーを同時生成させない、tone から絵文字注釈を TTS 前処理で機械挿入。
  - `docs/architecture-podcast-station.md:96-107` — Irodori v3 主軸、抽象化、HAL 人格 TTS 非依存、音響演出重視。
  - `docs/requirements-v1.0.md:592-630` — FR-090〜092 / FR-100〜103: TTS 抽象化、HAL 音声、読み仮名辞書、BGM、ジングル、ラウドネス、mp3 192kbps。
  - `docs/requirements-v1.0.md:632-666` — 動画生成と YouTube 配信は後続要件。Sprint 1A/1B では実装しない。
  - `docs/requirements-v1.0.md:714-724` — 本文転載は禁止、実在人物の無断声真似禁止、BGM/ジングルのライセンス確認。
  - `docs/requirements-v1.0.md:1043-1055` — Sprint 2 対象は TTS 抽象化、Irodori 接続、文単位合成、読み辞書、mp3、BGM/ジングル仮ミックス、Discord mp3 またはリンク投稿。
  - `docs/requirements-v1.0.md:1097-1107` — 読み崩れ対策、TTS 抽象化、Webhook 添付制限時の R2/S3 等リンク投稿余地。
  - `docs/roadmap.md:58-62` — Sprint 2 主要タスクは IMPLEMENTATION_PLAN-2.md の T23〜T31 と対応し、pydub+ffmpeg / -16 LUFS / mp3 192kbps/48kHz / 25MB 超リンク投稿を含む。
  - `AGENTS.md:47-50` — Sprint 1B の TTS/音声処理/動画/YouTube 禁止、コスト上限を超える呼び出し方の変更は人間判断、スコープ膨張は PROJECT_STATE にエスカレーション。
  - `AGENTS.md:52-59` — 実在人物の無断声真似禁止、AI 開示は Sprint 3、Go/Node/2言語化禁止。
  - `docs/DESIGN.md:200-209` — Sprint 2 は TTS/BGM/mp3、動画/YouTube は Sprint 3。スプリント越境禁止。
  - `docs/PROJECT_STATE.md:8` / `docs/PROJECT_STATE.md:99-108` — 現在は T22 Day 1/3 完了で Sprint 2 は T22 完了後、人間 Go 判断パッケージが必要。
  - `docs/hal-persona.md:18-23` / `docs/hal-persona.md:55-67` — 声質仕様、無断クローン禁止、VoiceDesign / Speaker Inversion、TTS 乗り換え時の声維持レビュー。
  - `config/hal_persona.yaml:41-45` — primary engine、voice strategy、reading dict、emoji annotation は Sprint 2 計画と整合。
  - `config/show_format.yaml:22-30` / `config/show_format.yaml:51-59` — ジングル segment、-16 LUFS、mp3、動画/AI disclosure は将来仕様として分離。
  - `.gitignore:16-22` — mp3/mp4/wav と素材本体は git 管理外。
- 実行/確認したテスト:
  - 文書レビューのため `uv run pytest` / `ruff` / `mypy` は未実行。コード変更はなく、検証は行番号付きドキュメント照合と `git status --short` に限定。
  - `rg` / `nl -ba` / `sed` で対象節を確認。

### 設計適合性

- ADR-0006 との整合: `TTSEngine` Protocol、Irodori-TTS v3 主軸、HAL 人格の TTS 非依存、VoiceDesign -> Speaker Inversion を確定仕様ではなく検証項目として扱う点は整合。
- architecture-podcast-station §4 との整合: `script -> tts -> mix` までを Sprint 2、`render -> publish` を Sprint 3 として分離している。構造化 JSON はコード側 parser、絵文字注釈は TTS 前処理という境界も一致。
- requirements §8.10-8.11 / §15.3 との整合: FR-090〜092 と FR-100〜103、Sprint 2 の対象項目を T23〜T31 で概ね網羅している。
- roadmap Sprint 2 との整合: pydub+ffmpeg、-16 LUFS、mp3 192kbps/48kHz、Discord 25MB 超リンク投稿を計画に反映している。
- スコープゲート: 計画冒頭と §7 で Sprint 1B 中の TTS 実装禁止、T22 完了、1B 完了 PR の人間マージ、人間 Go を明示しているため、Sprint 越境防止としては合格。
- タスク分解: T23/T25 をモック・決定的コードで先行でき、T24/T29/T31 は人間ブロッカーや下流成果物に依存する。T28 が T23-T27 を待つため、文単位合成前に engine / structure / normalize / annotate が揃う。循環依存は見当たらない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | `docs/IMPLEMENTATION_PLAN-2.md:70-80` | §6 は 5 項目すべてを「着手前ブロッカー」と呼ぶ一方、§7.2 は「実行環境」「声リファレンス」だけを解消し、他はモック駆動で並行可としている。実質的には Sprint 2 全体の Go ブロッカーと、T29/T31 などの ticket-local ブロッカーが混在している。現状でも T22 / 人間 merge / 人間 Go は守れるが、実装者が BGM 素材・mp3 配信方法・A/B/C 既定決定を「着手前に全解消必須」なのか「該当 ticket 前までで可」なのか読み違える余地がある。 | §6 を「Sprint 2 Go 前に必須」と「該当 ticket 着手前に必須」に分割するか、§7.2 で T24=実行環境/声、T29=BGM/ジングル、T31=配信方法、T32=A/B/C 継続判断のようにブロッカー粒度を明示する。 |
| Low | `docs/IMPLEMENTATION_PLAN-2.md:45-46` / `docs/IMPLEMENTATION_PLAN-2.md:61` / `docs/IMPLEMENTATION_PLAN-2.md:70-75` | クラウド GPU または R2/S3 リンク投稿を選ぶ場合、AGENTS.md §3.4 のコスト上限と要件 §9.5 の秘密管理が新たに効くが、§6 の人間判断待ちは provider / 月額上限 / 認証情報の保管方針までは明示していない。環境選択・配信方法の判断に内包されるため blocker ではないが、Sprint 2 着手後に追加判断が発生しやすい。 | §6 に「クラウド GPU / 外部ストレージを選ぶ場合は provider、月額上限、認証情報の `.env` 管理、リンク永続期間を人間が決める」を追記すると、後続 T24/T31 の手戻りが減る。 |

### セキュリティ / スコープ / 副作用

- secret: 計画は `.env` や実キーの追加を要求していない。外部 GPU / R2/S3 を選ぶ場合の秘密管理は Low 指摘として明示改善対象。
- 生成物: `.gitignore` は mp3/mp4/wav と素材本体を git 管理外にしており、計画 §8 の「生成 mp3/wav を commit しない」と整合。
- 法務: 実在人物の無断声真似・声クローン禁止、BGM/ジングル素材のライセンス確認、人間試聴判断は計画に含まれる。
- スコープ: 動画生成 / YouTube 投稿は Sprint 2 計画から除外されている。Playwright / 中国 IP プロキシ / Cookie 必須ルート / Go or Node 導入も計画には含まれていない。

### テスト不足

- ドキュメントレビューのため追加テスト要求なし。実装開始後は T23〜T31 それぞれでモック駆動の単体テスト、ffmpeg 小フィクスチャ、str 単位文分割回帰、T24 smoke、T32 聴感観察を TEST_LOG に残す必要がある。

## PR #22 T33/T34 日次自動配信 + 600M VoiceDesign レビュー (レビュー日: 2026-06-24 / レビュアー: Codex)

### 総合判定: PASS

Critical 0 / High 0 / Medium 2 / Low 1。`main...HEAD` の実装差分は T33/T33+/T34 の範囲に収まり、`scripts/daily_pipeline.sh`、launchd plist、Irodori timeout、文単位絵文字、VoiceDesign caption 配線は Sprint 2 の TTS/完パケ配信スコープ内である。AGENTS.md §3 の秘密漏洩・fail-open・timeout 必須・動画/YouTube 越境禁止に対する Critical/High 違反は確認されなかった。

### 確認したファイル

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/ORCHESTRATION_RUNBOOK.md`
- `docs/DESIGN.md`
- `docs/IMPLEMENTATION_PLAN-2.md`
- `docs/TEST_LOG.md`
- `docs/REVIEW_REPORT.md`
- `docs/editorial-policy.md`
- `docs/hal-persona.md`
- `docs/show-format.md`
- `config/hal_persona.yaml`
- `.gitignore`
- `scripts/daily_pipeline.sh`
- `scripts/launchd/com.karyu.daily-pipeline.plist`
- `src/karyu_tech_news/main.py`
- `src/karyu_tech_news/tts/engine.py`
- `src/karyu_tech_news/tts/irodori.py`
- `src/karyu_tech_news/tts/synthesize.py`
- `src/karyu_tech_news/collect/normalize.py`
- `src/karyu_tech_news/store/schema.py`
- `src/karyu_tech_news/store/repo.py`
- `src/karyu_tech_news/collect/runner.py`
- `src/karyu_tech_news/deliver/discord.py`
- `tests/test_tts_irodori.py`
- `tests/test_tts_synthesize.py`
- `tests/test_runner_fail_open.py`
- `tests/test_health.py`
- `tests/test_discord.py`
- `/Users/kairyon/tools/Irodori-TTS-Server/src/irodori_openai_tts/config.py` (外部サーバ実体の設定名確認)
- `/Users/kairyon/tools/Irodori-TTS-Server/src/irodori_openai_tts/app.py` (外部サーバ実体の caption 受け口確認)

### レビュー対象

- `git branch --show-current` → `agent/T33-daily-pipeline-impl`
- `git rev-parse --short HEAD` → `c585383`
- `git diff --name-status main...HEAD` → `config/hal_persona.yaml`、`docs/PROJECT_STATE.md`、`scripts/daily_pipeline.sh`、`scripts/launchd/com.karyu.daily-pipeline.plist`、`src/karyu_tech_news/main.py`、`src/karyu_tech_news/tts/engine.py`、`src/karyu_tech_news/tts/irodori.py`、`src/karyu_tech_news/tts/synthesize.py`、`tests/test_tts_irodori.py`、`tests/test_tts_synthesize.py`
- `git status --short --branch` → PR 差分外の未コミット変更あり: `.env.example`、`docs/IMPLEMENTATION_PLAN-2.md`、`docs/PROJECT_STATE.md`、`docs/QA_REPORT.md`。本レビューはユーザー指定どおり `main...HEAD` を対象にし、未コミット差分は戻していない。

### 根拠とした差分/行

- `scripts/daily_pipeline.sh:14-27` — `set -e` を使わず、launchd 環境の PATH、`IRODORI_TIMEOUT=300`、`IRODORI_HF_CHECKPOINT=Aratako/Irodori-TTS-600M-v3-VoiceDesign` を明示。
- `scripts/daily_pipeline.sh:37-67` — Irodori health check は `curl --max-time 5`、未起動時のみ server 起動、最大 180 秒 health 待ち。health 未到達でも fail-open 続行。
- `scripts/daily_pipeline.sh:41-48` — `mkdir` による原子的ロックで多重起動を回避。
- `scripts/daily_pipeline.sh:70-83` — `collect` / `draft` / `produce` を `run_step` で順次実行し、各段失敗時も次段へ進む。
- `scripts/daily_pipeline.sh:85-95` — 本ジョブが起動した server のみ、`ps ... | grep irodori_openai_tts` で確認してから kill。
- `scripts/launchd/com.karyu.daily-pipeline.plist:21-58` — `ProgramArguments`、`WorkingDirectory`、2026-06-24/25/26 06:30 の `StartCalendarInterval`、stdout/stderr log path。
- `config/hal_persona.yaml:41-57` — primary engine、VoiceDesign caption、Irodori 公式語彙に寄せた tone 別絵文字 mapping。
- `src/karyu_tech_news/main.py:521-590` — `produce` が `tts.caption` / `emoji_annotation` / reading dict を persona yaml から読み、`synthesize_script(..., emoji_mapping=..., caption=...)` へ配線。
- `src/karyu_tech_news/tts/engine.py:38-55` — `Capabilities.voice_design` と `SynthesisRequest.caption` の契約追加。
- `src/karyu_tech_news/tts/irodori.py:36-61` — 既定 timeout 300 秒、`IRODORI_TIMEOUT` 不正値は既定へ fail-open fallback。
- `src/karyu_tech_news/tts/irodori.py:80-90` — base URL / model / API key / timeout / caption を env または引数から解決し、秘密は header のみ。
- `src/karyu_tech_news/tts/irodori.py:98-120` — `voice_design=True`、caption がある場合だけ OpenAI 互換 body の `irodori.caption` に送出。
- `src/karyu_tech_news/tts/irodori.py:136-168` — `httpx.post(... timeout=self._timeout)`、最大 2 retry、エラーは status code または型名のみで秘密を出さない。
- `src/karyu_tech_news/tts/synthesize.py:55-69` — 文分割は str コードポイント単位で、max_chars 超過も byte slicing なし。
- `src/karyu_tech_news/tts/synthesize.py:131-150` — capabilities で文単位絵文字と caption を gate し、非対応 engine には caption を渡さない。
- `src/karyu_tech_news/tts/synthesize.py:152-160` — 1 文の `TTSError` は warning + skip で fail-open、結合済み wav を返す。
- `tests/test_tts_irodori.py:153-187` — timeout 300 秒、env override、不正 env fallback の回帰テスト。
- `tests/test_tts_irodori.py:192-227` — voice_design capability、caption body 送出、request caption 優先、caption 無し時に `irodori` key を省くテスト。
- `tests/test_tts_synthesize.py:151-183` — 絵文字を文単位で挿入し、非対応 engine / mapping 無しでは無効化するテスト。
- `tests/test_tts_synthesize.py:207-228` — VoiceDesign 対応 engine だけ caption を受け、非対応 engine では `None` に落とすテスト。
- `/Users/kairyon/tools/Irodori-TTS-Server/src/irodori_openai_tts/config.py:10-25` — server 側 env prefix は `IRODORI_`、`hf_checkpoint` は存在し、`IRODORI_HF_CHECKPOINT` が有効。
- `/Users/kairyon/tools/Irodori-TTS-Server/src/irodori_openai_tts/app.py:34-42` / `/Users/kairyon/tools/Irodori-TTS-Server/src/irodori_openai_tts/app.py:80-90` — server 側 `IrodoriOptions.caption` / `cfg_scale_caption` と `SpeechRequest.irodori` が存在。
- `/Users/kairyon/tools/Irodori-TTS-Server/src/irodori_openai_tts/app.py:783-790` — server 側 `SamplingRequest.caption` / `cfg_scale_caption` へ配線済み。
- `src/karyu_tech_news/collect/normalize.py:62-76` / `src/karyu_tech_news/collect/normalize.py:119-129` — FR-021 item_key 生成順 `external_id` → `link` → `sha256(title|published_at|source_id)` と空 item_key 拒否は維持。
- `src/karyu_tech_news/store/schema.py:52-57` — FR-031 `UNIQUE(source_id,item_key)` のみ。`hash` 単体 UNIQUE なし。
- `src/karyu_tech_news/store/repo.py:77-106` — insert 直前の空 item_key 拒否と既存 `(source_id,item_key)` skip。
- `src/karyu_tech_news/store/repo.py:109-131` — source_health は成功で `consecutive_failures=0` / `last_error=None`、失敗で +1 / `last_error` 保存。
- `src/karyu_tech_news/collect/runner.py:42-79` — 1 ソース fetch/DB 失敗時も後続 source へ進み、run を完了する fail-open。
- `src/karyu_tech_news/deliver/discord.py:82-105` / `src/karyu_tech_news/deliver/discord.py:108-145` — Webhook / mp3 投稿失敗は False を返し、HTTP status code または例外型名のみをログ化。
- `docs/IMPLEMENTATION_PLAN-2.md:66-70` / `docs/IMPLEMENTATION_PLAN-2.md:88-94` — Sprint 2 のテスト方針、str 単位分割、TTS 文単位 fail-open、動画/YouTube 禁止。
- `docs/editorial-policy.md:79-87` / `docs/hal-persona.md:35-39` — ナショナリズム表現、中国メディア本文朗読、無断声クローン禁止。
- `docs/hal-persona.md:51-58` — Irodori VoiceDesign、読み仮名辞書、絵文字注釈の方針。
- `docs/show-format.md:72-81` — BGM、-16 LUFS、mp3 192kbps/48kHz、素材ライセンス方針。
- `docs/PROJECT_STATE.md:8-12` と `docs/PROJECT_STATE.md:27-28` — T34 実装完了の記述と「本採用残作業は未着手」の記述が同居しており、Medium 指摘の根拠。
- `docs/TEST_LOG.md:951-1011` — T24/T30/T31 までの実音声・完パケ証跡はあるが、T33/T34 の 371/374/380 gate と 600M/caption E2E 証跡は未追記。

### 実行/確認したテスト

- `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run pytest tests/test_tts_irodori.py tests/test_tts_synthesize.py -q` → `43 passed`。
- `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run pytest` → `380 passed in 1.88s`。
- `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run ruff check .` → `All checks passed!`。
- `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run mypy src tests` → `Success: no issues found in 68 source files`。
- `bash -n scripts/daily_pipeline.sh` → exit 0。
- `plutil -lint scripts/launchd/com.karyu.daily-pipeline.plist` → `OK`。
- `git diff --check main...HEAD` → 出力なし。
- `git ls-files -u` → 出力なし。
- `rg -n '^(<<<<<<<|=======|>>>>>>>)' . --glob '!docs/REVIEW_REPORT.md'` → no matches (exit 1、実 conflict marker なし)。
- `git ls-files .env data/state.db artifacts assets | sort` → 出力なし。
- secret scan (`discord.com/api/webhooks/...`、`DISCORD_WEBHOOK_URL=.*https://`、長さ付き `sk-`、Slack/GitHub token 形を `uv.lock` / `docs/REVIEW_REPORT.md` / `tests/**` 除外で検索) → no matches。
- スコープ外検索 (`playwright` / `moviepy` / `youtube` / `googleapiclient` / `selenium` / `puppeteer` 等を `src config scripts tests docs/PROJECT_STATE.md` で検索) → 実装 import / 実行経路なし。`requires_cookie` は既存 source schema/config のみ。
- `UV_CACHE_DIR=/private/tmp/panda-tech-news-uv-cache uv run --with pytest-cov pytest --cov=karyu_tech_news --cov-report=term-missing` → ネットワーク制限で `pytest-cov` を取得できず失敗 (`Failed to fetch: https://pypi.org/simple/pytest-cov/`)。fresh coverage は未測定。既存証跡は `docs/TEST_LOG.md:807-809` の 96% と、T31 までの gate 証跡 `docs/TEST_LOG.md:1011` を参照。

### DESIGN.md / IMPLEMENTATION_PLAN-2.md との対応

- DESIGN.md §1 / §6 / §7 の fail-open と timeout 必須に対し、collect 既存 fail-open は `collect/runner.py` と `tests/test_runner_fail_open.py:122-160` で維持され、Irodori HTTP も `timeout=self._timeout` で明示されている。
- DESIGN.md §4.1 / AGENTS.md §3.2 の item_key / UNIQUE 不変条件は、今回差分で触られておらず、実装行も維持されている。
- DESIGN.md §7 / AGENTS.md §3.5 の秘密保護に対し、Webhook URL や API key は `.env` / header 経由で、ログは status code / exception class に限定されている。secret scan でも実キー混入なし。
- IMPLEMENTATION_PLAN-2.md §3 / §4 の `script -> tts -> mix` 一方向と T31 produce 経路に対し、今回差分は `main.py` の produce から `tts.synthesize` / `mix` を呼ぶ既存方向の拡張のみ。
- IMPLEMENTATION_PLAN-2.md §5 / §8 の str 単位分割、TTS 1 文 fail-open、生成 mp3/wav 非管理は `tts/synthesize.py` と `.gitignore:16-25` に適合。
- Sprint 2 境界: TTS / mp3 / Discord は Sprint 2 範囲。動画生成、YouTube 投稿、Playwright、Cookie 必須 route、Go/Node 導入は今回差分にない。
- コンテンツ方針: `strip_markdown_structure` 後の produce 経路は維持され、中国メディア本文の転載やナショナリズム表現を新たに生成する差分はない。PR 内の caption は「落ち着いた知的な女性ニュースキャスター...」で、実在人物の声真似指定ではない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | なし | なし |
| Medium | `docs/PROJECT_STATE.md:8-12` / `docs/PROJECT_STATE.md:27-28` | 同一ファイル内で「T34 (Irodori 600M VoiceDesign + caption本採用) 実装完了」と、「本採用の残作業は未着手 (人間の聴感 Go 待ち)」が併存している。コード差分は `daily_pipeline.sh` の 600M checkpoint と `config/hal_persona.yaml` の caption、`irodori.py` の caption 送出まで実装済みなので、PROJECT_STATE を真の記憶とする運用上、次のエージェントが T34 の状態を誤判定しうる。 | PR #22 の最終状態に合わせ、T34 が「本採用済み」なのか「実験止まり・未採用」なのかを 1 つに統一する。少なくとも `docs/PROJECT_STATE.md:27-28` の古い未着手文を改訂し、残作業があるなら実装済み部分と未実施部分を分けて書く。 |
| Medium | `docs/TEST_LOG.md:951-1011` / `docs/PROJECT_STATE.md:11` | `TEST_LOG.md` は T31 の `pytest 363` までで止まっており、T33/T33+/T34 の 371/374/380 gate、launchd/plist 静的検証、600M+caption produce E2E 証跡がない。AGENTS.md §8.3 とレビュー prompt は TEST_LOG の該当エントリ参照を要求しているため、現状の fresh gate はレビュー実行結果と PROJECT_STATE/QA_REPORT にはあるが、指定された証跡台帳に残っていない。 | `docs/TEST_LOG.md` に T33/T33+/T34 の実行ログを追記する。最低限、`pytest 380 passed` / `ruff` / `mypy`、`bash -n`、`plutil -lint`、実 E2E produce の結果、Discord 投稿結果、既知リスクを記録する。 |
| Low | `scripts/daily_pipeline.sh:41-48` / `scripts/daily_pipeline.sh:85-95` / `scripts/launchd/com.karyu.daily-pipeline.plist:30-58` | shell/plist は静的検証済みだが、ロック取得時の早期終了、PID 再利用ガード、launchd 日付設定を固定する自動テストはない。今回の差分規模では merge blocker ではないが、無人運用の中核なので将来変更時に壊れやすい。 | shell を直接単体テストするか、少なくとも `scripts/` 向けの smoke/fixture 検証手順を `TEST_LOG.md` に固定する。 |

### セキュリティ / 並行性

- secret commit: `.env` / `data/state.db` / `artifacts` / `assets` の実体は追跡されていない。`.gitignore:1-25` で `.env`、`data/`、音声/動画、素材本体は除外。
- secret 直書き: token 形の検索で実キーは検出されなかった。`IRODORI_API_KEY` は env から読み、Authorization header のみに使われる。
- secret ログ: Discord と Irodori は例外文字列をそのままログに出さず、status code または例外型名に限定している。
- SQL injection: 今回差分に raw SQL 追加なし。既存 DB 操作は SQLAlchemy ORM / `select()` 経由。
- 並行性: Sprint 1A の単一プロセス前提は維持。T33 の launchd/手動多重起動に対しては `mkdir` ロックで同一ジョブの並走を抑止している。
- 外部サーバ契約: ローカル Irodori-TTS-Server には `IRODORI_HF_CHECKPOINT` と nested `irodori.caption` の受け口が存在することを実ファイルで確認した。

### PR コメント案

PR #22 は PASS です。Critical 0 / High 0 / Medium 2 / Low 1。T33/T33+/T34 の実装は Sprint 2 範囲内で、fail-open、timeout 指定、secret 非漏洩、動画/YouTube 越境なしを確認しました。fresh gate も `pytest 380 passed`、ruff、mypy、`bash -n`、`plutil -lint` が通っています。

Medium はドキュメント整合です。`PROJECT_STATE.md` 内に T34 本採用完了と「本採用残作業は未着手」が併存している点、`TEST_LOG.md` が T31 までで止まり T33/T34 の gate/E2E 証跡が無い点は、merge 前または直後に必ず同期してください。機能・セキュリティ上の merge blocker は見つけていません。

## PR #22 追加コミット c7182e5 / T35 レビュー (レビュー日: 2026-06-24 / レビュアー: Codex)

### 総合判定: FAIL

Critical 0 / High 1 / Medium 2 / Low 0。無音バグ修正は launchd の bare PATH 起因という根因に合っており、`ffmpeg` の PATH 解決にも効く。一方、T35 の重点である「日本語ナレーションの漢字や日本語引用を誤って pinyin 化しないか」に対し、漢字だけの日本語引用を中国語扱いして pinyin 化する High を確認したため、PASS 不可。

### 確認したファイル

- `AGENTS.md`
- `docs/DESIGN.md`
- `docs/IMPLEMENTATION_PLAN-2.md`
- `docs/TEST_LOG.md`
- `docs/editorial-policy.md`
- `docs/hal-persona.md`
- `docs/show-format.md`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `scripts/daily_pipeline.sh`
- `src/karyu_tech_news/main.py`
- `src/karyu_tech_news/mix/master.py`
- `src/karyu_tech_news/script/fallback.py`
- `src/karyu_tech_news/tts/normalize.py`
- `src/karyu_tech_news/tts/synthesize.py`
- `tests/test_tts_normalize.py`

### レビュー対象

- `git status --short --branch` → `agent/T33-daily-pipeline-impl...origin/agent/T33-daily-pipeline-impl`。レビュー開始時点で未コミット変更あり: `.env.example`, `docs/IMPLEMENTATION_PLAN-2.md`。レビュー対象外として未変更。
- `git show --stat --oneline c7182e5` → T35 対象 6 ファイル: `pyproject.toml`, `scripts/daily_pipeline.sh`, `src/karyu_tech_news/tts/normalize.py`, `src/karyu_tech_news/tts/synthesize.py`, `tests/test_tts_normalize.py`, `uv.lock`。
- `git diff --stat main...HEAD` → PR #22 全体 19 ファイル。T35 は追加コミット `c7182e5` を中心に確認し、PR 全体の secret / 生成物 / スコープ外混入も検索。

### 根拠とした差分/行

- `scripts/daily_pipeline.sh:16-19` — launchd の bare PATH に `/opt/homebrew/bin:/usr/local/bin` を追加。`master_to_mp3` は `shutil.which("ffmpeg")` で PATH 解決するため、無人実行の ffmpeg 不在には有効。
- `scripts/daily_pipeline.sh:76-89` — `collect` / `draft` / `produce` は `run_step` で fail-open 実行され、produce 失敗はログに残して次へ進む既存設計。
- `src/karyu_tech_news/mix/master.py:69-73` — `ffmpeg` 不在時は `MasteringError("ffmpeg が見つかりません...")`。今回の PATH 追加はこの探索経路を補正している。
- `src/karyu_tech_news/tts/normalize.py:113-115` — 漢字検出 `_HAN_RE` とかな検出 `_KANA_RE`、対象範囲 `_QUOTED_RE`。
- `src/karyu_tech_news/tts/normalize.py:118-128` — `pypinyin` import は遅延し、未導入時は warning + 原文返却で fail-open。
- `src/karyu_tech_news/tts/normalize.py:131-143` — `「」` 内に漢字があり、かなが無ければ `_han_to_pinyin()` を適用する本体。
- `src/karyu_tech_news/tts/synthesize.py:139-144` — Markdown/ASCII gloss/読み辞書正規化後、文分割前に `transliterate_chinese_titles` を配線。
- `src/karyu_tech_news/script/fallback.py:32-36` / `src/karyu_tech_news/script/fallback.py:42-52` — fallback template は `「{title}」` で原題を引用するため、T35 の対象となる根拠。
- `tests/test_tts_normalize.py:115-135` — 中国語タイトル、かなを含む日本語引用、引用なし日本語ナレーション、中国語 span 限定の 4 テスト。ただし漢字だけの日本語引用は未カバー。
- `pyproject.toml:11-20` — `pypinyin>=0.55.0` を core dependency に追加。
- `uv.lock:648-656` / `uv.lock:673-685` / `uv.lock:890-896` — `pypinyin` が project の通常依存に入り、lock された。
- `docs/IMPLEMENTATION_PLAN-2.md:33-46` — Sprint 2 の新規依存は `ffmpeg` と optional `pydub` と記載され、「これ以外を足す場合は ADR」。
- `docs/IMPLEMENTATION_PLAN-2.md:84-88` — Sprint 2 固有 NG: TTS 1 文 fail-open、バイト単位切り詰め禁止、生成 mp3/wav commit 禁止。
- `docs/architecture-podcast-station.md:96-103` / `docs/hal-persona.md:51-58` / `docs/adr/ADR-0006-tts-irodori-abstraction.md:27-34` — Irodori の漢字読み弱点対策として読み仮名辞書・TTS 前処理を置く方針。
- `docs/editorial-policy.md:79-87` / `docs/hal-persona.md:35-39` — ナショナリズム表現、中国メディア本文朗読、実在人物声真似禁止。T35 差分に新規違反なし。
- `.gitignore:1-25` — `.env`, `data/`, 音声/動画生成物、素材本体を除外。
- `docs/TEST_LOG.md:1032` — T35 の無音バグ根因、翻字 smoke、`pytest 387` / ruff / mypy / shell 静的検証、実 produce 証跡の記録。

### 実行/確認したテスト

- 初回 `uv run pytest` / `uv run ruff check .` / `uv run mypy src tests` → sandbox が `/Users/kairyon/.cache/uv` を読めず起動前失敗 (`Operation not permitted`)。環境制約として扱い、`UV_CACHE_DIR=/private/tmp/karyu-uv-cache` で再実行。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run pytest` → `387 passed in 3.09s`。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run ruff check .` → `All checks passed!`。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run mypy src tests` → `Success: no issues found in 68 source files`。
- `bash -n scripts/daily_pipeline.sh && shellcheck scripts/daily_pipeline.sh` → exit 0。
- `git diff --check main...HEAD` → 出力なし。
- `git ls-files -u` → 出力なし。
- `rg -n '^(<<<<<<<|=======|>>>>>>>)' . --glob '!docs/REVIEW_REPORT.md'` → no matches (exit 1)。
- `git ls-files | rg '(^|/)\.env$|^data/|^artifacts/|\.(mp3|mp4|wav|m4a)$' || true` → 出力なし。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run pytest --cov=src/karyu_tech_news` → pytest-cov 未導入で `unrecognized arguments: --cov=src/karyu_tech_news`。fresh coverage は未測定。
- 翻字挙動 smoke:
  - `「三星电子HBM4」というニュース。` → `「san xing dian zi HBM4」というニュース。`
  - `「日本語の引用」が話題。` → 不変
  - `「生成AI」が話題です。` → `「sheng cheng AI」が話題です。`
  - `「東京大学」が発表しました。` → `「dong jing da xue」が発表しました。`
  - `「人工知能」は重要です。` → `「ren gong zhi neng」は重要です。`

### DESIGN.md / IMPLEMENTATION_PLAN-2.md との対応

- DESIGN.md §1 / §6 / §7 の fail-open と webhook 失敗非致命化は、T35 差分で破壊されていない。T35 の pypinyin import 失敗時も原文返却で fail-open。
- DESIGN.md §4.1 / §7 の item_key 生成順と `UNIQUE(source_id,item_key)` は T35 差分で触られていない。
- DESIGN.md §9 / IMPLEMENTATION_PLAN-2.md §3 の Sprint 境界では、T35 は Sprint 2 の TTS/音声前処理と日次 mp3 配信修正に収まる。動画/YouTube/Playwright/Cookie 必須ルートの実装追加なし。
- IMPLEMENTATION_PLAN-2.md §3 の依存制約に対し、`pypinyin` は機能上は TTS 前処理のため妥当性があるが、計画上の「ffmpeg + pydub 以外は ADR」には未対応。
- IMPLEMENTATION_PLAN-2.md §5 / §8 の str 単位処理は維持。T35 の翻字は文字列置換であり、バイト切り詰めはしていない。
- ADR-0006 / architecture-podcast-station / hal-persona の「Irodori は日本語特化で漢字読みが弱い、読み辞書・前処理で補う」方針には沿う。ただし今回のかな有無 heuristic は日本語引用を守るには不足。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `src/karyu_tech_news/tts/normalize.py:137-143` / `tests/test_tts_normalize.py:121-129` | 「漢字あり・かななし」のみで中国語原題と判定しているため、漢字だけの日本語引用を pinyin 化する。実測で `「生成AI」`、`「東京大学」`、`「人工知能」` がそれぞれ `sheng cheng AI` / `dong jing da xue` / `ren gong zhi neng` になった。T35 の重点である「日本語ナレーションの漢字や日本語引用を誤って pinyin 化しないか」に対し、かな判定は十分でない。 | 中国語原題である根拠をもう一段強める。例: fallback title 由来の span だけに metadata で印を付ける、簡体字特有文字の存在を条件にする、読み辞書/日本語 allowlist 後に除外する、または fallback template 側で中国語タイトル専用の前処理を呼ぶ。少なくとも漢字だけの日本語引用 (`生成AI`, `東京大学`, `人工知能` 等) を不変にする回帰テストを追加する。 |
| Medium | `docs/IMPLEMENTATION_PLAN-2.md:33-46` / `pyproject.toml:11-20` / `uv.lock:648-656` | `pypinyin` は TTS の中国語原題対策として機能的には理解できるが、Sprint 2 計画は新規依存を `ffmpeg` + optional `pydub` に限定し、それ以外は ADR と明記している。さらに `pypinyin` は `tts` extra ではなく core dependency に入っており、収集・台本だけの利用者にも常時入る。 | ADR または IMPLEMENTATION_PLAN-2.md に `pypinyin` 採用理由・代替案・依存スコープを追記する。可能なら TTS 専用 extra へ寄せるか、core に置く理由を明記する。 |
| Medium | `src/karyu_tech_news/tts/normalize.py:123-128` / `tests/test_tts_normalize.py:115-135` | pypinyin 未導入時の fail-open 実装はあるが、テストは通常 import 成功パスのみ。T35 の受け入れ観点に fail-open が含まれているため、ImportError 時に原文返却する回帰が固定されていない。 | `monkeypatch` で `pypinyin` import を失敗させる、または `_han_to_pinyin` の依存注入を切って、未導入時に原文が残るテストを追加する。 |
| Low | なし | なし | なし |

### セキュリティ / 並行性 / スコープ

- secret: `.env` / `data/` / `artifacts` / 音声動画生成物は追跡されていない。Webhook URL の直書きは今回差分にない。
- SQL injection: T35 差分に SQL / raw SQL 追加なし。
- 並行性: T35 差分は既存 `mkdir` lock に変更なし。Sprint 1A の単一プロセス前提を壊していない。
- Webhook fail-open: T35 差分は deliver 層に触っていない。既存 `post_audio` / `post_markdown` の失敗非致命化は維持。
- スコープ外混入: 動画生成、YouTube 投稿、Playwright、Cookie 必須 route、Go/Node 導入はなし。
- 無音バグ修正: PATH 追加は `master_to_mp3` の `ffmpeg` 探索に直接効くため根因修正として妥当。ただし produce が失敗した日の Discord 通知は既知リスクのまま。

### PR コメント案

PR #22 追加コミット `c7182e5` / T35 は **FAIL** です。Critical 0 / High 1 / Medium 2 / Low 0。

無音バグ修正は妥当です。`daily_pipeline.sh` の PATH に `/opt/homebrew/bin:/usr/local/bin` を足す変更は、`master_to_mp3` が `shutil.which("ffmpeg")` で探索する実装と一致しており、launchd の bare PATH 起因の ffmpeg 不在に効きます。fresh gate も `pytest 387 passed`、ruff、mypy、`bash -n` + shellcheck が通りました。

ただし翻字 heuristic が High です。`「」` 内の「漢字あり・かななし」を中国語原題とみなすため、漢字だけの日本語引用も pinyin 化します。実測で `「生成AI」` → `「sheng cheng AI」`、`「東京大学」` → `「dong jing da xue」`、`「人工知能」` → `「ren gong zhi neng」` になりました。T35 の重点である「日本語ナレーションの漢字や日本語引用を誤って pinyin 化しないか」に対し、かな判定だけでは不足です。

修正方針は、fallback title 由来の span だけを対象にする、簡体字特有文字の存在を条件にする、日本語 allowlist / 読み辞書後の除外を入れる、などで中国語原題の根拠を強めてください。あわせて漢字だけの日本語引用を不変にする回帰テストと、pypinyin 未導入時 fail-open のテストを追加してください。`pypinyin` を core dependency に入れる点も、IMPLEMENTATION_PLAN-2.md の「ffmpeg + pydub 以外は ADR」とずれるため、ADR/計画追記または optional extra 化の判断を残す必要があります。

## PR #22 追加コミット 1fb38ed / T35 再レビュー (レビュー日: 2026-06-24 / レビュアー: Codex)

### 総合判定: FAIL

Critical 0 / High 1 / Medium 1 / Low 0。前回 High の「漢字のみ日本語引用を pinyin 化する」問題は、簡体字特有文字を必須にする条件と回帰テストで解消を確認した。一方、`pypinyin` を optional extra `tts` へ移した結果、リポジトリ標準の通常テスト環境では pinyin 成功テストが必要依存なしで走りうるため、新規 High として FAIL 判定にする。

### 確認したファイル

- `AGENTS.md`
- `docs/DESIGN.md`
- `docs/IMPLEMENTATION_PLAN-2.md`
- `docs/PROJECT_STATE.md`
- `docs/TEST_LOG.md`
- `docs/REVIEW_REPORT.md`
- `docs/editorial-policy.md`
- `docs/hal-persona.md`
- `docs/show-format.md`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `scripts/daily_pipeline.sh`
- `src/karyu_tech_news/mix/master.py`
- `src/karyu_tech_news/script/fallback.py`
- `src/karyu_tech_news/tts/normalize.py`
- `src/karyu_tech_news/tts/synthesize.py`
- `tests/test_tts_normalize.py`

### レビュー対象

- `git status --short --branch` → `agent/T33-daily-pipeline-impl...origin/agent/T33-daily-pipeline-impl`、作業ツリー未コミット変更は `docs/REVIEW_REPORT.md` のみ。
- `git show --stat --oneline --decorate --no-renames 1fb38ed` → `pyproject.toml`、`src/karyu_tech_news/tts/normalize.py`、`tests/test_tts_normalize.py`、`uv.lock` の 4 ファイル。
- `git diff --stat --no-renames main...HEAD` → PR #22 全体 21 ファイル。T35 再レビューは追加コミット `1fb38ed` と、依存/証跡整合のため `main...HEAD` を確認。

### 根拠とした差分/行

- `src/karyu_tech_news/tts/normalize.py:111-124` — 判定条件を「漢字あり・かな無し・簡体字特有文字あり」に強化し、日本語新字体と同形の共有字は除外。
- `src/karyu_tech_news/tts/normalize.py:128-138` — `pypinyin` は遅延 import、未導入時は warning + 原文返却で fail-open。
- `src/karyu_tech_news/tts/normalize.py:147-156` — `any(ch in _SIMPLIFIED_HAN for ch in inner)` を満たす引用 span のみ `_han_to_pinyin()` を適用。
- `src/karyu_tech_news/tts/synthesize.py:139-144` — Markdown/ASCII gloss/読み辞書正規化後、文分割前に `transliterate_chinese_titles` を適用。
- `tests/test_tts_normalize.py:118-138` — 中国語原題の肯定ケース、かな入り日本語引用、引用なし日本語ナレーション、中国語 span 限定のテスト。
- `tests/test_tts_normalize.py:141-153` — `生成AI` / `東京大学` / `人工知能` / `国際会議` / `機械学習` / `半導体` / `自動運転` の不変テストと、簡体字肯定テスト。
- `tests/test_tts_normalize.py:156-160` — `pypinyin` 未導入時の fail-open テスト。
- `pyproject.toml:11-19` — core dependencies から `pypinyin` が除外されている。
- `pyproject.toml:23-28` — `pypinyin>=0.55.0` は optional extra `tts` のみ。
- `pyproject.toml:30-35` — dev dependency group に `pypinyin` は含まれていない。
- `uv.lock:650-656` — project 通常依存に `pypinyin` は含まれていない。
- `uv.lock:658-663` / `uv.lock:673-680` — `pypinyin` は `extra == 'tts'` marker 付き optional dependency。
- `docs/IMPLEMENTATION_PLAN-2.md:44-46` — 新規依存は ffmpeg + pydub 以外は ADR としていた制約。
- `docs/IMPLEMENTATION_PLAN-2.md:66` — T35 の `pypinyin` 採用理由、core ではなく optional extra `tts` に置く判断、簡体字特有文字条件を追記済み。
- `docs/TEST_LOG.md:1032` / `docs/PROJECT_STATE.md:30` — T35 証跡が `c7182e5`、旧 heuristic、`pytest 387` のままで、`1fb38ed` / `pytest 396` / optional extra 化が未反映。
- `docs/editorial-policy.md:79-87` / `docs/hal-persona.md:35-39` — ナショナリズム表現、中国メディア本文朗読、実在人物声真似禁止。T35 再差分に新規違反なし。

### 実行/確認したテスト

- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run pytest tests/test_tts_normalize.py -q` → `28 passed`。
- 翻字 smoke:
  - `「生成AI」が話題です。` → 不変
  - `「東京大学」が発表しました。` → 不変
  - `「人工知能」は重要です。` → 不変
  - `「三星电子HBM4」というニュース。` → `「san xing dian zi HBM4」というニュース。`
  - `今日は「豆包发布」を取り上げます。` → `今日は「dou bao fa bu」を取り上げます。`
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run pytest` → `396 passed in 1.86s`。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run ruff check .` → `All checks passed!`。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache uv run mypy src tests` → `Success: no issues found in 68 source files`。
- `bash -n scripts/daily_pipeline.sh && shellcheck scripts/daily_pipeline.sh` → exit 0。
- `git diff --check main...HEAD` → 出力なし。
- `git ls-files -u` → 出力なし。
- `rg -n '^(<<<<<<<|=======|>>>>>>>)' . --glob '!docs/REVIEW_REPORT.md'` → no matches (exit 1)。
- secret scan (`discord.com/api/webhooks/...`、`DISCORD_WEBHOOK_URL=.*https://`、`sk-...`、GitHub/Slack token 形を `uv.lock` / `docs/REVIEW_REPORT.md` / `tests/**` 除外で検索) → no matches。
- スコープ外検索 (`playwright` / `moviepy` / `googleapiclient` / `selenium` / `puppeteer` / `youtube` を `src config scripts tests docs/PROJECT_STATE.md` で検索) → 実装 import / 実行経路なし。
- `UV_CACHE_DIR=/private/tmp/karyu-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/panda-review-noextra-venv uv run pytest tests/test_tts_normalize.py -q` → fresh 環境作成中にネットワーク制限で `python-dotenv` wheel 取得に失敗。クリーン default 環境の実測は未完了。
- 代替確認: 現在環境では `pypinyin installed: True`。`builtins.__import__` で `pypinyin` import を遮断すると `transliterate_chinese_titles("「三星电子HBM4」というニュース。")` は原文返却となり、`tests/test_tts_normalize.py:118-121` / `tests/test_tts_normalize.py:151-153` の pinyin 成功期待値は満たせない。
- fresh coverage: `pytest-cov` が標準 dev 依存に無いため未測定。既存の 80% 以上証跡は過去ログ参照に留まる。

### DESIGN.md / IMPLEMENTATION_PLAN-2.md との対応

- DESIGN.md §1 / §6 / §7 の fail-open と webhook 失敗非致命化は T35 再差分で破壊されていない。`pypinyin` 未導入時も原文返却で produce 自体は継続する。
- DESIGN.md §4.1 / §7 の item_key 生成順と `UNIQUE(source_id,item_key)` は T35 再差分で触られていない。
- DESIGN.md §9 / IMPLEMENTATION_PLAN-2.md §3 の Sprint 境界では、T35 は Sprint 2 の TTS 前処理と日次 mp3 配信修正に収まる。動画/YouTube/Playwright/Cookie 必須ルートの実装追加なし。
- IMPLEMENTATION_PLAN-2.md §3 の依存制約に対し、`pypinyin` 採用理由と optional extra 化は `docs/IMPLEMENTATION_PLAN-2.md:66` で説明されたため、前回 Medium は解消。
- IMPLEMENTATION_PLAN-2.md §5 / §8 の str 単位処理は維持。T35 の翻字は文字列置換であり、バイト切り詰めはしていない。
- editorial-policy / hal-persona / show-format との矛盾は見当たらない。翻字は中国語原題の読み崩れ対策であり、本文転載や実在人物声真似を追加していない。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | `pyproject.toml:23-35` / `tests/test_tts_normalize.py:118-121` / `tests/test_tts_normalize.py:151-153` / `src/karyu_tech_news/tts/normalize.py:133-138` | `pypinyin` は optional extra `tts` のみに移ったが、通常の pytest suite には pinyin 成功を必須にするテストが常時含まれている。標準ゲートは AGENTS.md / TEST_LOG とも `uv run pytest` で、`uv run --extra tts pytest` ではない。現在の `.venv` では過去の core 依存時代の `pypinyin` が残っているため `396 passed` になっているが、import を遮断すると肯定ケースは fail-open で原文返却になり期待値を満たさない。クリーン default 環境では品質ゲートが赤になる、または T35 の肯定経路がテストされない構造。 | core を増やさない方針を維持するなら `pypinyin` を dev dependency group にも入れて標準 `uv run pytest` の依存にする、または positive pinyin テストを `pytest.importorskip("pypinyin")` 等で extra 依存テストとして明示し、PR ゲートに `uv run --extra tts pytest tests/test_tts_normalize.py` を追加する。 |
| Medium | `docs/TEST_LOG.md:1032` / `docs/PROJECT_STATE.md:30` | 永続証跡が追加コミット `c7182e5` 時点のまま。旧 heuristic「漢字あり・かな無し」、`pytest 387`、test 4 種、`pypinyin` 依存追加という記述で、`1fb38ed` の簡体字条件、optional extra 化、`pytest 396`、回帰テスト追加が反映されていない。レビュー prompt は TEST_LOG の該当エントリ参照を要求しており、PROJECT_STATE は真の記憶なので、次のエージェントが古い状態を信じるリスクがある。 | `docs/TEST_LOG.md` と `docs/PROJECT_STATE.md` に `1fb38ed` の修正内容、最新 gate、依存スコープ判断、残リスクを追記/更新する。 |
| Low | なし | なし | なし |

### セキュリティ / 並行性 / スコープ

- secret: `.env` / `data/` / `artifacts` / 音声動画生成物は追跡されていない。Webhook URL の直書きは今回差分にない。
- SQL injection: T35 再差分に SQL / raw SQL 追加なし。
- 並行性: T35 再差分は既存 `mkdir` lock に変更なし。Sprint 1A の単一プロセス前提を壊していない。
- Webhook fail-open: T35 再差分は deliver 層に触っていない。既存 `post_audio` / `post_markdown` の失敗非致命化は維持。
- スコープ外混入: 動画生成、YouTube 投稿、Playwright、Cookie 必須 route、Go/Node 導入はなし。
- 依存 scope: `pypinyin` を runtime core から `tts` extra へ移した判断自体は妥当。ただしテスト環境への供給方法が未解決。

### PR コメント案

PR #22 追加コミット `1fb38ed` / T35 再レビューは **FAIL** です。Critical 0 / High 1 / Medium 1 / Low 0。

前回 High の誤翻字は解消しています。`生成AI`、`東京大学`、`人工知能` は不変で、`三星电子HBM4` と `豆包发布` は pinyin 化されることを smoke と回帰テストで確認しました。`pytest 396 passed`、ruff、mypy、shellcheck、secret/scope 検索も現在環境では通っています。

新規 High は依存とテストゲートの不整合です。`pypinyin` は `tts` optional extra のみに移っていますが、標準の `uv run pytest` に含まれる `tests/test_tts_normalize.py` は pinyin 成功を必須にしています。現在の `.venv` には過去依存として `pypinyin` が残っているため緑ですが、import を遮断すると肯定ケースは fail-open で原文返却になり期待値を満たしません。core を増やさないなら `pypinyin` を dev dependency にも入れるか、positive pinyin テストを extra 依存として明示し、PR ゲートに extra 付き pytest を追加してください。

Medium は証跡更新です。`docs/TEST_LOG.md` / `docs/PROJECT_STATE.md` が `c7182e5` 時点の旧 heuristic・`pytest 387` のままなので、`1fb38ed` の簡体字条件、optional extra 化、`pytest 396` を反映してください。

## PR #22 追加コミット 009a54d / T35 R3 確認レビュー (レビュー日: 2026-06-24 / レビュアー: Codex)

### 総合判定: PASS

Critical 0 / High 0 / Medium 0 / Low 0。前回 R2 High の依存/ゲート不整合は、`pypinyin` を dev dependency group にも追加し、肯定系翻字テストへ `pytest.importorskip("pypinyin")` を付与したことで解消している。標準 `uv run pytest` 相当の dev gate で `396 passed` を確認した。R2 Medium の永続証跡更新も `docs/TEST_LOG.md` / `docs/PROJECT_STATE.md` に反映済み。

### 確認したファイル

- `AGENTS.md`
- `docs/DESIGN.md`
- `docs/PROJECT_STATE.md`
- `docs/TEST_LOG.md`
- `docs/REVIEW_REPORT.md`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `scripts/daily_pipeline.sh`
- `src/karyu_tech_news/tts/normalize.py`
- `tests/test_tts_normalize.py`

### レビュー対象

- `git status --short --branch` → `agent/T33-daily-pipeline-impl...origin/agent/T33-daily-pipeline-impl`。レビュー開始時点で未コミット変更なし。
- `git show --stat --oneline --decorate --no-renames 009a54d` → `docs/PROJECT_STATE.md`, `docs/REVIEW_REPORT.md`, `docs/TEST_LOG.md`, `pyproject.toml`, `tests/test_tts_normalize.py`, `uv.lock` の 6 ファイル。
- `git show --no-ext-diff --unified=80 --no-renames 009a54d` で R2 対応差分を確認。

### 根拠とした差分/行

- `pyproject.toml:23-28` — `pypinyin>=0.55.0` は runtime core ではなく optional extra `tts` に残っている。
- `pyproject.toml:30-39` — dev dependency group に `pypinyin>=0.55.0` が追加され、標準 `uv run pytest` の dev 環境で肯定系翻字テストが依存不足にならない。
- `pyproject.toml:79-82` — optional `pypinyin` の mypy missing import override は維持。
- `tests/test_tts_normalize.py:118-122` — `三星电子HBM4` の肯定系テストは `pytest.importorskip("pypinyin")` 後に期待値を検証。
- `tests/test_tts_normalize.py:136-140` — `豆包发布` の肯定系テストも `importorskip` 付き。
- `tests/test_tts_normalize.py:153-156` — 簡体字条件の肯定側 `「电子」` も `importorskip` 付き。
- `tests/test_tts_normalize.py:143-150` — `生成AI` / `東京大学` / `人工知能` など漢字のみ日本語引用の不変回帰テストは依存なしで実行される。
- `tests/test_tts_normalize.py:159-163` — `pypinyin` 未導入時は原文返却する fail-open テスト。
- `src/karyu_tech_news/tts/normalize.py:128-138` — `pypinyin` は遅延 import され、ImportError 時は warning + 原文返却。
- `src/karyu_tech_news/tts/normalize.py:147-156` — 簡体字特有文字を含む引用 span のみ pinyin 化。
- `docs/TEST_LOG.md:1034` — R1/R2 対応、dev group 追加、`pytest 396 passed`、実 produce 証跡が追記済み。
- `docs/PROJECT_STATE.md:30-31` — T35 の旧 `c7182e5` 証跡に加え、R1/R2 レビュー反映の最終状態が追記済み。
- `.gitignore:1-25` — `.env`, `data/`, 音声/動画生成物、素材本体は git 管理外。
- `docs/DESIGN.md:14-19` — fail-open、Webhook 失敗非致命、外部依存最小化の基準。
- `docs/DESIGN.md:139-147` — item_key 生成順と空 item_key 禁止。今回差分では未変更。
- `docs/DESIGN.md:176-180` — `.env` commit 禁止など実装上の禁止事項。今回差分で抵触なし。

### 実行/確認したテスト

- `uv run pytest tests/test_tts_normalize.py` / `uv run ruff check .` 初回 → sandbox が `/Users/kairyon/.cache/uv` を読めず起動前失敗 (`Operation not permitted`)。環境制約のため repo 内 cache を指定して再実行。
- `UV_CACHE_DIR=.uv_cache uv run pytest tests/test_tts_normalize.py` → `28 passed in 0.09s`。
- `UV_CACHE_DIR=.uv_cache uv run pytest` → `396 passed in 2.06s`。
- `UV_CACHE_DIR=.uv_cache uv run ruff check .` → `All checks passed!`。
- `UV_CACHE_DIR=.uv_cache uv run mypy src tests` → `Success: no issues found in 68 source files`。
- `bash -n scripts/daily_pipeline.sh && shellcheck scripts/daily_pipeline.sh` → exit 0。
- `git ls-files .env 'data/*' 'artifacts/*' '*.mp3' '*.mp4' '*.wav' '*.m4a'` → 出力なし。
- `git grep -n "https://discord.com/api/webhooks/[0-9]" -- ':!tests/test_discord_script.py' ':!tests/test_produce_pipeline.py' ':!docs/REVIEW_REPORT.md' || true` → 出力なし。
- `UV_CACHE_DIR=.uv_cache uv run --no-dev --with pytest pytest tests/test_tts_normalize.py -k 'transliterate' -q` → `13 passed`。ただし既存 `.venv` に `pypinyin` が残っており、完全な依存なし隔離環境の証明ではない。標準 dev gate の R2 High 解消確認としては `pyproject.toml:30-39` と full pytest 実測を根拠にした。

### DESIGN.md との対応

- DESIGN.md §1 の「最小構成・fail-open・状態の外部永続化」に対し、`pypinyin` は runtime core ではなく `tts` extra + dev group に限定され、未導入時も `normalize.py:133-138` で原文返却する。
- DESIGN.md §1 / §6 の Webhook 失敗非致命・ソース単位 fail-openは、今回差分で collect / deliver 層に変更がないため維持。
- DESIGN.md §4.1 / §7 の item_key 生成順、`UNIQUE(source_id,item_key)`、空 item_key 禁止は今回差分で触っていない。
- DESIGN.md §7 と AGENTS.md §3 の禁止事項について、`.env` / 生成音声 / Webhook URL 実値の commit は検出されず、動画/YouTube/Playwright/Cookie 必須 route/Go/Node 導入もなし。
- ドキュメント整合は `docs/TEST_LOG.md:1034` と `docs/PROJECT_STATE.md:30-31` で R2 後の最終状態に同期されている。

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Critical | なし | なし | なし |
| High | なし | R2 High は解消。標準 dev gate で `pypinyin` が供給され、肯定系テストも optional 依存であることを明示している。 | なし |
| Medium | なし | R2 Medium の `TEST_LOG` / `PROJECT_STATE` 更新漏れも解消。 | なし |
| Low | なし | なし | なし |

### セキュリティ / 並行性 / スコープ

- secret: `.env` / `data/` / `artifacts` / 音声動画生成物は追跡されていない。Webhook URL 実値の直書きは今回差分にない。
- SQL injection: `009a54d` に SQL / raw SQL 追加なし。
- 並行性: `009a54d` は依存・テスト・証跡更新のみで、launchd lock や DB 更新処理に変更なし。
- Webhook fail-open: deliver 層に変更なし。既存の失敗非致命設計を壊していない。
- スコープ外混入: 動画生成、YouTube 投稿、Playwright、Cookie 必須 route、Go/Node 導入なし。

### PR コメント案

PR #22 追加コミット `009a54d` / R3 確認レビューは **PASS** です。Critical 0 / High 0 / Medium 0 / Low 0。

R2 High は解消しています。`pypinyin` は runtime core ではなく optional extra `tts` に残しつつ、dev dependency group にも追加されているため、標準 `uv run pytest` の dev 環境で肯定系翻字テストが依存不足になりません。肯定系 3 件には `pytest.importorskip("pypinyin")` が入り、`--no-dev` など依存を落とした環境では fail ではなく skip できる形になっています。未導入時の runtime fail-open テストも維持されています。

fresh gate は `UV_CACHE_DIR=.uv_cache uv run pytest` が `396 passed`、ruff、mypy strict 68 files、`bash -n` + shellcheck がすべて通過。`docs/TEST_LOG.md` と `docs/PROJECT_STATE.md` も R2 後の最終状態に同期済みです。secret、生成音声、スコープ外実装の混入も確認できませんでした。
