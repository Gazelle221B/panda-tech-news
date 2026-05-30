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
