# 要件定義書 v1.0

華流テック通信 by HAL / karyu-tech-news

## 0. ドキュメント情報

文書名: 要件定義書 v1.0
プロジェクト名: karyu-tech-news
番組名: 華流テック通信
サブタイトル: HAL Daily Briefing
作成日: 2026年5月28日
ステータス: Sprint 1A 実装前確定版

本ドキュメントは、中華圏特化AIポッドキャスト「華流テック通信 by HAL」の要件を定義する。対象範囲は、番組コンセプト、編集方針、情報源管理、収集基盤、台本生成、音声化、配信、運用、法務・規約対応、Sprint 1A/1B の実装スコープまでとする。

既存の tc-newsflow は、RSS収集、dedupe、LLM Profile、出力形式切替、Developer News向けの Hook / Insight / Action 型プロンプト設計を持つため、Python版では実装そのものではなく、設計思想を継承する。

## 1. プロジェクト概要

### 1.1 目的

本プロジェクトの目的は、中国語圏の一次情報・準一次情報・コミュニティ情報を収集し、日本語リスナー向けに短時間で理解できるAIポッドキャストとして毎朝届けることである。

特に、英語圏・日本語圏メディアに流れてくる前の、中国AI、中国OSS、中国テック、中国ゲーム、中国サブカルの動きを拾うことを重視する。

### 1.2 番組コンセプト

日本のオタク・エンジニア・ビジネスマンに向けた、中華圏専門の Discover Daily 形式AIポッドキャスト。

中国語ネイティブの情報源から、まだ英日メディアに流れていないディープでニッチでキャッチーなトピックを、平日朝に5〜10分で届ける。

### 1.3 番組名

正式名称: 華流テック通信
サブタイトル: HAL Daily Briefing
表記揺れ許容: 華流テック通信 by HAL
キャスター名: HAL

HALは番組から独立したAIキャスター人格として扱う。将来的に別番組へ展開する可能性を残す。

### 1.4 想定リスナー

主対象は以下。

- 日本在住のエンジニア。
- AI、OSS、ゲーム、サブカルに関心のあるオタク層。
- 中国語圏の情報を追いたいが、中国語ソースを毎日読む時間がないビジネス層。
- 日本語メディアに流れてくる前の中国AI・テック情報を早めに掴みたい個人開発者・企画者。

### 1.5 成功状態

短期的な成功状態は、平日朝に安定して番組台本または音声が生成され、朝の確認工数が5分以内に収まること。

中期的な成功状態は、YouTube限定公開運用から一般公開へ移行し、継続視聴者がつくこと。

長期的な成功状態は、YouTube、Spotify、Apple Podcasts、Note、Xなどへ展開し、中華圏テック・サブカル情報の定点観測メディアとして成立すること。

## 2. スコープ

### 2.1 初期スコープ

初期スコープは以下。

- RSS / RSSHub による情報収集。
- SQLiteによる seen 管理、source health 管理、実行ログ保存。
- ソースTierに基づく信頼性管理。
- 収集失敗時の fail-open。
- LLMによるトピック選定、スコアリング、アーク配置。
- LLMによる日本語Markdown台本生成。
- Discord Webhookによる収集サマリー・台本投稿。
- TTSによる音声生成.
- BGM、ジングル、SEのミックス。
- 波形ビジュアライザ付き動画生成。
- YouTube限定公開アップロード。
- AI生成音声であることの明示。

### 2.2 Sprint 1A スコープ

Sprint 1Aでは、LLM、TTS、動画、YouTubeは実装しない。

Sprint 1Aの目的は、ソース定義YAMLからRSS/RSSHubを読み、SQLiteに保存し、seen管理とsource health管理を行い、Discordへ収集サマリーを投稿できる状態を作ることである。

Sprint 1Aの対象は以下。

- プロジェクト初期化。
- RSSHubセルフホスト用 docker-compose。
- sources.yaml の定義。
- feedparser/httpxによる取得。
- SQLite保存。
- source単位fail-open。
- source health記録。
- Discord Webhookで収集サマリー投稿。
- 3日間の収集観察。

### 2.3 Sprint 1B スコープ

Sprint 1Bでは、LLMを導入して台本生成まで行う。

対象は以下。

- MiMo / DeepSeek のLLM profile設定。
- トピック候補のスコアリング。
- Tier重み付き選定。
- 3〜5本の採用トピック選定。
- Markdown台本生成。
- A/B/C案のLLM役割分担比較。
- Discord Webhookによる台本投稿。
- 音声化なしの番組品質評価。

### 2.4 初期スコープ外

初期スコープ外は以下。

- Playwrightによるスクレイピング。
- 中国IPプロキシ。
- Cookie必須ルートの本格運用。
- 小红书、微博、知乎のログイン依存収集。
- Discord Bot常駐。
- リアクション承認フロー。
- TTS音声合成。
- 動画生成。
- YouTube自動アップロード。
- Spotify / Apple Podcasts申請。
- ボイスドラマ。
- 雑談番組。
- Dense uncensoredモデルによる創作番組。
- Hermes Agentによる自律運用。

これらはSprint 2以降で段階的に検討する。

## 3. 番組要件

### 3.1 配信頻度

平日配信を基本とする。

夜23:00 JSTに収集・生成バッチを実行し、翌朝7:00〜7:50に確認する。公開は朝8:00を目標とする。

土日は原則として通常配信しない。将来的に週次まとめ、特別回、実験回を入れる余地は残す。

### 3.2 尺

基本尺は5〜10分。
最大尺は15分。
初期MVPでは音声化前の台本長から推定尺を算出する。

1トピックあたりの目安は60〜120秒。トピック数は3〜5本。

### 3.3 話者

初期はAIキャスター「HAL」によるソロ進行。

対話形式、複数話者、パネル形式は初期スコープ外。将来的に雑談番組へ展開する場合に再検討する。

### 3.4 キャスター「HAL」

HALは20代前半、中性的な女性として設計する。声は落ち着いた低めのトーンで、透明感があり、聞き取りやすさを最優先する。

一人称は「ボク」。
基本はニュース読み。
要所で自然な驚きや感心を入れる。
過度なVtuber調、煽り、政治的断定、ナショナリズム表現は避ける。

参照イメージは、緒方恵美、坂本真綾、石川由依、榊原優希の中性的・透明感・低めの方向性。ただし実在声優の声を無断でクローンしない。

### 3.5 トーン

情報の信頼性はNHKニュース寄り。
会話の空気はRebuild.fm / TBS Podcast寄り。
表現は硬すぎず、しかし根拠を曖昧にしない。

番組の基本姿勢は「中国すごい」「日本終わった」ではなく、「中国語圏で何が起きていて、日本側から見ると何が面白いか」を冷静に翻訳・解説すること。

## 4. カバー領域

### 4.1 優先順位

優先順位は以下。

1. 中国AI
2. 中国AI関連OSS
3. 中国テック
4. 中国ゲーム
5. 中国サブカル
6. 中国OSS非AI
7. 中国アニメ

### 4.2 初期配分

Sprint 1AではAI寄りでよい。目的は収集基盤の安定性検証であり、番組の最終ジャンルバランスではない。

Sprint 1B以降で、ゲーム、サブカル、アニメ、OSS非AIを徐々に追加する。

### 4.3 将来の番組内配分

通常回では以下を目標とする。

AI / Tech / OSS: 2
Game / Subculture / Anime: 1

基本テンプレートは以下。

トピック1: AI、モデル、API、価格戦争、研究成果。
トピック2: OSS、開発者ツール、クラウド、スタートアップ。
トピック3: ゲーム、Bilibili、VTuber、サブカル、アニメ、ネット文化。

## 5. 編集ポリシー

### 5.1 ソース優先順位

中国語ネイティブソースを優先する。

英語圏・日本語圏に既に流れている一般ニュースは優先度を下げる。日本語メディアで既出の内容でも、中国語圏ソースに追加情報や現地文脈がある場合は採用可。

### 5.2 一次情報の扱い

公式・一次情報は単独ソースでも採用可。

対象は以下。

- 企業公式ブログ。
- ラボ公式発表。
- GitHub Release。
- 論文プレプリント。
- 大学・研究室公式発表。
- 政府・規制当局の公式発表。
- 信頼性の高い中華圏ニュースサイト。

### 5.3 コミュニティ情報・噂の扱い

コミュニティ発、未認証情報、噂、リークは単独採用しない。

採用条件は以下。

- 独立2ソース以上で言及されている。
- または、Tier1 / Tier2 ソースで追加確認できる。
- または、高信頼アカウントの言及がある。

採用する場合も、「噂レベル」「コミュニティで話題」「未確認」と明示する。

### 5.4 政治・規制・国際関係の扱い

イデオロギーやナショナリズムには踏み込まない。

ただし、AI規制、ゲーム規制、輸出規制、半導体規制、プラットフォーム規制など、ビジネス・技術への影響が不可分な場合は事実として扱う。

その場合も、番組の主軸は政治評論ではなく「技術・産業・ユーザー体験への影響」に置く。

### 5.5 ネタバレ方針

ゲーム・アニメ本編の重大ネタバレは避ける。

新作発表、売上、運営方針、炎上、イベント、技術的特徴、ファンコミュニティ動向は扱ってよい。

## 6. ソースTier定義

### 6.1 Tier1 公式

定義: ラボ、大学、企業、政府、公式GitHub、公式ブログ、arXiv等の一次情報。

採用条件: 単独採用可。
重み: 最大。
例: DeepSeek公式、Qwen公式、GitHub Release、大学研究室発表。

### 6.2 Tier2 準公式・高信頼メディア

定義: 認証アカウント、高信頼ニュースサイト、業界メディア。

採用条件: 単独採用可。
重み: 高。
例: 36Kr、机器之心、量子位、虎嗅、晚点 LatePost。

### 6.3 Tier3 コミュニティ

定義: 開発者コミュニティ、Bilibili UP主、知乎、掘金、SegmentFault、NGAなど。

採用条件: 独立2ソース、またはTier1/Tier2裏取りが望ましい。
重み: 中。
例: 掘金AIカテゴリ、Bilibili専門UP主、V2EX。

### 6.4 Tier4 噂・未認証

定義: 匿名微博、小红书未認証投稿、リーク系投稿、スクリーンショット由来情報。

採用条件: 原則不採用。採用時は独立2ソース必須かつ「噂」と明示。
重み: 低。

## 7. Source Selection Spike 要件

### 7.1 目的

Sprint 1Aの前に、初期収集ソース10本を決める。

目的は、最良の情報網を完成させることではなく、収集基盤の検証に使える安定ソースを用意すること。

### 7.2 初期ソース選定方針

- Tier1公式を5本。
- Tier2ニュースを3本。
- Tier3コミュニティを2本。
- Cookie必須ルートは含めない。
- Playwright、中国IPプロキシ、ログインCookie依存は含めない。
- AI比率は高めでよい。
- RSSHubルートは使ってよいが、壊れてもfail-openする。

### 7.3 初期候補

初期候補は docs/source-selection-spike-v0.1.md で定義する。

初期候補には以下を含める。

- DeepSeek GitHub Releases。
- Qwen GitHub Releases。
- Moonshot Kimi GitHub Releases。
- Zhipu / GLM GitHub Releases。
- Xiaomi MiMo GitHub Releases。
- 量子位。
- 36Kr Newsflash。
- 虎嗅。
- 掘金 AI Category。
- 掘金 AI Weekly Trending。

机器之心 は候補として保持するが、実RSSとして取得できる場合のみ有効化する。
Hugging Face Daily Papers は中華圏限定ソースではないため、Sprint 1Aでは初期10本から外す。

### 7.4 採用判定

- HTTP応答があること。
- feedparserで1件以上entryが取れること。
- Cookie不要で取得できること。
- 403、404、timeoutは初期候補から外す。
- bozoが立っていてもentryが取れていれば一旦採用可。
- RSSHub系はlocalhostのセルフホストで取得できれば採用可。

## 8. 機能要件

### 8.1 設定管理

#### FR-001 sources.yaml

システムは config/sources.yaml からソース定義を読み込めること。

各ソースは以下を持つ。

- id。
- name。
- url。
- tier。
- category。
- enabled。
- requires_cookie。
- notes。

#### FR-002 環境変数

システムは .env を読み込めること。

初期環境変数は以下。

- DISCORD_WEBHOOK_URL。
- MIMO_API_KEY。
- DEEPSEEK_API_KEY。
- ZHIHU_COOKIES placeholder。
- RSSHUB_BASE_URL。

Sprint 1Aでは DISCORD_WEBHOOK_URL と RSSHUB_BASE_URL のみ必須。

#### FR-003 LLM Profile

Sprint 1B以降、config/llm_profiles.yaml でLLM設定を切り替えられること。

MiMo、DeepSeek、OpenRouter、Ollama等を将来的に切替可能にする。

### 8.2 収集

#### FR-010 RSS取得

システムはRSS/Atomフィードを取得できること。

feedparserで各entryを内部形式に正規化する。

#### FR-011 RSSHub取得

システムはRSSHubセルフホスト経由のURLを取得できること。

RSSHubの一部ルートが失敗しても、他ソースの取得を継続する。

#### FR-012 タイムアウト

各ソース取得は30秒以内にタイムアウトする。

#### FR-013 リトライ

取得失敗時は最大2回リトライする。

#### FR-014 User-Agent

HTTPリクエストには明示的なUser-Agentを付与する。

例: karyu-tech-news/0.1

### 8.3 正規化

#### FR-020 RawItem

取得結果はRawItemに正規化する。

RawItemは以下を持つ。

- item_key。
- external_id。
- title。
- link。
- summary。
- published_at。
- fetched_at。
- source_id。
- raw_json。
- canonical_url_hash。

#### FR-021 item_key

保存前に必ず空でないitem_keyを生成する。

優先順位は以下。

- external_id。
- link。
- hash(title + published_at + source_id)。

#### FR-022 canonical_url_hash

同じURLが複数ソースから来た場合に備え、canonical_url_hashを保持する。

ただしSprint 1Aではクロスソース重複排除には使わない。Sprint 1B以降の重複検出・裏取り検出に使う。

### 8.4 永続化

#### FR-030 SQLite

システムはSQLiteに状態を保存する。

DBファイルは data/state.db。

#### FR-031 items テーブル

itemsテーブルは取得アイテムを保存する。

UNIQUE制約は UNIQUE(source_id, item_key) とする。

hash 単体にUNIQUEを張ってはならない。

#### FR-032 sources テーブル

sourcesテーブルはソース定義を保存または同期する。

#### FR-033 source_health テーブル

source_healthテーブルは各ソースの健全性を記録する。

保持項目は以下。

- source_id。
- last_success_at。
- last_failure_at。
- consecutive_failures。
- last_error。

#### FR-034 collect_runs テーブル

collect_runsテーブルは収集実行単位の記録を保存する。

保持項目は以下。

- started_at。
- finished_at。
- total_sources。
- successful_sources。
- failed_sources。
- total_items。
- new_items。

### 8.5 dedupe / seen管理

#### FR-040 ソース単位seen

同じsource_idとitem_keyの組み合わせは重複保存しない。

#### FR-041 クロスソース重複

異なるソースから同じURLが来た場合、Sprint 1Aでは別レコードとして扱う。

Sprint 1B以降、canonical_url_hashにより同一ネタ検出を行う。

#### FR-042 古いアイテム削除

90日以上前のitemは、将来的に定期削除対象とする。

Sprint 1Aでは必須ではない。

### 8.6 source health

#### FR-050 成功時更新

取得成功時、last_success_atを更新し、consecutive_failuresを0に戻す。

#### FR-051 失敗時更新

取得失敗時、last_failure_atを更新し、consecutive_failuresを1増やし、last_errorを保存する。

#### FR-052 連続失敗通知

consecutive_failuresが3以上になったソースはDiscord収集サマリーで警告表示する。

### 8.7 fail-open

#### FR-060 ソース単位fail-open

1つのソース取得が失敗しても、パイプライン全体を止めない。

#### FR-061 最低トピック数

Sprint 1B以降、候補トピックが3本未満の場合、エピソード生成をスキップする。

Sprint 1Aでは収集サマリーのみなので、最低トピック数判定は参考値として扱う。

### 8.8 Discord投稿

#### FR-070 Webhook投稿

システムはDiscord Webhookへ収集サマリーを投稿できること。

#### FR-071 投稿失敗時

Webhook投稿が失敗しても収集処理は失敗扱いにしない。ログにのみ記録する。

#### FR-072 添付

Sprint 1Aでは添付ファイルは扱わない。Markdown本文投稿のみ。

Sprint 2以降、mp3/mp4添付またはR2/S3等への外部保存リンク投稿を検討する。

### 8.9 LLM編集・台本生成

Sprint 1B以降の要件。

#### FR-080 トピックスコアリング

LLMは候補アイテムをスコアリングし、3〜5本を選定できること。

評価軸は以下。

- 重要度。
- 新規性。
- 中華圏らしさ。
- 日本リスナーへの関係性。
- ソースTier。
- 裏取り状況。
- 番組アーク上の配置。

#### FR-081 アーク配置

番組は以下の流れを基本とする。

- 重要ニュース。
- 技術・産業的な深掘り。
- 前向きまたは面白い話題。

#### FR-082 台本生成

LLMは日本語Markdown台本を生成する。

台本は Hook / Insight / Action を含む。

#### FR-083 LLM A/B/C検証

初期は以下を比較する。

- A案: MiMo Editor → DeepSeek Writer。
- B案: MiMo Editor → MiMo Writer。
- C案: DeepSeek Editor → MiMo Writer。

評価項目は以下。

- 採用率。
- 修正回数。
- 読み上げ自然さ。
- コスト。
- JSON安定性。
- 台本のAI要約臭。

### 8.10 TTS・音声化

Sprint 2以降の要件。

#### FR-090 TTS抽象化

TTSエンジンを抽象化し、Irodori、Style-Bert-VITS2、AivisSpeech、CosyVoice等を差し替え可能にする。

#### FR-091 HAL音声

HALの声はTTS非依存のキャラクター定義として管理する。

Irodori-TTSのVoiceDesign → Speaker Inversion固定化は検証項目であり、確定仕様ではない。

#### FR-092 読み仮名辞書

固有名詞の読みを制御する辞書を用意する。

対象は、中国企業名、中国モデル名、中国人名、ゲーム名、アニメ名、地名。

### 8.11 音響合成

Sprint 2以降の要件。

#### FR-100 BGM

Lo-fi + 中華風アンビエントBGMを薄く敷く。

#### FR-101 ジングル

オープニング、トランジション、エンディングのジングルを扱う。

#### FR-102 ラウドネス

mp3出力時に聞きやすいラウドネスへ正規化する。

#### FR-103 ファイル形式

初期音声形式はmp3 192kbpsを想定する。

### 8.12 動画生成

Sprint 2以降の要件。

#### FR-110 静止画動画

番組ロゴと音声を組み合わせた動画を生成する。

#### FR-111 波形ビジュアライザ

ffmpeg showwaves等で簡易波形を表示する。

#### FR-112 mp4出力

YouTube投稿用にmp4を生成する。

### 8.13 YouTube配信

Sprint 2以降の要件。

#### FR-120 限定公開

初期2週間はYouTube限定公開で運用テストする。

#### FR-121 AI開示

AI音声キャスターを使用していることを動画説明欄に明記する。

例: 「本番組はAI音声キャスターHALによる自動生成番組です。」

#### FR-122 自動アップロード

将来的にYouTube Data APIで自動アップロードする。

Sprint 1A/1Bでは実装しない。

## 9. 非機能要件

### 9.1 メンテナンス性

Python 3.11+で統一する。

Go実装のtc-newsflowからは設計思想のみ継承する。2言語構成にはしない。

依存関係は最小限にする。

### 9.2 持続可能性

個人運用を前提にする。

朝の確認工数は最終的に5分以内を目標にする。

失敗時に原因が追えることを重視する。

### 9.3 耐障害性

ソース単位でfail-openする。

Webhook失敗で収集を止めない。

LLM失敗時はリトライし、将来的に別profileへフォールバックする。

TTS失敗時は文単位でリトライする。

### 9.4 観測可能性

全実行ログを保存する。

source_healthを保存する。

collect_runsを保存する。

Sprint 1B以降はLLM入出力、スコア理由、採用理由を保存する。

### 9.5 セキュリティ

APIキー、Webhook URL、Cookieは .env で管理する。

.env はgit管理しない。

.env.example のみgit管理する。

### 9.6 法務・規約対応

中国メディア記事の本文転載は禁止する。

出力は要約とHAL自身の解説にする。

実在人物の無断声真似・声クローンは禁止する。

BGM/ジングルは商用利用可能素材、または自前生成素材を使う。

YouTube等のAI生成コンテンツポリシーはフェーズ移行時に確認する。

### 9.7 コスト

月額目安は1,500〜3,000円。

上限予算は月1万円以内。

ローカルGPUを基本とし、クラウドGPUは初期不要。

## 10. 技術構成

### 10.1 実装言語

Python 3.11+。

### 10.2 主要ライブラリ候補

feedparser。
httpx。
pydantic。
pyyaml。
sqlalchemy。
python-dotenv。
typer または click。
pytest。
pydub。
google-api-python-client。
discord.py または Webhook直POST。

Sprint 1Aでは、feedparser、httpx、pydantic、pyyaml、sqlalchemy、python-dotenv、typer、pytestを使用する。

### 10.3 実行環境

Windows 11。
Intel Core i7 / i9クラス。
RTX 4070 Ti Super。
128GB RAM。
Docker Desktop。
RSSHubセルフホスト。

### 10.4 リポジトリ構成

```text
karyu-tech-news/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── requirements-v1.0.md
│   └── source-selection-spike-v0.1.md
├── config/
│   ├── sources.yaml
│   ├── llm_profiles.yaml
│   ├── hal_persona.yaml
│   └── show_format.yaml
├── assets/
│   ├── jingles/
│   ├── bgm/
│   ├── logo.png
│   └── voice_reference/
├── src/
│   └── karyu_tech_news/
│       ├── collect/
│       ├── edit/
│       ├── script/
│       ├── tts/
│       ├── mix/
│       ├── video/
│       ├── deliver/
│       └── main.py
├── data/
│   ├── state.db
│   └── episodes/
└── tests/
```

## 11. CLI要件

### 11.1 Sprint 1A CLI

Sprint 1Aで必要なCLIは以下。

```bash
python -m karyu_tech_news --help
python -m karyu_tech_news init-db
python -m karyu_tech_news validate-sources
python -m karyu_tech_news collect
python -m karyu_tech_news post-summary
```

### 11.2 Sprint 1B CLI

Sprint 1B以降で追加するCLIは以下。

```bash
python -m karyu_tech_news draft --date today
python -m karyu_tech_news post-discord --date today
python -m karyu_tech_news evaluate --date today
```

### 11.3 Sprint 2以降 CLI

Sprint 2以降で追加するCLIは以下。

```bash
python -m karyu_tech_news synthesize --date today
python -m karyu_tech_news mix --date today
python -m karyu_tech_news render-video --date today
python -m karyu_tech_news upload-youtube --date today
```

## 12. データベース要件

### 12.1 items

itemsは取得済み記事・リリース・投稿を保存する。

主なカラムは以下。

- id。
- source_id。
- item_key。
- external_id。
- title。
- link。
- summary。
- published_at。
- fetched_at。
- raw_json。
- canonical_url_hash。

制約は以下。

- UNIQUE(source_id, item_key)。

### 12.2 sources

sourcesはソース定義を保存する。

主なカラムは以下。

- id。
- name。
- url。
- tier。
- category。
- enabled。
- requires_cookie。
- notes。

### 12.3 source_health

source_healthは各ソースの状態を保存する。

主なカラムは以下。

- source_id。
- last_success_at。
- last_failure_at。
- consecutive_failures。
- last_error。

### 12.4 collect_runs

collect_runsは収集実行の結果を保存する。

主なカラムは以下.

- id。
- started_at。
- finished_at。
- total_sources。
- successful_sources。
- failed_sources。
- total_items。
- new_items。

### 12.5 future tables

Sprint 1B以降で追加候補。

- topic_candidates。
- episode_drafts。
- llm_runs。
- script_versions。
- episode_assets。
- publish_jobs。

## 13. 運用フロー

### 13.1 Sprint 1A 運用

23:00 JSTにcollectを実行する。

処理は以下。

- sources.yaml読み込み。
- enabled=trueのソースのみ取得。
- 各ソースのFetchResult生成。
- RawItem正規化。
- SQLite保存。
- source_health更新。
- collect_runs保存。
- Discord収集サマリー投稿。

### 13.2 Sprint 1B 運用

23:00 JSTにcollectを実行する。
23:05 JSTにdraftを実行する。
DiscordにMarkdown台本を投稿する。
翌朝に人間が確認する。

### 13.3 Sprint 2 運用

23:00 JSTに収集・台本生成・音声化・動画化まで行う。
翌朝7:00〜7:50に確認する。
8:00に限定公開または公開する。

## 14. Discord投稿要件

### 14.1 Sprint 1A サマリー形式

投稿例。

```text
📰 華流テック通信 - 収集レポート
日時: 2026-05-28 23:05 JST
実行時間: 12.3秒
✅ 成功: 8/10 ソース
❌ 失敗: 2/10 ソース
⚠️ 要対応:
- juejin-ai-category: consecutive_failures=3
📥 新規アイテム: 47件
Tier別:
- Tier1 公式: 5件
- Tier2 ニュース: 28件
- Tier3 コミュニティ: 14件
カテゴリ別:
- AI: 22
- Tech: 15
- OSS: 7
- Game: 3
```

### 14.2 Sprint 1B 台本投稿

投稿内容は以下。

- 番組タイトル。
- 生成日時。
- 採用トピック一覧。
- Markdown台本。
- ソース一覧。
- LLM profile。
- 推定尺。
- 注意事項。

## 15. Sprint計画

### 15.1 Sprint 1A

目的: 収集基盤を作る。LLMは使わない。

期間: 5〜10日。

チケットは以下。

1. プロジェクト初期化とCLIスケルトン。
2. sources.yamlスキーマと初期ソースリスト。
3. RSS/RSSHub取得モジュール。
4. SQLiteスキーマと永続化層。
5. seen管理とdedupe。
6. source health管理。
7. fail-open統合テスト。
8. Discord Webhookサマリー投稿。
9. 3日連続収集観察。

順番は、#8を#9より先に実装する。観察期間中にDiscordへサマリーが届く状態にする。

#### Sprint 1A DoD

- python -m karyu_tech_news collect が完走する。
- 10本前後のソースを取得できる。
- 一部ソースが失敗しても全体が止まらない。
- SQLiteにitemsが蓄積される。
- 同じソースを2回collectしても重複登録されない。
- source_healthが更新される。
- Discordに収集サマリーが届く。
- 3日連続で動作する。

### 15.2 Sprint 1B

目的: LLMで台本を作る。音声化はしない。

期間: 5〜7日。

チケット候補は以下。

- LLM profile定義。
- MiMo / DeepSeek接続確認。
- 候補アイテム抽出。
- Tier重み付きスコアリング。
- 3〜5トピック選定。
- Markdown台本生成。
- A/B/C比較ログ保存。
- Discord台本投稿。
- 3日間の台本品質観察。

#### Sprint 1B DoD

- 3〜5本のトピックが選ばれる。
- Markdown台本が生成される。
- ソース一覧が付く。
- A/B/CのどのLLM構成で生成したか記録される。
- Discordに台本が投稿される。
- 人間が読んで「音声化する価値がある」水準に近づいている。

### 15.3 Sprint 2

目的: 音声化する。

対象は以下。

- TTS抽象化。
- Irodori-TTS接続。
- 文単位合成。
- 固有名詞読み辞書。
- mp3生成。
- BGM/ジングル仮ミックス。
- Discordへmp3またはリンク投稿。

### 15.4 Sprint 3

目的: 配信ワークフローを作る。

対象は以下。

- 波形動画生成。
- YouTube限定公開アップロード。
- AI音声開示文言。
- 朝確認フロー。
- 必要ならDiscord Bot化。

## 16. 未確定事項

未確定事項は以下。

- 初期10本のURL実取得結果。
- MiMo / DeepSeek の実際のmodel IDとendpoint。
- HALの音声リファレンス。
- TTSエンジンの最終選定。
- 番組の挨拶と締めフレーズ。
- BGM/ジングル素材。
- YouTubeチャンネル名。
- R2/S3等の外部ストレージ要否。
- Spotify / Apple Podcasts配信ポリシー。

## 17. リスクと対策

### 17.1 RSSHubルートが壊れる

対策: source単位fail-open。3回連続失敗でDiscord通知。代替ソースを持つ。

### 17.2 ソースがAIに偏りすぎる

対策: Sprint 1Aでは容認。Sprint 1B以降でゲーム・サブカル・アニメを追加。

### 17.3 台本がAI要約臭い

対策: Hook / Insight / Action を必須化。LLM Criticを導入。A/B/C比較。

### 17.4 中国語固有名詞の読みが崩れる

対策: 読み仮名辞書を作る。台本生成時にカナ表記を併記する。

### 17.5 TTS音声が不自然

対策: TTS抽象化により別エンジンへ切替可能にする。

### 17.6 Webhook添付制限

対策: Sprint 1では添付しない。Sprint 2以降、mp3/mp4はR2/S3等に置いてリンク投稿する可能性を残す。

### 17.7 規約・著作権問題

対策: 本文転載しない。要約と解説に徹する。AI生成音声を明示する。実在人物の無断声真似をしない。

## 18. 受け入れ基準

### v0.1 受け入れ基準

- Source Selection Spikeが完了している。
- config/sources.yaml初版がある。
- Cookie不要の初期ソースが10本前後ある。

### v0.2 受け入れ基準

- Sprint 1A完了。
- collectが3日連続で動く。
- Discordに収集サマリーが届く。

### v0.3 受け入れ基準

- Sprint 1B完了。
- Markdown台本が生成される。
- LLM A/B/C比較ログがある。

### v0.4 受け入れ基準

- mp3音声が生成される。
- TTSエラー時に文単位リトライできる。

### v0.5 受け入れ基準

- 限定公開YouTube動画が生成・投稿できる。

## 19. 次アクション

次に実行するのは以下。

1. この文書を docs/requirements-v1.0.md として保存する。
2. docs/source-selection-spike-v0.1.md を作成する。
3. 初期10本のURLをローカルでcurl/feedparser検証する。
4. config/sources.yaml 初版を確定する。
5. Sprint 1A Ticket #1 の実装へ進む。

## 20. 判断ログ

### DL-001 Python単一化

理由: TTS、音声処理、Discord、YouTube APIがPythonで揃う。Goとの2言語構成は個人運用のメンテナンス性を下げる。

### DL-002 tc-newsflowは設計思想のみ継承

理由: 既存コードは有用だが、音声化・TTS・配信まで含めるならPythonに寄せた方がよい。

### DL-003 Sprint 1A/1B分割

理由: 収集不安定性と台本品質問題を分離するため。

### DL-004 Discord BotではなくWebhookから開始

理由: Bot常駐はGateway、権限、リアクション監視、再起動復帰など運用負荷が高い。Sprint 1AではWebhookで十分。

### DL-005 RSSHubはセルフホスト

理由: Cookie管理、ルート障害調査、安定運用のため。

### DL-006 Hugging Face Daily Papersは初期除外

理由: 有用だが中華圏専門ソースではない。Sprint 1Aではノイズになるため、1B以降の補助ソースに回す。
