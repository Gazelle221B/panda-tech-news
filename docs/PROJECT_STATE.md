# プロジェクト状態

> 最終更新: 2026-05-31 / 更新者: Codex (独立レビュー)
> 本ファイルは全エージェントが随時更新する。**Antigravity の内部記憶ではなくここを真の記憶とする** (WORKFLOW §13)。

## 現在のフェーズ

**Sprint 1A 実装中** — Ticket #3 (RSS/RSSHub フェッチャ) 完了・検証グリーン

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
| Ticket #4 (SQLite スキーマ・永続化) | ⏳ 次の実装対象 |

## 作業中ブランチ

`agent/T3-impl` (初期実装 T1+T2 は `main` へコミット済)

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

2026-05-31: T4 (Ticket #3 RSS/RSSHub フェッチャ) 独立レビュー PASS。Critical/High/Medium 指摘なし、Low 2件 (duration_ms 計測範囲、README/AGENTS ステータス同期)。証跡は `docs/REVIEW_REPORT.md` に追記済み。

## Antigravity QA の直近結果

2026-05-30: 初期実装 (Ticket #1 + #2先行) の QA 確認完了。WORKFLOW に従い、初期ベースラインとして main にコミット。現在は Ticket #3 のため `agent/T3-impl` ブランチへ移行。

## 次に実行すべきアクション (優先順)

1. ~~ソース検証~~ ✅ / ~~sources.yaml 確定~~ ✅ / ~~Ticket #1 + #2先行 実装~~ ✅ / ~~Ticket #3 フェッチャ~~ ✅ (検証グリーン)
2. **Ticket #4**: SQLite スキーマ + 永続化層 (`UNIQUE(source_id, item_key)`、item_key 生成順 external_id→link→hash)。`init-db` コマンド。
3. Ticket #5 (dedupe) 〜 #9 (Discord) を依存グラフに沿って。

## 人間判断待ちの事項

- ~~Python モジュール名~~ → **確定・実装済**: モジュール `karyu_tech_news`、配布名 `panda-tech-news` 維持、ビルドは hatchling (`packages = ["src/karyu_tech_news"]`)、console script `karyu`。
- ~~ソース URL 実取得検証~~ → ✅ 完了 (2026-05-29)。
- ~~コミット/ブランチ運用: Ticket #1+#2先行 を `agent/<task>` ブランチに乗せるか直接コミットか。~~ → 初期実装として直接 `main` へコミット済。以降は `agent/<task>` 運用を厳格に適用。
- 初期9本に Game/Subculture 系を1本予備で入れるか (Spike §3 B案、Sprint 1A 観察中に並行検討可)。
- LLM 役割 A/B/C のどれを初期既定にするか (ADR-0005、実測後確定)。
- HAL の声リファレンス確定タイミング (Sprint 2 までは保留可)。
- 番組オープニング/エンディング挨拶フレーズの確定 (Sprint 1B 以降で可)。

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
|| 2026-05-30 | Antigravity | AGENTS.md / CLAUDE.md 追加 (2026-05-30) |
|| 2026-05-30 | Claude Code | AGENTS.md/CLAUDE.md + architecture.md / domain/collection.md / styleguide.md / README.md 追加。T1+T2 実装ベースに知識ベース文書を整備 |
| 2026-05-31 | OpenCode | Ticket #3 (T4) RSS/RSSHub フェッチャ実装完了。collect/normalize.py + fetcher.py + テスト 24件追加。pytest 48 pass / ruff・mypy(strict) clean |
| 2026-05-31 | Codex | T4 RSS/RSSHub フェッチャ独立レビュー PASS を `docs/REVIEW_REPORT.md` に記録。Critical/High/Medium 指摘なし |
