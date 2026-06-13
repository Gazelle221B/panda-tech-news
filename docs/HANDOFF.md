# 引き継ぎ書 (HANDOFF) — 2026-06-13 更新

> **これは時点スナップショットである** (いずれ陳腐化する)。恒久的な運用手順は [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md)、真の進捗記憶は [PROJECT_STATE.md](./PROJECT_STATE.md)。
> 用途: オーケストレーター交代時に「今どこで・次に何をすべきか」を 5 分で把握する。

## 1. 30 秒サマリー

**華流テック通信 (中華圏テック AI ポッドキャストのニュース番組) は本番稼働中。** 収集 → LLM 編集 → 台本生成 → Discord 配信のパイプライン (Sprint 1A + 1B) が完成し、実 LLM API (MiMo + DeepSeek) で variant A 配信が始まっている。残るは Sprint 1B の品質観察 (T22) の 3 日完走と、その後の人間判断のみ。

- **ブランチ**: `agent/T22-impl` (最新コミット `3336462`、origin に push 済み)
- **品質ゲート**: pytest 242 / ruff / mypy strict すべて緑
- **次の自動アクション**: T22 Day 2 (06-13 朝) / Day 3 (06-14 朝) のスケジュール自動実行

## 2. 完成済み (動くもの)

| フェーズ | 状態 | 証跡 |
|---|---|---|
| Sprint 1A (収集基盤) | ✅ 完全終了。3 日連続稼働・Discord HTTP 204・main マージ済み | TEST_LOG, PR #1-9 |
| Sprint 1B (LLM 編集・台本) | ✅ T12-T21 実装・**PR #10 マージ済み** (main `b76f6c4`) | REVIEW_REPORT (Codex PASS), QA_REPORT (Antigravity PASS) |
| T13 (実 API 接続) | ✅ 完了。MiMo `https://api.xiaomimimo.com/v1` / `mimo-v2.5-pro`、DeepSeek 接続確認 | PROJECT_STATE 2026-06-12 |
| T22 (3 日品質観察) | 🔄 Day 2/3 完了 (Day2 は手動補完)。Day 3 は 06-14。**観察中の懸案: writer(DeepSeek) の生成成否が日で振れる (Day1=0/5→Day2=4/5 が template)** | TEST_LOG |

## 3. 残作業 (完成までの正確な経路)

```
[06-13 朝] T22 Day 2 自動実行 ──┐
[06-14 朝] T22 Day 3 自動実行 ──┤→ 3日総括 + DoD 更新 + Sprint 1B 完了 PR 自動作成
                                 │
[人間] Sprint 1B 完了 PR を merge ← ★人間専権ゲート (AI 不可)
                                 │
[人間] Sprint 2 Go 判断 ────────← ★人間専権ゲート (判断材料は §4 に準備済み)
                                 │
[Go 後] agent/T23-impl で Sprint 2 (音声化) 着手 → RUNBOOK §3 の委任サイクル
```

**重要**: 上記の人間ゲート 2 つは AI が代替できない。T22 は 3 *暦日* の観察設計であり短縮不可。「準備完了・実行待ち」が規則内で到達できる最大状態。

## 4. 人間判断待ち (材料は準備済み — 人間の入力のみ必要)

| 判断 | 準備済み材料 |
|---|---|
| Sprint 1B 完了 PR の merge | T22 完了で PR 自動作成。Codex/QA は PASS 済 |
| Sprint 2 Go 宣言 + TTS 実行環境 | [IMPLEMENTATION_PLAN-2.md §6](./IMPLEMENTATION_PLAN-2.md) (Codex レビュー PASS) |
| HAL 声リファレンス試聴 | ADR-0006。T24 着手前 |
| 番組挨拶フレーズ | [proposals/greeting-phrases-v0.1.md](./proposals/greeting-phrases-v0.1.md) (3 案) |
| Game/Subculture 予備ソース | [proposals/game-subculture-source-v0.1.md](./proposals/game-subculture-source-v0.1.md) (IndieNova 推奨) |
| BGM/ジングル素材・配信ポリシー | [proposals/distribution-policy-and-bgm-research-v0.1.md](./proposals/distribution-policy-and-bgm-research-v0.1.md) |
| A/B/C 既定 variant | T22 観察データを見て確定 (ADR-0005) |

## 5. 引き継ぐ人/AI が最初にやること

1. [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) §1 の起動シーケンスを実行。
2. §2 決定木で現在地を判定 (おそらく行 #4「Sprint 1B 観察中」か #5/#6)。
3. スケジュールタスクの実行結果を `ls ~/.claude/scheduled-tasks/` と TEST_LOG 末尾で確認。
4. 未実行で当日朝なら RUNBOOK §4 日次ループを手動実行して観察を補完。
5. 人間ゲートに当たったら停止し、本書 §4 の材料を添えて人間に渡す。

## 6. 環境メモ

- 実行: `uv run python -m karyu_tech_news <cmd>` または `uv run karyu <cmd>`
- `.env` に必要なキー (名前のみ・値は管理外): `DISCORD_WEBHOOK_URL` / `MIMO_API_KEY` / `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY` / `RSSHUB_BASE_URL`
- RSSHub: `docker compose up -d rsshub` (Docker 表示 unhealthy でも `curl localhost:1200` が 200 なら正常)
- 外部 AI CLI は全て導入・稼働確認済み: codex / agy / gemini / opencode (1.17.4 へ upgrade 済、Go プラン + 無料枠 smoke OK) / copilot / gh / qwen (RUNBOOK §3 参照)
- OpenCode は当初 `UnknownError` (≤1.15.0 の seq バグ) で不可だったが 2026-06-13 に `opencode upgrade` で解消済み
