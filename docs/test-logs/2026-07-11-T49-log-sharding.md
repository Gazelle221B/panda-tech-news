# T49 — 追記型共有ログのシャーディング (ADR-0008)

- 日付: 2026-07-11
- ブランチ: `agent/T49-log-sharding-impl`
- 実装者: Claude Code
- 参照: [ADR-0008](../adr/ADR-0008-append-log-sharding.md)

## 背景

`docs/TEST_LOG.md` / `docs/REVIEW_REPORT.md` / `docs/QA_REPORT.md` への並行追記が、並行 PR (#29〜#32) を必然的にコンフリクトさせる事象が実際に発生した。本チケットは恒久対策として、追記型共有ログを「1チケット1ファイル」へシャーディングする。本ファイル自体がその新方式の最初の実例。

## 変更内容

1. `docs/adr/ADR-0008-append-log-sharding.md` 新規作成 (Status: Accepted)。
2. `docs/test-logs/` / `docs/review-reports/` / `docs/qa-reports/` の3ディレクトリを新設。
3. `docs/TEST_LOG.md` / `docs/REVIEW_REPORT.md` / `docs/QA_REPORT.md` の冒頭に凍結注記を追加 (既存本文は無変更)。
4. `docs/PROJECT_STATE.md` 冒頭に運用変更注記を追加 (既存本文は無変更)。
5. `AGENTS.md` §6/§8.3/§10 を ADR-0008 に合わせて更新 (外科的変更、構造は不変)。
6. `docs/commit-rules.md` の TEST_LOG/PROJECT_STATE 言及箇所を同期。
7. `docs/WORKFLOW.md` / `docs/ORCHESTRATION_RUNBOOK.md` / `prompts/implement.md` / `prompts/review.md` / `prompts/qa.md` の証跡書き先の言及を新方式へ同期 (言及の書き換えのみ、構造変更なし)。
8. `docs/adr/INDEX.md` に ADR-0008 の行を追加。
9. 本ファイル (`docs/test-logs/2026-07-11-T49-log-sharding.md`) を新規作成し、実例として本チケットのゲート結果を記録。

## 品質ゲート (fresh 実行)

```bash
$ uv sync            # 依存解決 OK
$ uv run pytest
459 passed in 2.15s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 72 source files

$ git diff --check
(出力なし = クリーン)
```

## 既知の制限

- 本チケットはドキュメントのみの変更であり、コード (`src/` / `tests/`) は無変更。pytest/mypy の件数・ファイル数は直前の T45 (store DTO 境界導入, 2026-07-10) から変化なし。
- 過去ログ (`docs/TEST_LOG.md` 等) の内容は意図的に移行・削除していない (ADR-0008 の不採用案 (c) を参照)。

## Codex レビュー指摘対応 (2026-07-11, 同一ブランチ内修正)

PR #33 の Codex レビュー FAIL (High 3 / Medium 2) への対応:

1. **High — AGENTS.md 旧書き先の残存**: §7 ロール表 (旧 TEST_LOG/REVIEW_REPORT/QA_REPORT) → `docs/test-logs/` 等のチケットログに置換。§7「永続化 > 内部記憶」・§9 DoD「3日連続稼働」・§12.4 の多段タスク記録先も新方式へ。過去の事実記述 (§2 フェーズ履歴等) は保持。
2. **High — §11「状態を必ず書く」の矛盾解消**: チケット進捗・証跡は `docs/test-logs/` + PR 本文へ、`PROJECT_STATE.md` はマージ後の docs ブランチでオーケストレーターが更新、緊急追記のみ単独 docs PR、と書き換え。あわせて ADR-0008「影響」節に「PR #33 自身は main から切った docs 専用ブランチであり、PROJECT_STATE.md への注記追加は本運用ルール自体の導入として行う (impl チケットではない)」旨を明記し自己矛盾を解消。
3. **High — ADR-0008 Status**: `Proposed` → `Accepted (発効: PR #33 の人間マージ時点)` へ変更。`docs/adr/INDEX.md` の行も同期。
4. **Medium — 他の恒久文書の旧書き先同期**: `docs/hal-persona.md` §6 (QA_REPORT.md → docs/qa-reports/)、`docs/IMPLEMENTATION_PLAN-2.md` T32 行 + 改訂フッター、`docs/IMPLEMENTATION_PLAN-1B.md` 改訂フッター、`docs/agentic-workflow-research-2026.md` 運用ルール5。歴史的記述 (完了済み T11/T22 の記録) は保持。
5. **Medium — merge=union 棄却根拠の正確化**: 「union は git 組み込みの merge driver だが、GitHub の PR マージ判定・Web UI マージは `.gitattributes` の merge 属性 (union/カスタム driver とも) を尊重しない」に表現を修正し、一次資料を脚注で引用 (GitHub community discussion #9288、確認日 2026-07-11。実例として kubernetes/kubernetes#70576)。本リポジトリでの実測 (並行 PR #29〜#32 の再コンフリクト) も根拠に追記。

### 再ゲート (fresh 実行)

```
uv run pytest         → 459 passed
uv run ruff check .   → All checks passed!
uv run mypy src tests → Success: no issues found in 72 source files
git diff --check      → クリーン
```
