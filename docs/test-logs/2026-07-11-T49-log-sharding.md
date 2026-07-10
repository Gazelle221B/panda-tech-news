# T49 — 追記型共有ログのシャーディング (ADR-0008)

- 日付: 2026-07-11
- ブランチ: `agent/T49-log-sharding-impl`
- 実装者: Claude Code
- 参照: [ADR-0008](../adr/ADR-0008-append-log-sharding.md)

## 背景

`docs/TEST_LOG.md` / `docs/REVIEW_REPORT.md` / `docs/QA_REPORT.md` への並行追記が、並行 PR (#29〜#32) を必然的にコンフリクトさせる事象が実際に発生した。本チケットは恒久対策として、追記型共有ログを「1チケット1ファイル」へシャーディングする。本ファイル自体がその新方式の最初の実例。

## 変更内容

1. `docs/adr/ADR-0008-append-log-sharding.md` 新規作成 (Status: Proposed)。
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
