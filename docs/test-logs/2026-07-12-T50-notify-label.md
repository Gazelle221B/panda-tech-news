# T50 — notify_failure() の label 表示バグ修正 (Issue #42)

- 日付: 2026-07-12
- ブランチ: `agent/T50-notify-label-impl`
- 実装者: Claude Code
- 参照: [Issue #42](https://github.com/Gazelle221B/panda-tech-news/issues/42)

## 背景

`scripts/daily_pipeline.sh` の `notify_failure()` は `label` 引数 (`"produce"` / `"publish"`) を
受け取るが、成功時ログが `log "produce 失敗通知: 処理完了"` の固定文言だったため、`publish` 失敗
時の通知でも "produce" と表示されていた。T38 Sprint 3 Codex レビュー対応時にスコープ外として発見
していた既知の軽微な表示バグ (docs/test-logs/2026-07-06-T38-sprint3.md「保守側に倒した判断」参照)
を、本チケットで最小修正する。

## 変更内容

1. `scripts/daily_pipeline.sh` `notify_failure()` の成功/失敗ログを固定文言から `${label}` を
   使う形へ書き換え (`"produce 失敗通知: 処理完了"` → `"${label} 失敗通知: 処理完了"`、
   `"WARNING: produce 失敗通知コマンドが失敗"` → `"WARNING: ${label} 失敗通知コマンドが失敗"`)。
   ロジック・呼び出し側は無変更 (`notify_failure` は既に `label` を第一引数で受け取っていたため、
   ログ出力側の 2 行のみの外科的修正)。
2. `tests/test_daily_pipeline.py` の `test_publish_failure_propagates_return_code` に、通知ログが
   `"publish 失敗通知: 処理完了"` を含むことの assertion を追加 (修正前は label 非依存のログ文言
   のみを検証していた)。
3. `tests/test_produce_pipeline.py` の既存 `test_daily_pipeline_returns_nonzero_when_produce_fails_after_alert`
   は `label="produce"` のケースであり、修正後も `"produce 失敗通知: 処理完了"` は変わらず出力
   されるため無修正のまま緑を確認。

## 品質ゲート (fresh 実行)

```
$ shellcheck scripts/daily_pipeline.sh
(出力なし = クリーン)

$ uv run pytest
538 passed, 1 skipped in 4.91s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 82 source files

$ git diff --check
(出力なし = クリーン)
```

pytest 件数は T38 マージ時点 (538 passed, 1 skipped) から変化なし (既存テストへの assertion 追加
のみで、新規テスト関数は追加していないため)。

## 保守側に倒した判断

- `notify_failure()` のロジック自体 (Discord 送信の成否判定、`raise SystemExit(0)` 等) には手を
  入れず、ログ文言の label 参照のみを直した。スコープ外の変更禁止 (AGENTS §3.4 / Karpathy 12.3
  外科的変更) に従い、関連する呼び出し側 (`run_step` のログ・`notify_failure` の呼び出し箇所) も
  無変更。
