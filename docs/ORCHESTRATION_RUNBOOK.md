# 自律オーケストレーション運用書 (ORCHESTRATION_RUNBOOK)

> **対象読者: 本プロジェクトのオーケストレーターを務める AI エージェント (Claude Code/Opus またはその後継)。**
> 目的: オーケストレーターが交代しても、この 1 冊を読めば「現在地の判定 → 次の一手の決定 → 適切な AI への委任 → 検証 → 記録」を**人間の逐次指示なしに**回せるようにする。
> 位置づけ: [WORKFLOW.md](./WORKFLOW.md) が *組織契約* (誰が何の役割か) を定義するのに対し、本書は *操作手順* (どう自走するか) を定義する。両者は補完関係。
> 不変条件 ([AGENTS.md](../AGENTS.md) §3「絶対 NG」) は本書より常に優先。本書と §3 が矛盾したら §3 に従う。

---

## 1. 起動シーケンス (コールドスタート時に必ずこの順で読む)

1. [AGENTS.md](../AGENTS.md) — 最上位の指示書・禁止事項 (§3)。
2. [docs/PROJECT_STATE.md](./PROJECT_STATE.md) — **真の記憶**。現在のフェーズ・人間判断待ち・改訂履歴。内部記憶より常にこちらを信じる。
3. 本書 (ORCHESTRATION_RUNBOOK.md) — 次の一手の決め方。
4. [docs/TEST_LOG.md](./TEST_LOG.md) の末尾 — 直近の運用実走の結果 (T22 観察記録など)。
5. 必要に応じ [docs/HANDOFF.md](./HANDOFF.md) — 直近の引き継ぎ時点スナップショット (あれば)。

読んだら **§2 の決定木で現在地を判定**してから動く。「とりあえず実装」を始めない (§12.1 Think Before Coding)。

---

## 2. 状態判定 → 次アクションの決定木 (本書の核)

PROJECT_STATE.md の「現在のフェーズ」と git/PR 状態を突き合わせ、上から順に最初に当てはまる行を実行する。

| # | 判定条件 (確認コマンド) | 現在地 | 次の一手 |
|---|---|---|---|
| 1 | `git status` が dirty | 作業途中で中断 | 未コミット変更の意図を PROJECT_STATE と照合 → §5 ゲート → commit (作業ブランチへ)。意図不明な変更は破棄せず人間判断待ちに記録 |
| 2 | `uv run pytest` が赤 | 品質ゲート破れ | §5 を緑にするまで他作業を止める。原因が自分の変更でなければ `git log` で犯人を特定し PROJECT_STATE に記録 |
| 3 | TEST_LOG に T22 Day N 未記録 かつ 当日朝 | 日次観察日 | §4 日次運用ループを実行し観察を記録 |
| 4 | T22 が 3 日未達 | Sprint 1B 観察中 | スケジュールタスク (§7) の自動実行を待つ。手動補完が必要なら §4 を実行 |
| 5 | T22 完了 かつ Sprint 1B 完了 PR 未作成 | 観察完了 | 3 日総括を TEST_LOG に記入 → DoD 更新 → 完了 PR 作成 (`gh pr create`)。**merge はしない** (§6 人間ゲート) |
| 6 | Sprint 1B 完了 PR がマージ済み かつ Sprint 2 Go 未宣言 | 次フェーズ判断待ち | **停止して人間を待つ** (§6)。判断材料は [IMPLEMENTATION_PLAN-2.md §6](./IMPLEMENTATION_PLAN-2.md) と `docs/proposals/` に準備済み |
| 7 | 人間が Sprint 2 Go を PROJECT_STATE に記録済み | Sprint 2 着手可 | 最新 main から `agent/T23-impl` を切り、[IMPLEMENTATION_PLAN-2.md](./IMPLEMENTATION_PLAN-2.md) の T23 から §3 の委任サイクルで実装 |
| 8 | 上記いずれも非該当 | 平常運用 | §4 日次運用ループ (本番配信の継続) + ドキュメントのドリフト点検 |

> **原則**: 決定木が「人間ゲート」を指したら、追加作業を発明せず停止する。ゲートを迂回する作業 (例: 観察を待たず Sprint 2 コードを書く) は §6/§3.4 違反であり、プロダクトを*前進ではなく劣化*させる。

---

## 3. 外部 AI ルーティング (誰に投げるか・正確な呼び出し方)

> **大原則**: オーケストレーター (あなた) のトークンは希少資源。他の AI ができることは委任し、自分は**計画・統合・判断・検証**に集中する。
> **検証必須**: 委任結果は必ず自分で検証してから採用する (出典 URL の実在確認、コードなら §5 ゲート)。外部 AI の出力を無検証で「事実」として記録しない (本プロジェクトでは Gemini の引用 URL 2 件が 404 だった実績あり)。
> **役割分離 (WORKFLOW §1, 最重要)**: **実装者・レビュアー・QA は必ず別 AI**。PR 作者 ≠ レビュアー。同一コンテキストで自己承認しない。

| 用途 | 委任先 CLI | 非対話呼び出し | モデル指針 |
|---|---|---|---|
| **日常実装・リファクタ・テスト** | **OpenCode** | `opencode run -m <model> "<prompt>"` (リポジトリ直下で。`--print-logs` でログ可視化) | Go プラン (有料サブ優先): `opencode-go/qwen3.7-max` / `opencode-go/qwen3.7-plus` / `opencode-go/minimax-m3` / `opencode-go/kimi-k2.6`。**トークン上限到達時**は OpenCodeZen 無料枠 `opencode/nemotron-3-ultra-free` (最有力) → `opencode/deepseek-v4-flash-free` の順で試す |
| **独立レビュー** (実装には関与させない) | **Codex** (GPT-5 high reasoning) | `codex exec --sandbox workspace-write "<prompt>"` | プロンプトは [prompts/review.md](../prompts/review.md) を Sprint 読み替えで使用。判定は PASS/FAIL + 重大度別件数 |
| **最終 QA・整合性確認** | **Antigravity** (agy, Gemini 大コンテキスト) | `agy -p "<prompt>"` | プロンプトは [prompts/qa.md](../prompts/qa.md)。DoD 全項目チェック + ドリフト検出 |
| **調査・セカンドオピニオン** | **Gemini** (検索グラウンディング) | `gemini -p "<prompt>"` | 一次情報の URL は**必ず自分で実在検証** (`curl -so /dev/null -w "%{http_code}"`) |
| **Git/PR ワークフローのみ** | **Copilot CLI** または `gh` | `gh pr create` / `gh pr view` 等 | **コーディングには絶対使わない** (月 300 req 制限)。PR 作成・Issue 分析専用 |

委任の型 (推奨):
```bash
# 実装委任 (OpenCode, Go プラン) — バックグラウンド実行して結果を回収
opencode run -m opencode-go/qwen3.7-max "<具体的タスク + 完了条件 + 触ってはいけない範囲>" > /tmp/oc-out.txt 2>&1 &

# 独立レビュー (Codex)
codex exec --sandbox workspace-write "$(cat prompts/review.md) 対象: <Ticket>。基準: DESIGN.md / IMPLEMENTATION_PLAN-*.md"

# QA (Antigravity)
agy -p "$(cat prompts/qa.md) 対象: <Ticket>。DoD: IMPLEMENTATION_PLAN-*.md の該当節"
```

> **既知の不調**: OpenCode CLI が `UnknownError` を連続で返すことがある (2026-06 時点)。2 回連続失敗したら **区分 D (環境失敗)** として PROJECT_STATE「人間判断待ち」に記録し、当該タスクはインライン (自分) で代替するか別モデルにフォールバックする (WORKFLOW §4)。

---

## 4. 日次運用ループ (本番配信の心臓部)

平日朝、以下を順に実行する (要件 §13.2)。各ステップは fail-open — 1 つの失敗で全体を止めない。

```bash
cd /Users/kairyon/projects/panda-tech-news
git checkout agent/T22-impl                  # 作業ブランチ (フェーズにより切り替え)
docker compose up -d rsshub                   # 掘金など RSSHub 経由ソース用 (unhealthy 表示でも実応答 200 なら可)
uv run python -m karyu_tech_news collect --post          # 収集 → SQLite → Discord サマリー
uv run python -m karyu_tech_news draft --variant A --post # LLM 編集判定 → 3-5 本選定 → 台本 → Discord 台本投稿
uv run python -m karyu_tech_news evaluate                 # A/B/C 定量サマリー
```

記録すべき観察項目 (TEST_LOG.md へ):
- 収集: 成功ソース数 / 新着件数 / fail-open 発火の有無
- 編集: 候補数 → 採用数 / llm 成功・retry・fallback 回数 / editor JSON 安定性
- コスト: トークン消費 (要件 §9.7 月 1,500-3,000 円の範囲内か)
- 配信: Discord HTTP ステータス (204 期待)
- 品質: 「音声化する価値」観点の所感 / [editorial-policy.md](./editorial-policy.md) 違反の有無

---

## 5. 品質ゲート (完了宣言前に必ず・記憶で代用しない)

```bash
uv run pytest        # 全テスト緑 (現状 242)
uv run ruff check .  # lint クリーン
uv run mypy src tests # 型 strict クリーン
```

3 つとも**フレッシュ実行で**緑を確認してからのみ「完了」と言う ([commit-rules.md](./commit-rules.md))。
コミット前チェックリストは [AGENTS.md](../AGENTS.md) §8.3。秘密値 (API キー / Webhook URL / トークン) をログ・ドキュメント・コミットに含めない。

---

## 6. エスカレーション — ここで必ず止まる (人間専権ゲート)

以下は AI が代替してはならない。決定木が指したら停止し、PROJECT_STATE「人間判断待ち」に判断材料を添えて記録する ([AGENTS.md](../AGENTS.md) §7, WORKFLOW §4)。

- **A 実装失敗** → OpenCode 差し戻し (2 回連続失敗で停止)
- **B 設計矛盾** → Claude Code/Opus (アーキテクト) が DESIGN/ADR で解決
- **C 要件不明・レビュー判断割れ** → **人間**
- **D 環境失敗** (依存・認証・課金) → 2 回連続で停止し**人間**
- **E スコープ膨張** ("ついでに") → 即停止し**人間**

**特に AI が絶対に単独で行わない 4 行為**:
1. `main` への merge / 直接 push
2. コスト上限を超える LLM 呼び出し方の変更 (要件 §9.7)
3. Sprint 境界の越境 (観察未完での次 Sprint コード着手, §3.4)
4. API 契約・課金・声リファレンス試聴などの**人間の意思決定そのもの**

---

## 7. 既に動いている自動化 (確認方法つき)

| 仕掛け | 内容 | 確認 |
|---|---|---|
| ローカルスケジュールタスク | `t22-day2-observation` (06-13 朝) / `t22-day3-observation` (06-14 朝) が §4 ループ + 記録 + push を自走。Day 3 は 3 日総括 + DoD 更新 + 完了 PR 作成まで | `ls ~/.claude/scheduled-tasks/` / アプリ内「Scheduled」 |
| (注意) 実行条件 | スケジュールタスクは**アプリ起動中のみ**発火。閉じていれば次回起動時に実行 | — |

新しい定期運用を組むときも、人間ゲート (§6) を踏むタスクは「下書き・PR 作成まで」に留め、merge は人間に残す。

---

## 8. このプロジェクトの不変条件 (要約・全文は AGENTS.md §3)

- リポジトリ: main 直 push 禁止 / merge 人間専権 / hook スキップ禁止 / `.env` commit 禁止
- データ: `UNIQUE(source_id, item_key)` のみ / 空 `item_key` INSERT 禁止 / `item_key` 生成順固定 / str(コードポイント)単位の切り詰め
- 耐障害性: ソース単位 fail-open / Discord 失敗で collect を落とさない / HTTP は必ずタイムアウト 30s + リトライ 2
- コンテンツ: 記事本文転載禁止 (要約と HAL 解説のみ) / 無断声クローン禁止 / ナショナリズム表現禁止 / AI 音声の明示
- 言語: Python 3.11+ 単一 (Go/Node へ戻さない)
- LLM 設計: JSON 判定と日本語台本を同時に書かせない / tone は LLM に並べさせず決定的コードで / fallback 無しで配信しない

---

> 改訂: 運用手順が変わったら本書を更新し、PROJECT_STATE の改訂履歴に記録する。状態スナップショットは本書ではなく [HANDOFF.md](./HANDOFF.md) / [PROJECT_STATE.md](./PROJECT_STATE.md) に置く (本書は陳腐化しない恒久手順に保つ)。
