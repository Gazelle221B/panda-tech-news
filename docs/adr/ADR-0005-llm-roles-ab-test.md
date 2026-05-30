# ADR-0005: LLM 役割分担 (editor/writer) を A/B/C 検証で確定する

- 日付: 2026-05-28
- ステータス: Accepted (検証は Sprint 1B)
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §8.9 FR-083, §5.3, [meeting.md](../meeting.md), [config/llm_profiles.yaml](../../config/llm_profiles.yaml)

## 背景

中華圏ソースから日本語台本を作るのに、編集判定 (スコアリング・tone・既出判定) と 台本生成 (本文執筆) で別 LLM を使い分けたい。当初案は「編集=MiMo V2.5-Pro、台本=DeepSeek V4 Flash」だが、**この割り当ての根拠は推測でしかなく、日本語の自然さはベンチでは測れない**。

加えて 2026-05 に DeepSeek (75%値下げ恒久化) と Xiaomi MiMo (最大99% OFF + Token Plan 増量) が価格戦争に入り、どちらをどの役割に置くべきかは実測しないと決められない。

## 決定

役割分担を**固定せず**、設定ファイルで切替可能にして Sprint 1B で1週間 A/B/C 検証し、実測で確定する。tc-newsflow の LLMProfile 思想を継承 ([design-inheritance §2](../design-inheritance-tc-newsflow.md))。確定後も切替機構は保持し、モデル更新時に再評価する。

### 検証パターン
| 案 | editor (編集判定) | writer (台本生成) |
|---|---|---|
| A (推奨初期) | MiMo V2.5-Pro | DeepSeek V4 Flash |
| B | MiMo V2.5-Pro | MiMo V2.5-Pro |
| C | DeepSeek V4 | MiMo V2.5-Pro |

[config/llm_profiles.yaml](../../config/llm_profiles.yaml) の `ab_test:` に対応。

### 評価軸
採用率 / 修正回数 / 読み上げ自然さ (主観) / コスト / JSON 安定性 / 台本の AI 要約臭。

## 根拠

- 編集判定は「中国文脈理解・長コンテキスト・JSON 安定性」が効き (MiMo の 1M コンテキストが有利な可能性)、台本生成は「日本語の自然さ・コスト」が効く。要求特性が違うので別 profile が妥当。
- OpenAI 互換 API を最大公約数とすれば、DeepSeek・MiMo・OpenRouter・Ollama を同一インターフェースで並走でき、A/B/C 切替が設定だけで済む。
- 価格戦争下では特定ベンダー固定がリスク。抽象化レイヤーは必須。
- 値下げはプロモ的側面が強く、レート制限・品質が予告なく変わるため、キャッシュ制御とフォールバックモデル (要件 §9.3「3回リトライ後に別 profile フォールバック」) を併せて持つ。

## 影響

- Sprint 1B で `edit/` と `script/` が別 profile を受け取れる構造にする。
- A/B/C の生成ログを `llm_runs` / `script_versions` テーブル (要件 §12.5) に保存し、振り返り可能にする。
- editor に MiMo のようなフロンティア級を置くと「書き直したくなりすぎる」傾向があるため、編集者プロンプトは「差し戻しと方向提示のみ、本文は書き直さない」を厳格に縛る (組織比喩の第二原則, [architecture §2](../architecture-podcast-station.md))。
- 実 model ID と endpoint は接続確認時に確定 (要件 §16 未確定事項)。

## 不採用案

- **役割を最初から固定**: 推測ベースの割り当てを実装に焼き込むと、実測で逆だった場合に作り直し。
- **単一 LLM で編集も台本も**: tone 判定の JSON 安定性と台本の自然さを同時最適化できず、片方が犠牲になる。
- **LLM 二次検証 (Critic) を最初から**: コスト倍。Sprint 1B では決定的ルール + editor 判定に留め、LLM Critic は品質が伸び悩んだら追加 ([design-inheritance §13](../design-inheritance-tc-newsflow.md))。
