# 引き継ぎ書 (HANDOFF) — 2026-07-09 更新 (T36/T37 マージ済、T42 準備中)

> **これは時点スナップショットである** (いずれ陳腐化する)。恒久的な運用手順は [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md)、真の進捗記憶は [PROJECT_STATE.md](./PROJECT_STATE.md)。
> 用途: オーケストレーター交代時に「今どこで・次に何をすべきか」を 5 分で把握する。

## 1. 30 秒サマリー

**華流テック通信 (中華圏テック AI ポッドキャストのニュース番組) は本番稼働中。** 収集 → LLM 編集 → 台本生成 → TTS 音声合成 (Irodori 600M VoiceDesign) → mp3 完パケ → Discord 配信のパイプライン (Sprint 1A + 1B + Sprint 2) が完成し、実 API で本番配信できる状態。**日次自動配信 (launchd) は 3 日間の限定実運用後、2026-06-27 に撤去済み — 現在は手動実行のみで、恒常スケジューラの再導入は人間判断待ち。** 直近は T36 (音声品質ハードニング, [PR #23](https://github.com/Gazelle221B/panda-tech-news/pull/23)) と T37 (agentic workflow docs 統合, [PR #24](https://github.com/Gazelle221B/panda-tech-news/pull/24)) がいずれもマージ済み (2026-06-26 / 2026-06-29)。Sprint 3 (配信, T38-T41) は [PR #25](https://github.com/Gazelle221B/panda-tech-news/pull/25) が DRAFT で存在するが、人間 Go 判断の記録確認が未完了。

- **fresh 品質ゲート実測 (2026-07-09, `origin/main` `b8114bf` 上)**: `uv run pytest -q` **438 passed** / `uv run mypy src tests` **Success: no issues found in 70 source files**。
- **次のアクション**: ① Sprint 3 PR #25 の人間 Go 判断根拠を確認 ② T32 (話速) の人間聴感判断 ③ 恒常スケジューラ運用方針の決定 ④ T42 (TTS 読み上げハードニング、旧 T38 から採番衝突で改称) の PR 化

## 2. 完成済み (動くもの)

| フェーズ | 状態 | 証跡 |
|---|---|---|
| Sprint 1A (収集基盤) | ✅ 完全終了。3 日連続稼働・Discord HTTP 204・main マージ済み | TEST_LOG, PR #1-9 |
| Sprint 1B (LLM 編集・台本) | ✅ 完全終了・main マージ済み (PR #10/#11/#12) | REVIEW_REPORT (Codex PASS), QA_REPORT (Antigravity PASS) |
| Sprint 2 (音声化) | ✅ 完了。TTS 抽象化・Irodori 600M VoiceDesign+caption・ラウドネス -16LUFS・mp3 完パケ・BGM mixer・produce 永続化・Discord mp3 配信まで main 到達 (T23-T31, PR #13-#19) | PROJECT_STATE 改訂履歴 |
| T33/T34/T35 (日次自動配信 + 600M 本採用) | ✅ main 到達 ([PR #22](https://github.com/Gazelle221B/panda-tech-news/pull/22), 2026-06-23 マージ) | PROJECT_STATE 2026-06-23〜24 |
| T36 (音声品質ハードニング) | ✅ マージ済み ([PR #23](https://github.com/Gazelle221B/panda-tech-news/pull/23), 2026-06-26)。3 秒無音検出・clip/LUFS gate・daily pipeline 失敗通知 | fresh gate: pytest 438 / ruff / mypy strict 70 |
| T37 (agentic workflow docs 統合) | ✅ マージ済み ([PR #24](https://github.com/Gazelle221B/panda-tech-news/pull/24), 2026-06-29)。RUNBOOK/WORKFLOW/prompts のドリフト是正 | PROJECT_STATE 2026-06-29 |
| 日次自動配信 launchd | ⏸ **撤去済み (2026-06-27)、現在停止中**。3 日限定運用 (06-24〜26) のみで恒久運用はしていない | PROJECT_STATE launchd 記録 |

## 3. 作業中

- **T42 — TTS 読み上げハードニング** (旧チケット番号 T38 だったが、Sprint 3 の [PR #25](https://github.com/Gazelle221B/panda-tech-news/pull/25) が T38-T41 を既に使用しているため採番衝突を避けて T42 へ改称)。`config/reading_dict.yaml` / `src/karyu_tech_news/tts/normalize.py` の読み仮名・正規化強化が対象。**PR 準備中** (未 PR 化)。
- **Sprint 3 (配信, T38-T41)**: [PR #25](https://github.com/Gazelle221B/panda-tech-news/pull/25)「波形動画 + YouTube 限定公開 + 朝確認フロー (v0.5)」が DRAFT で 2026-07-05 から存在。AGENTS.md §3.4 は Sprint 越境 (スコープ膨張) NG を定めており、Sprint 3 着手には本来「人間の Go 判断」が前提。当該 Go 判断が `docs/PROJECT_STATE.md` 等に記録されているか未確認 — 次の引き継ぎ先はこれを最優先で確認すること。
- **[PR #26](https://github.com/Gazelle221B/panda-tech-news/pull/26)** (T43, RSSHub healthcheck を curl 化) が 2026-07-09 に OPEN。本 HANDOFF 更新作業とは独立レーン。

## 4. 人間判断待ち (材料は準備済み — 人間の入力のみ必要)

| 判断 | 準備済み材料 |
|---|---|
| ① Sprint 3 [PR #25](https://github.com/Gazelle221B/panda-tech-news/pull/25) の Go 判断記録確認 | AGENTS.md §3.4 (スコープ膨張 NG)。DRAFT のまま着手根拠を `docs/PROJECT_STATE.md` で追跡できるか要確認 |
| ② 日次自動配信の恒常スケジューラ再導入 | 3 日限定 launchd (`scripts/launchd/com.karyu.daily-pipeline.plist`) は撤去済みだがテンプレートは保持。恒久 launchd / `/schedule` クラウド実行 / 停止継続のいずれか人間判断 |
| ③ T32 話速調整の聴感判断 | Irodori 600M VoiceDesign 実音声サンプル複数 (draft #6-#11 等) が既に生成済み。人間の聴感評価待ち |
| ④ BGM/ジングル素材ライセンス | mixer は素材非依存で実装済み。実素材の採用・権利確認は人間判断 |
| ⑤ A/B/C 既定 variant 確定 | T22 実測データが 2026-06-14 から揃っている ([TEST_LOG.md](./TEST_LOG.md) T22 総括)。現状は暫定で variant A を既定運用中 |

## 5. 引き継ぐ人/AI が最初にやること

1. [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) §1 の起動シーケンスを実行。
2. `gh pr list --state all` で PR #25 (Sprint 3 DRAFT) / PR #26 (T43) など進行中レーンの最新状態を確認。
3. 本書 §4 の人間判断待ち事項のうち、前回訪問時から解消されたものがないか `docs/PROJECT_STATE.md` の最新エントリで確認。
4. T42 (TTS 読み上げハードニング) の作業ブランチがあれば `git branch -a | grep -i t42` 等で確認し、PR 化状況を把握。
5. 人間ゲートに当たったら停止し、本書 §4 の材料を添えて人間に渡す。

## 6. 環境メモ

- 実行: `uv run python -m karyu_tech_news <cmd>` または `uv run karyu <cmd>`
- `.env` に必要なキー (名前のみ・値は管理外): `DISCORD_WEBHOOK_URL` / `MIMO_API_KEY` / `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY` / `RSSHUB_BASE_URL`
- RSSHub: `docker compose up -d rsshub` ([PR #26](https://github.com/Gazelle221B/panda-tech-news/pull/26) で healthcheck を curl 化中。公式イメージに wget 不在で常時 unhealthy 表示の既知問題)
- 日次自動配信は `scripts/daily_pipeline.sh` で手動実行可能 (`collect → draft → produce → Discord` を 1 本化)。launchd 常駐は撤去済みのため自動発火はしない。
- HAL 声リファレンスは Booth 購入の許諾済み音声で確定済み (`assets/` 配置、Irodori `voices.json` で `hal` voice に alias)。
- 外部 AI CLI は全て導入・稼働確認済み: codex / agy / gemini / opencode / copilot / gh / qwen (RUNBOOK §3 参照)
