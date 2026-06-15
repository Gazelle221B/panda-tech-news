# プロジェクト状態

> 最終更新: 2026-06-14 / 更新者: Claude Code (Sprint 1B 完全終了・マージ済み → Sprint 2 着手 T23)
> 本ファイルは全エージェントが随時更新する。**Antigravity の内部記憶ではなくここを真の記憶とする** (WORKFLOW §13)。

## 現在のフェーズ

**Sprint 1B 完全終了 (マージ済み) → Sprint 2 (音声化) 着手中** — Sprint 1B は PR #10/#11/#12 すべて main にマージ済み (main `16d03ed`)。T22 3日観察で捕捉した 2 defects (writer 300字超過 / canonical URL 横断 dedup) は修正・Codex PASS・QA PASS を経てマージ済み。**writer 修正後の台本品質を確認**: LLM 生成トピックは Hook/Insight/Action・カナ化+原語併記・日本リスナー視点の洞察を満たし「音声化する価値」水準 (template fallback も健全)。**Sprint 1B 全 DoD 達成**。
**Sprint 2 着手 (2026-06-14)**: マージ + 人間「進めてください」を Go と解釈。**T23 (TTSEngine Protocol + 設定駆動エンジン選択 FR-090) を実装** (`tts/engine.py` + MockTTSEngine、エンジン非依存・モック駆動、pytest 257 緑)。Sprint 2 の非ブロッカー部 (T23/T25/T26/T27/T28) はモック駆動で先行実装可能 (1B の T13 方式)。
**残 (人間ブロッカー)**: ① **T24 実 Irodori 接続の実行環境** (GPU/クラウド/課金 or Kokoro fallback) ② **HAL 声リファレンス試聴確定** (ADR-0006) ③ T29 BGM/ジングル素材。詳細は [IMPLEMENTATION_PLAN-2.md §6](./IMPLEMENTATION_PLAN-2.md)。

| ステップ | 状態 |
|---|---|
| 要件定義 v1.0 | ✅ 確定 |
| Source Selection Spike v0.1 | ✅ ドラフト確定 (URL検証は実装前夜に実施) |
| マルチエージェント WORKFLOW v1.0.1 | ✅ 確定 |
| 全体構想 (architecture-podcast-station) | ✅ 本日文書化 (meeting全読より) |
| 設計継承メモ (design-inheritance) | ✅ 本日文書化 (tc-newsflowコード全読より) |
| ロードマップ | ✅ 本日確定 |
| DESIGN.md / IMPLEMENTATION_PLAN.md | ✅ 確定 (Sprint 1A) |
| ADR-0001〜0006 | ✅ 確定 |
| 番組仕様 (hal-persona / show-format / editorial-policy) | ✅ 確定 (md + config yaml 両方) |
| `config/` (sources / llm_profiles / hal_persona / show_format) | ✅ 本日作成 |
| ブートストラップ (.gitignore / .env.example / docker-compose / scripts) | ✅ 本日作成 |
| Python モジュール名 | ✅ 確定: `karyu_tech_news` (2026-05-30, 全docsのCLI例に一致) |
| 初期ソース URL ローカル検証 | ✅ 完了 (2026-05-29)。有効9本(ADOPT5+監視4)/保留2本。meeting3.md・Spike §7 |
| `config/sources.yaml` の enabled 確定 | ✅ 確定 (11本中9有効、jiqizhixin-rss/huxiu-rss は disabled 保持) |
| `src/karyu_tech_news/` Ticket #1 + #2先行 | ✅ 完了。CLI(version/validate-sources/info)+Pydanticスキーマ。pytest 24 pass / ruff・mypy(strict) clean |
| Ticket #3 (RSS/RSSHub フェッチャ, fail-open) | ✅ 完了 (2026-05-31)。collect/normalize.py + fetcher.py。pytest 48 pass / ruff・mypy(strict) clean |
| Ticket #4 (SQLite スキーマ・永続化) | ✅ Antigravity QA PASS (2026-06-01)。PRAGMA foreign_keys=ON 有効化、total_sources 不一致検出、idx_items_published DESC 修正、info Sprint 表示更新。pytest 60 pass / ruff・mypy(strict) clean |
| Ticket #5 (seen 管理 / dedupe) | ✅ Antigravity QA PASS (2026-06-01)。`UNIQUE(source_id, item_key)` での dedupe 実装完了。pytest 65 pass / ruff・mypy(strict) clean |
| Ticket #6 (source_health 更新) | ✅ Antigravity QA PASS (2026-06-01)。FR-050/051/052に適合し正常動作を確認。pytest 73 pass / ruff・mypy(strict) clean |
| Ticket #7 (collect runner: fail-open 統合) | ✅ Antigravity QA PASS (2026-06-01)。fail-open 設計および集計整合性の確実な動作を検証済。pytest 81 pass / ruff・mypy(strict) clean |
| Ticket #8 (Discord Webhook サマリー投稿) | ✅ Antigravity QA PASS (2026-06-01)。run 境界内の集計整合性、Webhook 送信時の fail-open 担保を確認。pytest 88 pass / ruff・mypy(strict) clean |
| Ticket #9 (CLI統合: `collect` コマンド) | ✅ Antigravity QA PASS (2026-06-02)。dry-run、実実行、重複排除、不正引数処理を実CLIで確認。pytest 104 pass / ruff・mypy(strict) clean |
| Ticket #11 (T11) 3日連続稼働観察 | ✅ 完了 (2026-06-04)。Day1-3 全 9/9 成功、Discord 実配信 (HTTP 204)、fail-open 健全、dedup 実DB実証。**Sprint 1A 完全終了** |
| Ticket T12 (LLM profile ローダ + provider 抽象) | ✅ 実装完了 (2026-06-10)。`llm/profile.py` + `llm/client.py`。A/B/C 切替を設定だけで解決、API キーは env 名参照のみ。pytest 134 pass / ruff・mypy(strict) clean。Codex レビュー待ち |
| Ticket T14 (候補抽出 + ローカル事前スコア) | ✅ 実装完了 (2026-06-10)。`edit/prescore.py`。中華圏キーワード辞書 + Tier ボーナス、上限40件。実DBスモークで候補40件抽出を確認 |
| Ticket T15 (LLM 編集判定) | ✅ 実装完了 (2026-06-10)。`edit/judge.py`。temp=0 + JSON モード、頑健 JSON 抽出、corroboration は canonical_url_hash で決定的に集計 |
| Ticket T16 (多様性キャップ選定 + アーク配置) | ✅ 実装完了 (2026-06-10)。`edit/select.py` + `edit/arc.py`。Tier3/4 独立2ソースゲート + 4パス充填 + 三幕構成。全て決定的コード |
| Ticket T17 (Markdown 台本生成) | ✅ 実装完了 (2026-06-11)。`script/generate.py`。Hook/Insight/Action 契約 + 検証 (300字/URL/禁止表現/噂明示) + エピソード組み立て |
| Ticket T18 (fallback 二重防御) | ✅ 実装完了 (2026-06-11)。`script/fallback.py`。違反フィードバック付き再生成 → テンプレ乱択4パターン |
| Ticket T19 (1B 新テーブル + 永続化) | ✅ 実装完了 (2026-06-11)。topic_candidates / episode_drafts / llm_runs / script_versions + repo 4関数 |
| Ticket T20 (A/B/C 比較ログ集計) | ✅ 実装完了 (2026-06-11)。`edit/abtest.py`。採用率/修正回数/コスト/JSON安定性の variant 別集計 |
| Ticket T21 (CLI draft/evaluate + Discord 台本投稿) | ✅ 実装完了 (2026-06-11)。`script/runner.py` (統合, editor 崩壊時 neutral fallback) + `deliver/discord.py` post_markdown (2000字チャンク) + CLI 2コマンド。実DB `draft --dry-run` スモーク済み |
| Ticket T13 (MiMo/DeepSeek 実接続 smoke) | ✅ **完了 (2026-06-12)**。人間が API 契約・キー設定 → 両系統疎通。mimo 実 endpoint `https://api.xiaomimimo.com/v1` / model `mimo-v2.5-pro` 確定 (config 修正)。deepseek-chat は実体 deepseek-v4-flash |
| Ticket T22 (3日間の台本品質観察) | ✅ **完了 (2026-06-14、3日完走)**。Day1: 候補40→採用5 (llm=5/t=0)。Day2: 候補30→採用5 (llm=1/**t=4**)・7/9ソース・fail-open実証。Day3: 候補40→採用5 (llm=0/**t=5**)・9/9ソース。**結論: editor(MiMo) JSON 100% 安定継続、writer(DeepSeek) 300字超過で template 率 0→80→100% 悪化 (根因 DB 確定)、横断 dedup 欠落 (Day3 発見)**。インフラ DoD 全達成・コンテンツ品質は 2 defects 修正待ち |
| **Sprint 1B 全 DoD** | ✅ **完全終了 (2026-06-14、PR #10/#11/#12 マージ済 main `16d03ed`)**。2 defects 修正後の台本は「音声化する価値」水準を確認 |
| Ticket T23 (TTSEngine Protocol + 設定駆動エンジン選択) | ✅ 実装完了 (2026-06-14)。`tts/engine.py` — Protocol (synthesize/voices/name/capabilities) + データモデル + MockTTSEngine + `select_engine` (FR-090)。エンジン非依存・モック駆動。pytest 257 緑 / ruff / mypy strict clean。Codex レビュー待ち |

## 作業中ブランチ

`agent/T22-impl` (最新 main `b76f6c4` から分岐。`agent/T12-impl` は PR #10 squash マージ済みのため規約 §8.2 に従い切り直し)

## 直近の設計判断

- **言語**: Python 3.11+ 単一 (ADR-0001)
- **Sprint分割**: 収集と LLM を別スプリント (ADR-0002)
- **Discord**: Webhook 起点、Bot は将来 (ADR-0003)
- **RSSHub**: セルフホスト (ADR-0004)
- **Tier4 噂**: 原則不採用、独立2ソースかつ「噂」明示で例外

## 未解決リスク

| リスク | 現状 |
|---|---|
| `https://www.jiqizhixin.com/rss` がデータサービスへリダイレクト | `enabled: false` で保持、代替に量子位 |
| `https://www.pingwest.com/feed` が404 | 初期10本から除外、虎嗅で代替 |
| GitHub Atom URL のローカル feedparser 動作 | 未検証 |
| RSSHub セルフホスト Docker Desktop での起動性 | 未検証 |
| Hugging Face Daily Papers の公式 RSS 不在 | 初期スコープ外、1B以降 |

## Codex レビューの直近結果

2026-06-12: Sprint 2 実装計画ドラフト (IMPLEMENTATION_PLAN-2.md) 独立レビュー **PASS** (Critical 0 / High 0 / Medium 1 / Low 1)。Medium (ブロッカー粒度の混在) と Low (クラウド GPU/外部ストレージ選択時の費用・認証判断の明示) は同日中に計画へ反映済み。証跡は `docs/REVIEW_REPORT.md` 末尾。

2026-06-03: ドキュメント同期 + CLIテスト分離修正レビュー PASS。Critical/High/Medium/Low 指摘なし。実 `.env` webhook 存在下でも pytest 104 pass、ruff/mypy strict clean、秘密保護を確認。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-02: T10 (Ticket #9 CLI統合: `collect` コマンド) 再々レビュー PASS。Critical/High/Medium/Low 指摘なし。`--source` 複数指定時の未知/disabled ID検証、DB更新統合テスト、Webhook fail-open を確認。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-02: T10 (Ticket #9 CLI統合: `collect` コマンド) 再レビュー FAIL。High 1件: 複数 `--source` 指定時に未知/disabled IDを黙って無視する。Medium 1件: dry-run の `source_health` 未書き込み確認不足。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-02: T10 (Ticket #9 CLI統合: `collect` コマンド) 独立レビュー FAIL。High 1件: `collect --source <id>` 未実装。Medium 1件: T10受け入れ条件のDB状態検証不足。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-01: T9 (Ticket #8 Discord Webhook サマリー投稿) 再レビュー PASS。Critical/High/Medium/Low 指摘なし。run 境界内の Tier/カテゴリ集計と Webhook fail-open を確認。証跡は `docs/REVIEW_REPORT.md` に追記済み。

## Antigravity QA の直近結果

2026-06-12: Sprint 2 計画 + 決定支援文書群の整合性 QA **PASS** を QA_REPORT に記録。相互参照・スコープ整合・秘密情報・AGENTS 300 行制限すべて合格。QA がドリフト 2 種を検出・修正 (AGENTS/README の古いテスト件数 235→242、README ステータス節の実態同期)。

2026-06-02: Ticket #9 (T10) `collect` CLI 結合の QA 確認完了。実CLIを用いた完走、DBへのアイテム新規追加（71件）、同一バッチでの重複排除、不正な `--source` 指定に対する exit 1 終了など、要件 §15.1 および実装計画の DoD をすべて満たしていることを確認し QA PASS。証跡は `docs/QA_REPORT.md` に追記済み。
2026-06-01: Ticket #8 (T9) Discord Webhook サマリー投稿の QA 確認完了。要件 §14.1 に基づくサマリーフォーマットの正確性、JSTタイムゾーン変換、収集実行時間の正確性、そして Webhook 送信失敗時の fail-open 設計（FR-071）を確認し QA PASS。証跡は `docs/QA_REPORT.md` に追記済み。
2026-06-01: Ticket #7 (T8) collect runner fail-open 統合の QA 確認完了。1ソースのDBエラーが後続処理に影響しないフェイルオープン設計、および `collect_runs` と `source_health` の正確な集計と状態遷移を確認し QA PASS。証跡は `docs/QA_REPORT.md` に追記済み。

2026-06-01: Ticket #6 (T7) source_health 更新の QA 確認完了。FR-050/051/052に適合し、正常な状態遷移とタイムゾーン対応を確認し QA PASS。証跡は `docs/QA_REPORT.md` に追記済み。
2026-06-01: Ticket #5 (T6) seen 管理 / dedupe の QA 確認完了。`UNIQUE(source_id, item_key)` での重複排除、同一バッチ内の重複防止などを確認し QA PASS。証跡は `docs/QA_REPORT.md` に追記済み。
2026-06-01: Ticket #4 (T5) SQLite スキーマ・永続化の QA 確認完了。`PRAGMA foreign_keys=ON` 有効化による参照整合性、重複排除（dedupe）、収集実行記録の整合性、およびすべての設計整合性を検証済。証跡は `docs/QA_REPORT.md` に追記済み。

1. ~~Ticket #9 (T10) `collect` CLI 結合~~ ✅ 実装完了 (2026-06-02)。`main.py` および `cli.py` に `collect` コマンドを統合。
2. ~~T10 Codex レビュー~~ ✅ PASS (2026-06-02)。High 指摘対応（`--source` 不正IDの厳密チェック）完了。
3. ~~Antigravity QA~~ ✅ PASS (2026-06-02)。T10 `collect` CLI 結合の最終 QA完了。Sprint 1A 実装のすべての完了条件を満たす。
4. ~~人間承認 & Merge~~ ✅ T1〜T10 は main にマージ済 (PR #1〜#7、最新 `df4e931`)。
5. ~~Ticket #11 (T11) 3日連続稼働観察~~ ✅ **完了 (2026-06-04)**: Day1 (4新着) / Day2 (58新着, HTTP204) / Day3 (1新着, HTTP204)。全日 9/9 成功・fail-open 健全。Day2/Day3 にて Discord 配信確認。**Sprint 1A 完全終了**。
6. doc-sync + テスト分離修正 (現ブランチ `agent/T11-impl`) は Codex レビュー PASS 済 (2026-06-03) → **人間承認でマージ可** (テストコード変更を含むため PR 経由推奨)。
7. **次フェーズ: Sprint 1B (LLM編集・台本生成) 解禁** — LLM profile 定義 / MiMo・DeepSeek 接続確認 / Tier重みスコアリング / 3-5本選定 / Markdown台本 / A/B/C比較ログ ([roadmap.md](./roadmap.md) Sprint 1B 節)。

## 人間判断待ちの事項

- ~~Python モジュール名~~ → **確定・実装済**: モジュール `karyu_tech_news`、配布名 `panda-tech-news` 維持、ビルドは hatchling (`packages = ["src/karyu_tech_news"]`)、console script `karyu`。
- ~~ソース URL 実取得検証~~ → ✅ 完了 (2026-05-29)。
- ~~コミット/ブランチ運用: Ticket #1+#2先行 を `agent/<task>` ブランチに乗せるか直接コミットか。~~ → 初期実装として直接 `main` へコミット済。以降は `agent/<task>` 運用を厳格に適用。
- 初期9本に Game/Subculture 系を1本予備で入れるか (Spike §3 B案)。**→ 決定支援資料作成済み (2026-06-12): [proposals/game-subculture-source-v0.1.md](./proposals/game-subculture-source-v0.1.md)。IndieNova を実検証 OK (HTTP 200) の第一候補として推薦、採否は人間**。
- LLM 役割 A/B/C のどれを初期既定にするか (ADR-0005、実測後確定)。
- **【Sprint 1B 着手前ブロッカー】実 LLM model ID / endpoint の確定** (要件 §16): `deepseek-chat` / `mimo-v2.5-pro` はプレースホルダ。MiMo 海外課金が困難なら OpenRouter フォールバック。API 契約・課金は人間判断 (WORKFLOW §4 区分 D)。詳細は [IMPLEMENTATION_PLAN-1B.md](./IMPLEMENTATION_PLAN-1B.md) §6。
- HAL の声リファレンス確定タイミング (Sprint 2 までは保留可)。
- **【Sprint 2 Go 判断パッケージ】** T22 完了 + Sprint 1B 完了 PR マージ後に人間が判断: ① Sprint 2 着手の Go/No-Go ② Irodori-TTS-Server 実行環境 (macOS 可否 / 別マシン / クラウド GPU) ③ HAL 声リファレンス試聴 ④ BGM/ジングル素材とライセンス ⑤ mp3 配信方法 (Discord 添付 25MB vs R2/S3 リンク)。詳細は [IMPLEMENTATION_PLAN-2.md](./IMPLEMENTATION_PLAN-2.md) §6。
- 番組オープニング/エンディング挨拶フレーズの確定 (Sprint 1B 以降で可)。**→ 候補 3 案作成済み (2026-06-12): [proposals/greeting-phrases-v0.1.md](./proposals/greeting-phrases-v0.1.md)。音読/試聴して選定は人間**。
- **【環境・区分 D】OpenCode CLI が全モデルで UnknownError (2026-06-12)**: `opencode run` が go/qwen3.7-max・go/qwen3.7-plus・zen 無料 (deepseek-v4-flash-free) の 3 連続で「Unexpected server error」。モデル非依存のためクライアント/サーバー側の問題 — `opencode` の再ログイン・更新等の復旧確認は人間。今回の起草はインライン代替で影響なし。
- (E2E 検証 2026-06-11 で発見) タイトルが短い GitHub リリース (例「v1.0.0」) は台本見出しにソース名を併記すべきか — T22 観察で要否判断。
- **(T22 Day 2 で発見・Day 2 に DB 診断で真因確定) writer (DeepSeek) の台本生成成否が日で振れる** (Day1=0/5→Day2=4/5 が template fallback)。editor (MiMo) は 100% 安定なので問題は writer 側。
  - **確定した真因** (llm_runs/script_versions の実データ解析): writer LLM 呼び出し自体は**成功** (`ok=1`、API エラー無し)。template 落ちした 4 本はいずれも **`attempts=3` (再生成上限) まで `validate_topic_script` の「300 字超過 (空白除く)」検証に通らず** fallback。成功 1 本は空白除き ≤300 字で通過。**= DeepSeek が `TOPIC_CHAR_LIMIT=300` を超える長さで書き、フィードバック再生成 3 回でも 300 字未満に収められないのが真因**。日次変動は題材による DeepSeek の冗長度の差。
  - **人間判断の選択肢** (post-T22): ① writer プロンプトに明示的な字数バジェット (例「空白除き 250 字以内」と上限より厳しめ) を入れる ← **最有力・低リスク・コスト不変** ② 再生成フィードバックに現在の文字数と目標差分を入れる ③ `TOPIC_CHAR_LIMIT` を緩める (ただし読み上げ尺 §9.1 と TTS 時間に影響) ④ writer を DeepSeek 以外へ差し替え (llm_profiles.yaml variant、コスト再評価)。
  - **今は直さない**: prompt/閾値を T22 観察期間中に変えると Day1/2/3 比較が汚染される (§12.4)。**T22 完了後**に上記から人間が選択 → 通常の実装→Codex→QA サイクルで反映。**fallback が機能し番組は毎日成立しているため緊急度は中**。
- **(運用) ローカルスケジュールタスクの信頼性**: T22 Day 2 の自動実行 (06-13 07:47) が発火したが記録・コミットを残さず途中失敗した。Day 3 (06-14) も同様に失敗する可能性があるため、**Day 3 朝に TEST_LOG へ Day 3 記録が無ければ [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) §4 を手動実行**して補完する (本 Day 2 と同手順)。

## 本日 (2026-05-30) 追加した成果物

meeting.md / meeting2.md / tik-choco コードdump の全読に基づき作成:
- 全体構想: `docs/architecture-podcast-station.md`
- 設計継承: `docs/design-inheritance-tc-newsflow.md`
- ロードマップ: `docs/roadmap.md`
- ADR-0005 (LLM役割A/B), ADR-0006 (TTS抽象化)
- config: `sources.yaml` / `llm_profiles.yaml` / `hal_persona.yaml` / `show_format.yaml`
- bootstrap: `.gitignore` / `.env.example` / `docker-compose.yml` / `scripts/spike_curl_check.sh`

## 改訂履歴

| 日付 | 更新者 | 内容 |
|---|---|---|
| 2026-05-30 | Claude Code | 初版作成、DESIGN/IMPLEMENTATION_PLAN 確定後の状態スナップショット |
| 2026-05-30 | Claude Code | meeting3.md 反映: ソース検証完了(有効9本)、Ticket #1 + #2先行 実装・検証グリーン(pytest 24 / ruff / mypy strict) |
| 2026-05-30 | Codex | T1 + T3(schema) 独立レビュー PASS を `docs/REVIEW_REPORT.md` に記録。次アクションは Ticket #3 |
| 2026-05-30 | Antigravity | AGENTS.md / CLAUDE.md 追加 (2026-05-30) |
| 2026-05-30 | Claude Code | AGENTS.md/CLAUDE.md + architecture.md / domain/collection.md / styleguide.md / README.md 追加。T1+T2 実装ベースに知識ベース文書を整備 |
| 2026-05-31 | OpenCode | Ticket #3 (T4) RSS/RSSHub フェッチャ実装完了。collect/normalize.py + fetcher.py + テスト 24件追加。pytest 48 pass / ruff・mypy(strict) clean |
| 2026-05-31 | Codex | T4 RSS/RSSHub フェッチャ独立レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium 指摘なし |
| 2026-05-31 | Antigravity | PR #1 の Codex/Copilot 指摘コメントへの対応・コード及びドキュメント修正完了 |
| 2026-05-31 | OpenCode | Ticket #4 (T5) SQLite スキーマ・永続化層実装完了。store/schema.py + repo.py + init-db CLI + テスト 9件追加。pytest 57 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T5 SQLite スキーマ + 永続化層の独立レビュー FAIL を `docs/REVIEW_REPORT.md` に記録。High 1件 |
| 2026-06-01 | OpenCode | T5 Codex レビュー指摘対応完了。PRAGMA foreign_keys=ON 有効化、total_sources 不一致検出、idx_items_published DESC 修正、info Sprint 表示更新、テスト 3件追加。pytest 60 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T5 SQLite スキーマ + 永続化層の再レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし |
| 2026-06-01 | Antigravity | Ticket #4 (T5) SQLite スキーマ・永続化層の QA 完了。すべての設計・受け入れ条件の適合を確認し QA PASS |
| 2026-06-01 | OpenCode | Ticket #5 (T6) seen 管理 / dedupe 完了。tests/test_dedupe.py に 5 テスト追加。pytest 65 pass / ruff・mypy(strict) clean |
| 2026-06-01 | OpenCode | Ticket #6 (T7) source_health 更新完了。tests/test_health.py に 8 テスト追加。pytest 73 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T6 seen 管理 / dedupe の独立レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし |
| 2026-06-01 | Codex | T7 source_health 更新の独立レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし |
| 2026-06-01 | Antigravity | Ticket #6 (T7) source_health 更新の QA 完了。すべての設計・受け入れ条件の適合を確認し QA PASS |
| 2026-06-01 | OpenCode | Ticket #7 (T8) collect runner 統合完了。collect/runner.py 実装、fail-open 統合。tests/test_runner_fail_open.py に 6 テスト追加。pytest 79 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T8 collect runner 統合の独立レビュー FAIL を `docs/REVIEW_REPORT.md` に記録。High 1件: 実 DB エラー時の rollback 不足で fail-open が破れる |
| 2026-06-01 | OpenCode | T8 Codex レビュー指摘対応完了。session.rollback() 追加、IntegrityError 回帰テスト追加。pytest 80 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T8 collect runner 統合の再レビュー FAIL を `docs/REVIEW_REPORT.md` に記録。High 1件: 実 DB エラー時に未保存 item が `collect_runs.new_items` に過大計上される |
| 2026-06-01 | OpenCode | T8 Codex 再レビュー指摘対応完了。total_new_items加算をcommit成功後に移動、commit失敗時の回帰テスト追加。pytest 81 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T8 collect runner 統合の再々レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし |
| 2026-06-01 | Antigravity | Ticket #7 (T8) collect runner fail-open 統合の QA 完了。すべての設計・受け入れ条件の適合を確認し QA PASS |
| 2026-06-01 | OpenCode | Ticket #8 (T9) Discord Webhook サマリー投稿完了。deliver/discord.py 実装、format_summary + post_summary。tests/test_discord.py に 6 テスト追加。pytest 87 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T9 Discord Webhook サマリー投稿の独立レビュー FAIL を `docs/REVIEW_REPORT.md` に記録。High 1件: run 終了後の item が Tier/カテゴリ集計に混ざる |
| 2026-06-01 | OpenCode | T9 Codex レビュー指摘対応完了。`format_summary()` の item 集計条件に `Item.fetched_at <= run.finished_at` を追加、回帰テスト追加。pytest 88 pass / ruff・mypy(strict) clean |
| 2026-06-01 | Codex | T9 Discord Webhook サマリー投稿の再レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし |
| 2026-06-01 | Antigravity | Ticket #8 (T9) Discord Webhook サマリー投稿の QA 完了。すべての設計・受け入れ条件の適合を確認し QA PASS |
| 2026-06-01 | OpenCode | Ticket #9 (T10) CLI統合完了。main.py に collect コマンド追加、--post/--dry-run オプション実装。tests/test_cli_integration.py に 9 テスト追加。pytest 97 pass / ruff・mypy(strict) clean |
| 2026-06-02 | Codex | T10 CLI統合の独立レビュー FAIL を `docs/REVIEW_REPORT.md` に記録。High 1件: `collect --source <id>` 未実装。Medium 1件: T10受け入れ条件のDB状態検証不足 |
| 2026-06-02 | OpenCode | T10 Codex レビュー指摘対応完了。`--source` オプション追加、DB状態検証テスト追加。pytest 101 pass / ruff・mypy(strict) clean |
| 2026-06-02 | Codex | T10 CLI統合の再レビュー FAIL を `docs/REVIEW_REPORT.md` に記録。High 1件: 複数 `--source` 指定時に未知/disabled IDを黙って無視する |
| 2026-06-02 | OpenCode | T10 Codex 再レビュー指摘対応完了。複数 `--source` 指定時の未知/disabled ID検証を追加。pytest 104 pass / ruff・mypy(strict) clean |
| 2026-06-02 | Codex | T10 CLI統合の再々レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし。次工程は Antigravity QA |
| 2026-06-02 | Antigravity | Ticket #9 (T10) CLI統合の QA 完了。実CLIを用いた完走、重複排除、不正引数処理等の正常動作を確認し QA PASS |
| 2026-06-02 | Claude Code | T11 Day 1 実走: collect 9/9成功・4新着、dedup実証(他8本0new)、zhipu-glm 301自動追従、Discordサマリー §14.1 プレビュー確認。fresh pytest 104/ruff/mypy strict 緑。TEST_LOG 稼働記録 Day1 記入。作業ブランチを agent/T11-impl に同期 |
| 2026-06-03 | Claude Code | T11 Day 2 実走: `collect --post` で 9/9成功・58新着、**Discord 実配信成功 (HTTP 204)**。本プロジェクト初の Webhook 到達。fail-open発火なし。TEST_LOG 稼働記録 Day2 記入。残: Day 3 (06-04) |
| 2026-06-03 | Claude Code | ドキュメント同期: AGENTS.md/README/commit-rules/main.py を実装実態(T1-T10完了・CLI 5コマンド・pytest 104)に更新。`post-summary` 表記を `collect --post` に是正、⏳マーカー除去、テスト数48→104 |
| 2026-06-03 | Claude Code | テスト分離修正: `test_cli_integration.py::test_collect_with_post_no_webhook_url` を `delenv`→`setenv("")` に変更 (実 .env webhook を `load_dotenv` が再投入する非hermetic欠陥)。実.env下でも pytest 104/ruff/mypy strict 緑。**テストコード変更につき merge 前に Codex レビュー要 (WORKFLOW §11)** |
| 2026-06-03 | Codex | ドキュメント同期 + CLIテスト分離修正の独立レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium/Low 指摘なし |
| 2026-06-04 | Claude Code | T11 Day 3 実走: `collect --post` で 9/9成功・1新着・**Discord HTTP 204**。**3日連続稼働 (06-02/03/04) 達成 → T11 完了 → Sprint 1A 完全終了**。全日 fail-open 健全。fresh pytest 104/ruff/mypy strict 緑。TEST_LOG Day3 + 総括記入。次: Sprint 1B |
| 2026-06-04 | Claude Code | Sprint 1B 準備 (アーキテクト): roadmap 現在地を 1B へ移動 (1A DoD 全チェック)、`docs/IMPLEMENTATION_PLAN-1B.md` 作成 (タスク T12〜T22 + 設計集約インデックス + 着手前ブロッカー)。AGENTS/README 地図に追加。**実装着手は実 model ID/endpoint 確定後** |
| 2026-06-10 | Claude Code | T11 マージ (PR #9) 確認 → 最新 main から `agent/T12-impl` 分岐。Sprint 1B 計画 docs コミット。**着手方針の明確化**: ブロッカー (API契約/課金) が直接塞ぐのは T13 接続確認のみ。計画 §5 のとおり他タスクはモック駆動で先行実装し、実 model ID は config 差し替えのみで反映可能な構造を維持する |
| 2026-06-10 | Claude Code | Ticket T12 実装完了: `llm/profile.py` (YAML ローダ + 重複/参照検証 + A/B/C 役割解決) + `llm/client.py` (OpenAI 互換 chat、リトライ2回、ollama think=false、reasoning_content フォールバック、キー値非漏洩)。テスト30件追加。fresh pytest 134 / ruff / mypy strict 緑。TEST_LOG に証跡追記 |
| 2026-06-10 | Claude Code | T14 (prescore: 中華圏キーワード辞書 + Tier ボーナス) / T15 (judge: temp=0 JSON 判定 + corroboration 決定的集計) / T16 (select/arc: 編集ゲート + 多様性キャップ + 三幕構成) 実装完了。各チケット TDD・全ゲート緑 |
| 2026-06-11 | Claude Code | T17 (台本生成: Hook/Insight/Action 契約 + 検証) / T18 (fallback: 再生成 → テンプレ乱択) / T19 (1B 4テーブル + repo) / T20 (A/B/C evaluate 集計) 実装完了。各チケット TDD・全ゲート緑 |
| 2026-06-11 | Claude Code | T21 実装完了: `script/runner.py` (draft 統合, editor 崩壊時 neutral fallback + 使用量記録) + `deliver/discord.py` post_markdown (2000字チャンク) + CLI `draft`/`evaluate`。実 DB で `draft --dry-run` スモーク (候補40件)。fresh pytest **235** / ruff / mypy strict 緑。**Sprint 1B コード側完了 — 残: T13 (人間: API契約) → T22 (観察)。merge は Codex レビュー + QA + 人間承認後** |
| 2026-06-11 | Claude Code | ローカル LLM E2E 2系統完了 (全断 fail-open=テンプレ配信 / 正常系 llm=5)。E2E 発見バグ 2 件修正: `reasoning` フォールバック + editor 部分判定欠落の neutral 充填。PR #10 にレビュアー向け結果コメント |
| 2026-06-11 | Claude Code | **運用リハーサル Day 0**: §13.2 日次フローを実データで初完走 (collect 9/9・70新着・HTTP204 → draft 候補40→採用5 llm=5 → **Discord 台本初配信**)。セキュリティ修正: httpx INFO ログの Webhook トークン露出を抑制 (要件 §9.5、リポジトリ混入なし・必要なら Webhook 再発行を推奨)。pytest 238 緑 |
| 2026-06-12 | Claude Code | PR #10 Copilot レビュー指摘 3 件対応 (4431b03): 台本文字数上限の厳密化 (ラベル込み300字 + 境界回帰テスト) / `profiles_file` 型注釈 `Path \| None` / IMPLEMENTATION_PLAN-1B ステータス行の実態同期。全スレッド返信・resolve 済み。fresh pytest 239 / ruff / mypy strict 緑 |
| 2026-06-12 | Codex | Sprint 1B (T12〜T21) 独立レビュー **FAIL** を REVIEW_REPORT に記録。Critical 1件: Webhook 4xx/5xx 時に `post_summary()` の `logger.exception` が HTTPStatusError の URL 文字列 (トークン込み) をログ出力する経路が残存 |
| 2026-06-12 | Claude Code | Codex Critical 対応 (818f88e): 例外ログを status code / 例外型名のみにサニタイズ、caplog 回帰テスト 3 件追加 (post_summary HTTP/接続 + post_markdown のトークン非露出を固定)。fresh pytest 242 緑 |
| 2026-06-12 | Codex | 再レビュー **PASS** を REVIEW_REPORT に記録。Critical/High 指摘なし。修正経路と回帰テストを確認、fresh pytest 242 / ruff / mypy strict 緑 |
| 2026-06-12 | Antigravity | Sprint 1B QA **PASS** を QA_REPORT に記録。IMPLEMENTATION_PLAN-1B §1 DoD 全 6 項目合格 (Discord 台本投稿はローカル LLM 実証を証跡とする)。UI/UX・回帰・整合性 OK。未解決リスク: T13 実 API (人間判断待ち)・T22 観察。**マージ残条件は人間承認のみ** |
| 2026-06-12 | Claude Code | **PR #10 の人間承認 squash マージを確認** (main `b76f6c4`、2026-06-12 01:41 JST。`agent/T12-impl` 先端とツリー一致 = T13/T22 Day 1 含む全コミット取り込み済み)。マージ後 main で品質ゲート fresh 緑 (pytest 242 / ruff / mypy strict)。規約 §8.2 に従い `agent/T22-impl` を分岐。**T22 Day 2 (06-13)・Day 3 (06-14) 07:47 JST のローカルスケジュール自動実行を設定** (Day 3 は 3日総括 + DoD 更新 + Sprint 1B 完了 PR 作成まで。merge は人間承認のみ) |
| 2026-06-12 | Claude Code | **Sprint 2 (音声化) 実装計画ドラフト作成** ([IMPLEMENTATION_PLAN-2.md](./IMPLEMENTATION_PLAN-2.md)): T23〜T32 タスク分解 + 設計集約インデックス (ADR-0006/architecture §4 を正とする) + 着手 3 条件ゲート (T22 完了 / 1B PR マージ / 人間 Go) + 着手前ブロッカー 5 件。**Sprint 1B 期間中の TTS コード導入はなし** (文書のみ、§3.4 遵守)。AGENTS/README 地図 + 古い T13 待ち記述を実態同期 |
| 2026-06-12 | Codex | Sprint 2 実装計画ドラフトの独立レビュー **PASS** を REVIEW_REPORT に記録 (Critical 0 / High 0 / Medium 1 / Low 1)。スコープ NG (動画/YouTube/Playwright 等) の混入なし、`.gitignore` と生成物方針の整合を確認 |
| 2026-06-12 | Claude Code | Codex 指摘 2 件を計画に反映: §6 を「ゲート粒度つき表」に再構成 (Sprint 2 Go 前 / T24 / T29 / T31 / T32 前を明示) + クラウド GPU・外部ストレージ選択時の provider/費用/認証管理/リンク永続期間の判断事項を追記。§7.2 をチケット単位ブロッカー解消方式に明確化 |
| 2026-06-12 | Claude Code | 人間判断待ち 2 件の決定支援資料を作成: ① 挨拶フレーズ候補 3 案 ([proposals/greeting-phrases-v0.1.md](./proposals/greeting-phrases-v0.1.md)) ② Game/Subculture 予備ソース推薦 ([proposals/game-subculture-source-v0.1.md](./proposals/game-subculture-source-v0.1.md) — Gemini に調査委任 + セルフホスト RSSHub 実検証。IndieNova HTTP 200/12件、yystv・gcores は 503 で除外)。**OpenCode CLI は 3 連続 UnknownError → 区分 D として人間判断待ちに記録** (起草はインライン代替) |
| 2026-06-12 | Claude Code | roadmap 未確定事項の残り 2 件 (BGM/ジングル素材源・Spotify/Apple AI ポリシー) を Gemini に調査委任し、出典 URL を実在検証の上で確度ラベル付き調査メモ化 ([proposals/distribution-policy-and-bgm-research-v0.1.md](./proposals/distribution-policy-and-bgm-research-v0.1.md))。**Apple/Spotify のポリシー引用 URL は 404 (無効引用) — 申請前の公式一次確認を必須と明記**。DOVA/Audiostock は実在確認済み。これで要件 §16 未確定事項は全件「解決済み / 人間ゲート / 資料準備済み」のいずれかに到達 |
| 2026-06-12 | Antigravity | 本日のドキュメント変更群 (Sprint 2 計画 + 提案 4 本 + 実態同期) の整合性 QA **PASS** を QA_REPORT に記録。ドリフト 2 種を検出・修正: AGENTS/README の古いテスト件数 235→242、README ステータス節の Sprint 1B 仕上げへの同期。Claude Code が残存ドリフト 2 箇所 (README の「T13 待ち」記述) を追加修正 |
| 2026-06-12 | Claude Code | **自律オーケストレーション基盤を整備** (引き継ぎ要請対応): ① [ORCHESTRATION_RUNBOOK.md](./ORCHESTRATION_RUNBOOK.md) 新設 — 交代した AI が状態判定→次手→外部 AI 委任 (OpenCode 実装/Codex レビュー/Antigravity QA/Gemini 調査/Copilot Git) →検証→記録を人間の逐次指示なしに回す操作手順。OpenCode の正確なモデル文字列 (`opencode-go/qwen3.7-max` 等 + 無料フォールバック) と非対話呼び出しを実機確認の上で記載。② [HANDOFF.md](./HANDOFF.md) 新設 — 時点スナップショット。③ AGENTS.md 地図 + 起動時読書順に組込。**規則遵守: main 直 push せず agent/T22-impl へ。merge・Sprint 越境・人間判断は据え置き** (RUNBOOK §6 に明文化) |
| 2026-06-13 | Claude Code | **OpenCode 委任経路を復旧** (区分 D 環境failure の自己解決): 実装委任が `UnknownError` で不通 → ログ解析で根因特定 (`NOT NULL constraint failed: session_message.seq` = OpenCode ≤1.15.0 の空セッション DB バグ) → `opencode upgrade` で 1.15.0→1.17.4 → `opencode-go/qwen3.7-max` (Go プラン) と `opencode/nemotron-3-ultra-free` (無料枠) 両方で smoke OK。RUNBOOK §3 を「稼働確認済み + 再発時の対処 (upgrade 優先)」に更新。これで実装委任 (OpenCode) / レビュー (Codex) / QA (Antigravity) / 調査 (Gemini) の 4 経路すべて稼働確認済み |
| 2026-06-13 | Claude Code | **T22 Day 2 を手動完走** (自動実行が記録を残さず失敗していたため RUNBOOK §2 決定木に従い補完): collect 7/9・30新着・fail-open実証 (Docker停止でjuejin失敗も完走)、draft 候補30→採用5・Discord配信成功。**重要観察: writer(DeepSeek) が 5本中4本 template fallback (Day1=0/5 から悪化)、editor(MiMo) は 100% 安定継続**。TEST_LOG に Day 2 記録、人間判断待ちに writer 変動 + スケジュール信頼性を追記。fresh pytest 242/ruff/mypy strict 緑 |
| 2026-06-14 | Claude Code | **T22 Day 3 手動完走 → T22 完了・3日観察締結** (autopilot)。colima 起動でフル 9/9 ソース観察: collect 53新着、draft 候補40→採用5 (**template=5/llm=0**)。**writer 300字超過が間欠でなく構造的と確定** (template率 0→80→100%、DB で全5本 attempts=3→300字超過を確認)。**NEW: canonical URL 横断 dedup 欠落を発見** (juejin 2ソースの同一記事が同一エピソードに2回採用)。TEST_LOG に Day3+3日総括、DoD/roadmap を実績更新 (インフラ✅/品質は条件付き)。スケジュール自動実行は Day2/3 とも無音失敗 → 機構の不安定を確定。次: 観察 PR 作成 (人間マージ) + 2 defects を別ブランチで TDD 修正 |
| 2026-06-14 | Claude Code | **T22 観察 PR #11 作成 + 2 defects 修正 PR #12 完了** (autopilot)。PR #11: Copilot レビュー 4 件対応 (ステータス同期/表記/可搬性) + 全スレッド resolve。PR #12 (`agent/T22-fixes-impl`、最新 main から分岐・code+tests のみ): defect① WRITER_CHAR_BUDGET=260 + 再生成フィードバック強化 / defect② canonical_url_hash 横断 dedup。**実装はインライン (OpenCode 委任は seq バグでないハング+並行編集汚染のため撤退、git reset で復旧)**。pytest 246 緑、**Codex 独立レビュー PASS + Antigravity QA PASS**。経験的検証 (draft #5): template 率 100%→40%・全 canonical hash ユニーク (重複解消)。残: 人間マージ承認のみ |
| 2026-06-14 | 人間 | **PR #11 + #12 を承認マージ** → main `16d03ed`。Sprint 1B 完全終了。「進めてください」で Sprint 2 着手を指示 |
| 2026-06-14 | Claude Code | **Sprint 2 着手 — T23 (TTSEngine Protocol) 実装** (autopilot)。ADR-0006 のエンジン抽象を `tts/engine.py` に実装: `TTSEngine` Protocol (runtime_checkable) + Voice/Capabilities/SynthesisRequest(空text検証)/SynthesisResult + MockTTSEngine (決定的・モック駆動) + `select_engine` (FR-090 設定駆動)。テスト11件。pytest 257 / ruff / mypy strict (51 files) 緑。**非ブロッカー部 (T23/T25-T28) はモック駆動で継続可。T24 (実 Irodori) は実行環境・声の人間ブロッカー待ち** |
| 2026-06-14 | 人間 | **TTS 実行環境を Kokoro fallback (Mac 実行) に決定** + 「T25-T28 を継続」を指示。Kokoro 採用で T24 の GPU/課金ブロッカーが実質解消 (実 Kokoro 接続はモックパイプライン完成後に依存追加して繋ぐ) |
| 2026-06-14 | Claude Code | **Sprint 2 モック駆動パイプライン T25-T28 実装完了** (autopilot, インライン)。T25 構造化台本 (`script/structure.py`, architecture §4 の segment 化) / T26 読み仮名辞書 (`tts/normalize.py` + `config/reading_dict.yaml`, FR-092) / T27 絵文字注釈 (`tts/annotate.py`, capabilities ゲート) / T28 文単位合成+wav結合 (`tts/synthesize.py`, str単位分割・fail-open)。MockTTSEngine を有効 wav 出力に改良し全行程をモック駆動で実テスト。テスト計33件追加、pytest 290 / ruff / mypy strict (59 files) 緑。**残ブロッカー: T24 実 Kokoro/Irodori 接続 (依存追加) / T29 BGM 素材 / T31 配信方法 / T32 A/B/C 既定** |
| 2026-06-14 | Codex | Sprint 2 パイプライン (T25-T28, [PR #14](https://github.com/Gazelle221B/panda-tech-news/pull/14)) 独立レビュー: 初回 FAIL (High1/Med3/Low1) → 修正反復 → **最終 PASS**。指摘 (絵文字単独文化/全滅時無効wav/concat異パラメータ/原語グロス二重読み/type alias/sample_rate不整合) を全て修正・回帰テスト追加。pytest 298 緑 |
| 2026-06-14 | Antigravity | Sprint 2 パイプライン QA **PASS** を QA_REPORT に記録。動作 (pytest 298/ruff/mypy)・回帰 (collect/draft 無影響)・設計適合 (architecture §4/ADR-0006)・スコープ (実TTS無/動画無/str単位/fail-open/秘密無) 全合格。**残: 人間マージ (#13→#14)** |
| 2026-06-14 | 人間 | T24 を **kokoro-onnx の optional 依存追加**で進める方針を決定 (依存最小 §5 を保ちつつ音声時のみ extra) |
| 2026-06-14 | Claude Code | **T24 Kokoro アダプタ実装** (autopilot, インライン)。`tts/kokoro.py`: KokoroTTSEngine (遅延 optional import・未導入で TTSError・backend 注入でテスト可) + `floats_to_wav` (numpy 非依存)。pyproject に extra `tts` (kokoro-onnx)。`select_engine("kokoro")` は遅延 import で循環回避。テスト8件、pytest 306 / ruff / mypy strict (61 files) 緑。**実モデル smoke (extra 導入 + モデル DL + HAL 声試聴) は人間環境ブロッカー** (T13 の音声版) |
| 2026-06-14 | Codex | T24 ([PR #15](https://github.com/Gazelle221B/panda-tech-news/pull/15)) 独立レビュー: 初回 FAIL (uv.lock未コミット/speed未伝播/非hermeticテスト) → 修正 → **PASS**。uv lock --check 通過・kokoro-onnx 0.5.0 実API一致を確認 |
| 2026-06-14 | Antigravity | T24 QA **PASS**。依存最小遵守 (kokoro-onnx optional)・回帰なし・実モデル接続未実行 (hermetic)・voice_clone=False。pytest 307 緑。**Sprint 2 の自律実装可能分 (T23-T28) 完了。残 T29(BGM素材)/T30(ffmpeg)/T31(配信方法)/T32(実音声観察) は全て人間ブロッカー or 重依存+実音声待ち** |
