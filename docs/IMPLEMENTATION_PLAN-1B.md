# 実装計画: Sprint 1B — LLM 編集・台本生成

> 役割: Sprint 1B の **タスク分解と着手前ブロッカー**を定義する。Sprint 1A の [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) (T1〜T11) の続き (T12〜)。
> ステータス: T12〜T21 実装済み (2026-06-10〜11、モック駆動 + ローカル LLM E2E 検証済み)。**§6 のブロッカーが直接塞ぐのは T13 (実 API 接続 smoke) のみ** — 他タスクは §5 の方針 (LLM 呼び出しはモックで JSON 契約を固定) で先行実装した。T13 解消後に T22 (3日観察) を実施。
> 体制: アーキテクト Claude Code(Opus) / 実装 OpenCode / レビュー Codex / QA Antigravity ([WORKFLOW.md](./WORKFLOW.md) §1)。

## 1. ゴールと DoD

ゴール: SQLite の収集済み候補から LLM で **3-5 本**を選び、**日本語 Markdown 台本 + ソース一覧 + A/B/C 判定ログ**を Discord に投稿する。**音声化はしない** (Sprint 2)。

### Sprint 1B DoD (要件 §15.2) — T22 3日観察 (06-12〜14) で検証

インフラ DoD (全達成):
- [x] 3-5本のトピックが選ばれる (3日とも候補→採用5本)
- [x] Markdown 台本が生成される (Hook/Insight/Action)
- [x] ソース一覧が付く
- [x] どの A/B/C 構成で生成したか記録される (`llm_runs`/`evaluate`、案A 3回・JSON安定100%)
- [x] Discord に台本が投稿される (3日とも投稿成功)

コンテンツ品質 DoD (条件付き):
- [~] 人間が読んで「音声化する価値がある」水準に近い — **writer (DeepSeek) の 300字超過問題で未達**。editor (MiMo) 判定は良好だが台本生成が template 落ち (Day1 0/5→Day2 4/5→Day3 5/5)。**T22 が捕捉した 2 defects (writer 300字遵守 / canonical URL 横断 dedup) の修正後に再評価** (詳細 [TEST_LOG.md](./TEST_LOG.md) T22 3日間総括)。

## 2. 設計の所在 (集約インデックス — 新規設計はこれらを正とする)

Sprint 1B の設計は既存ドキュメントに分散済み。**本計画では重複生成せず参照する**:

| 設計項目 | 正の所在 |
|---|---|
| LLM 役割分担 (editor/writer)・A/B/C | [ADR-0005](./adr/ADR-0005-llm-roles-ab-test.md) + [config/llm_profiles.yaml](../config/llm_profiles.yaml) |
| LLMProfile 抽象 (provider 切替) | [design-inheritance §2](./design-inheritance-tc-newsflow.md) |
| スコアリング→tone→アーク配置 (番組の核) | [design-inheritance §4](./design-inheritance-tc-newsflow.md) |
| 多様性キャップ選定 | [design-inheritance §5](./design-inheritance-tc-newsflow.md) |
| rune 切り詰め / fallback / プロンプト契約 | [design-inheritance §6-8](./design-inheritance-tc-newsflow.md) |
| 機能要件 (FR-080〜083) | [requirements-v1.0.md §8.9](./requirements-v1.0.md) |
| 構造化台本 JSON (script→tts 境界) | [architecture-podcast-station §4](./architecture-podcast-station.md) |
| 編集方針 (採否・禁止表現) | [editorial-policy.md](./editorial-policy.md) |
| 番組構成・台本投稿形式 | [show-format.md](./show-format.md) §5/§8 + 要件 §14.2 |

## 3. レイヤー・データの追加

新レイヤー ([architecture.md](./architecture.md) §1 の逆向き依存禁止に従う):
```
collect → store ← deliver        (1A 既存)
            ↑
          edit → script           (1B 追加。store を読み、台本を書き戻す)
            ↑
          llm/ (provider 抽象)     (edit/script から呼ぶ。collect/deliver は import しない)
```
- `src/karyu_tech_news/llm/` — profile ローダ + OpenAI 互換クライアント + fallback
- `src/karyu_tech_news/edit/` — ローカル事前スコア + LLM 編集判定 + 多様性キャップ + アーク配置
- `src/karyu_tech_news/script/` — Markdown 台本生成 + 構造化

新テーブル (要件 §12.5):
- `topic_candidates` (候補 + score/tone/source_tier/corroboration)
- `episode_drafts` (採用トピック + メタ)
- `llm_runs` (A/B/C 入出力・コスト・JSON安定性ログ)
- `script_versions` (台本本文 + 使用 profile + 推定尺)

## 4. タスク分解 (T12〜)

| ID | 内容 | 追加/変更 | 依存 |
|---|---|---|---|
| T12 | LLM profile ローダ + provider 抽象 (OpenAI互換)。editor/writer 解決・A/B/C 切替を設定だけで | `llm/profile.py` `client.py` | なし (config 既存) |
| T13 | MiMo/DeepSeek 接続確認 (実 model ID/endpoint 確定) | smoke test | **§6 ブロッカー** |
| T14 | 候補抽出 + ローカル事前スコア (キーワード辞書で LLM 前に絞る) | `edit/prescore.py` | T12 |
| T15 | LLM 編集判定 (score/tone/source_tier/corroboration の JSON, temp=0) | `edit/judge.py` | T12,T14 |
| T16 | 多様性キャップ選定 + アーク配置 (決定的コード) → 3-5本確定 | `edit/select.py` `arc.py` | T15 |
| T17 | Markdown 台本生成 (Hook/Insight/Action, 300字, 中国語固有名詞カナ化, 本文転載禁止) | `script/generate.py` | T16 |
| T18 | fallback 二重防御 (再生成 → テンプレ乱択 3-5パターン) | `script/fallback.py` | T17 |
| T19 | 新テーブル (topic_candidates/episode_drafts/llm_runs/script_versions) + 永続化 | `store/schema.py` `repo.py` | T16,T17 |
| T20 | A/B/C 比較ログ保存 + `evaluate` (採用率/修正回数/コスト/JSON安定性) | `edit/abtest.py` | T19 |
| T21 | CLI `draft` / `post-discord` / `evaluate` + Discord 台本投稿 (要件 §14.2) | `main.py` `deliver/discord.py` | T17-T20 |
| T22 | 3日間の台本品質観察 (1B 版の観察。「音声化する価値」評価) | `docs/TEST_LOG.md` | T21 |

## 5. テスト方針
- 各タスク unit (80% カバレッジ)。**LLM 呼び出しはモックで JSON 契約を固定** (実 API は T13 smoke のみ)。
- 決定的コード (アーク配置・多様性キャップ・rune 切り詰め) は実 LLM 不要で完全テスト可能 — **ここを厚く**。
- fallback: LLM が JSON を崩した/タイムアウトした入力でテンプレ生成に落ちる回帰テスト。
- 環境変数を未設定にするテストは `monkeypatch.setenv("VAR", "")` ([styleguide.md](./styleguide.md) §9)。

## 6. 人間判断待ち (着手前ブロッカー)
- **実 model ID / endpoint の確定** (要件 §16): `deepseek-chat` / `mimo-v2.5-pro` はプレースホルダ。MiMo 海外課金が困難なら OpenRouter フォールバック (`llm_profiles.yaml` の `mimo-openrouter`)。**API 契約・課金は人間判断** (WORKFLOW §4 区分 D)。
- **A/B/C の初期既定**: ADR-0005 は実測後確定。T13 接続後に1週間 A/B/C を回す。初期は **A (editor=mimo, writer=deepseek)**。
- **コスト上限の運用**: 要件 §9.7 (月1,500-3,000円)。LLM 呼び出し回数上限・キャッシュ方針を着手前に確認。

## 7. 着手手順
1. **§6 ブロッカー (実 model ID/endpoint) を人間が解消**。
2. `agent/T11-impl` を merge 後、**最新 main から `agent/T12-impl` を切る** (commit-rules §5 / AGENTS §8.2)。
3. T12 から順に: 実装 (OpenCode) → 独立レビュー (Codex) → QA (Antigravity) → 人間 merge。

## 8. 絶対 NG (Sprint 1B 固有)
- **LLM に JSON と日本語台本を同時に書かせない** (片方崩れる)。編集判定=JSON / 台本=プレーンテキスト / 構造化はコード側 ([architecture-podcast-station §4](./architecture-podcast-station.md))。
- **tone を LLM に「並べさせない」**。採点=LLM、並べ替え=決定的コード (design-inheritance §4.3)。
- **中国メディア記事本文の転載禁止** (要約と HAL 解説のみ, [editorial-policy.md](./editorial-policy.md) §10)。
- **バイト単位の文字列切り詰め禁止** (rune/str 単位, design-inheritance §6)。
- **TTS / 音声 / 動画 / YouTube はまだ書かない** (Sprint 2 以降, AGENTS §3.4 の精神を継続)。
- **fallback 無しで LLM 出力をそのまま配信しない** (JSON 崩壊日に番組が出ない, design-inheritance §7)。

---
> 改訂: タスク完了ごとの進捗・証跡は `docs/test-logs/` のチケットログと PR 本文に記録し、[PROJECT_STATE.md](./PROJECT_STATE.md) の更新はマージ後の docs ブランチでオーケストレーターが行う (ADR-0008)。設計判断は ADR を追加し本書 §2 を同期。
