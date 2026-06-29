# karyu-tech-news / 華流テック通信 by HAL

中華圏特化AIポッドキャスト「**華流テック通信 — HAL Daily Briefing**」のリポジトリ。

中国語ネイティブの一次情報・準一次情報・コミュニティ情報を収集し、日本語リスナー向けに**平日朝5〜10分**で届けることを目的とする。

> 詳細な背景・意思決定の経緯は `docs/meeting.md` および `docs/meeting2.md` を参照。

---

## ステータス

- フェーズ: **Sprint 2 (音声化・日次自動配信) code loop 完了後の人間判断待ち** — Sprint 1A/1B、T23〜T35 は main 到達済み。T36 で中国語原題の発話退避、produce fail-fast、無音/clip/LUFS gate、日次 pipeline 失敗通知までハードニング済み。
- 品質: T36 fresh gate は pytest **438 pass** / ruff / mypy strict (70 files) / shellcheck / plutil 緑。実 Irodori dry-run produce は -16.2 LUFS / true peak 安全域 / 3秒以上無音なしを確認。
- 次アクション: **T32 人間試聴、日次配信の恒久運用判断、BGM 素材ライセンス、variant 既定確定** ([docs/PROJECT_STATE.md](docs/PROJECT_STATE.md))

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
| ワークフロー | [docs/WORKFLOW.md](docs/WORKFLOW.md) | エージェント間契約 |
| ワークフロー研究メモ | [docs/agentic-workflow-research-2026.md](docs/agentic-workflow-research-2026.md) | agentic / multi-agent 最新知見の運用反映根拠 |
| オーケストレーション運用 | [docs/ORCHESTRATION_RUNBOOK.md](docs/ORCHESTRATION_RUNBOOK.md) | 現在地判定・委任・検証・記録の手順 |
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

## 現在のスコープ要旨

**「収集 → LLM 編集判定 → 3-5 本選定 → Markdown 台本生成 → Irodori 600M VoiceDesign + caption による mp3 完パケ → Discord 投稿」** までコード実装済み。動画 / YouTube は未実装 (Sprint 3 以降、人間 Go 後)。variant A で運用中、音声品質の最終判断は T32 の人間試聴が残る。

### Quick start (現時点で動くもの)

```bash
uv sync                                            # 基本依存 + Python 3.11+ を用意
uv sync --extra tts                                # produce / 実TTS を使う場合のみ
cp .env.example .env                               # DISCORD_WEBHOOK_URL を埋める
docker compose up -d rsshub                         # 掘金など RSSHub 経由ソース用
uv run python -m karyu_tech_news --help
uv run python -m karyu_tech_news validate-sources  # ソース定義をスキーマ検証
uv run python -m karyu_tech_news init-db           # SQLite 初期化
uv run python -m karyu_tech_news collect --post    # 収集 → SQLite → Discord 投稿
uv run python -m karyu_tech_news draft --dry-run   # 台本候補の確認 (LLM 不使用)
uv run python -m karyu_tech_news draft --post      # LLM 台本生成 → Discord (要 API キー)
uv run python -m karyu_tech_news produce --dry-run # 保存済み台本 → 音声完パケ (要 --extra tts + TTS 設定)
uv run python -m karyu_tech_news evaluate          # A/B/C 検証の定量サマリー
uv run pytest                                      # テスト (438 pass, 2026-06-26時点)
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

> Discord 投稿は独立コマンドではなく `collect --post` / `draft --post` / `produce --post` に統合。

## マルチエージェント運用

本リポジトリは `docs/WORKFLOW.md` で定義されたロール (人間 / Claude Code (Opus) / OpenCode / Codex / Antigravity) によって駆動される。実装は `agent/<task-id>-impl` ブランチで行い、main への直接 push は禁止。

## ライセンスと法務

- 中国メディア記事本文の転載は禁止。要約とHAL自身の解説のみ。
- 実在人物の無断声真似・声クローンは禁止 (Irodori-TTS モデルカード遵守)。
- AI生成音声であることをYouTube動画説明欄に明示。
