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
