# 自律オーケストレーション運用書 (ORCHESTRATION_RUNBOOK)

> **対象読者: 本プロジェクトのオーケストレーターを務める AI エージェント (Claude Code/Opus またはその後継)。**
> 目的: オーケストレーターが交代しても、この 1 冊を読めば「現在地の判定 → 次の一手の決定 → 適切な AI への委任 → 検証 → 記録」を**人間の逐次指示なしに**回せるようにする。
> 位置づけ: [WORKFLOW.md](./WORKFLOW.md) が *組織契約* (誰が何の役割か) を定義するのに対し、本書は *操作手順* (どう自走するか) を定義する。両者は補完関係。
> 不変条件 ([AGENTS.md](../AGENTS.md) §3「絶対 NG」) は本書より常に優先。本書と §3 が矛盾したら §3 に従う。
> 最終見直し: 2026-06-29。agentic / multi-agent 研究反映の根拠は [agentic-workflow-research-2026.md](./agentic-workflow-research-2026.md)。

---

## 1. 起動シーケンス (コールドスタート時に必ずこの順で読む)

1. [AGENTS.md](../AGENTS.md) — 最上位の指示書・禁止事項 (§3)。
2. [docs/PROJECT_STATE.md](./PROJECT_STATE.md) — **真の記憶**。現在のフェーズ・人間判断待ち・改訂履歴。内部記憶より常にこちらを信じる。
3. 本書 (ORCHESTRATION_RUNBOOK.md) — 次の一手の決め方。
4. [docs/TEST_LOG.md](./TEST_LOG.md) の末尾 — 直近の運用実走の結果 (T32/T36 観察・日次配信など)。
5. 必要に応じ [docs/HANDOFF.md](./HANDOFF.md) — 直近の引き継ぎ時点スナップショット (あれば)。

読んだら **§2 の決定木で現在地を判定**してから動く。「とりあえず実装」を始めない (§12.1 Think Before Coding)。

---

## 2. 状態判定 → 次アクションの決定木 (本書の核)

PROJECT_STATE.md の「現在のフェーズ」と git/PR 状態を突き合わせ、上から順に最初に当てはまる行を実行する。

| # | 判定条件 (確認コマンド) | 現在地 | 次の一手 |
|---|---|---|---|
| 1 | `git status` が dirty | 作業途中で中断 | 未コミット変更の意図を PROJECT_STATE と照合 → §5 ゲート → commit (作業ブランチへ)。意図不明な変更は破棄せず人間判断待ちに記録 |
| 2 | `uv run pytest` が赤 | 品質ゲート破れ | §5 を緑にするまで他作業を止める。原因が自分の変更でなければ `git log` で犯人を特定し PROJECT_STATE に記録 |
| 3 | `PROJECT_STATE.md` が T36 code loop 完了・T32 人間試聴待ちを示す | Sprint 2 実装側は完了、聴感判断待ち | 新機能を発明しない。必要作業は (a) 証跡整理 (b) docs drift 修正 (c) 人間判断材料の更新に限定 |
| 4 | `~/Library/LaunchAgents/com.karyu.daily-pipeline.plist` が存在 | 3日限定 launchd が残存している可能性 | `launchctl list | grep karyu` と plist を確認。残っていれば人間TODO履歴と照合し、不要なら撤去記録を PROJECT_STATE に残す |
| 5 | 日次配信を継続する人間Goがある | 継続運用 | §4 の日次運用ループを実行し、TEST_LOG / PROJECT_STATE へ収集・台本・音声・Discord・音質ゲートの結果を記録 |
| 6 | 日次配信継続Goが無い | 人間判断待ち | 恒久 launchd / `/schedule` クラウド実行 / 停止の判断材料だけ整備し、新しい定期実行は作らない |
| 7 | T36 PR/ブランチが未PR・未merge | 実装完了後の公開待ち | fresh §5 ゲート → REVIEW/QA 証跡確認 → PR 作成。**merge はしない** (§6 人間ゲート) |
| 8 | 上記いずれも非該当 | 平常運用 | ドキュメント drift 点検、依存・モデル・CLI仕様の再確認、既存DoDの維持 |

> **原則**: 決定木が「人間ゲート」を指したら、追加作業を発明せず停止する。ゲートを迂回する作業 (例: 観察を待たず Sprint 2 コードを書く) は §6/§3.4 違反であり、プロダクトを*前進ではなく劣化*させる。

---

## 3. 外部 AI ルーティング (誰に投げるか・正確な呼び出し方)

> **大原則**: オーケストレーター (あなた) のトークンは希少資源。他の AI ができることは委任し、自分は**計画・統合・判断・検証**に集中する。
> **検証必須**: 委任結果は必ず自分で検証してから採用する (出典 URL の実在確認、コードなら §5 ゲート)。外部 AI の出力を無検証で「事実」として記録しない (本プロジェクトでは Gemini の引用 URL 2 件が 404 だった実績あり)。
> **役割分離 (WORKFLOW §1, 最重要)**: **実装者・レビュアー・QA は必ず別 AI**。PR 作者 ≠ レビュアー。同一コンテキストで自己承認しない。

| 用途 | 委任先 CLI | 非対話呼び出し | モデル指針 |
|---|---|---|---|
| **日常実装・リファクタ・テスト** | **OpenCode** | `opencode run -m <model> "<prompt>"` (リポジトリ直下で。`--print-logs` でログ可視化) | **タスクの難易度に応じて選ぶ (§3.2)。値段順・固定リストではない**。Go 枠上限到達時は Zen 無料枠へ。**他にも認証済みプロバイダが存在するが本ワークフローでは使用しない (§3.1)** |
| **独立レビュー** (実装には関与させない) | **Codex** (GPT-5系) | `codex exec --sandbox workspace-write -c model_reasoning_effort=<effort> "<prompt>"` | **タスクの難所に応じて effort を選ぶ (§3.3)。xhigh は禁止ではなく難所用**。プロンプトは [prompts/review.md](../prompts/review.md) を Sprint 読み替えで使用。判定は PASS/FAIL + 重大度別件数 |
| **最終 QA・整合性確認** | **Antigravity** (agy, Gemini系既定) | `agy -p "<prompt>"` | **既定モデルは Gemini 3.5 Flash (Pro ではない)。タスクに応じて `--model` で選ぶ (§3.4)**。プロンプトは [prompts/qa.md](../prompts/qa.md)。DoD 全項目チェック + ドリフト検出 |
| **調査・セカンドオピニオン** | **Gemini** (検索グラウンディング) | `gemini -p "<prompt>"` | ⚠️ **2026-06-22 時点で認証切れを確認 (§3.4)。実行前に `gemini -p` が非対話で通るか要確認**。一次情報の URL は**必ず自分で実在検証** (`curl -so /dev/null -w "%{http_code}"`) |
| **Git/PR ワークフローのみ** | **`gh` (素のサブコマンド)** | `gh pr create` / `gh pr view` 等 | **コーディングには絶対使わない**。`gh` の素のサブコマンドは REST API 直接呼び出しで月300req制限の対象外。AIエージェント (`copilot`/`gh copilot`) を呼ぶ場合のみ枠を消費 (§3.5) |

委任の型 (推奨):
```bash
# 実装委任 (OpenCode, Go プラン) — バックグラウンド実行して結果を回収
# 注: これは独立シェル/人間の対話シェル向けの例。Claude Code の Bash tool から呼ぶ場合は
#     生 `&` ではなく run_in_background:true パラメータを使うこと
#     (tool管理外のバックグラウンド化はプロセス回収タイミングでstdoutを失うリスクがあり、
#     2026-06-14 の T22 委任時のハング+並行編集汚染→git reset 復旧の一因とみられる)。
#     並行して別ブランチ/別PRを触る可能性がある場合は git worktree で隔離すること。
opencode run -m opencode-go/qwen3.7-max "<具体的タスク + 完了条件 + 触ってはいけない範囲>" > /tmp/oc-out.txt 2>&1 &

# 独立レビュー (Codex)
# 注: effort は省略しないこと。~/.codex/config.toml のグローバル既定が xhigh になっている環境があり、
#     未指定だと毎回無自覚に xhigh で走る。xhigh 自体は禁止ではなく難所では正解だが、
#     定型レビューまで毎回 xhigh だとトークンを浪費する → タスクの難所に応じて §3.3 の表から選ぶ
#     (2026-06-22 codex exec 実行で -c 指定が確実に効くことを確認済み)。
codex exec --sandbox workspace-write -c model_reasoning_effort=<effort> "$(cat prompts/review.md) 対象: <Ticket>。基準: DESIGN.md / IMPLEMENTATION_PLAN-*.md"

# QA (Antigravity)
agy -p "$(cat prompts/qa.md) 対象: <Ticket>。DoD: IMPLEMENTATION_PLAN-*.md の該当節"
```

> **稼働確認済み (2026-06-13)**: `opencode-go/qwen3.7-max` (Go プラン) と `opencode/nemotron-3-ultra-free` (無料枠) の両方で smoke テスト成功。
> **既知の不調と対処**: OpenCode ≤1.15.0 は `UnknownError` (実体は `NOT NULL constraint failed: session_message.seq` — 空セッション DB で seq 計算が NULL になるアプリバグ) を連発した。**`opencode upgrade` で 1.17.4 以上にすると解消**。再発したら ① まず `opencode upgrade` ② `opencode db "SELECT count(*) FROM session_message"` でローカル DB を確認。2 回連続失敗が続けば **区分 D (環境失敗)** として PROJECT_STATE「人間判断待ち」に記録し、当該タスクはインライン (自分) か Codex に一時フォールバック (WORKFLOW §4)。

### 3.1 OpenCode 認証済みプロバイダと使用範囲

`opencode providers list` で確認できる認証済みプロバイダは複数あるが、本ワークフローで使うのは **OpenCode Go (`opencode-go/*`)** と **OpenCode Zen 無料枠 (`opencode/*-free`, 認証不要)** のみ。以下は**使用しない**:

- **GitHub Copilot (oauth)** → `github-copilot/*` モデル群。本書 §3 表「Git/PR ワークフローのみ」の Copilot CLI 月 300 req 制限と同一サブスクリプションの premium request 枠を共有している可能性が高く、未検証のまま使うと PR/Issue 用の枠を無自覚に消費しうる。
- **Xiaomi Token Plan (China) (api)** → `xiaomi-token-plan-cn/*`。本番 MiMo エディタ (`config/llm_profiles.yaml`) と同一キーかどうか未確認。さらに `mimo-v2.5-tts-voiceclone` / `mimo-v2.5-tts-voicedesign` を含み、AGENTS.md §3.5「無断声クローン禁止」に隣接する領域のため触らない。
- 直接 `deepseek/*` (API キー) も認証済みだが、コスト追跡を `opencode-go`/Zen の命名規則に揃えるため本ワークフローでは使わない。

OpenCode のモデルカタログは継続的に拡大する (`opencode models --verbose` で最新確認、`opencode stats` でコスト確認)。**smoke test 前の新顔モデルを優先採用しない** — 名前が良さそうでも実績のあるモデルを優先する。

### 3.2 タスク難易度別のモデル選択 (2026-06-22、単純な値段順にしない)

**原則**: 安い = 常に正解ではない。高い/高ベンチマーク = 常に正解でもない。OpenCode Go の利用枠は **$ 換算のローリング上限** ($12/5時間・$30/週・$60/月、`opencode.ai/docs/go`) — モデルの単価がそのまま消費速度を決める。タスクの難易度に対して過不足ないモデルを選び、同程度の品質が見込める場合のみ安い方を選ぶ。

**検証状況 (2026-06-22)**: Go プラン 13 種・Zen 無料枠 5 種、**計 18 モデル全てを `opencode run` で実 smoke test 済み** (簡単な dedupe 関数を書かせ接続性とコード正確性を確認、全モデル正答)。ただし下表の「コード特化」「長時間耐久」等の比較優位の記述はこの smoke test では検証できていない (タスクが簡単すぎて差が出ない) — 外部ベンチマーク/比較記事の報告値であり、本プロジェクトの実難易度タスクでの追体験はまだ無い。新規モデルはまず難易度の低いタスクで実績を作ってから難易度の高いタスクに広げる。

| タスク特性 | 推奨モデル | 理由 |
|---|---|---|
| 定型実装 (既存パターン踏襲、IMPLEMENTATION_PLAN.md の記述が具体的) | `opencode-go/deepseek-v4-flash` / `opencode-go/mimo-v2.5` | $0.14/$0.28 と最安格、1M context。SWE-bench Verified 79% 相当の報告あり |
| 条件分岐・エッジケースが絡む実装 (fail-open, dedupe 等) | `opencode-go/deepseek-v4-flash` (`--variant max` 指定) / `opencode-go/kimi-k2.7-code` / `opencode-go/minimax-m2.7` / `opencode-go/qwen3.7-plus` | 中価格帯。K2.7-Code は temperature 固定で再現性が高くコード特化との報告。M2.7 は使用量倍率の注記なし |
| レビュー差し戻し後の修正・複数制約を同時に満たす実装 | `opencode-go/deepseek-v4-pro` / `opencode-go/mimo-v2.5-pro` | DeepSeek は SWE-bench Verified 80.6% (報告値)。コストは Flash 系の約12倍だが、差し戻し2往復より1回で通る方が結果的に安い |
| 長時間・複数モジュール横断の自律実装 (T30/T31 規模、数百秒〜) | `opencode-go/kimi-k2.6` | 13時間・4000+ tool call 耐久の報告 (本モデルのみ 2026-06-13 に実タスクでも稼働確認済み)。単発の精度よりエンドツーエンド完走の信頼性を優先 |
| 大規模コンテキストの調査・トレース (複数モジュール横断で挙動を追う) | `opencode-go/qwen3.6-plus` / `opencode-go/glm-5.2`、または無料の `opencode/nemotron-3-ultra-free` | いずれも 1M context。**GLM-5.2 は同価格の GLM-5.1 (202K context) を仕様上完全に上回るため 5.1 を使う理由はない** (両方 smoke test 済み)。Nemotron は無料で Go 枠を消費しない |
| 些末な確認・使い捨ての実験 | Zen 無料枠: `opencode/north-mini-code-free` / `opencode/deepseek-v4-flash-free` / `opencode/mimo-v2.5-free` / `opencode/big-pickle` | Go プランの $ 枠を消費しない。big-pickle は最古参 (2025-10-17) で特長不明だが smoke test は通過 |
| **最終手段** (上記で品質が足りない場合のみ。デフォルトにしない) | `opencode-go/minimax-m3` (**表示名が「3x usage」= $ 枠消費が単価の3倍相当とみられる**) / `opencode-go/qwen3.7-max` (カタログ最高額 $2.50/$7.50) | 最高ベンチマークだが Go 枠消費が最も速い |

これで Go プラン 13 種 (`deepseek-v4-flash/pro`, `glm-5.1/5.2`, `kimi-k2.6/k2.7-code`, `mimo-v2.5/v2.5-pro`, `minimax-m2.7/m3`, `qwen3.6-plus`, `qwen3.7-max/plus`) と Zen 無料枠 5 種 (`big-pickle`, `deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`, `north-mini-code-free`) の全 18 モデルが上表のいずれかに対応する。

**検証状況の詳細**: `kimi-k2.6` / `qwen3.7-max` / `qwen3.7-plus` / `minimax-m3` は 2026-06-13 に実タスクで委任実績あり。残り 14 モデルは 2026-06-22 に `opencode run` 経由で接続性とコード正答 (smoke レベル) を確認済み — Zen 無料枠の `nemotron-3-ultra-free` は初回 smoke test がハングしたが再試行で正常応答 (一時的な無料枠混雑とみられ、システム自体の不調ではないと判断: `opencode-go/kimi-k2.6` で同時刻に正常応答を確認済み)。

### 3.3 Codex の reasoning effort 選択 (2026-06-22、xhigh は禁止ではなく適材適所)

**原則**: `~/.codex/config.toml` のグローバル既定は `xhigh`。**xhigh 自体は禁止ではない** — トークン消費は大きいが、本当に難しいレビュー (設計矛盾の深い追跡、複数ファイル横断の整合性調査) では正しい選択。避けるべきは「惰性で常に最高値」「逆に常に同じ値に固定する」という思考停止であり、タスクの難所に応じて選ぶ。`-c model_reasoning_effort=<level>` (`none`/`minimal`/`low`/`medium`/`high`/`xhigh`) で明示指定すること (未指定だとグローバル既定の xhigh に無自覚に流れる)。

| タスク特性 | 推奨 effort | 理由 |
|---|---|---|
| 定型チケットの単発レビュー (差分が小さく既存パターンに沿う) | `high` | 十分な精度でトークン消費を抑える既定値 |
| 差し戻し後の再レビュー (前回指摘の修正箇所のみ確認) | `medium`〜`high` | スコープが狭く、過剰な深掘りは不要 |
| 設計不整合の深い追跡・複数ファイル横断のデータ整合性調査 (例: 2026-06-21 の PR #18 ミスマージ調査) | `xhigh` | `gh` の表示と `git merge-base` の実態が食い違うような見落としやすい根因を掘る必要があり、浅い推論では誤判定するリスクがある |
| Sprint 終端の複数チケット横断レビュー・QA ゲート最終判定 | `xhigh` | 個々のチケットの整合性だけでなく Sprint 全体の DoD 適合まで見るため探索範囲が広い |

**モデル (ChatGPT 認証、本構成の auth mode)**: 既定 `gpt-5.5` (2026年2月リリース、1M context [experimental])。`gpt-5.5` が `model not found` で 404 する既知の不具合報告がある ([openai/codex#26892](https://github.com/openai/codex/issues/26892)) — その場合は `-c model="gpt-5.4"` にフォールバック (同じく 1M context experimental)。`gpt-5.4-mini` は軽量タスク/サブエージェント向けの安価版。`gpt-5.3-codex-spark` は ChatGPT **Pro** 限定のプレビューで本契約が Pro かは未確認のため前提にしない。`gpt-5.2-codex` は API キー認証向けで本構成 (ChatGPT 認証) では使わない。旧称 `gpt-5.3-codex` への参照は config.toml の `model_migrations` で `gpt-5.4` に自動移行される。

**ネイティブなレビュー専用コマンド**: `codex exec` への自前プロンプトに加え、diff スコープを直接指定できる `codex review` / `codex exec review` サブコマンドが存在する (`--base <branch>` で base 比較、`--uncommitted` で作業中差分、`--commit <SHA>` で単一コミット。例: `codex review --base main "$(cat prompts/review.md)"`)。現行方式は Codex 自身が git 履歴を能動的に探索する前提で実用上機能しているが、diff 境界を明示したい場合の選択肢として記録する (本書の既定コマンドは変更していない、採用は別途判断)。

**運用上の注意**: `codex doctor` で過去のロールアウトに `opencode-go` プロバイダ経由の実行が 1 件存在することを確認した (`openai=62, opencode-go=1`)。config.toml に `[model_providers.opencode-go]` が登録されているため `codex exec -m opencode-go/<model>` で OpenCode Go の同じ有料枠に課金される経路が技術的に存在する — 本ワークフローでは使わない。意図的でなければ `-m opencode-go/...` を明示的に渡していないか確認すること。

### 3.4 Antigravity (agy) のモデル選択とコマンド (2026-06-22)

**原則**: §3.2/§3.3 と同じ「タスクの難易度で選ぶ、固定値にしない」。`agy models` で確認できるのは Gemini 系 (`Gemini 3.5 Flash` の Low/Medium/High、`Gemini 3.1 Pro` の Low/High) に加え **`Claude Sonnet 4.6 (Thinking)` / `Claude Opus 4.6 (Thinking)` / `GPT-OSS 120B (Medium)`** という他社モデルも選択可能。**実機確認**: `--model` 未指定時の既定は **`Gemini 3.5 Flash`**(Pro系ではない)。本プロジェクトが Antigravity に求める役割は「大コンテキストでの整合性確認・記憶装置」([prompts/qa.md](../prompts/qa.md)) であり、既定の Flash がその目的に十分かはタスク次第。

| タスク特性 | 推奨モデル | 理由 |
|---|---|---|
| 単純な状態確認・軽い質問 | 既定の `Gemini 3.5 Flash` のままで可 | 既定で十分、変更コストを払う理由がない |
| Sprint 終端の最終 QA・複数ドキュメント横断の整合性確認 (prompts/qa.md が本来想定する用途) | `--model "Gemini 3.1 Pro (High)"` | 「大コンテキストでの整合性確認」という起用理由に最も合致する |
| 他社モデルでの視点確認が目的の場合 | (`Claude Sonnet 4.6` / `Claude Opus 4.6` が選択可能だが) **本ワークフローの最終QA役では使わない** | Antigravity を起用する理由は Codex (GPT系) / Claude Code (Claude系) とは別系統の視点を確保すること。Antigravity経由でClaudeモデルを選ぶとその独立性の前提が崩れる |

**コマンド一覧 (`agy --help` 実機確認、v1.0.9)**: 主要モードは3種 — 対話 TUI (`agy`)、単発非対話 (`agy -p "<prompt>"` / `--print`、本ワークフローの既定呼び出し)、Async Subagent モード (バックグラウンドでサブエージェントが並行実行し diff を返す、対話 TUI 内のスラッシュコマンド経由)。サブコマンドは `models` (モデル一覧)、`changelog`、`plugin`/`plugins` (import 元に `gemini`/`claude` を指定可能)、`install` (PATH設定)、`update`。`--sandbox` でターミナル制限付き実行、`--add-dir` で追加ワークスペース、`-c/--continue` で直前の会話継続。

**Async Subagent モードは使わない**: [WORKFLOW.md](../WORKFLOW.md) は既に「Antigravity CLI(agy)のサブエージェント・オーケストレーションは課金壁とバグの境界が曖昧で透明性に欠ける」と判定済み。2026-06-22 の調査でもこれを裏付ける外部報告 (Google AI Pro/Ultra ユーザーから「5時間リフレッシュのはずが複数日ロックアウトされる」という2026年6月の複数のクォータ不具合報告) を確認した。本ワークフローでは単発 `agy -p` のみを使い、ネイティブなサブエージェント機能には依存しない。

**クォータ構造 (OAuth個人認証、Google公式発表ベース)**: Google AI Pro/Ultra は **5時間ごとにリフレッシュ**するクォータ、無料ティアは**週次**のクォータ。具体的な契約ティア (Free/Pro/Ultra) は本機からは確認できず未確認。クォータ超過分は別売りの AI credits で追加購入可能。

**重要な発見: 標準 `gemini` CLI の認証が切れている**: 本プロジェクトの「調査・セカンドオピニオン」役 (`gemini -p`) を実機確認したところ、キャッシュ済み認証が失効しブラウザでの再認証確認を要求された (非対話実行不可)。Google公式発表 ([google-gemini/gemini-cli Discussion #27274](https://github.com/google-gemini/gemini-cli/discussions/27274)) によれば2026-06-18に Gemini CLI の Pro/Ultra/無料ティア提供が Antigravity CLI へ統合されており、これが原因の可能性が高い。認証フローはユーザーの明示的許可なく起動していない (ブラウザ確認の時点で安全側に停止)。対応は人間判断 — 詳細は [PROJECT_STATE.md](./PROJECT_STATE.md) 「人間判断待ちの事項」参照。

### 3.5 GitHub Copilot CLI (`copilot`/`gh copilot`) のモデルとコマンド (2026-06-22)

**最優先の注意**: 本ワークフローでは**コーディングタスクに使わない** (上表、月300 premium request制限)。以下はこの制約を変える提案ではなく、許可された用途 (PR作成・Issue分析・リリースノート) を行う際に必要な精度のための知識。

**`gh <subcommand>` と `gh copilot`/`copilot` は別物 (重要)**: `gh pr create` / `gh pr view` / `gh issue list` 等の素の `gh` サブコマンドは GitHub REST API を直接呼ぶだけで LLM を介さず、**300 req/月の対象外**。AI エージェントを起動する `copilot` (`gh copilot` は同じバイナリの薄いランチャー、未インストール時は自動ダウンロード) だけが premium request を消費する。**実機確認 (2026-06-22)**: 最小限のプロンプト1回で `copilot -p "..."` は「Total usage est: 1 Premium request」と表示——ツールを何も使わない単純な質問でも必ず1消費する (検証目的の試し打ちも本番枠を消費するため、本書でも今回1回のみに留めた)。本ワークフローで `gh pr create` 等を使う分には量を気にしなくてよいが、`copilot`/`gh copilot` を呼ぶ判断は1回ごとに月間枠を意識すること。

**モデル (`copilot --help` 実機確認、v1.0.6)**: `--model` で選択可能なのは Claude 7種 (`claude-opus-4.6`/`-fast`/`4.5`, `claude-sonnet-4.6`/`4.5`/`4`, `claude-haiku-4.5`) / Gemini 1種 (`gemini-3-pro-preview`) / GPT 10種 (`gpt-5.4`, `gpt-5.3-codex`, `gpt-5.2-codex`, `gpt-5.2`, `gpt-5.1-codex-max`, `gpt-5.1-codex`, `gpt-5.1`, `gpt-5.1-codex-mini`, `gpt-5-mini`, `gpt-4.1`)。**実機確認: `--model` 未指定時の既定は `gpt-5.4`**。OpenCode の `github-copilot` プロバイダ経由で見えるモデル (`gpt-5.3-codex`/`gpt-5.4`/`gpt-5.4-mini`、§3.1) はこの一部のみで、本体の方がカタログがずっと広い (§3.1 既存の「未検証のまま使うとPR/Issue用の枠を無自覚に消費しうる」という警告は今回新たな証拠なし、変更しない)。

**`--reasoning-effort <level>` (`low`/`medium`/`high`/`xhigh`) が独立フラグとして存在**: Codex の `-c model_reasoning_effort=` (§3.3) と同じ概念だが専用フラグ化されている。同じ理由でタスクに応じて選ぶもので、固定しない。

**AGENTS.md はデフォルトで読む**: `--no-custom-instructions` (「Disable loading of custom instructions from AGENTS.md and related files」) というオプトアウト専用フラグの存在から確認。

**本体は実質 Claude Code/Codex 級のフル機能エージェント**: `--allow-tool`/`--deny-tool`/`--yolo`/`--allow-all`/`--autopilot`/MCP連携 (`--add-github-mcp-tool` 等)/カスタムエージェント (`--agent`)/プラグイン (`--plugin-dir`) まで揃っている。**300 req/月の制限こそが「コーディングに使わない」の唯一の理由であり、能力不足が理由ではない** — 量さえ許せば実装作業も技術的には可能だが、本ワークフローでは枠を使い切るリスクが高すぎるため踏襲しない。

**安全な許可パターンの例 (将来 `copilot` でGit操作を許可する場合)**: `--allow-tool='shell(git:*)' --deny-tool='shell(git push)'` のように、拒否ルールが許可ルールより常に優先されるため「git系は許可するが push だけ拒否」のような精密な制御が可能。`--yolo`/`--allow-all` は使わない。

### 3.6 agmsg によるクロスエージェント連携 (2026-06-22 導入・実通信検証済み)

**位置づけ**: [WORKFLOW.md §7](../WORKFLOW.md) が「複数ハーネスを束ねる安定した既製オーケストレーション製品は存在しない…当面は手動運用、または痛点一箇所の軽量スクリプト化に留める」とした、その「軽量スクリプト」に該当する道具。[agmsg](https://github.com/fujibee/agmsg) は **bash + sqlite3 のみ**で動くクロスエージェント・メッセージング (daemon/MCP サーバ無し)。Claude Code / Codex / Antigravity / OpenCode / Copilot CLI が共有 SQLite ファイル経由で相互にメッセージを送受信する。重量級フレームワークではないため §7 の「軽量に留める」方針に反しない。導入スコープは人間 (プロダクトオーナー) の明示指示による **「文書統合」** (利用可能な選択肢として整備するに留め、新規自動化・役割変更はしない)。

**重要 — これは何で、何でないか**:
- **本プロジェクトの依存ではない**。ユーザーのマシン全体 (`~/.agents/skills/agmsg/`) にインストールされた**オーケストレーション用ツール**であり、`pyproject.toml` にも Python パッケージにも一切触れない。bash+sqlite で製品コードの外側で完結するため、**ADR-0001 (Python 単一・Go/Node へ戻さない) に抵触しない** (CLI エージェント群そのものと同じ「外部ツール」カテゴリ)。
- **文書ハンドオフ ([WORKFLOW §0](../WORKFLOW.md)) を置き換えない**。REVIEW_REPORT.md / QA_REPORT.md / PROJECT_STATE.md は引き続き**真実の源**。agmsg が運ぶのは生の成果物ではなく**ポインタ・サマリー・通知** (例「レビュー準備できた、REVIEW_REPORT.md 見て」「commit SHA / Issue 番号はこれ」)。agmsg 自身の設計思想 (「成果物はディスクに書き一行のポインタを送る」) がこの原則と一致する。
- **§3 既存の一発委任の*代替*ではなく*補完***。§3 表の `codex exec` / `opencode run` / `agy -p` は**オーケストレーターからの一方向・使い捨て委任** (結果を回収して終わり)。agmsg は**永続化された双方向ピア連携** (履歴が SQLite に残り、セッションを跨いで replay 可能) が本質的に要る場面に限って使う。
- **Task ラッパーエージェントの自己代行バグの修正ではない** (別軸の話)。`Task(subagent_type="codex-agent")` 等の haiku ラッパー経由委任には、外部 CLI を実際に呼ばず自分の Bash/Read で代行し中身の無い「完了しました」を返す不具合がある (2026-06-22、4 エージェント定義へ「委任の実効性」節を追記して対処済み)。**本書 §3 の直接シェル呼び出し (`codex exec` 等を Bash tool で実行) が信頼できる既定経路であり、委任を Task ラッパー経由へ切り替えないこと**。agmsg はこれとはさらに別の、ピア間連携用の経路。

**karyu チーム (2026-06-22 実機検証済み)**: 本プロジェクト用チーム `karyu` に 5 identity が登録済み — `claude` (claude-code) / `codex` (codex) / `antigravity` (antigravity) / `opencode` (opencode) / `copilot` (copilot)、全て本リポジトリパス紐付け。`claude` から 4 エージェント全てへ送信 → 全員から返信を実機確認済み (`history.sh karyu` に永続記録)。

**呼び出し方 (スクリプト直接、検証済み)**:
```bash
S=~/.agents/skills/agmsg/scripts
$S/team.sh karyu                       # メンバー確認
$S/send.sh karyu <from> <to> "<msg>"   # 送信 (引数は厳密に4つ、msg はクォート必須)
$S/inbox.sh karyu <agent>              # 受信 (閲覧した時点で既読化される)
$S/history.sh karyu                    # 全履歴 (既読/未読問わず閲覧、未読を消費しない)
```

**運用上の落とし穴 (実機で踏んだもの)**:
- **共有 SKILL.md は単一タイプ**: `~/.agents/skills/agmsg/SKILL.md` は導入時 `--agent-type` 未指定だったため **codex 向け**になっている。Antigravity / Gemini はこの共有ファイルを読む設計のため、SKILL.md 経由で自動発見させると `whoami.sh ... codex` を実行して**自分を codex と誤認**する。`agy` へ委任する際は inbox.sh/send.sh の**スクリプトパスと identity を明示**して渡すこと (Copilot/OpenCode は専用 SKILL.md を持つためこの問題は無い)。
- **Copilot の `--allow-tool` はワイルドカード必須**: `shell(bash)` (コロン無し) は「引数ゼロの bash」しか許可せず、スクリプト実行は全て拒否される。`shell(bash:*)` のように `:*` を付ける (§3.5 の `shell(git:*)` と同じ構文。`copilot --help` の例が根拠)。
- **`AGMSG_STORAGE_PATH` は DB のみ隔離**: チーム設定 (`teams/<name>/config.json`) は常に本番ディレクトリに書かれる。サンドボックステストでもチーム設定の痕跡は手動掃除 (`reset.sh` + `rm -rf teams/<name>`) が要る。
- **Codex サンドボックス**: `install.sh` が `~/.codex/config.toml` の `writable_roots` に agmsg の `db/`/`teams/`/`run/` を追記済み (`codex exec --sandbox workspace-write` から agmsg 書き込みを可能にするため)。導入時に元ファイルは `.bak` へバックアップされている。

**使いどころの判断**: 単発の委任 (レビュー1件・実装1タスク) は §3 表の直接呼び出しで十分で、agmsg を噛ませる必要はない。agmsg を使うのは ①セッションを跨いで連携履歴を残したい ②複数エージェントが同じ「部屋」で非同期にやり取りする ③オーケストレーター不在でもピア同士が通知し合う、といった**永続・双方向が本質的に要る**場面に限る。現状の本プロジェクトは人間ゲート待ち (§2 決定木) が多く単発委任で足りるため、agmsg は**「整備済みの選択肢」**という位置づけ (常用を強制しない)。

### 3.7 研究反映済みの agentic workflow guardrails (2026-06-29)

委任前に必ず context packet を作る。最低限の項目:

- objective: 何を達成するか
- in-scope / out-of-scope: 触ってよい範囲、触ってはいけない範囲
- authority docs: `AGENTS.md`、`PROJECT_STATE.md`、該当 DESIGN / IMPLEMENTATION_PLAN / ADR
- writable files: 書き込み許可ファイル。指定がなければ read-only
- required evidence: 必要なテスト、diff、line reference、外部URL検証
- stop conditions: 人間ゲート、環境失敗2回、同一レビューFAIL2回など

並列化のルール:

- 並列可: repo探索、一次情報調査、独立レビュー、QA、互いに disjoint なファイルの実装。
- 原則不可: 同じファイル群への同時編集、`PROJECT_STATE.md` の同時更新、同じPRへの複数ライターの直接push。
- 必要時のみ: worktree で隔離し、統合はオーケストレーターが diff を読んで行う。

採用前チェック:

- 外部AIやagmsgの発言は権威ではない。採用するには repo 内差分、実行ログ、一次情報、PR review のいずれかに接続する。
- 完了判定は MAST 型失敗を見る: specification gap / inter-agent misalignment / verification・termination failure が残っていないか。
- 最新モデル・価格・CLI仕様に依存する判断は、実行時に `--help` / 公式docs / smoke test で再確認する。

---

## 4. 日次運用ループ (本番配信の心臓部)

平日朝、以下を順に実行する (要件 §13.2)。`collect` / `draft` は fail-open — 1 つのソース失敗や Discord 投稿失敗で全体を止めない。一方 `produce` は配信品質ゲートであり、TTS 文欠落・無音・LUFS/true peak 失敗時は Discord へ失敗通知を試みたうえで非 0 終了し、launchd/外部監視へ失敗を伝える。

```bash
cd "$(git rev-parse --show-toplevel)"        # リポジトリルートへ移動 (環境非依存)
docker compose up -d rsshub                   # 掘金など RSSHub 経由ソース用 (unhealthy 表示でも実応答 200 なら可)
uv run python -m karyu_tech_news collect --post          # 収集 → SQLite → Discord サマリー
uv run python -m karyu_tech_news draft --variant A --post # LLM 編集判定 → 3-5 本選定 → 台本 → Discord 台本投稿
uv run python -m karyu_tech_news produce --engine irodori-tts-v3 --post # 音声完パケ → Discord mp3 (人間Go済みの場合のみ。品質ゲート失敗は非0)
# 任意: 配信後の観察・比較用。日次配信ループの成否判定には含めない。
uv run python -m karyu_tech_news evaluate                 # A/B/C 定量サマリー
```

記録すべき観察項目 (TEST_LOG.md へ):
- 収集: 成功ソース数 / 新着件数 / fail-open 発火の有無
- 編集: 候補数 → 採用数 / llm 成功・retry・fallback 回数 / editor JSON 安定性
- コスト: トークン消費 (要件 §9.7 月 1,500-3,000 円の範囲内か)
- 配信: Discord HTTP ステータス (204 期待)
- 音声: mp3 秒数 / LUFS / true peak / `max_silence` / skipped 文数 / produce fail-fast の有無
- 品質: 「配信する価値」観点の所感 / [editorial-policy.md](./editorial-policy.md) 違反の有無

---

## 5. 品質ゲート (完了宣言前に必ず・記憶で代用しない)

```bash
uv run pytest        # 全テスト緑 (2026-06-26時点: 438。件数は記憶でなくfresh出力を信じる)
uv run ruff check .  # lint クリーン
uv run mypy src tests # 型 strict クリーン (2026-06-26時点: 70 files)
git diff --check     # whitespace / conflict marker 確認
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
