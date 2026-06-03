# karyu-tech-news / 華流テック通信 by HAL

中華圏特化AIポッドキャスト「**華流テック通信 — HAL Daily Briefing**」のリポジトリ。

中国語ネイティブの一次情報・準一次情報・コミュニティ情報を収集し、日本語リスナー向けに**平日朝5〜10分**で届けることを目的とする。

> 詳細な背景・意思決定の経緯は `docs/meeting.md` および `docs/meeting2.md` を参照。

---

## ステータス

- フェーズ: **Sprint 1A 実装完了** (T1〜T10 QA PASS) — **Ticket #11 (3日連続稼働観察) 進行中** (Day 2/3, Discord 実配信成功)
- ソース検証: 完了 (2026-05-29)。有効9本 (ADOPT 5 + 監視 4) / 保留2本。詳細は [docs/source-selection-spike-v0.1.md](docs/source-selection-spike-v0.1.md) §7
- 次アクション: T11 Day 3 (`collect --post` を 2026-06-04 に実行) → 完了で Sprint 1B (LLM統合) 解禁

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
| ワークフロー | [docs/WORKFLOW.md](docs/WORKFLOW.md) | エージェント間契約 |
| 状態 | [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | 永続化された進捗 |
| Spike | [docs/source-selection-spike-v0.1.md](docs/source-selection-spike-v0.1.md) | 初期ソース選定 (11本/有効9) |
| ADR | [docs/adr/INDEX.md](docs/adr/INDEX.md) | 重要決定の記録ハブ (0001-0006) + TEMPLATE |
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

## Sprint 1A スコープ要旨

LLM・TTS・動画・YouTubeは未実装。**「ソース定義YAMLを読み、RSS/RSSHubから収集してSQLiteに保存し、Discordへ収集サマリーを投稿する」** ところまで。

### Quick start (現時点で動くもの)

```bash
uv sync                                            # 依存 + Python 3.11+ を用意
cp .env.example .env                               # DISCORD_WEBHOOK_URL を埋める
docker compose up -d rsshub                         # 掘金など RSSHub 経由ソース用
uv run python -m karyu_tech_news --help
uv run python -m karyu_tech_news validate-sources  # ソース定義をスキーマ検証
uv run python -m karyu_tech_news init-db           # SQLite 初期化
uv run python -m karyu_tech_news collect --post    # 収集 → SQLite → Discord 投稿
uv run pytest                                      # テスト (104 pass)
```

### CLI 進捗 (Sprint 1A 全実装済み)

| コマンド | 状態 |
|---|---|
| `version` / `info` / `validate-sources` | ✅ T1-T2 |
| `init-db` | ✅ T4 (SQLite 初期化・冪等) |
| `collect` (`--source` / `--post` / `--dry-run`) | ✅ T3-T10 (収集→保存→dedupe→source_health→Discord) |

> Discord 投稿は独立コマンドではなく `collect --post` に統合。

## マルチエージェント運用

本リポジトリは `docs/WORKFLOW.md` で定義されたロール (人間 / Claude Code (Opus) / OpenCode / Codex / Antigravity) によって駆動される。実装は `agent/<task-id>-impl` ブランチで行い、main への直接 push は禁止。

## ライセンスと法務

- 中国メディア記事本文の転載は禁止。要約とHAL自身の解説のみ。
- 実在人物の無断声真似・声クローンは禁止 (Irodori-TTS モデルカード遵守)。
- AI生成音声であることをYouTube動画説明欄に明示。
