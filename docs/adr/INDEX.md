# ADR インデックス — karyu-tech-news

> 役割: 全 Architecture Decision Record のナビゲーションハブ。**ここが ADR の正本リスト**。
> 新規 ADR は [TEMPLATE.md](./TEMPLATE.md) をコピーして作成する。
> 参照元: [AGENTS.md](../../AGENTS.md) §10, [DESIGN.md](../DESIGN.md) Appendix A

## ADR 運用ルール

- **一度 Accepted にした ADR は書き換えない**。決定を変える時は**新しい ADR を起こし**、旧 ADR のステータスを `Superseded by ADR-NNNN` に更新する。
- 番号は連番 (`ADR-0007-<kebab-title>.md`)。
- 重大な設計判断 (言語/スプリント境界/外部依存/抽象化方針) は必ず ADR 化し、本 INDEX と AGENTS.md §3/§5 を同期する (AGENTS.md §11.2)。

## 一覧

| # | タイトル | ステータス | 影響スプリント | 要旨 |
|---|---|---|---|---|
| [0001](./ADR-0001-python-single-language.md) | 実装言語を Python に単一化 | Accepted | 全体 | Go/ハイブリッド不採用。tc-newsflow は設計思想のみ継承、コード移植不可 |
| [0002](./ADR-0002-sprint-1a-1b-split.md) | Sprint 1A(収集) と 1B(LLM/台本) を分割 | Accepted | 1A/1B | 収集の不安定性と台本品質問題を分離。1A DoD 未達で 1B に進まない |
| [0003](./ADR-0003-discord-webhook-first.md) | Discord は Webhook 起点、Bot は将来 | Accepted | 1A | Bot 常駐の運用負荷を回避。Webhook 直 POST で開始 |
| [0004](./ADR-0004-rsshub-self-host.md) | RSSHub をセルフホスト | Accepted | 1A | Public インスタンスの Cookie 管理・障害調査不能を回避。`docker compose` で自前運用 |
| [0005](./ADR-0005-llm-roles-ab-test.md) | LLM 役割 (editor/writer) を A/B/C 検証で確定 | Accepted (検証は 1B) | 1B | 役割を固定せず設定で切替。価格戦争下のベンダー固定リスクを抽象化で回避 |
| [0006](./ADR-0006-tts-irodori-abstraction.md) | TTS は Irodori-TTS v3 主軸 + 抽象化レイヤー | Accepted (実装は 2) | 2 | `TTSEngine` で差し替え可能に。HAL 人格は TTS 非依存 |
| [0007](./ADR-0007-youtube-httpx-cli-approval.md) | YouTube 配信は httpx 直叩き + CLI 承認フロー | Accepted (実装は 3) | 3 | SDK・Discord Bot 不採用。OAuth refresh token + resumable upload を httpx で直接実装、公開は `karyu approve` |

## スプリント別の効き方

- **Sprint 1A (現在)**: 0001 / 0002 / 0003 / 0004 が実装を直接拘束する。
- **Sprint 1B**: 0005 (LLM 役割) が起動。
- **Sprint 2**: 0006 (TTS) が起動。

## 関連の地図

```
ADR-0001 (Python単一) ─ 全レイヤーの前提
ADR-0002 (Sprint分割) ─ スコープ境界の根拠 (§3.4 スコープ膨張NG)
ADR-0003 (Webhook) ───┐
ADR-0004 (RSSHub) ─────┼─ collect/deliver の外部依存方針
ADR-0005 (LLM役割) ────┼─ edit/script の抽象化 (1B)
ADR-0006 (TTS) ────────┘─ tts の抽象化 (2)
```
