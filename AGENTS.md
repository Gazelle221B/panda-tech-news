# AGENTS.md — panda-tech-news / 華流テック通信 by HAL

> このファイルは Claude Code / Codex CLI / Copilot CLI / Gemini CLI など **AGENTS.md 対応の全 AI ツールが自動読込する最上位の指示書**である。`CLAUDE.md` は本ファイルへのシンボリックリンク。
> 詳細は本書末尾のドキュメント地図と `docs/` 配下を必ず参照すること。本書は要旨と禁止事項に絞り 300 行以内に収める。

## 1. プロジェクト概要

中華圏特化 AI ポッドキャスト **「華流テック通信 — HAL Daily Briefing」** を生成・配信するパイプライン。中国語ネイティブの一次・準一次・コミュニティ情報を収集し、日本語リスナー向けに **平日朝 5〜10 分** で届けることを目的とする。

| 項目 | 値 |
|---|---|
| 配布名 (PyPI想定) | `panda-tech-news` |
| Python モジュール名 | `karyu_tech_news` |
| 実行コマンド | `karyu` / `python -m karyu_tech_news` |
| 番組名 / キャスター | 華流テック通信 / HAL (AIキャスター, [docs/hal-persona.md](docs/hal-persona.md)) |
| 言語 | **Python 3.11+ 単一** (ADR-0001) |
| パッケージ管理 | `uv` (hatchling ビルド) |

## 2. 現在のフェーズ (随時更新は `docs/PROJECT_STATE.md`)

- **Sprint 1A 実装中** — 収集基盤の検証 (LLM/TTS/動画/YouTube は実装しない)
- 完了: Ticket #3 まで (CLI / ソーススキーマ / RSS・RSSHub フェッチャ / fail-open)
- 次: **Ticket #4** (SQLite スキーマ・永続化層)
- 作業ブランチ: `agent/T4-impl`

## 3. 絶対 NG (禁止事項) — 最優先

`docs/DESIGN.md` §7 + `docs/WORKFLOW.md` §11 / §12 / §15 を要旨化したもの。**いずれか抵触しそうな場合は実装を止めてエスカレーション**する。

### 3.1 リポジトリ運用 NG
- **`main` への直接 push 禁止**。実装は必ず `agent/<task-id>-impl` ブランチ。
- **merge は人間承認のみ**。AI エージェントは merge 不可 (例外は明示的人間許可のみ)。
- **`--no-verify` / `--no-gpg-sign` 等の hook スキップ禁止** (グローバルルール優先)。
- **`.env` を commit 禁止**。`.env.example` のみ管理 (要件 §9.5)。

### 3.2 データ・スキーマ NG
- **`hash` 単体に UNIQUE 制約を張ってはならない**。`UNIQUE(source_id, item_key)` のみ (FR-031)。
- **`item_key` が空のレコードを INSERT してはならない**。書き込み直前にアサート。
- **`item_key` 生成順を変えてはならない**: `external_id` → `link` → `sha256(title|published_at|source_id)` (FR-021)。
- **バイト単位の文字列切り詰め禁止**。必ず Python の `str` (コードポイント) 単位で扱う (`docs/design-inheritance-tc-newsflow.md` §6)。

### 3.3 耐障害性 NG
- **1 ソースの失敗でパイプライン全体を止めてはならない** (ソース単位 fail-open, FR-060)。
- **Discord Webhook 失敗で collect を fail させてはならない** (FR-071)。ログに記録のみ。
- **タイムアウト未指定の HTTP 呼び出し禁止**。各取得 30 秒 (FR-012)、リトライ最大 2 回 (FR-013)。

### 3.4 スコープ膨張 NG (Sprint 1A 中)
**Sprint 1A で以下を導入してはならない**: LLM 呼び出し / TTS / 音声処理 / 動画生成 / YouTube 投稿 / Playwright / 中国 IP プロキシ / Cookie 必須ルート。
「ついでに〜したい」と思ったら即停止し、`docs/PROJECT_STATE.md` の「人間判断待ち」へエスカレーション (WORKFLOW §4 区分 E)。

### 3.5 コンテンツ NG
- **中国メディア記事本文の転載禁止**。要約と HAL の解説のみ (要件 §9.6 法務)。
- **実在人物の無断声真似・声クローン禁止** (Irodori-TTS モデルカード遵守)。
- **「中国すごい」「日本終わった」型のナラティブ・政治断定・ナショナリズム表現禁止** ([docs/editorial-policy.md](docs/editorial-policy.md) §1, §10)。
- **AI 生成音声であることを YouTube 動画説明欄に明示**しない配信禁止 (FR-121, Sprint 3 以降)。

### 3.6 言語選定 NG
- **Go / Node.js / 2 言語ハイブリッドへ戻してはならない** (ADR-0001)。`tc-newsflow` (Go) は設計思想のみ継承し、コード移植不可。

## 4. 主要コマンド

```bash
# セットアップ
uv sync                                            # 依存解決 + Python 3.11+
cp .env.example .env                               # DISCORD_WEBHOOK_URL を埋める
docker compose up -d rsshub                         # RSSHub セルフホスト (Tier3 掘金用)

# CLI (現時点で動くもの)
uv run python -m karyu_tech_news --help
uv run python -m karyu_tech_news version
uv run python -m karyu_tech_news info               # 環境設定確認 (秘密値は set/not set のみ)
uv run python -m karyu_tech_news validate-sources   # config/sources.yaml をスキーマ検証
# または: uv run karyu validate-sources

# 品質ゲート (PR 前に必ず通す)
uv run pytest                                       # ユニットテスト (現状 24 / pass)
uv run ruff check .                                 # Lint
uv run mypy src tests                               # 型 (strict)

# 将来 CLI (Sprint 1A 実装予定)
uv run python -m karyu_tech_news init-db            # ⏳ Ticket #4
uv run python -m karyu_tech_news collect [--dry-run] [--source <id>]  # ⏳ Ticket #3〜#10
uv run python -m karyu_tech_news post-summary       # ⏳ Ticket #9
```

## 5. アーキテクチャ方針 (Sprint 1A)

`docs/DESIGN.md` が **単一の真実の源 (Single Source of Truth)**。要旨:

- **最小構成・fail-open・状態の外部永続化** の 3 原則に集中。
- **依存最小**: `feedparser` / `httpx` / `pydantic` / `sqlalchemy` / `pyyaml` / `python-dotenv` / `typer` / `pytest` のみ。
- **設定駆動**: ソース / LLM プロファイル / HAL 人格 / 番組フォーマットを YAML 化。
- **逆向き依存禁止**: `collect → store ← deliver`。`deliver` は `store` の読み取りのみ参照。
- **永続化**: SQLite (`data/state.db`)。4 テーブル `sources` / `items` / `source_health` / `collect_runs` (`docs/DESIGN.md` §4)。

判断基準を自力で引くための知識ベース: レイヤー責務とフローチャート分岐は [docs/architecture.md](docs/architecture.md)、ドメイン用語・状態遷移は [docs/domain/collection.md](docs/domain/collection.md)、コーディング規約は [docs/styleguide.md](docs/styleguide.md)。

長期ビジョン (三番組構成の AI ポッドキャスト局) は [docs/architecture-podcast-station.md](docs/architecture-podcast-station.md) を参照。本リポジトリで実装するのはニュース番組のみ (北極星)。

## 6. ディレクトリ構造

```text
panda-tech-news/
├── AGENTS.md                # 本書 (実体)。各 AI ツールが自動読込
├── CLAUDE.md                # → AGENTS.md (symlink)
├── README.md                # 人間向け概要・ドキュメント地図
├── pyproject.toml           # 配布名 panda-tech-news / モジュール karyu_tech_news / console script `karyu`
├── docker-compose.yml       # RSSHub セルフホスト (ADR-0004)
├── .env.example             # 環境変数雛形 (.env は git 管理外)
├── docs/
│   ├── requirements-v1.0.md         # 問題定義 (人間が作成、起点)
│   ├── DESIGN.md                    # ★ 単一の真実の源 (Sprint 1A)
│   ├── architecture.md              # レイヤー責務・判断基準フローチャート
│   ├── styleguide.md                # コーディング規約・命名・スニペット
│   ├── domain/collection.md         # 収集コンテキストの用語・ルール・状態遷移
│   ├── IMPLEMENTATION_PLAN.md       # T1〜T11 タスク分解
│   ├── WORKFLOW.md                  # マルチエージェント契約 (ロール・I/O・DoD)
│   ├── PROJECT_STATE.md             # 永続化された進捗 (全エージェント随時更新)
│   ├── TEST_LOG.md / REVIEW_REPORT.md / QA_REPORT.md  # 証跡 (実装/レビュー/QA)
│   ├── roadmap.md                   # Sprint 1A→1B→2→3→局化
│   ├── architecture-podcast-station.md  # 長期ビジョン
│   ├── design-inheritance-tc-newsflow.md # Go版からの継承パターン
│   ├── source-selection-spike-v0.1.md   # 初期 11 ソース選定 (9 有効/2 保留)
│   ├── hal-persona.md / show-format.md / editorial-policy.md  # 番組仕様
│   └── adr/                         # INDEX.md (一覧ハブ) + TEMPLATE.md + ADR-0001〜0006 (Accepted)
├── prompts/                 # 各エージェント宛 system プロンプト
│   ├── architect.md  implement.md  review.md  qa.md
├── config/
│   ├── sources.yaml         # ソース定義 (11本, enabled 9)
│   ├── llm_profiles.yaml    # MiMo / DeepSeek / Ollama (Sprint 1B 起動)
│   ├── hal_persona.yaml     # HAL 機械可読人格
│   └── show_format.yaml     # 番組構成テンプレ
├── src/karyu_tech_news/     # 実装本体 (src-layout)
│   ├── __init__.py / __main__.py / main.py / config.py
│   ├── collect/  (T3-T4 で追加: fetcher / normalize / runner)
│   ├── store/    (T5-T7 で追加: schema / repo)
│   └── deliver/  (T9 で追加: discord)
├── tests/                   # pytest (現状 24 / pass)
├── scripts/                 # spike_curl_check.sh など検証スクリプト
├── data/                    # state.db 等 (.gitkeep 以外 git 管理外)
└── assets/                  # bgm / jingles / voice_reference (素材本体は git 管理外)
```

## 7. マルチエージェント運用 (本プロジェクト固有の最重要原則)

`docs/WORKFLOW.md` が定義する組織マッピング。**実装者・レビュアー・QA は必ず別エージェント** (PR 作者 ≠ レビュアー)。

| ロール | 実行基盤 | 責務 | 主な成果物 |
|---|---|---|---|
| 人間 (プロダクトオーナー) | — | 要件・スコープ定義、merge 承認 | `docs/requirements-v1.0.md` |
| Claude Code (Opus, アーキテクト) | Claude Code | 上流設計、難所エスカレーション | `docs/DESIGN.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/adr/` |
| OpenCode (実装ミドルチーム) | OpenCode + 低コストモデル | 実装の主軸 | コード, `docs/TEST_LOG.md` |
| Codex (専任レビュアー) | Codex CLI + GPT-5 high reasoning | 独立レビュー (実装には関与しない) | `docs/REVIEW_REPORT.md` |
| Antigravity (テックリード / QA) | agy + Gemini 大コンテキスト | 最終 QA、状態保持の補助 | `docs/QA_REPORT.md` |

**永続化 > 内部記憶**: 状態は必ず `docs/PROJECT_STATE.md` に書く。モデルの内部記憶を真実の源にしない (WORKFLOW §13)。

**エスカレーション分類** (WORKFLOW §4):
- A. 実装失敗 → OpenCode 差し戻し
- B. 設計矛盾 → Claude Code/Opus
- C. 要件不明・レビュー判断割れ → **人間**
- D. 環境失敗 (依存・認証・ビルド) → 2 回連続失敗で停止し人間へ
- E. スコープ膨張 → 即停止し人間へ

## 8. コミット規約とブランチ運用

> 完了ゲート・コミット前チェックの実行手順は [docs/commit-rules.md](docs/commit-rules.md) に集約。**「完了」と言う前に pytest / ruff / mypy を fresh 出力で確認**する (記憶で代用しない)。

### 8.1 コミットメッセージ
[グローバル `~/.claude/rules/common/git-workflow.md`](~/.claude/rules/common/git-workflow.md) に従う Conventional Commits:

```
<type>: <description>

<optional body>
```

`type`: `feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `perf` / `ci`

例 (本リポジトリの直近):
- `feat: T1 and T2 initial implementation`
- `docs: update QA report and project state for Sprint 1A initial implementation`

### 8.2 ブランチ運用
- `main`: 常に安定。直接 push 禁止。
- `agent/T<N>-impl`: 各実装チケット (例: `agent/T3-impl`)。同一ブランチ内でレビュー差し戻し修正可。
- merge は **Codex レビュー PASS + Antigravity QA PASS + 人間承認** の三条件を満たした後のみ。

### 8.3 PR / コミット前チェックリスト
- [ ] `uv run pytest` グリーン
- [ ] `uv run ruff check .` クリーン
- [ ] `uv run mypy src tests` strict クリーン
- [ ] `docs/TEST_LOG.md` に実行ログを追記
- [ ] `docs/PROJECT_STATE.md` を最新化
- [ ] 「絶対 NG」(§3) に抵触していないか自己点検
- [ ] `.env` / 秘密情報 / 生成 mp3・mp4 を含めていないか

## 9. 品質ゲート (Definition of Done)

`docs/WORKFLOW.md` §10 + `docs/IMPLEMENTATION_PLAN.md` 完了の定義より:

- ユニットテスト 80% 以上カバレッジ (`pytest --cov`)
- mypy strict / ruff lint クリーン
- `python -m karyu_tech_news collect` が完走し、SQLite に items が追加される
- 同一ソース 2 回 collect で items が増えない (`UNIQUE(source_id, item_key)`)
- 1 ソースで例外発生時、他ソースが完走し `source_health.consecutive_failures` が増加
- Discord に要件 §14.1 形式のサマリーが届く
- 3 日連続稼働 (`docs/TEST_LOG.md` に証跡)

## 10. ドキュメント地図 (詳細は各 md へ)

| 種別 | パス | 役割 |
|---|---|---|
| 要件 | [docs/requirements-v1.0.md](docs/requirements-v1.0.md) | 問題定義の起点 (FR-001〜FR-122) |
| 設計 | [docs/DESIGN.md](docs/DESIGN.md) | **Sprint 1A 単一の真実の源** |
| アーキテクチャ | [docs/architecture.md](docs/architecture.md) | レイヤー責務・判断基準フローチャート (AI が分岐を引く知識ベース) |
| ドメイン | [docs/domain/collection.md](docs/domain/collection.md) | 収集コンテキストのユビキタス言語・ビジネスルール・状態遷移 |
| 規約 | [docs/styleguide.md](docs/styleguide.md) | コーディング規約・命名規則・スニペット例 |
| コミット/完了ゲート | [docs/commit-rules.md](docs/commit-rules.md) | 完了宣言ゲート・コミット前チェック・DoD/境界の集約 |
| 実装計画 | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | T1〜T11 タスク分解 |
| ワークフロー | [docs/WORKFLOW.md](docs/WORKFLOW.md) | エージェント間契約 |
| 状態 | [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | 永続化された進捗 (★ ここを真の記憶とする) |
| 長期ビジョン | [docs/architecture-podcast-station.md](docs/architecture-podcast-station.md) | 三番組構成 AI ポッドキャスト局 |
| 設計継承 | [docs/design-inheritance-tc-newsflow.md](docs/design-inheritance-tc-newsflow.md) | Go 版からの継承パターン |
| ロードマップ | [docs/roadmap.md](docs/roadmap.md) | Sprint 1A→1B→2→3→局化 |
| Spike | [docs/source-selection-spike-v0.1.md](docs/source-selection-spike-v0.1.md) | 初期 11 ソース選定結果 |
| 番組仕様 | [docs/hal-persona.md](docs/hal-persona.md), [docs/show-format.md](docs/show-format.md), [docs/editorial-policy.md](docs/editorial-policy.md) | HAL 人格 / 構成 / 編集方針 |
| ADR | [docs/adr/INDEX.md](docs/adr/INDEX.md) | ADR 一覧ハブ (0001 Python単一 〜 0006 TTS抽象化)。新規は TEMPLATE.md から |
| プロンプト | [prompts/](prompts/) | 各エージェント宛 system 指示 |
| 証跡 | [docs/TEST_LOG.md](docs/TEST_LOG.md) / [docs/REVIEW_REPORT.md](docs/REVIEW_REPORT.md) / [docs/QA_REPORT.md](docs/QA_REPORT.md) | 実装 / レビュー / QA の根拠 |

## 11. AI エージェント向け運用ルール (本書まとめ)

1. **作業開始時に必ず読む**: 本書 → `docs/PROJECT_STATE.md` → `docs/DESIGN.md` → 該当 Ticket の `docs/IMPLEMENTATION_PLAN.md` 該当行。
2. **判断ログを残す**: 設計判断・代替案検討は ADR (`docs/adr/ADR-000N-*.md`) に追記。
3. **状態を必ず書く**: 進捗更新・人間判断待ち事項は `docs/PROJECT_STATE.md` へ。
4. **疑ったら止める**: 絶対 NG (§3) に抵触する/しそうなら実装を止め、`docs/PROJECT_STATE.md` の「人間判断待ち」にエスカレーション理由を書く。
5. **Sprint 越境禁止**: Sprint 1A の DoD (§9) を満たすまで 1B 以降の機能 (LLM/TTS/動画/YouTube) を導入しない。
6. **ドキュメントは Single Source of Truth**: 議論や決定は md に書く。チャット会話の合意のみで実装を進めない。
7. **言語**: 日本語で応答 (英語のみのドキュメント作成は例外)。

## 12. コーディング原則 (Karpathy 4 原則)

> 出典: [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — Andrej Karpathy による LLM コーディング pitfall ([X 元投稿](https://x.com/karpathy/status/2015883857489522876)) を 4 原則に整理したもの。
> 適用: 全エージェント (Claude Code / OpenCode / Codex / Antigravity)。グローバル `~/.claude/CLAUDE.md` の同名セクションを本プロジェクト固有の手続きに翻訳した実装ガイド。**§3「絶対 NG」と矛盾する場合は §3 を優先**。

### 12.1 Think Before Coding — 実装前に思考する
**勝手に仮定しない。混乱を隠さない。トレードオフを提示する。**

本プロジェクトでの具体化:
- **DESIGN.md を読まずに実装着手しない**。設計矛盾を発見したら実装を止め、`docs/PROJECT_STATE.md`「人間判断待ち」へ追記 (WORKFLOW §4 区分 B「設計失敗」)。
- 複数解釈があれば全部出す。例: 取得失敗時の表現を「例外を raise」/「`FetchResult.error` に包む」のどちらにするか — 後者が fail-open に合致するが、判断根拠を ADR か実装コメントに残す。
- 不明点はチケット着手前に列挙し、Codex レビュー前に Q&A を済ませる (「レビューで初出の疑問」は要件失敗 C の兆候)。

### 12.2 Simplicity First — 最小実装
**問題を解く最小コード。投機的な機能は書かない。**

本プロジェクトでの具体化:
- DESIGN.md §1「最小構成・fail-open・状態の外部永続化」と完全合致。Sprint 1A で LLM/TTS/動画を入れる誘惑を断つ (§3.4)。
- 単一用途のための抽象化禁止。Sprint 1A で `TTSEngine` プロトコルや LLM プロバイダ抽象を**先回りで書かない** ([ADR-0006](docs/adr/ADR-0006-tts-irodori-abstraction.md) は Sprint 2 着手時に有効化)。
- 「ジュニアエンジニアに『これ複雑すぎ』と言われないか?」自問し、Yes なら書き直す。`tc-newsflow` Go 版の落とし穴も「最初から直す」方針 ([design-inheritance §13](docs/design-inheritance-tc-newsflow.md))。

### 12.3 Surgical Changes — 外科手術的変更
**触るのは必要な箇所だけ。自分が作ったゴミだけ片付ける。**

本プロジェクトでの具体化:
- `agent/T<N>-impl` ブランチ内では Ticket #N に直接トレースできない変更を禁止。Ticket #3 (フェッチャ) で `config.py` の既存型ヒントをついでに整理するのは NG。
- 既存スタイルに合わせる (§5 のレイヤー逆向き依存禁止、ruff 100 文字行長、mypy strict 既存設定を変更しない)。
- 未関連の dead code を見つけても**削除せず**、`docs/PROJECT_STATE.md`「人間判断待ち」へ記載に留める。
- 自分の変更で orphan になった import/関数/変数のみ削除可。事前から残っていた死コードに手を出さない。

### 12.4 Goal-Driven Execution — 目標駆動実行
**成功基準を定義し、検証されるまでループする。**

本プロジェクトでの具体化:
- 各 Ticket の成功基準 = `docs/IMPLEMENTATION_PLAN.md`「完了の定義」+ 本書 §9 品質ゲート。曖昧な「動いた」は採用しない。
- 命令形 → 検証可能形へ変換:
  - 「fail-open を実装」→「1 ソースが例外を投げても他ソースが完走し、`source_health.consecutive_failures` が +1 されるテストを書き緑にする」
  - 「dedupe を入れる」→「同一 `(source_id, item_key)` を 2 回 insert すると 1 行のままになるテストを書く」
- 多段タスクは `1. ... → verify: ...` 形式を `docs/TEST_LOG.md` に記録 (例: `1. fetcher.py → verify: pytest tests/test_fetcher.py -q が緑`)。
- pytest + ruff + mypy strict が**3 つとも緑**になるまで自走可能。「ローカルで動いた気がする」で止めない。

---

> 改訂方針: 重大な設計判断は ADR を追加 → 本書 §3 / §5 / §10 を更新。`docs/PROJECT_STATE.md` の「直近の設計判断」も同期。
> 本書の対象範囲を超える詳細は必ず該当 md へポインタを置く (300 行制限維持のため)。
