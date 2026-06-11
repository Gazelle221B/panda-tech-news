# プロジェクト状態

> 最終更新: 2026-06-11 / 更新者: Claude Code (Sprint 1B 実装: T12〜T21 完了)
> 本ファイルは全エージェントが随時更新する。**Antigravity の内部記憶ではなくここを真の記憶とする** (WORKFLOW §13)。

## 現在のフェーズ

**Sprint 1B 実装完了 + 運用リハーサル稼働中** — T12〜T21 実装済み (pytest 238 / ruff / mypy strict / カバレッジ 96%)。E2E 検証 2 系統 (LLM 全断 fail-open / 正常系 llm=5) 完了。**2026-06-11 に §13.2 日次フローを実データで初完走**: collect 9/9 (70新着) → draft (候補40→採用5, 全 LLM 生成) → **Discord 台本初配信成功** (ローカル LLM variant L)。**残タスク**: T13 (実 API 接続 — 人間ブロッカー: API 契約・課金。解消後は .env にキー設定のみ) と T22 (3日品質観察 — variant L でのリハーサルは開始済み)。PR #10 の merge には Codex レビュー + Antigravity QA + 人間承認が必要 (WORKFLOW §10)。

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
| Ticket T13 (MiMo/DeepSeek 実接続 smoke) | ⏸ **人間ブロッカー待ち** (API 契約・課金、IMPLEMENTATION_PLAN-1B §6)。解消後は `.env` にキー設定 → `draft` 実行のみ (コード変更不要) |
| Ticket T22 (3日間の台本品質観察) | ⏸ T13 解消後に実施 |

## 作業中ブランチ

`agent/T12-impl` (最新 main `965f37d` から分岐)

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

2026-06-03: ドキュメント同期 + CLIテスト分離修正レビュー PASS。Critical/High/Medium/Low 指摘なし。実 `.env` webhook 存在下でも pytest 104 pass、ruff/mypy strict clean、秘密保護を確認。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-02: T10 (Ticket #9 CLI統合: `collect` コマンド) 再々レビュー PASS。Critical/High/Medium/Low 指摘なし。`--source` 複数指定時の未知/disabled ID検証、DB更新統合テスト、Webhook fail-open を確認。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-02: T10 (Ticket #9 CLI統合: `collect` コマンド) 再レビュー FAIL。High 1件: 複数 `--source` 指定時に未知/disabled IDを黙って無視する。Medium 1件: dry-run の `source_health` 未書き込み確認不足。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-02: T10 (Ticket #9 CLI統合: `collect` コマンド) 独立レビュー FAIL。High 1件: `collect --source <id>` 未実装。Medium 1件: T10受け入れ条件のDB状態検証不足。証跡は `docs/REVIEW_REPORT.md` に追記済み。

2026-06-01: T9 (Ticket #8 Discord Webhook サマリー投稿) 再レビュー PASS。Critical/High/Medium/Low 指摘なし。run 境界内の Tier/カテゴリ集計と Webhook fail-open を確認。証跡は `docs/REVIEW_REPORT.md` に追記済み。

## Antigravity QA の直近結果

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
- 初期9本に Game/Subculture 系を1本予備で入れるか (Spike §3 B案、Sprint 1A 観察中に並行検討可)。
- LLM 役割 A/B/C のどれを初期既定にするか (ADR-0005、実測後確定)。
- **【Sprint 1B 着手前ブロッカー】実 LLM model ID / endpoint の確定** (要件 §16): `deepseek-chat` / `mimo-v2.5-pro` はプレースホルダ。MiMo 海外課金が困難なら OpenRouter フォールバック。API 契約・課金は人間判断 (WORKFLOW §4 区分 D)。詳細は [IMPLEMENTATION_PLAN-1B.md](./IMPLEMENTATION_PLAN-1B.md) §6。
- HAL の声リファレンス確定タイミング (Sprint 2 までは保留可)。
- 番組オープニング/エンディング挨拶フレーズの確定 (Sprint 1B 以降で可)。
- (E2E 検証 2026-06-11 で発見) タイトルが短い GitHub リリース (例「v1.0.0」) は台本見出しにソース名を併記すべきか — T22 観察で要否判断。

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
