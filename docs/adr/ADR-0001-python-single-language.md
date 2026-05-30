# ADR-0001: 実装言語を Python に単一化する

- 日付: 2026-05-28
- ステータス: Accepted
- 決定者: 人間 (プロダクトオーナー) + Claude Code (アーキテクト)
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §10.1, DL-001, DL-002

## 背景

既存資産として Go 製 `tic-choco/tc-newsflow` があり、RSS 収集・LLM プロファイル切替・developer-news 向けプロンプト設計などが整理されている。Python に乗せ換えるとこれらの実装資産を捨てることになる。

一方、本プロジェクトの最終形は「収集 → 編集判定 → 台本 → TTS → ミックス → 動画 → 配信」のエンドツーエンド。TTS/音声処理/Discord/YouTube API のエコシステムは Python が支配的。

## 検討した案

| 案 | 長所 | 短所 |
|---|---|---|
| Go 単一 (tc-newsflow 拡張) | 既存資産流用、性能 | TTS / pydub / YouTube SDK が薄い、個人運用で2言語化リスク |
| Python 単一 | エコシステム最厚、個人運用持続性、依存関係簡潔 | Go の高速性は捨てる |
| ハイブリッド (Go: 収集/編集、Python: TTS/配信) | 長所のいいとこ取り | 2言語の保守負担、IPC/プロセス間連携が個人運用の致命傷になりやすい |

## 決定

**Python 3.11+ に単一化する。** Go 実装からは設計思想 (Hook/Insight/Action、tone別アーク配置、LLMProfile 抽象化、fail-open 設計) のみを継承する。

## 根拠

- TTS、音声処理 (pydub)、Discord (discord.py / Webhook 直 POST)、YouTube Data API (google-api-python-client) がすべて Python で揃う。
- 個人運用において 2 言語構成は「デバッグ・デプロイ・依存管理が倍」になり、要件 §9.2 の持続可能性と直接衝突する。
- Go の性能優位は本ユースケース (1日1回のバッチ、~100アイテム規模) では顕在化しない。
- 設計思想は「単一の真実の源」として DESIGN.md に転写されるため、Go コードへの参照は不要。

## 影響

- tc-newsflow の Go コードは設計参考資料として `docs/tik-choco-tc-newsflow-*.md` に残し、import 不可能であることを許容する。
- Sprint 1A 着手から CI / Lint / 型チェック / テストフレームワークはすべて Python ベース。
- 将来 Go に戻る選択肢は残るが、その時は本 ADR を Superseded にする。

## 不採用案の代替検討

ハイブリッド案は「いつか必要になりそうなパフォーマンス」を理由に2言語化するもので、現時点で観測されていない問題への先回り。要件が顕在化したら別 ADR で再評価する。
