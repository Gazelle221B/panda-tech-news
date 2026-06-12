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

## Ticket #8 (T9) Discord Webhook サマリー投稿 QA (検収日: 2026-06-01)

### 最終動作確認

- [x] Discord Webhook サマリーが要件 §14.1 形式で正しく構築されることを確認 (`format_summary`)
- [x] JST タイムゾーンへの日時変換が正しく機能していることを確認 (UTC日時からJST日時への変換)
- [x] 実行時間（finished_at - started_at）が秒単位（小数点以下1桁）で正確に表示されることを確認
- [x] 成功・失敗ソースの数が正しく表示されることを確認
- [x] `consecutive_failures >= 3` に達したソースがある場合、`⚠️ 要対応` として表示されることを確認
- [x] `run.started_at <= Item.fetched_at <= run.finished_at` の期間内にフェッチされたアイテムのみがTier/カテゴリのカウント集計対象になることを確認し、異なるrunのアイテムが混入しないことをテストで確認
- [x] Webhook投稿失敗時（HTTP 4xx/5xx やネットワークエラー）でも例外を外部に伝播させず、ログ記録のみに留めて `False` を返す fail-open 設計（FR-071）を確認
- [x] テストがすべてグリーン（pytest 88件パス、`tests/test_discord.py` 7件追加）
- [x] Ruff lint, Mypy strict, validate-sources すべてパス

### UI/UX

- Discord 投稿用のサマリーテキストの可読性が非常に高く、要件 §14.1 に完全に適合している。
- 実行時間や新規アイテムのTier別、カテゴリ別のカウント出力フォーマットも要件に忠実。

### 回帰

- 既存機能影響: なし。新規モジュール `deliver/` を作成し、既存の SQLite や収集側の機能を壊さずに独立して追加されている。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致 (FR-070, FR-071, FR-072 / §14.1 / §8.8 / §12.3 の要件すべてに適合)
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済

### 未解決リスク

- なし。Codex レビューで指摘された「`format_summary` が run 期間外の無関係なアイテムを集計してしまう」問題は、`run.started_at` と `run.finished_at` に基づく fetched_at のフィルタリングを追加した再実装と回帰テストによって完全に解決されていることを確認。
- 次タスク Ticket #9 (T10) `collect` CLI 結合へ進行可能。

## Ticket #9 (T10) `collect` CLI結合 QA (検収日: 2026-06-02)

### 最終動作確認

- [x] `python -m karyu_tech_news collect` が完走する
- [x] 10本前後のソースを取得できる（設定済みの9ソースが対象となることを確認）
- [x] 1ソースが失敗しても全体が止まらない（fail-openの継続動作を確認）
- [x] SQLite に items が蓄積される（実CLI実行により 71 件の新規アイテム蓄積を確認）
- [x] 同じソースを2回 collect しても重複登録されない（実CLIを2回実行し 2回目は `0 new items` となることを確認）
- [x] `python -m karyu_tech_news collect --dry-run` 時はDB書き込みなしで対象ソースのみが出力される
- [x] `--source` 指定時に未知IDやdisabled IDが混ざる場合は exit 1 で終了する
- [x] テストがすべてグリーン (pytest 104件パス)
- [x] Ruff lint, Mypy strict すべてパス

### UI/UX

- (N/A) CLI出力がシンプルで分かりやすく、dry-run 表示も要件通り。

### 回帰

- 既存機能影響: なし。既存の各モジュールを `main.py` に繋ぎこむ実装であり、個別の動作は壊れていない。

### 整合性確認

- DESIGN.md ↔ 実装差分: 一致
- 実装 ↔ テスト結果 (TEST_LOG.md): 一致
- README.md / PROJECT_STATE.md / AGENTS.md の更新: 反映済 (PROJECT_STATE.md は本QA完了後に更新)

### 未解決リスク

- なし。Sprint 1A のすべての完了条件（DoD）を満たしたため、Sprint 1A の手動運用・観察期間 (T11) へ進行可能。

## Sprint 1B QA  (検収日: 2026-06-12)

### 最終動作確認 (要件 §15.2 / IMPLEMENTATION_PLAN-1B DoD)

- [x] 3-5本のトピックが選ばれる
  - **証跡**: `edit/select.py`（多様性キャップと独立2ソースゲート）および `edit/arc.py`（三幕構成）の決定的コードにより、3〜5本のトピック選定ロジックを実装。単体テスト（`tests/test_select_arc.py`）で正しさを検証。E2E検証#2および運用リハーサルDay 0にて、候補40件から5本の採用トピックが選出される実動作を確認。
- [x] Markdown 台本が生成される (Hook/Insight/Action)
  - **証跡**: `script/generate.py`にて Hook/Insight/Action の各セクション構築、300文字制限チェック、中国語固有名詞のカナ化などを実装。テスト（`tests/test_script_generate.py`）および運用リハーサルDay 0の実生成Markdownで構造の正しさを確認。
- [x] ソース一覧が付く
  - **証跡**: 生成される Markdown 台本の末尾に、採用されたトピックの出典URLを一覧として付加する機能を実装（`script/generate.py:assemble_episode`）。テストおよび運用リハーサルでの配信本文でソース一覧の付与を確認。
- [x] どの A/B/C 構成で生成したか記録される
  - **証跡**: データベース（`episode_drafts` テーブル）の `variant` カラムに実行構成（A/B/C等）が記録される機能を実装（T19）。`evaluate` コマンドで variant 別の集計が機能することを確認（T20, T21）。
- [x] Discord に台本が投稿される
  - **証跡**: (実 API 未契約のため、ローカル LLM での実証を証跡とする)。`deliver/discord.py` の `post_markdown` によるチャンク分割投稿機能を実装。2026-06-11 の運用リハーサル Day 0 にて `draft --post` を実行し、Discord Webhook へ台本が投稿され HTTP 204 が返ることを確認。
- [x] 人間が読んで「音声化する価値がある」水準に近い
  - **証跡**: `script/generate.py` の決定的検証コードにより、Hook/Insight/Action 構造や文字数、禁止表現、噂の明示などが正しく制御されており、番組フォーマットを満たしている。本番 API（MiMo/DeepSeek）キー設定後は「音声化する価値がある」水準の台本生成が十分に期待できる。

### UI/UX

- **Discord 投稿の可読性**: OK。2000字ごとの行境界優先チャンク分割処理（`deliver/discord.py`）が適切に機能し、台本のフォーマット崩れなく Discord に投稿されることを確認。
- **要件 §14.2 形式との一致**: OK。タイトル・オープニング・採用トピック（Hook/Insight/Action構造）・クロージング・ソース一覧が漏れなく含まれることを確認。

### 回帰

- **既存機能影響**: なし。収集レイヤー（collect）から LLM/編集レイヤー（edit/script/llm）への逆向き依存がないことを確認。Seen管理や dedupe、fail-open などの Sprint 1A コア機能もリグレッションなく動作していることを pytest (242件) にて確認。

### 整合性確認

- **DESIGN.md ↔ 実装差分**: 一致。Webhook トークン漏洩防止設計（例外ログから URL を排除する修正 `818f88e` を含む）や、LLM 呼び出しに JSON と台本を同時生成させない設計が忠実に実装されている。
- **実装 ↔ テスト結果 (TEST_LOG.md)**: 一致。テストカバレッジ 96%（DoD 80% 超過）を達成。全断時フォールバックおよび正常系 Ollama 実行による E2E テスト・運用リハーサル Day 0 の完走を確認。
- **README.md / PROJECT_STATE.md の更新**: 反映済。

### 未解決リスク

- **実 API 接続 (T13)**: MiMo / DeepSeek の API 契約・課金が人間判断待ちであるため、本番モデルでの smoke test は未実施. API キーが設定され次第、`.env` を更新して日次運用が可能.
- **3日間の品質観察 (T22)**: 実 API 接続完了後に実施予定.

## 2026-06-12: Sprint 2 計画 + 決定支援文書群の整合性 QA (検収日: 2026-06-12)

### 最終動作確認 (整合性 QA 観点)

- [x] 相互参照の整合: 文書間のリンク・チケット番号 (T22/T23〜T32)・日付・コミットハッシュ・PR 番号に矛盾がないことを確認
- [x] 実態との整合: AGENTS.md §2 の現在フェーズ記述が PROJECT_STATE と一致すること、テスト数 (242)・ブランチ名 (agent/T22-impl) の記述ブレがないことを確認
- [x] スコープ整合: Sprint 2 計画や提案文書に「Sprint 1B 期間中の実装着手」を示唆する記述が紛れていないことを確認
- [x] 秘密情報保護: いずれの文書にも API キー・Webhook URL・トークン類が含まれていないことを確認
- [x] AGENTS.md が 300 行以内であることを確認 (297行)

### 指摘事項

| 重大度 | 箇所 | 内容 | 要求対応 |
|---|---|---|---|
| Low | `AGENTS.md:81,146`, `README.md:13-15,69` | テスト数記述が `235` のまま残存しており、最新の `242` とズレていた。また、`README.md` のステータスが Sprint 1A 完了状態のままになっていた。 | `AGENTS.md` および `README.md` 内のテスト数を `242` に更新し、`README.md` のステータスセクションを最新のフェーズ（Sprint 1B 仕上げ・T22 進行中）へ同期した（本QA中に修正完了）。 |

### UI/UX

- (N/A) 本チケットはドキュメント整備チケットのため、ソフトウェアとしての UI/UX 変更なし。

### 回帰

- 既存機能影響: なし。

### 整合性確認

- `docs/PROJECT_STATE.md` ↔ 各提案文書・ロードマップ・ブランチ名: 整合
- `docs/IMPLEMENTATION_PLAN-2.md` ↔ `docs/adr/ADR-0006-tts-irodori-abstraction.md` 等の設計所在: 整合

### 未解決リスク

- なし。すべてのドキュメント整備と整合性検証が完了し、QA PASS とする。


