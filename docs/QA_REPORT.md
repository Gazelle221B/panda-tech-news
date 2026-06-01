# QA報告

> 検収者: Antigravity (テックリード / Gemini 大コンテキスト)
> 参照: [requirements-v1.0.md](./requirements-v1.0.md) §15.1, [DESIGN.md](./DESIGN.md), [REVIEW_REPORT.md](./REVIEW_REPORT.md)
> 役割: Codex レビュー合格後、人間 merge 承認前の最終 QA。

QA の目的は **「受け入れ条件 (要件側) を満たしているか」** を確認することで、Codex のレビュー (実装が DESIGN に従っているか) とは別軸。

---

## テンプレ (スプリント / 大タスク完了ごとに追記)

```markdown
## Sprint 1A QA  (検収日: YYYY-MM-DD)

### 最終動作確認 (要件 §15.1 DoD)

- [ ] python -m karyu_tech_news collect が完走する
- [ ] 10本前後のソースを取得できる
- [ ] 一部ソースが失敗しても全体が止まらない
- [ ] SQLite に items が蓄積される
- [ ] 同じソースを2回 collect しても重複登録されない
- [ ] source_health が更新される
- [ ] Discord に収集サマリーが届く
- [ ] 3日連続で動作する

### UI/UX

- Discord 投稿の可読性: OK / NG (詳細)
- 要件 §14.1 形式との一致: OK / NG

### 回帰

- 既存機能影響: なし (新規プロジェクト)

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md の更新: 反映済

### 未解決リスク

- (Sprint 1B に持ち越す事項)
```

---

## 履歴

(検収ごとに追記)

## T1 + T2/T3(schema) 初期実装 QA (検収日: 2026-05-30)

### 最終動作確認

- [x] (N/A) python -m karyu_tech_news collect が完走する (※本フェーズでは対象外)
- [x] sources.yaml が正しくロードされ、11本中9本が enabled として認識される
- [x] 各コマンド (`version`, `info`, `validate-sources`) がエラーなく動作する
- [x] テストがすべてグリーン (pytest 24件パス)

### UI/UX

- Discord 投稿の可読性: (N/A)
- CLI 出力: OK (Tier別・カテゴリ別の集計やマスク処理が要件通り動作している)

### 回帰

- 既存機能影響: なし (新規プロジェクト)

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md の更新: 反映済

### 未解決リスク

- なし (次タスク T3 へ進行可能)

## T4 RSS/RSSHub フェッチャ実装 QA (検収日: 2026-05-31)

### 最終動作確認

- [x] 1ソースが失敗しても全体が止まらない (fail-openの実装確認)
- [x] (N/A) SQLite に items が蓄積される (次タスク T5/T6以降)
- [x] URL の scheme/host 小文字化や UTM パラメータ除去が正しく行われ canonical_url_hash が計算される (FR-022)
- [x] external_id → link → sha256(...) の順で item_key が生成される (FR-021)
- [x] テストがすべてグリーン (pytest 48件パス)

### UI/UX

- (N/A)

### 回帰

- 既存機能影響: なし。config 等の修正も既存機能を壊していない。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済

### 未解決リスク

- なし。Codex の Low 指摘事項 (duration_ms に HTTP 待ち時間を含める件) は、2026-05-31 PRコメント対応にて修正・検証完了。

## Ticket #4 (T5) SQLite スキーマ・永続化 QA (検収日: 2026-06-01)

### 最終動作確認

- [x] スキーマ初期化 (`init-db`) がエラーなく動作し、2回連続実行しても壊れない（冪等）
- [x] SQLAlchemy/SQLite において `PRAGMA foreign_keys=ON` が有効であり、存在しない `source_id` を持つアイテムや `source_health` レコードの挿入が `IntegrityError` で防がれる（参照整合性）
- [x] アイテム追加時の重複排除（seen管理）が `UNIQUE(source_id, item_key)` に基づき正しく動作する（dedupe）
- [x] 空の `item_key` を持つアイテムを挿入しようとした際、`ValueError` で防がれる
- [x] 収集実行記録（`CollectRun`）の開始と完了、集計結果（成功数/失敗数/総アイテム数/新規アイテム数）が適切に記録される
- [x] `finish_collect_run` 実行時、`total_sources` と実際の `FetchResult` 数が異なる場合は `ValueError` で防がれる
- [x] データベースに `published_at DESC` のインデックス `idx_items_published` が意図通り作成されている
- [x] テストがすべてグリーン（pytest 60件パス）

### UI/UX

- `info` コマンドが `Sprint phase: 1A (Ticket #4 SQLite)` と表示されることを確認

### 回帰

- 既存機能影響: なし。config / cli などの修正も既存機能を壊していない。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致（§4 のテーブル、インデックス、外部キー、seen管理などすべて適合）
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済

### 未解決リスク

- なし。Codex レビューの High/Medium/Low 指摘事項（外部キー有効化、total_sources不一致、descインデックス、info表示）は再レビューにてすべて修正・合格していることを確認済。

## Ticket #5 (T6) seen 管理 / dedupe QA (検収日: 2026-06-01)

### 最終動作確認

- [x] (N/A) python -m karyu_tech_news collect が完走する (次タスク T10)
- [x] 同じソースを2回 collect しても重複登録されない（`UNIQUE(source_id, item_key)` による `insert_items` 内での dedupe が正しく行われ、既存レコードがスキップされることを確認）
- [x] 同一バッチ（1回の `insert_items` 呼び出し）内に重複アイテムが存在しても、1件だけが保存されることを確認（SQLAlchemy の autoflush と `select` による存在チェックで担保）
- [x] テストがすべてグリーン（pytest 65件パス、`tests/test_dedupe.py` の5件追加分を含む）

### UI/UX

- (N/A)

### 回帰

- 既存機能影響: なし。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致（`UNIQUE(source_id, item_key)` の制約および空 `item_key` の禁止要件を満たしている）
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済

### 未解決リスク

- なし。次タスク Ticket #6 (T7) `source_health` の fail-open 管理へ進行可能。

## Ticket #6 (T7) source_health 更新 QA (検収日: 2026-06-01)

### 最終動作確認

- [x] source_health が更新される（既存実装 `update_source_health_success` および `update_source_health_failure` によって、初回成功/失敗、連続失敗のカウントアップ/リセット、最新エラーの保存が正しく行われることを確認）
- [x] SQLiteから取得する tz-naive な datetime に対し、比較側の timezone を除去（`.replace(tzinfo=None)`）して正確に比較するアサーション処理が実装されている
- [x] テストがすべてグリーン（pytest 73件パス、`tests/test_health.py` の8件追加分を含む）
- [x] Ruff lint, Mypy strict, validate-sources すべてパス

### UI/UX

- (N/A) Discord警告 (consecutive_failures >= 3) の準備として、連続3回失敗時の状態遷移テストが整備されていることを確認。

### 回帰

- 既存機能影響: なし。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致 (FR-050, FR-051, FR-052 / domain/collection.md に完全に適合)
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済

### 未解決リスク

- なし。次タスク Ticket #7 (T8) collect runner (fail-open 統合) へ進行可能。

## Ticket #7 (T8) collect runner fail-open 統合 QA (検収日: 2026-06-01)

### 最終動作確認

- [x] 1ソースが例外を投げても全体が止まらない（`runner.py` 内の `try-except` および `session.rollback()` の実装により、DBエラー等が発生しても後続のソース処理が継続されるフェイルオープン設計を確認）
- [x] SQLite に items が蓄積される（`insert_items` と各ソース毎のコミットにより安全に蓄積されることを確認）
- [x] source_health が更新される（フェッチの成否および DB 例外の有無に応じて正しく状態更新・DB コミットが行われる）
- [x] `collect_runs` に正しい集計情報が登録される（特にDBコミット失敗時には新規アイテム数にカウントされないロジックを回帰テストで担保）
- [x] テストがすべてグリーン（pytest 81件パス、`tests/test_runner_fail_open.py` 8件追加）
- [x] Ruff lint, Mypy strict, validate-sources すべてパス

### UI/UX

- (N/A)

### 回帰

- 既存機能影響: なし。既存モジュールの関数（fetch_one, insert_items 等）の呼び出し順序や引数の使われ方が要件仕様に従っている。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致 (FR-050, 051, 052, 060 に適合。セッション境界やエラーハンドリングも要件通り)
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済 (PROJECT_STATE.md は本QA完了後に更新)

### 未解決リスク

- なし。次タスク Ticket #8 (T9) Discord Webhook サマリー投稿 へ進行可能。
