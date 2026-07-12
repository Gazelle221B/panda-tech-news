# Agentic Workflow Research Notes 2026-06-29

目的: 最新のエージェント駆動開発 / マルチエージェント駆動開発の知見を、このリポジトリの運用契約へ落とし込む。ここでの結論は [WORKFLOW.md](./WORKFLOW.md) と [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) の根拠メモであり、プロダクトコードの依存ではない。

## 参照した一次情報・研究

| 出典 | 要点 | 本プロジェクトへの反映 |
|---|---|---|
| Anthropic, [Building effective agents](https://www.anthropic.com/research/building-effective-agents) | 成功例は複雑なフレームワークではなく、単純で合成可能なパターンに寄る。 | OpenCode / Codex / Antigravity / agmsg は固定パイプライン化しすぎず、成果物とゲートを明示する。 |
| OpenAI, [A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) | 単一エージェントを強くしてから、必要時だけ manager / handoff 型の multi-agent へ進む。guardrails と human-in-the-loop が必須。 | 通常は単一オーケストレーターが所有し、サブエージェントは明確な境界のある補助に限定する。 |
| Cemri et al., [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) / MAST | MAS 失敗は specification / inter-agent misalignment / verification・termination に集中し、表層的なプロンプト修正では足りない。 | 委任時に「仕様・書込範囲・停止条件・検証証跡」を必須入力にする。レビューは終了条件と未検証主張を明示的に見る。 |
| Cognition, [Don't Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents) / [Multi-Agents: What's Actually Working](https://cognition.ai/blog/multi-agents-working) | 並列ライターは暗黙判断が衝突しやすい。実用的なのは、複数エージェントが知性を足しても書き込みは単一スレッドに保つパターン。 | 同じファイルへの並列編集を避ける。並列化は探索・レビュー・QA・独立ファイルに限定し、統合はオーケストレーターが行う。 |
| Yang et al., [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793) | モデル性能だけでなく、検索・閲覧・編集・実行結果を返す Agent-Computer Interface が性能を左右する。 | `rg` / diff / テストログ / line reference を標準化し、レビュー・QA は具体的なファイル行とコマンド結果に紐付ける。 |
| Yadav et al., [More Capable, Less Cooperative?](https://arxiv.org/abs/2604.07821) | 能力が高いほど協調するとは限らず、明示プロトコルが性能を改善する。 | ロール分離だけに頼らず、handoff contract と expected output を毎回書く。 |
| Zhang et al., [When Embedding-Based Defenses Fail](https://arxiv.org/abs/2605.01133) | MAS 通信は攻撃面でもあり、悪性/誤情報メッセージをテキスト類似度だけで防げない。 | agmsg や外部AIの発言を権威にしない。権威は repo 内成果物・実行ログ・一次情報に限定する。 |

## 運用ルールへの変換

1. **単一オーケストレーター所有**: 全体計画・書込統合・完了判定は 1 エージェントが持つ。複数エージェントは判断材料を出すが、真の状態は `PROJECT_STATE.md` と git 差分。
2. **並列化は「知性」だけ、書き込みは絞る**: 調査・レビュー・QA は並列可。同じファイル群を複数ライターに同時編集させない。必要なら worktree で隔離する。
3. **Context packet を必須にする**: 委任には objective / in-scope / out-of-scope / authority docs / writable files / required evidence / stop conditions を含める。
4. **検証を終了条件にする**: 「できた」ではなく、どのテスト・diff・line reference・実データで確認したかを終了条件にする。
5. **通信は transport、権威ではない**: agmsg は通知・ポインタ・履歴の transport。`docs/review-reports/` / `docs/qa-reports/` のチケットログ (2026-07-11 以降, ADR-0008) / `PROJECT_STATE.md` / PR review / 人間 merge を置き換えない。
6. **モデル・ベンチ情報は期限付き**: モデル名・ベンチ順位・CLI仕様は変わる。日付・確認コマンド・一次情報が無い claims はワークフローの恒久根拠にしない。
7. **レビューは MAST 型失敗を見る**: specification gap、inter-agent misalignment、verification/termination failure を明示チェックする。
