# ADR-NNNN: <決定の要約を動詞で>

- 日付: YYYY-MM-DD
- ステータス: Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
- 決定者: 人間 (プロダクトオーナー) + Claude Code (アーキテクト)
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §X, 関連 ADR, config ファイル等

> 使い方: 本ファイルを `cp docs/adr/TEMPLATE.md docs/adr/ADR-NNNN-<kebab-title>.md` でコピーし、`NNNN` を連番に。記入後 [INDEX.md](./INDEX.md) に1行追加する。
> 既存 ADR (0001〜0006) と構造を揃えること。一度 Accepted にしたら書き換えず、変更時は新規 ADR で Supersede する。

## 背景

この決定が必要になった文脈・課題・制約。なぜ今これを決めるのか。

## 検討した案

| 案 | 長所 | 短所 |
|---|---|---|
| 案A | ... | ... |
| 案B | ... | ... |

## 決定

**採用する案を一文で明記。** 具体的に何をどうするか。

## 根拠

なぜこの案か。要件 (FR-xxx) や本プロジェクトの原則 (最小構成・fail-open・状態の外部永続化、AGENTS.md §3 絶対NG) との整合。

## 影響

- 実装・他ドキュメント・将来スプリントへの波及。
- 更新すべき箇所: `AGENTS.md` §3/§5、`docs/DESIGN.md`、`docs/PROJECT_STATE.md`「直近の設計判断」。

## 不採用案

不採用にした案と、その理由 (特に「いつか必要そう」という先回りを退ける根拠)。
