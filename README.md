# karyu-tech-news / 華流テック通信 by HAL

中華圏特化AIポッドキャスト「**華流テック通信 — HAL Daily Briefing**」のリポジトリ。

中国語ネイティブの一次情報・準一次情報・コミュニティ情報を収集し、日本語リスナー向けに**平日朝5〜10分**で届けることを目的とする。

> 詳細な背景・意思決定の経緯は `docs/meeting.md` および `docs/meeting2.md` を参照。

---

## ステータス

- フェーズ: **Sprint 3 (配信) main 到達 (2026-07-12, PR #25 マージ) — ロードマップ全スプリント (1A/1B/2/3) のコード完成**。v0.5 経路 (mp3 → 波形動画 mp4 → YouTube 限定公開 → 朝確認 → approve 公開) 実装済み。実アップロード smoke は YouTube OAuth セットアップ ([#35](https://github.com/Gazelle221B/panda-tech-news/issues/35)) 待ち。
- 品質: pytest **538 passed** / ruff / mypy strict (82 files) / shellcheck 緑 (2026-07-12 実測)。新規依存ゼロ (httpx + ffmpeg のみ, [ADR-0007](docs/adr/ADR-0007-youtube-httpx-cli-approval.md))。独立レビュー 3 ラウンド + QA PASS。
- 次アクション: **人間判断・作業は全件 Issue 化済み ([`human-decision` ラベル](https://github.com/Gazelle221B/panda-tech-news/issues?q=is%3Aissue+is%3Aopen+label%3Ahuman-decision) #34〜#41 + バグ #42)**。筆頭は [#35 YouTube OAuth セットアップ](https://github.com/Gazelle221B/panda-tech-news/issues/35) と [#34 T32 人間試聴](https://github.com/Gazelle221B/panda-tech-news/issues/34) ([docs/PROJECT_STATE.md](docs/PROJECT_STATE.md))

## ドキュメント地図

| 種別 | パス | 役割 |
|---|---|---|
| 要件 | [docs/requirements-v1.0.md](docs/requirements-v1.0.md) | 問題定義の起点 |
| 全体構想 | [docs/architecture-podcast-station.md](docs/architecture-podcast-station.md) | AIポッドキャスト局ビジョン (north star) |
| ロードマップ | [docs/roadmap.md](docs/roadmap.md) | Sprint 1A→1B→2→3→局化 |
| 設計 | [docs/DESIGN.md](docs/DESIGN.md) | **単一の真実の源** (Sprint 1A) |
| アーキテクチャ | [docs/architecture.md](docs/architecture.md) | レイヤー責務・判断基準フローチャート |
| ドメイン | [docs/domain/collection.md](docs/domain/collection.md) | 収集の用語・ビジネスルール・状態遷移 |
| 規約 | [docs/styleguide.md](docs/styleguide.md) | コーディング規約・命名・スニペット |
| コミット/完了ゲート | [docs/commit-rules.md](docs/commit-rules.md) | 完了宣言ゲート・コミット前チェック・DoD |
| 設計継承 | [docs/design-inheritance-tc-newsflow.md](docs/design-inheritance-tc-newsflow.md) | Go版から継承する設計パターン |
| 実装計画 | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Sprint 1A タスク分解 |
| 実装計画(1B) | [docs/IMPLEMENTATION_PLAN-1B.md](docs/IMPLEMENTATION_PLAN-1B.md) | Sprint 1B タスク分解 (T12〜) |
| 実装計画(2) | [docs/IMPLEMENTATION_PLAN-2.md](docs/IMPLEMENTATION_PLAN-2.md) | Sprint 2 (音声化) タスク分解 (T23〜) + 着手ゲート |
| 実装計画(3) | [docs/IMPLEMENTATION_PLAN-3.md](docs/IMPLEMENTATION_PLAN-3.md) | Sprint 3 (配信) タスク分解 (T38〜) + 人間ブロッカー |
| ワークフロー | [docs/WORKFLOW.md](docs/WORKFLOW.md) | エージェント間契約 |
| ワークフロー研究メモ | [docs/agentic-workflow-research-2026.md](docs/agentic-workflow-research-2026.md) | agentic / multi-agent 最新知見の運用反映根拠 |
| オーケストレーション運用 | [docs/ORCHESTRATION_RUNBOOK.md](docs/ORCHESTRATION_RUNBOOK.md) | 現在地判定・委任・検証・記録の手順 |
| 状態 | [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | 永続化された進捗 |
| Spike | [docs/source-selection-spike-v0.1.md](docs/source-selection-spike-v0.1.md) | 初期ソース選定 (11本/有効9) |
| ADR | [docs/adr/INDEX.md](docs/adr/INDEX.md) | 重要決定の記録ハブ (0001-0007) + TEMPLATE |
| 番組仕様 | [docs/hal-persona.md](docs/hal-persona.md), [docs/show-format.md](docs/show-format.md), [docs/editorial-policy.md](docs/editorial-policy.md) | HAL人格 / 構成 / 編集方針 |
| プロンプト | [prompts/](prompts/) | 各エージェント宛指示 |

## 設定とブートストラップ

| パス | 役割 |
|---|---|
| [config/sources.yaml](config/sources.yaml) | RSS/RSSHub ソース定義 (初期11本) |
| [config/llm_profiles.yaml](config/llm_profiles.yaml) | MiMo/DeepSeek/Ollama プロファイル (Sprint 1B) |
| [config/hal_persona.yaml](config/hal_persona.yaml) | HAL 人格 (機械可読、TTS非依存) |
| [config/show_format.yaml](config/show_format.yaml) | 番組構成テンプレ (機械可読) |
| [docker-compose.yml](docker-compose.yml) | RSSHub セルフホスト |
| [.env.example](.env.example) | 環境変数サンプル (`cp .env.example .env`) |
| [scripts/](scripts/) | Spike 検証スクリプト (curl / feedparser) |

## 現在のスコープ要旨

**「収集 → LLM 編集判定 → 3-5 本選定 → Markdown 台本生成 → Irodori 600M VoiceDesign + caption による mp3 完パケ → Discord 投稿 → 波形動画 mp4 → YouTube 限定公開 → 朝確認 → approve 公開」** までコード実装済み (v0.5 経路)。variant A で運用中、音声品質の最終判断は T32 の人間試聴、実 YouTube アップロード smoke は OAuth セットアップ (人間) が残る。

### Quick start (現時点で動くもの)

```bash
uv sync                                            # 基本依存 + Python 3.11+ を用意
uv sync --extra tts                                # produce / 実TTS を使う場合のみ
cp .env.example .env                               # DISCORD_WEBHOOK_URL を埋める
docker compose up -d rsshub                         # 掘金など RSSHub 経由ソース用
uv run python -m karyu_tech_news --help
uv run python -m karyu_tech_news validate-sources  # ソース定義をスキーマ検証
uv run python -m karyu_tech_news init-db           # SQLite 初期化
uv run python scripts/generate_bgm.py              # 暫定BGM (コード生成, algorave風) を assets/bgm/ へ生成 (Issue #36)
uv run python -m karyu_tech_news collect --post    # 収集 → SQLite → Discord 投稿
uv run python -m karyu_tech_news draft --dry-run   # 台本候補の確認 (LLM 不使用)
uv run python -m karyu_tech_news draft --post      # LLM 台本生成 → Discord (要 API キー)
uv run python -m karyu_tech_news produce --dry-run # 保存済み台本 → 音声完パケ (要 --extra tts + TTS 設定)
uv run python -m karyu_tech_news publish --dry-run # 完パケ mp3 → 波形動画 mp4 (要 ffmpeg)
uv run python -m karyu_tech_news publish --post    # mp4 → YouTube 限定公開 + Discord 朝確認 (要 OAuth)
uv run python -m karyu_tech_news approve           # 朝確認 ✅ → 公開へ切り替え (人間のみ)
uv run python -m karyu_tech_news evaluate          # A/B/C 検証の定量サマリー
uv run pytest                                      # テスト
```

### CLI 進捗

| コマンド | 状態 |
|---|---|
| `version` / `info` / `validate-sources` | ✅ T1-T2 |
| `init-db` | ✅ T4 (SQLite 初期化・冪等) |
| `collect` (`--source` / `--post` / `--dry-run`) | ✅ T3-T10 (収集→保存→dedupe→source_health→Discord) |
| `draft` (`--variant` / `--post` / `--dry-run`) | ✅ T12-T19, T21 (候補→判定→選定→台本→投稿)。実 API 接続済み (T13) |
| `produce` (`--engine` / `--post` / `--dry-run`) | ✅ T31-T36 (構造化→TTS→BGM optional→-16 LUFS mp3→Discord、fail-fast品質ゲート) |
| `evaluate` | ✅ T20 (採用率/修正回数/コスト/JSON安定性) |
| `publish` (`--audio-id` / `--post` / `--dry-run`) | ✅ T38-T40 (mp3→波形動画→YouTube unlisted→video_versions→Discord 朝確認) |
| `approve` (`--video-id` / `--post`) | ✅ T40 (朝確認 ✅ → public 切り替え。人間のみ実行) |
| `youtube-auth` | ✅ T39 (初回 OAuth。refresh token を取得して .env へ) |

> Discord 投稿は独立コマンドではなく `collect --post` / `draft --post` / `produce --post` / `publish --post` に統合。

## YouTube 配信セットアップ (人間が一度だけ)

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成し、**YouTube Data API v3** を有効化する。
2. 「OAuth 同意画面」を設定 (External / テストユーザーに自分の Google アカウントを追加) し、スコープに `youtube.upload` / `youtube` を含める。
3. 「認証情報」→ OAuth クライアント ID (種類: **デスクトップアプリ**) を作成し、client ID / client secret を `.env` の `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` に設定する。
4. `uv run karyu youtube-auth` を実行し、表示された URL を配信チャンネルの Google アカウントで認可 → 表示された `YOUTUBE_REFRESH_TOKEN=...` を `.env` に貼る。
5. smoke: `uv run karyu publish --dry-run` (mp4 生成のみ) → `uv run karyu publish` (限定公開アップロード) → YouTube Studio で確認 → `uv run karyu approve` (公開する場合のみ)。

> アップロードは 1 本あたり 1600 quota units (既定 10,000/日)。自動テストから実 API は叩かない ([IMPLEMENTATION_PLAN-3 §8](docs/IMPLEMENTATION_PLAN-3.md))。

## マルチエージェント運用

本リポジトリは `docs/WORKFLOW.md` で定義されたロール (人間 / Claude Code (Opus) / OpenCode / Codex / Antigravity) によって駆動される。実装は `agent/<task-id>-impl` ブランチで行い、main への直接 push は禁止。

## ライセンスと法務

- 中国メディア記事本文の転載は禁止。要約とHAL自身の解説のみ。
- 実在人物の無断声真似・声クローンは禁止 (Irodori-TTS モデルカード遵守)。
- AI生成音声であることをYouTube動画説明欄に明示。
