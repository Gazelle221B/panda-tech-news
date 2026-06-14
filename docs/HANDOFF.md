# 引き継ぎ書 (HANDOFF) — 2026-06-14 更新 (T22 完了)

> **これは時点スナップショットである** (いずれ陳腐化する)。恒久的な運用手順は [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md)、真の進捗記憶は [PROJECT_STATE.md](./PROJECT_STATE.md)。
> 用途: オーケストレーター交代時に「今どこで・次に何をすべきか」を 5 分で把握する。

## 1. 30 秒サマリー

**華流テック通信 (中華圏テック AI ポッドキャストのニュース番組) は本番稼働中。** 収集 → LLM 編集 → 台本生成 → Discord 配信のパイプライン (Sprint 1A + 1B) が完成し、実 LLM API (MiMo + DeepSeek) で variant A 配信中。**T22 3日観察 (06-12〜14) 完了** — インフラ DoD 全達成。ただし観察が **2 defects を捕捉**: writer (DeepSeek) の 300字超過による台本テンプレ落ち (品質 DoD 未達) と、canonical URL 横断 dedup 欠落。これらの修正が「音声化する価値」到達の前提。

- **ブランチ**: `agent/T22-impl` (T22 観察 docs)。2 defects 修正は別ブランチで実施。
- **品質ゲート**: pytest 242 / ruff / mypy strict すべて緑
- **次のアクション**: ① T22 観察 PR を人間マージ ② 2 defects を TDD 修正 (実装 OpenCode 委任→Codex→QA) ③ Sprint 2 は人間 Go 後

## 2. 完成済み (動くもの)

| フェーズ | 状態 | 証跡 |
|---|---|---|
| Sprint 1A (収集基盤) | ✅ 完全終了。3 日連続稼働・Discord HTTP 204・main マージ済み | TEST_LOG, PR #1-9 |
| Sprint 1B (LLM 編集・台本) | ✅ T12-T21 実装・**PR #10 マージ済み** (main `b76f6c4`) | REVIEW_REPORT (Codex PASS), QA_REPORT (Antigravity PASS) |
| T13 (実 API 接続) | ✅ 完了。MiMo `https://api.xiaomimimo.com/v1` / `mimo-v2.5-pro`、DeepSeek 接続確認 | PROJECT_STATE 2026-06-12 |
| T22 (3 日品質観察) | ✅ 完了 (06-14)。インフラ DoD 全達成・6/6 Discord 配信成功。**品質 DoD は writer 300字超過で未達** (template率 0→80→100%)。横断 dedup 欠落も発見 | TEST_LOG T22 総括 |

## 3. 残作業 (完成までの正確な経路)

```
[完了] T22 3日観察 → インフラ DoD 達成 + 2 defects 捕捉
   │
[AI] 2 defects を別ブランチで TDD 修正 (実装 OpenCode→Codex レビュー→Antigravity QA)
   │   ① writer 300字遵守 (プロンプト字数バジェット + 再生成フィードバック強化)
   │   ② canonical URL 横断 dedup (選定段階)
   │
[AI] 修正後 draft 再実行で template 率改善を検証
   │
[人間] T22 観察 PR + 2 defects 修正 PR を merge ← ★人間専権ゲート (AI 不可)
   │
[人間] Sprint 2 Go 判断 ────────────────────← ★人間専権ゲート (材料は §4)
   │
[Go 後] agent/T2x-impl で Sprint 2 (音声化) 着手 → RUNBOOK §3 の委任サイクル
```

**重要**: merge と Sprint 2 Go は AI が代替できない人間ゲート。2 defects の修正は AI が実施可能 (Sprint 1B 品質範囲、TTS 未着手なので §3.4 非該当)。

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
