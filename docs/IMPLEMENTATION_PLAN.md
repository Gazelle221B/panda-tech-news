# 実装計画: Sprint 1A 収集基盤

> 参照: [DESIGN.md](./DESIGN.md), [requirements-v1.0.md](./requirements-v1.0.md) §15.1
> 作成: アーキテクト (Claude Code / Opus)
> 想定実装者: OpenCode (実装ミドルチーム)
> 想定レビュアー: Codex (専任)

## タスク分解

| ID | 内容 | 変更対象ファイル | 依存 | 想定モデル |
|---|---|---|---|---|
| T1 | プロジェクト初期化・CLIスケルトン | `pyproject.toml`, `src/karyu_tech_news/__init__.py`, `cli.py`, `main.py`, `.env.example`, `.gitignore` | なし | haiku |
| T2 | RSSHub セルフホスト docker-compose | `docker-compose.yml`, `README.md` 追記 | なし | haiku |
| T3 | sources.yaml スキーマ + 初期10ソース | `config/sources.yaml`, `config/__schema__.py`, `tests/test_sources_schema.py` | T1 | sonnet |
| T4 | RSS/RSSHub 取得モジュール | `src/karyu_tech_news/collect/fetcher.py`, `normalize.py`, `tests/test_fetcher.py` | T1, T3 | sonnet |
| T5 | SQLite スキーマ + 永続化層 | `src/karyu_tech_news/store/schema.py`, `repo.py`, `tests/test_store.py` | T1 | sonnet |
| T6 | seen 管理 / dedupe (UNIQUE(source_id,item_key)) | `store/repo.py` 拡張, `tests/test_dedupe.py` | T5 | sonnet |
| T7 | source_health 更新 (成功/失敗/連続失敗) | `store/repo.py` 拡張, `tests/test_health.py` | T5 | sonnet |
| T8 | collect runner: fail-open 統合 | `collect/runner.py`, `tests/test_runner_fail_open.py` | T4, T5, T6, T7 | sonnet |
| T9 | Discord Webhook サマリー投稿 | `deliver/discord.py`, `tests/test_discord.py` | T5 | sonnet |
| T10 | `python -m karyu_tech_news collect` 結合 | `cli.py`, `main.py`, `tests/test_cli_integration.py` | T8, T9 | sonnet |
| T11 | 3日連続稼働観察 (手動運用) | `docs/PROJECT_STATE.md` 更新, `docs/TEST_LOG.md` 追記 | T10 | n/a |

## 依存グラフ

```
T1 ──┬─ T3 ──┬─ T4 ──┐
     │       │       ├─ T8 ─ T10 ─ T11
     ├─ T5 ──┼─ T6 ──┤
     │       └─ T7 ──┘
     └─ T2 (独立、並行可)
                     └─ T9 ──┘
```

## 並列実行可能ペア

OpenCode が複数並列で取れる単位:
- T1 ↔ T2 (完全独立)
- T3 と T5 (T1完了後並列可、ファイル衝突なし)
- T6 と T7 (T5完了後並列可、同一ファイル `repo.py` を編集するため衝突注意)
- T9 は T5 のみ依存。T4/T6/T7 と並列可

## テスト方針

### Unit Test (各タスクごと必須)

- T3: 不正YAMLで例外 / tier∉{1..4}で例外 / id重複検知。
- T4: feedparser モック / タイムアウト / リトライ回数 / bozo=1かつentries>=1で採用。
- T5: スキーマ作成冪等性 / `UNIQUE(source_id, item_key)` 違反検知。
- T6: 同一source+keyの2回投入で1行のみ存在。
- T7: 成功で `consecutive_failures=0` リセット / 失敗で +1 / `last_error` 保存。
- T8: 1ソースが例外を投げても他ソースが完走 / `collect_runs` に1行追加。
- T9: HTTP 4xx/5xx で例外を上げない (FR-071)。本文整形が要件 §14.1 と一致。
- T10: ドライランで DB 書き込みなし / 通常実行で全テーブル更新。

### Integration Test

- ローカル feedparser でモックフィードを生成し、`collect` → SQLite → `post-summary` まで通す。
- RSSHub は docker-compose を立てたうえで localhost:1200 の掘金カテゴリで疎通テスト (CI スキップ可、ローカルのみ)。

### 最低カバレッジ

- ユニット: 80%以上 (要件 §9.4 観測可能性に直結)。
- 結合: クリティカルパス (collect → store → discord) のハッピーパス1本必須。

## 禁止事項 (再掲: DESIGN.md §7より)

- `hash` 単体 UNIQUE 禁止。
- `item_key` 空での INSERT 禁止。
- `.env` commit 禁止。
- Webhook 失敗で run を fail させない。
- main 直接 push 禁止。実装は `agent/T<N>-impl` ブランチ。
- Sprint 1A スコープ外 (LLM/TTS/動画/YouTube/Playwright/Cookie必須ルート) 導入禁止。

## 完了の定義 (Sprint 1A 全体)

要件 §15.1 の DoD に加え、本計画固有の合格条件:

- [ ] T1〜T10 のユニットテストが全パス、`pytest --cov` で 80%以上。
- [ ] `python -m karyu_tech_news collect` が完走し、SQLite に items が新規追加される。
- [ ] 同一ソースを2回 collect しても items 行が増えない (`UNIQUE(source_id, item_key)` 効果検証)。
- [ ] 1ソースで擬似的に例外を投げても全体が完走し、`source_health.consecutive_failures` が増える。
- [ ] Discord に要件 §14.1 形式のサマリーが届く。
- [ ] 3日連続で動作し、`docs/TEST_LOG.md` に証跡が残る。
- [ ] `docs/PROJECT_STATE.md` が現フェーズ・直近結果を反映している。

## エスカレーション・トリガー

WORKFLOW §4 の分類に従う:

| 症状 | エスカレーション先 |
|---|---|
| Codex レビューで同一箇所2回連続リジェクト | 人間 (要件失敗 C) |
| `feedparser` で全ソース取得不能 | 人間 (環境失敗 D) |
| RSSHub セルフホストが2回ビルド失敗 | 人間 (環境失敗 D) |
| 設計矛盾を実装中に発見 | Claude Code/Opus (設計失敗 B) |
| 「ついでに LLM も入れたい」と思った | 即停止 → 人間 (スコープ膨張 E) |

## タスクごとの想定コミット粒度

OpenCode は **1タスク=1ブランチ=複数コミットOK** だが、ブランチ単位ではテストグリーン状態で push する。レビュー差し戻しは同一ブランチで修正。
