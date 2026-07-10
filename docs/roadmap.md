# ロードマップ: 華流テック通信 by HAL

> 出典: [requirements-v1.0.md](./requirements-v1.0.md) §15, [meeting.md](./meeting.md), [meeting2.md](./meeting2.md)
> 上位ビジョン: [architecture-podcast-station.md](./architecture-podcast-station.md)
> 受け入れ基準は要件 §18 の v0.1〜v0.5 に対応。

実装は「収集が安定するか → 台本が読む価値あるか → 音にする → 配信する」の順。各段の DoD を満たすまで次に進まない (ADR-0002)。

---

## 段階一覧

| Sprint | 目的 | 作る | 作らない | 受け入れ |
|---|---|---|---|---|
| **1A** | 収集基盤 | RSS/RSSHub→SQLite, source_health, fail-open, Discord収集サマリー | LLM/TTS/動画/YouTube | v0.2 |
| **1B** | 台本生成 | LLM編集判定, Tier重みスコアリング, 3-5本選定, Markdown台本, A/B/C比較ログ, Discord台本投稿 | 音声化 | v0.3 |
| **2** ✅ | 音声化 | TTS抽象化, Irodori接続, 文単位合成, 読み仮名辞書, mp3, BGM/ジングル仮ミックス | 動画/YouTube | v0.4 |
| **3** (PR #25 DRAFT) | 配信 | 波形動画, YouTube限定公開, AI開示, 朝確認フロー, (必要ならBot化) | — | v0.5 |
| **将来** | 局化 | 雑談番組, ボイスドラマ, 三番組統合, Spotify/Apple | — | — |

## Sprint 1A — 収集基盤 (✅ 完了 2026-06-04)

ゴール: `python -m karyu_tech_news collect` が完走し、SQLite に蓄積、Discord にサマリー、3日連続稼働。

チケット分解と DoD は [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) (T1〜T11)。LLM は呼ばない。

**着手前の前提タスク (人間)**: 初期10ソースの URL を `scripts/spike_curl_check.sh` + `scripts/spike_feedparser_check.py` で実取得検証し、[source-selection-spike-v0.1.md](./source-selection-spike-v0.1.md) §7 に結果記入 → [config/sources.yaml](../config/sources.yaml) の enabled 確定。

### Sprint 1A DoD (要件 §15.1) — ✅ 全達成 (T11, 2026-06-04)
- [x] `collect` が完走する
- [x] 10本前後を取得できる (有効9ソース)
- [x] 一部失敗しても止まらない (fail-open)
- [x] SQLite に items 蓄積 (134件)
- [x] 2回 collect で重複登録されない
- [x] source_health 更新
- [x] Discord にサマリー到達 (HTTP 204)
- [x] 3日連続稼働 (06-02 / 06-03 / 06-04)

## Sprint 1B — 台本生成 (✅ 完了 2026-06-14、PR #10/#11/#12 マージ済)

ゴール: SQLite の候補から LLM で3-5本選び、Markdown台本+ソース一覧+A/B判定ログを Discord 投稿。

主要タスク:
- LLM profile 定義 ([config/llm_profiles.yaml](../config/llm_profiles.yaml)) と MiMo/DeepSeek 接続確認 (実 model ID/endpoint 確定)
- 候補抽出 → ローカル事前スコア → LLM 編集判定 (score/tone/source_tier/corroboration) → アーク配置 ([design-inheritance §4](./design-inheritance-tc-newsflow.md))
- 多様性キャップ付き候補選定 (design-inheritance §5)
- Markdown台本生成 (Hook/Insight/Action, 300字, 中国語固有名詞カナ化, 本文転載禁止)
- A/B/C 比較ログ保存 ([ADR-0005](./adr/ADR-0005-llm-roles-ab-test.md))
- `llm_runs` テーブル等の追加 (要件 §12.5)
- CLI: `draft --date today`, `post-discord --date today`, `evaluate --date today`

### Sprint 1B DoD (要件 §15.2) — T22 3日観察で検証
- [x] 3-5本選定 / Markdown台本生成 / ソース一覧付与
- [x] どの A/B/C 構成で生成したか記録 (案A 3回・JSON安定100%)
- [x] Discord に台本投稿 (3日とも成功)
- [~] 「音声化する価値がある」水準に近い — writer (DeepSeek) 300字超過で未達。2 defects 修正後に再評価 ([TEST_LOG](./TEST_LOG.md) T22 総括)

## Sprint 2 — 音声化 (✅ 完了。T23〜T31 main 到達、T33〜T37 で日次自動配信・品質ハードニング・運用文書まで反映済み)

ゴール: mp3 完パケ。TTS 抽象化 + Irodori 接続 ([ADR-0006](./adr/ADR-0006-tts-irodori-abstraction.md))。

主要タスク: `TTSEngine` インターフェース, Irodori-TTS-Server 接続 (OpenAI互換), 文単位合成+結合, 読み仮名辞書 (FR-092), 絵文字注釈レイヤー (tone→感情, [architecture §4](./architecture-podcast-station.md)), 構造化台本JSON, pydub+ffmpeg ミックス, ラウドネス正規化 -16 LUFS, mp3 192kbps/48kHz, Discord へ mp3 (25MB超なら R2/S3 リンク, 要件 §17.6)。

### Sprint 2 実績
- T23-T31: TTS 抽象化 / 実音声 (Kokoro+Irodori) / 構造化台本・読み仮名・絵文字・文単位合成 / ラウドネス -16LUFS・mp3 完パケ / BGM mixer / produce 永続化・Discord mp3 配信 — main 到達 (PR #13-#19)。
- T33/T34/T35: 日次自動配信 (`collect→draft→produce→Discord`) + Irodori 600M VoiceDesign+caption 本採用 — main 到達 ([PR #22](https://github.com/Gazelle221B/panda-tech-news/pull/22), 2026-06-23)。日次 launchd は 3 日限定運用後の 2026-06-27 に撤去済み (現在手動運用のみ、恒常化は人間判断待ち)。
- T36: 音声品質ハードニング (3秒無音検出・clip/LUFS gate・失敗通知) — main 到達 ([PR #23](https://github.com/Gazelle221B/panda-tech-news/pull/23), 2026-06-26)。
- T37: agentic workflow docs 統合・ドリフト是正 — main 到達 ([PR #24](https://github.com/Gazelle221B/panda-tech-news/pull/24), 2026-06-29)。
- 残課題 (人間判断): T32 話速の聴感判断 / BGM 素材ライセンス / A/B/C 既定 variant 確定 / 恒常スケジューラ再導入方針。

## Sprint 3 — 配信 (現在地: [PR #25](https://github.com/Gazelle221B/panda-tech-news/pull/25) が T38-T41 実装で DRAFT、2026-07-05〜。人間 Go 判断の記録確認待ち)

ゴール: YouTube 限定公開まで自動化。

主要タスク: ffmpeg showwaves 波形動画 + 静止画ロゴ → mp4, YouTube Data API アップロード (OAuth), AI生成開示文言 (FR-121), 朝の承認フロー (✅→公開/🔁→再生成/❌→スキップ, 必要なら Discord Bot 化), 限定公開2週間運用テスト。

## 配信フェーズ (番組公開戦略, 要件 §7)
1. 1-2週: YouTube 限定公開 + Discord アーカイブ (固有名詞読み/BGM音量/話速/承認フロー/AI開示を実運用で詰める)
2. 3-4週: YouTube 公開、SNS告知控えめ
3. 2ヶ月: X クリップ + リンク
4. 3ヶ月〜: Spotify/Apple 申請 (AI生成ポリシー要確認), Note 記事化

## 成功指標 (暫定, meeting §12)
- 3ヶ月: 平日連続配信、朝確認5分以内
- 6ヶ月: YouTube登録100人、Discord 20人
- 12ヶ月: Spotify/Apple 正式配信、月間1000人

## 将来: 局化 ([architecture §1](./architecture-podcast-station.md))
ニュース完パケ後、雑談番組 (Multi-Agent 二話者, uncensored Dense) → ボイスドラマ (character RAG, Hermes Agent Skills, Fish S2 Pro) → 三番組統合。

## 未確定事項 (要件 §16)
初期10本URL実取得結果 / MiMo・DeepSeek 実model ID・endpoint / HAL音声リファレンス / TTS最終選定 / 挨拶・締めフレーズ / BGM・ジングル素材 / YouTubeチャンネル名 / R2・S3要否 / Spotify・Apple配信ポリシー。

> Pythonモジュール名は `karyu_tech_news` に確定済み (2026-05-30, [PROJECT_STATE.md](./PROJECT_STATE.md))。
