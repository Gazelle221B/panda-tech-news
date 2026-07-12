# 引き継ぎ書 (HANDOFF) — 2026-07-12 更新 (Sprint 3 マージ済、全スプリントのコード完成)

> **これは時点スナップショットである** (いずれ陳腐化する)。恒久的な運用手順は [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md)、真の進捗記憶は [PROJECT_STATE.md](./PROJECT_STATE.md)。
> 用途: オーケストレーター交代時に「今どこで・次に何をすべきか」を 5 分で把握する。

## 1. 30 秒サマリー

**華流テック通信 (中華圏テック AI ポッドキャストのニュース番組) は、ロードマップ全スプリント (1A 収集 / 1B LLM 編集・台本 / 2 音声化 / 3 配信) のコードが main 到達済み。** 収集 → LLM 編集 → 台本 → TTS (Irodori 600M VoiceDesign) → mp3 完パケ → 波形動画 mp4 → YouTube 限定公開 → Discord 朝確認 → approve 公開、の v0.5 経路まで実装完了 ([PR #25](https://github.com/Gazelle221B/panda-tech-news/pull/25) を 2026-07-12 マージ、人間 Go + 自律許可は PR コメントに記録)。**日次自動配信は T44 恒常スケジューラ (平日 Weekday launchd) が導入・稼働中** (正式決定の記録のみ [#40](https://github.com/Gazelle221B/panda-tech-news/issues/40) で待ち)。**残る人間タスク・判断は全件 GitHub Issue 化済み (#34〜#42, `human-decision` ラベル)** — YouTube の実配信開始だけが人間のアカウント操作 ([#35](https://github.com/Gazelle221B/panda-tech-news/issues/35)) を待っている。

- **fresh 品質ゲート実測 (2026-07-12, PR #25 マージ直前)**: `uv run pytest` **538 passed, 1 skipped** / `uv run ruff check .` clean / `uv run mypy src tests` **strict clean (82 files)** / shellcheck / uv lock 緑。
- **次のアクション**: [`human-decision` Issues](https://github.com/Gazelle221B/panda-tech-news/issues?q=is%3Aissue+is%3Aopen+label%3Ahuman-decision) の消化。筆頭は [#35 YouTube OAuth セットアップ + 実アップロード smoke](https://github.com/Gazelle221B/panda-tech-news/issues/35) と [#34 T32 人間試聴](https://github.com/Gazelle221B/panda-tech-news/issues/34)。AI 側で拾える実装タスクは [#42 notify_failure 表示バグ](https://github.com/Gazelle221B/panda-tech-news/issues/42) のみ。

## 2. 完成済み (動くもの)

| フェーズ | 状態 | 証跡 |
|---|---|---|
| Sprint 1A (収集基盤) | ✅ 完全終了。3 日連続稼働・Discord HTTP 204 | TEST_LOG (凍結), PR #1-9 |
| Sprint 1B (LLM 編集・台本) | ✅ 完全終了 (PR #10/#11/#12)。variant A 本番配信中 | REVIEW_REPORT / QA_REPORT (凍結) |
| Sprint 2 (音声化) | ✅ 完了 (T23-T31, PR #13-#19)。Irodori 600M VoiceDesign・-16LUFS・mp3 完パケ・Discord 配信 | PROJECT_STATE 改訂履歴 |
| 音声品質・運用ハードニング | ✅ T33-T37 / T42-T49 マージ済み (PR #22-#24, #26-#33)。無音/clip/LUFS gate・読み辞書・DTO 境界・ADR-0008 ログシャーディング | 各チケットログ |
| **Sprint 3 (配信)** | ✅ **main 到達 (T38-T41, PR #25, 2026-07-12)**。波形動画・YouTube 限定公開 (public は人間 approve のみ)・AI 開示強制・朝確認フロー・PUBLISH_YOUTUBE opt-in | docs/test-logs/2026-07-06-T38-sprint3.md, docs/review-reports/ + docs/qa-reports/ の 2026-07-12 ログ |
| 日次自動配信 | ✅ **T44 恒常スケジューラ (平日) 導入・稼働中** + T47 state.db バックアップ (PR #29) | `launchctl list` 実機確認 2026-07-12 |

## 3. 作業中

- なし (実装レーンはすべて main 到達済み。オープン PR ゼロ)

## 4. 人間判断待ち — GitHub Issues が正 (2026-07-12 移行)

[`human-decision` ラベル](https://github.com/Gazelle221B/panda-tech-news/issues?q=is%3Aissue+is%3Aopen+label%3Ahuman-decision): [#34](https://github.com/Gazelle221B/panda-tech-news/issues/34) T32 試聴 / [#35](https://github.com/Gazelle221B/panda-tech-news/issues/35) YouTube OAuth / [#36](https://github.com/Gazelle221B/panda-tech-news/issues/36) BGM ライセンス / [#37](https://github.com/Gazelle221B/panda-tech-news/issues/37) variant 既定 / [#38](https://github.com/Gazelle221B/panda-tech-news/issues/38) Game/Subculture ソース / [#39](https://github.com/Gazelle221B/panda-tech-news/issues/39) 挨拶フレーズ / [#40](https://github.com/Gazelle221B/panda-tech-news/issues/40) 日次恒久運用の記録 / [#41](https://github.com/Gazelle221B/panda-tech-news/issues/41) gemini CLI。実装タスク: [#42](https://github.com/Gazelle221B/panda-tech-news/issues/42) (bug)。

## 5. 引き継ぐ人/AI が最初にやること

1. [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) §1 の起動シーケンスを実行。
2. `gh issue list --label human-decision` と `gh pr list` で残タスクの最新状態を確認 (本書 §4 は時点スナップショット)。
3. 人間判断が下りた Issue があれば、その決定を PROJECT_STATE へ記録 (docs ブランチ, ADR-0008) してから実装レーンを起こす。
4. 人間ゲートに当たったら停止し、該当 Issue に材料を添えてコメントする。

## 6. 環境メモ

- 実行: `uv run python -m karyu_tech_news <cmd>` または `uv run karyu <cmd>`
- `.env` に必要なキー (名前のみ・値は管理外): `DISCORD_WEBHOOK_URL` / `MIMO_API_KEY` / `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY` / `RSSHUB_BASE_URL` + Sprint 3 の `YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN` (取得手順は README「YouTube 配信セットアップ」)
- RSSHub: `docker compose up -d rsshub` (healthcheck は T43 で curl 化済み)
- 日次自動配信: T44 launchd (平日) が稼働中。YouTube publish 段は `PUBLISH_YOUTUBE=1` の明示 opt-in まで動かない (既定 off)
- HAL 声リファレンスは Booth 購入の許諾済み音声で確定済み (`assets/` 配置、Irodori `voices.json` で `hal` voice に alias)
- 外部 AI CLI: codex / agy / opencode / copilot / gh / grokbuild ほか稼働確認済み (RUNBOOK §3)。gemini CLI は認証失効中 ([#41](https://github.com/Gazelle221B/panda-tech-news/issues/41))
