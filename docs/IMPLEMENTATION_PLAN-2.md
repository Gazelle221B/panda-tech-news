# 実装計画: Sprint 2 — 音声化 (mp3 完パケ)

> ステータス: **計画ドラフト (2026-06-12 作成)。実装着手は ①T22 完了 ②Sprint 1B 完了 PR の人間マージ ③人間の Sprint 2 Go 判断 の 3 条件成立後のみ** (AGENTS.md §3.4 / WORKFLOW §4 区分 E)。本書は準備ドキュメントであり、Sprint 1B 期間中に TTS コードを 1 行も導入しない。
> 体制: アーキテクト Claude Code(Opus) / 実装 OpenCode / レビュー Codex / QA Antigravity ([WORKFLOW.md](./WORKFLOW.md) §1)。

## 1. ゴールと DoD

ゴール: Sprint 1B が生成した Markdown 台本から **1 エピソードの mp3 完パケ** を生成し Discord に届ける。**動画・YouTube はやらない** (Sprint 3)。

### Sprint 2 DoD (要件 §15.3 + roadmap Sprint 2 節)
- [ ] `TTSEngine` 抽象化レイヤー経由で Irodori-TTS-Server に接続できる (FR-090、エンジン差し替え可能)
- [ ] 構造化台本 JSON から文単位合成・結合で 1 エピソードの音声が生成される
- [ ] 読み仮名辞書が中国固有名詞の読みに適用される (FR-092)
- [ ] BGM/ジングル仮ミックス + ラウドネス正規化 -16 LUFS + mp3 192kbps/48kHz (FR-100〜103)
- [ ] Discord に mp3 が届く (25MB 超はリンク投稿、要件 §17.6)
- [ ] 人間が聴いて「配信する価値がある」水準 (3日観察、T32)

## 2. 設計の所在 (集約インデックス — 新規設計はこれらを正とする)

| 設計項目 | 正の所在 |
|---|---|
| TTS エンジン選定・抽象化・弱点対策 | [ADR-0006](./adr/ADR-0006-tts-irodori-abstraction.md) (`TTSEngine` Protocol 定義含む) |
| 完パケ 7 層パイプラインと Sprint 境界 | [architecture-podcast-station §4](./architecture-podcast-station.md) |
| 構造化台本 JSON (script→tts 境界)・segment 検出 | [architecture-podcast-station §4](./architecture-podcast-station.md) + [config/show_format.yaml](../config/show_format.yaml) |
| 絵文字注釈レイヤー (tone→感情、Irodori 固有) | [architecture-podcast-station §4](./architecture-podcast-station.md) |
| HAL の声質仕様 (VoiceDesign キャプション) | [hal-persona.md](./hal-persona.md) + [config/hal_persona.yaml](../config/hal_persona.yaml) |
| 機能要件 (FR-090〜103) | [requirements-v1.0.md §8.10-8.11](./requirements-v1.0.md) |
| 文字列切り詰め・fallback の流儀 | [design-inheritance §6-7](./design-inheritance-tc-newsflow.md) (文分割にも適用: str 単位、バイト禁止) |
| 法務 (実在人物クローン禁止・AI 開示) | 要件 §9.6 / [editorial-policy.md](./editorial-policy.md)。開示文言の動画掲載は Sprint 3 (FR-121) |

## 3. レイヤー・データの追加

```
script/structure.py   # 台本テキスト → 構造化 JSON (マーカー分割、tone は edit 層から引き継ぎ)
tts/engine.py         # TTSEngine Protocol + SynthesisRequest/Result + 設定駆動エンジン選択
tts/irodori.py        # Irodori-TTS-Server アダプタ (OpenAI 互換 POST /v1/audio/speech)
tts/normalize.py      # テキスト正規化 + 読み仮名辞書適用 (config/reading_dict.yaml)
tts/annotate.py       # 絵文字注釈 (tone→絵文字。capabilities で非対応エンジンはスキップ)
tts/synthesize.py     # 文単位合成 + リトライ + wav 結合 (1 文失敗で番組を止めない)
mix/mixer.py          # BGM/ジングルの時間軸配置 (show_format.yaml の segment 構造に従う)
mix/master.py         # -16 LUFS 正規化 + mp3 192kbps/48kHz 出力
```

- 依存の流れ: `script → tts → mix` (一方向。tts が edit/llm を参照しない)
- 新規依存: `pydub` (Python) + `ffmpeg` (システム)。roadmap Sprint 2 節で既定。これ以外を足す場合は ADR
- 新テーブル: `audio_versions` (episode_draft_id, engine, duration_sec, lufs, path, created_at)。音声ファイル本体は `data/episodes/` (git 管理外)
- 素材: `assets/bgm/` `assets/jingles/` (本体 git 管理外、§6 人間判断待ち)

## 4. タスク分解 (T23〜)

| ID | 内容 | 成果物 | 依存 |
|---|---|---|---|
| T23 | ✅ **実装済 (2026-06-14)** `TTSEngine` Protocol + 設定駆動エンジン選択 (FR-090)。モック駆動 | `tts/engine.py` | なし |
| T24 | Irodori-TTS-Server 接続 smoke (実行環境・声リファレンスは **§6 ブロッカー**) | `tts/irodori.py` + smoke | T23, **§6** |
| T25 | ✅ **実装済 (2026-06-14)** 構造化台本 (segment 化、tone 引き継ぎ。LLM に JSON を書かせず保持済み構造から組む) | `script/structure.py` | なし |
| T26 | ✅ **実装済 (2026-06-14)** 読み仮名辞書 + テキスト正規化 (FR-092、最長一致1パス置換) | `tts/normalize.py` `config/reading_dict.yaml` | T25 |
| T27 | ✅ **実装済 (2026-06-14)** 絵文字注釈レイヤー (tone→絵文字、capabilities 分岐、入力非破壊) | `tts/annotate.py` | T23, T25 |
| T28 | ✅ **実装済 (2026-06-14)** 文単位合成 + 結合 (str 単位分割、失敗文 fail-open、wave 結合) | `tts/synthesize.py` | T23-T27 |
| T29 | BGM/ジングル仮ミックス (素材は **§6 ブロッカー**。pydub + ffmpeg) | `mix/mixer.py` | T28, **§6** |
| T30 | ラウドネス正規化 -16 LUFS + mp3 192kbps/48kHz (FR-102/103) | `mix/master.py` | T29 |
| T31 | `audio_versions` 永続化 + CLI `produce` + Discord mp3 投稿 (25MB 超はリンク、§6) | `store/` `main.py` `deliver/discord.py` | T30 |
| T32 | 3日間の音声品質観察 (固有名詞読み/話速/BGM 音量/「配信する価値」評価) | `docs/TEST_LOG.md` | T31 |

## 5. テスト方針
- TTS 呼び出しはモック (音声バイトのスタブ) で JSON/バイト契約を固定。実合成は T24 smoke と T32 観察のみ。
- 決定的コード (segment 分割・正規化・読み辞書・注釈・時間軸配置) は実エンジン不要で完全テスト可能 — **ここを厚く** (1B と同方針)。
- ffmpeg 依存テストは小さなフィクスチャ wav で。CI 不能な聴感評価は T32 の人間観察に委ねる。
- 文分割は **str (コードポイント) 単位**。バイト切り詰めの回帰テストを置く (design-inheritance §6)。

## 6. 人間判断待ち (ブロッカー粒度つき — どの時点までに決めるか)

| 判断事項 | ゲート | 内容 |
|---|---|---|
| **Sprint 2 Go 宣言** | **Sprint 2 着手前 (必須)** | §7.1 の 3 条件成立を人間が PROJECT_STATE に記録 |
| **Irodori-TTS-Server 実行環境** | **T24 着手前** | モデルカード想定は NVIDIA GPU (RTX 4070 Ti Super 級)。開発機は macOS — Apple Silicon 稼働可否 / 別マシン / クラウド GPU の選択 (WORKFLOW §4 区分 D)。**クラウドを選ぶ場合は provider・月額上限 (要件 §9.7 と合算)・認証情報の `.env` 管理も併せて決める**。不可なら Kokoro 等 fallback エンジンで T24 を代替する判断も人間 |
| **HAL 声リファレンス確定** | **T24 着手前** | VoiceDesign キャプション合成 → 試聴 → Speaker Inversion 固定化の検証 (ADR-0006)。**試聴判断は人間** |
| **BGM/ジングル素材** | **T29 着手前** | Lo-fi + 中華風アンビエント (FR-100)。入手元・ライセンス確認は人間。候補ライブラリ調査済み: [proposals/distribution-policy-and-bgm-research-v0.1.md](./proposals/distribution-policy-and-bgm-research-v0.1.md) |
| **mp3 配信方法** | **T31 着手前** | Discord 添付 (25MB 以内) か R2/S3 リンクか (要件 §17.6)。**外部ストレージの場合は provider・費用・認証情報の `.env` 管理・リンク永続期間も決める** |
| **A/B/C 既定 variant** (ADR-0005) | **T32 観察前** | T22 実測を見て確定 |

## 7. 着手手順 (ゲート)
1. **T22 完了** (3日観察、2026-06-14 予定) → **Sprint 1B 完了 PR を人間がマージ** → **人間が Sprint 2 Go を宣言** (PROJECT_STATE に記録)。
2. §6 の表のゲートに従う: T24 着手前までに「実行環境」「声リファレンス」を解消。**T29/T31/T32 のブロッカーは該当チケット着手前までで可** — それまで T23〜T28 はモック駆動で並行実装する (1B の T13 方式)。
3. 最新 main から `agent/T23-impl` を切る (commit-rules §5)。T23 から順に: 実装 (OpenCode) → 独立レビュー (Codex) → QA (Antigravity) → 人間 merge。

## 8. 絶対 NG (Sprint 2 固有)
- **実在人物の無断声真似・声クローン禁止** (要件 §9.6 / Irodori モデルカード)。声は VoiceDesign 生成のオリジナルのみ。
- **動画生成・YouTube 投稿はまだ書かない** (Sprint 3。AGENTS §3.4 の精神を継続)。
- **LLM に構造化 JSON と日本語台本を同時に書かせない** (1B §8 と同一。segment 化はコード側)。
- **TTS 1 文の失敗で番組全体を止めない** (fail-open: 失敗文スキップ記録 or 台本テキスト配信に degrade)。
- **バイト単位の文字列切り詰め禁止** (str 単位、design-inheritance §6)。
- **生成 mp3/wav を git にコミットしない** (`data/` `assets/` は管理外)。

---
> 改訂: タスク完了ごとに [PROJECT_STATE.md](./PROJECT_STATE.md) を更新。設計判断は ADR を追加し本書 §2 を同期。
