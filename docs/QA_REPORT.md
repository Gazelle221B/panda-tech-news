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
