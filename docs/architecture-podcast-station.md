# アーキテクチャ: AIポッドキャスト局 (全体像)

> 出典: [meeting.md](./meeting.md)(AIポッドキャスト構築プロジェクト議事録), [meeting2.md](./meeting2.md)
> 位置づけ: 要件定義書 ([requirements-v1.0.md](./requirements-v1.0.md)) が「華流テック通信 (ニュース番組)」に絞った**手前にある、より大きな構想**を記録する。
> 注意: 本書は**長期ビジョン**。直近で作るのはニュース番組のみ ([roadmap.md](./roadmap.md))。雑談/ドラマは将来段階。

要件定義書はこのビジョンの**第一段階 (ニュース) だけ**を実装スコープに切り出したもの。なぜニュースから始めるか、最終的に何を目指すかを失わないために本書を残す。

---

## 1. 真の目的: 三番組構成の「AIポッドキャスト局」

議事録の出発点は「AIの創造性をどう創作に落とすか」だったが、実体は **AIポッドキャスト局の構築**だった。三番組を段階的に作る:

| 番組 | 性質 | 必要なモデル特性 | 段階 |
|---|---|---|---|
| **ニュース** | 事実の翻訳。正確性と構造。発散させない | Instruct + 強い contract | **第一段階 (= 華流テック通信)** |
| **雑談** | 間と崩れが命。冗長性と脱線が魅力 | uncensored Dense、話者ごと別 context | 第二段階 |
| **ボイスドラマ** | 感情の振れ幅。タブー領域に踏み込む | abliterated Dense + character RAG | 第三段階 |

第四段階で三番組統合・相互参照・配信統合 → 「局」として完成。

**なぜニュースから**: 既に動く土台 (tc-newsflow) があり、音響演出・配信パイプラインの泥臭い部分 (タイミング、ラウドネス、配信先要件差) は三番組共通だから。ニュースで配管を通してから創作番組へ。

## 2. 組織比喩 = 設計原理 (作家・編集・出版社)

単なる比喩ではなく、2026年のオープンソース AI スタックを統合する設計原理。

| 層 | 対応モデル | 役割 |
|---|---|---|
| **作家層** | Dense (uncensored) モデル | 連続した人格・一貫した声。タブー領域へ踏み込める |
| **編集層** | MoE Instruct モデル | 専門エキスパート召喚。作家の暴走を翻訳、上位要求を作家が呑める形に降ろす緩衝材 |
| **出版社層** | ハーネス (自律制御基盤) | 刊行スケジュール・シリーズ整合性・レーベルカラー・読者ターゲットを保持、規範を発信 |

### 比喩から導く設計原則
1. **作家は出版社と直接話さない** — 編集が緩衝材。Director の機械的指示を Editor が情景的指示に翻訳
2. **編集は作家の文体を尊重し書き直さない** — フィードバックで再生成させる (Dense の「声の一貫性」を守る)
3. **出版社は個別シーンを読まない** — 構造化 state (章番号・伏線・感情カーブ・文字数) だけ渡す
4. **Critic は別人格・別モデルファミリー** — 評価が甘くなるのを防ぐ (Writer=Qwen系なら Critic=Gemma系)
5. **編集会議を組み込む** — 章の切れ目で Editor/Director/Critic が作家不在で矛盾を解消してから渡す

> **ニュース番組への適用**: この全体構造のうち、ニュースが使うのは「編集 (MoE: スコアリング/tone判定) + 出版社 (ハーネス: ステージ進行・配信)」が中心。作家層の uncensored Dense はニュースには**過剰**(事実曲解の傾向が出るため不要)。雑談・ドラマで本領発揮する。これは tc-newsflow が既に部分実装している三層 ([design-inheritance §4](./design-inheritance-tc-newsflow.md))。

## 3. モデル選定 (議事録の確定 + 価格戦争の反映)

> 2026年5月時点。価格・順位はモデル更新で入れ替わる前提。**LLM プロバイダも抽象化レイヤーで切替可能にする** ([ADR-0005](./adr/ADR-0005-llm-roles-ab-test.md))。

| 層 | 第一候補 | 根拠 |
|---|---|---|
| ニュース編集 | **MiMo V2.5-Pro** / **DeepSeek V4** | 中国文脈理解・長コンテキスト。A/B/C で実測確定 |
| ニュース台本 | **DeepSeek V4 Flash** | コスト最優先。中国語ネイティブ |
| 雑談/ドラマ作家 | **Qwen3.6 27B abliterated** | Apache 2.0、Dense、24GB VRAM。派生エコシステムが厚い |
| (ドラマ代替) | Gemma 4 31B Dense abliterated | マルチモーダル要件が出たら |
| ハーネス | Hermes Agent (NousResearch) | 自己改善・スキル蓄積。「出版社が経験を新人作家に渡す」と合致 |

価格戦争メモ: DeepSeek V4 Pro が 2026-05 に 75% 値下げを恒久化、Xiaomi MiMo が対抗で最大99% OFF + Token Plan 増量。**API のみ運用が現実的**になった。ただし値下げはプロモ的側面が強く、レート制限・品質は予告なく変わるため、キャッシュ制御とフォールバックモデルを準備する。

## 4. 完パケ・パイプライン (ニュース番組の最終形)

`collect → edit → script → tts → mix → render → publish` の7層。tc-newsflow は `script` まで実装済み。残りを足してニュースを完パケ化する。

```
[collect]  RSS/RSSHub → SQLite (Sprint 1A)
   ↓
[edit]     LLM スコアリング・tone判定・アーク配置・既出フィルタ (Sprint 1B)
   ↓
[script]   日本語台本生成 (Hook/Insight/Action) → 構造化JSON (Sprint 1B)
   ↓
[tts]      Irodori-TTS で文単位合成 (Sprint 2)
   ↓
[mix]      BGM/ジングル/SE を時間軸に並べ、ラウドネス正規化 -16 LUFS (Sprint 2)
   ↓
[render]   ffmpeg showwaves 波形ビジュアライザ + 静止画ロゴ → mp4 (Sprint 3)
   ↓
[publish]  Discord Webhook → YouTube Data API (Sprint 3)
```

### 構造化台本 (script → tts の境界)
台本はプレーンテキストではなく、音声化のため segment 構造化が必須。
```json
{
  "segments": [
    {"type": "intro_jingle", "asset": "opening"},
    {"type": "opening", "voice": "HAL", "text": "...", "bgm": "calm", "bgm_volume": 0.15},
    {"type": "transition", "asset": "transition_short"},
    {"type": "topic", "voice": "HAL", "text": "...", "bgm": "serious", "tone": "hard_negative"}
  ],
  "metadata": {"title": "...", "duration_estimate_sec": 480, "topics_count": 3}
}
```
**LLM はプレーンテキスト台本を出し、コード側でパースして JSON 化**する (LLM に JSON と日本語コピーを同時に書かせると片方崩れる)。「まずは、」「続いては、」「最後は、」等の既知マーカーで segment 境界を検出、tone は edit 層の判定結果から引く。[config/show_format.yaml](../config/show_format.yaml) がこの segment 構造の元。

### 絵文字注釈レイヤー (Irodori 固有)
tc-newsflow の tone 判定 (hard_negative/constructive/bright) を Irodori-TTS の絵文字スタイル制御に変換する後処理層。台本生成段階では絵文字を入れず、TTS 前処理で機械的に挿入する設計。ただし T36 ASR QA で異物読みと尺伸長を確認したため、production 既定では無効。[hal_persona.yaml](../config/hal_persona.yaml) `tts.emoji_annotation_enabled: true` を明示した persona だけ `tts.emoji_annotation` マッピングを使う。

## 5. TTS 戦略 (Irodori-TTS v3 主軸 + 抽象化)

詳細は [ADR-0006](./adr/ADR-0006-tts-irodori-abstraction.md)。要点:

- **主軸**: Irodori-TTS v3 (日本語特化、OpenAI 互換サーバー、48kHz、MIT、絵文字スタイル制御、Speaker Inversion)
- **弱点対策**: 漢字読み精度が弱い → **読み仮名辞書** (FR-092) が前提
- **抽象化**: `TTSEngine` インターフェースで Kokoro / Fish S2 Pro / CosyVoice3 / Style-Bert-VITS2 を差し替え可能に
- **HAL 人格は TTS 非依存** ([hal-persona.md](./hal-persona.md)) — エンジンが変わっても声を維持

## 6. 音響演出こそ品質を決める

議事録の結論: **ニュース番組の品質は台本の質より音響演出と話速で決まる**。聞きやすいラウドネス、適切な間、ジングルと台詞の繋ぎ、BGM 音量バランス — これは LLM プロンプトでは制御できず、ffmpeg と asset 選定の問題。**ここに時間をかける覚悟があるかが AI ポッドキャスト局の成否を分ける**。台本は現状品質で十分、毎朝聴きたくなるかは音響にかかる。

## 7. 既存事例の地図 (車輪の再発明回避)

- 学術: CreAgentive (arXiv 2509.26461) — 三段階エージェント、Story Prototype、千章規模を安価生成
- 実務: r/ClaudeAI "Multi-Agent Editorial Team for Novel Writing" — Claude起草/Gemini編集/7並列Reviewer。「作家と編集を別モデルに」という結論が本構想と一致
- フレームワーク: LangGraph (状態遷移) / CrewAI (ロールベース、組織比喩と親和) / AutoGen (会話駆動)

**独自性が残る領域**: (1) 作家層に意図的に Dense uncensored、(2) Dense/MoE の機能分担をアーキ特性で設計、(3) 「出版社」を編集とも作家とも独立した規範発信主体として実装。

## 8. 本書とニュース番組実装の関係

```
本書 (AIポッドキャスト局 全体構想)
  └─ 第一段階だけを切り出し → requirements-v1.0.md (華流テック通信)
       └─ さらに収集だけを切り出し → DESIGN.md / IMPLEMENTATION_PLAN.md (Sprint 1A)
```

実装は常にニュース番組の最小スコープから。本書は「なぜニュースから始めるか」「最終的に局を目指す」という north star を失わないための参照点であり、雑談・ドラマの設計を今確定するものではない。
