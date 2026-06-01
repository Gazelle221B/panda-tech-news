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
