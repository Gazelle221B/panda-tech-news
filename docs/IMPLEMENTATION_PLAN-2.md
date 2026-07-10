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
- 新規依存: `ffmpeg` (システム, T30 で使用) + `pydub` (Python, **T29 の BGM 時間軸合成で使用**)。roadmap Sprint 2 節で既定。**T30 は ffmpeg 単体で完結し pydub 不要** (依存最小 §5)。これ以外を足す場合は ADR
- 新テーブル: `audio_versions` (episode_draft_id, engine, duration_sec, lufs, path, created_at)。音声ファイル本体は `data/episodes/` (git 管理外)
- 素材: `assets/bgm/` `assets/jingles/` (本体 git 管理外、§6 人間判断待ち)

## 4. タスク分解 (T23〜)

| ID | 内容 | 成果物 | 依存 |
|---|---|---|---|
| T23 | ✅ **実装済 (2026-06-14)** `TTSEngine` Protocol + 設定駆動エンジン選択 (FR-090)。モック駆動 | `tts/engine.py` | なし |
| T24 | ✅ **実音声 smoke 成功 (2026-06-17)** Kokoro (ONNX) で実機合成・全パイプライン実音声生成 (`tts/kokoro.py`)。Irodori 主軸アダプタも実装 (`tts/irodori.py`, OpenAI 互換 httpx, emoji_style 対応, `select_engine('irodori-tts-v3')`)。Markdown マーカー読み上げ defect を smoke で発見・修正。**残: 話速調整 (T32) / Irodori 実サーバ smoke (人間環境)** | `tts/kokoro.py` `tts/irodori.py` | T23 |
| T25 | ✅ **実装済 (2026-06-14)** 構造化台本 (segment 化、tone 引き継ぎ。LLM に JSON を書かせず保持済み構造から組む) | `script/structure.py` | なし |
| T26 | ✅ **実装済 (2026-06-14)** 読み仮名辞書 + テキスト正規化 (FR-092、最長一致1パス置換) | `tts/normalize.py` `config/reading_dict.yaml` | T25 |
| T27 | ✅ **実装済 (2026-06-14)** 絵文字注釈レイヤー (tone→絵文字、capabilities 分岐、入力非破壊) | `tts/annotate.py` | T23, T25 |
| T28 | ✅ **実装済 (2026-06-14)** 文単位合成 + 結合 (str 単位分割、失敗文 fail-open、wave 結合) | `tts/synthesize.py` | T23-T27 |
| T29 | ✅ **実装済 (2026-06-18)** BGM 仮ミックス。**判断: 素材非依存設計** — `assets/bgm/` に素材があれば pydub で全編に低音量 BGM (-18dB) を敷き、無ければ素通し (passthrough)。pydub 未導入・デコード失敗も fail-open。素材ライセンス (§6 人間ゲート) を待たずコードを通せる (T30 を BGM から切り離したのと同手法)。pydub は optional extra `tts` | `mix/mixer.py` | T28 (素材は **§6**) |
| T30 | ✅ **実装済 (2026-06-17)** ラウドネス正規化 -16 LUFS + mp3 192kbps/48kHz (FR-102/103)。ffmpeg `loudnorm` 2-pass (pass1 測定→pass2 線形補正→pass3 出力再測定で証跡化) を subprocess 実行。**判断: T29(BGM) に先行実装** — マスタリングは入力 wav 単体で完結し BGM 素材 (人間ゲート §6) に非依存なため「素の音声→完パケ mp3」のE2E経路を先行開通。**pydub は足さず ffmpeg 単体**で完結 (依存最小 §5)。実 smoke: 実エピソード wav -20.17→**-16.30 LUFS** / TP -1.71 dBTP / 73s=1.7MB | `mix/master.py` | **T28** (T29 とは独立) |
| T31 | ✅ **実装済 (2026-06-18)** `audio_versions` 永続化 + CLI `produce` + Discord mp3 添付。produce: 保存済み台本→構造化→文単位合成→BGMミックス→-16LUFS mp3→記録→(Discord)。**T36 契約更新**: 文単位の合成失敗は `synthesize_script` 内では fail-open で最後まで試し欠落数を集計するが、produce 境界では `skipped_sentences > 0` を不完全音声として fail-fast し、mp3 生成・DB 記録・Discord 投稿を行わない。BGM無し・Discord失敗は fail-open で続行。文単位で無音/実質無音/低有音率 chunk を落とし、concat 後に有効音声が 0 文、TTS 合成 wav が実質無音/長時間無音、または実運用尺 (>=5s) で post-encode LUFS/true peak が測定不能・true peak が -1.0 dBTP 超なら mp3 を成功扱いせず fail-fast。`post_audio` は 25MB 超でメッセージに degrade・秘密非漏洩。**配信=Discord 添付** (人間判断、実測1.7MB/73s が 25MB 内。R2/S3 は将来)。**実 produce: 実 draft→643s/192k/48kHz/-16.3 LUFS/15.4MB**。Codex PASS + QA PASS ([PR #18](https://github.com/Gazelle221B/panda-tech-news/pull/18)) | `store/` `main.py` `deliver/discord.py` `tts/synthesize.py` | T30, T29 |
| T32 | 3日間の音声品質観察 (固有名詞読み/話速/BGM 音量/「配信する価値」評価) | `docs/test-logs/` のチケットログ (ADR-0008) | T31 |

> **運用メモ (Kokoro ローカル実行, T24)**: `tts/kokoro.py` のモデル/voices パスは環境変数 `KOKORO_MODEL_PATH` / `KOKORO_VOICES_PATH` で指定する設計 (未設定時はカレントディレクトリ相対の既定値を探すため、`uv run karyu produce --engine kokoro` は T36 以降、無音 mp3 を残さず非 0 終了しうる)。モデル本体は人間が `~/.cache/karyu-tts/kokoro-v1.0.onnx` / `voices-v1.0.bin` に DL 済み (2026-06-17)。ローカルで kokoro エンジンを動かす際は `.env.example` の該当項目をコピーして `.env` に設定すること。

> **依存メモ (T35→T36 中国語原題の発話退避)**: T35 では fallback テンプレ Hook の「<中国語原題>」を `pypinyin` で pinyin (声調なし) へ翻字していたが、T36 ASR QA で長い pinyin 羅列そのものが異物読みになることを確認したため廃止。現在の `tts/normalize.transliterate_chinese_titles` は後方互換名で、実体は中国語原題 quote を `この話題` へ退避する。読み辞書に完全一致する短い固有名詞 (`灵晟` など) だけカナ読みを残す。これにより `pypinyin` 依存は `pyproject.toml` / `uv.lock` から削除済み。

> **T36 音声入力 QA メモ**: TTS 前処理は inline Markdown link / bare URL を読ませず、`原語（カナ読み）` はカナ読みだけを残す。実運用で検出した `灵晟（リンション）` / `「ling cheng」` は読み辞書で `リンション` に統一する。長い中国語原題 quote は pinyin 化せず `この話題` へ退避する。

> **T36 音声出力 QA メモ**: BGM 前の TTS wav で最大連続無音秒数を測り、3.0 秒以上なら fail-fast。文単位 chunk は 0フレーム/壊れた wav/デジタル無音/実質無音に加え、0.2 秒以上で有音 window が 10% 未満かつ有音時間が 0.15 秒未満の低有音率 chunk も skipped として扱う。短い実発話に長めの前後無音が付いた chunk は、絶対有音時間で誤 skip を避ける。

> **T36 ASR QA メモ**: Irodori の絵文字スタイル注釈は、実音声 ASR で異物句と尺伸長を誘発したため production 既定では無効 (`tts.emoji_annotation_enabled: false`)。再採用は明示 opt-in とし、ASR + 人間聴感で再検証してから行う。

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
- **文単位合成は最後まで試す** (fail-open: 失敗文を記録し残りの合成を継続)。ただし produce 境界では欠落文がある完パケを成功扱いせず、mp3 生成・DB 記録・Discord 投稿前に fail-fast する。
- **バイト単位の文字列切り詰め禁止** (str 単位、design-inheritance §6)。
- **生成 mp3/wav を git にコミットしない** (`data/` `assets/` は管理外)。

---
> 改訂: タスク完了ごとの進捗・証跡は `docs/test-logs/` のチケットログと PR 本文に記録し、[PROJECT_STATE.md](./PROJECT_STATE.md) の更新はマージ後の docs ブランチでオーケストレーターが行う (ADR-0008)。設計判断は ADR を追加し本書 §2 を同期。
