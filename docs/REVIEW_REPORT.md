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
