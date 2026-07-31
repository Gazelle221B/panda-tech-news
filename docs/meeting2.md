# AIポッドキャスト構築プロジェクト 議事録

**日付**: 2026年5月26日
**テーマ**: AIによる創造性の探求から、実装可能なAIポッドキャスト局の設計へ

---

## 1. 議論の出発点と発展経路

会話は「AIの創造性、特に無検閲モデルの発散をどう創作に落とし込むか」という抽象的な問いから始まった。そこから「自律的に制御するハーネスが必要」という要件追加を経て、組織比喩（作家・編集・出版社）が提示され、これが議論全体の中核概念となった。先行研究と既存実装の調査を経て、具体的なモデル選定（Dense uncensored × MoE × Hermes Agent）へと収束。

中盤で既存の Go 製ニュースフローツール tik-choco/tc-newsflow のソースコードレビューを実施し、それが既にこの組織比喩を部分的に実装していることを確認。最終的に、本プロジェクトの真の目的が**AIポッドキャスト局の構築（ニュース・雑談・ボイスドラマの三本立て）**であることが判明し、まずニュースを完パケで仕上げる方針へ収束。TTS は Irodori-TTS v3 を主軸とする案で着地。

---

## 2. 基礎概念：組織比喩としての創作ハーネス

### 2.1. 三層の役割定義

**作家層 = Dense uncensored モデル**
全パラメータが毎トークンに関与する Dense アーキテクチャの性質を、「連続した人格・一貫した声を持つ作家」に対応づける。安全層が剥がれた uncensored 化により、タブー領域（暴力、性、死、倫理的グレーゾーン）に踏み込める。これは創作上の必須条件で、特にボイスドラマでは避けて通れない。

**編集層 = MoE Instruct モデル**
Mixture of Experts の sparse activation を、「専門領域ごとに脳内エキスパートを召喚する編集者」に対応づける。指示追従性が高く、作家の暴走を翻訳し、上位からの要求を作家が呑める形に降ろす緩衝材として機能。

**出版社層 = ハーネス（自律制御基盤）**
個々のエージェントの上位にある制度・契約・ワークフロー。文章を書かないし編集判断もしないが、刊行スケジュール、シリーズ整合性、レーベルカラー、読者ターゲットといったメタコンテキストを保持し、規範を発信する。

### 2.2. 比喩から導かれる設計原則

第一原則として、**作家は出版社と直接話さない**。創作組織の鉄則で、編集が緩衝材になることで作家を制度的圧力から守る。実装上、Director の機械的指示を Writer に直接渡さず、Editor が情景的指示に翻訳する。

第二原則として、**編集は作家の文体を尊重し書き直さない**。Editor は文章を直接編集せず、フィードバックを生成して Writer に再生成させる。これを破ると Dense の利点である「声の一貫性」が崩壊する。

第三原則として、**出版社は個別シーンを読まない**。Director には構造化された state（章番号、回収済み伏線、感情カーブ、文字数）だけを渡し、本文は Editor が要約してから流す。

第四原則として、**Critic は別人格・別モデルファミリーで実装**。作家・編集と同じモデル系統だと評価が甘くなるため、Writer に Qwen 系を使ったなら Critic は Gemma 系、のようにクロスする。

第五原則として、**編集会議という機構を組み込む**。章の切れ目で Editor・Director・Critic が作家不在で議論し、矛盾する要求を組織内で解消してから作家に渡す。これがシングルエージェント制御より優れた点。

---

## 3. 既存事例の地図

調査の結果、各部品はすべて先行例が存在することが判明した。

**学術系**として、CreAgentive（arXiv 2509.26461, 2025年9月）が最も近い構造。三段階エージェントワークフロー（初期化・生成・執筆）と Story Prototype（ジャンル非依存のナレッジグラフ）を中核に持ち、100章あたり$1未満で千章規模を安定生成。CREA（NeurIPS 2025）は画像生成側で Creative Director を含む5エージェント構成。Multi-Agent Based Character Simulation for Story Writing（ACL 2025）はキャラクター単位でエージェント化する系統。

**実務系**として、r/ClaudeAI の「Multi-Agent Editorial Team for Novel Writing」投稿（2025年12月）が組織モデルとほぼ同型の構成を実装。Claude が起草、Gemini が編集、7体並列 Reviewer Agents、Revision Agent で統合。「異なるモデルは異なる強みを持つ」「ハイブリッドな文体崩壊を避けるため作家と編集を別モデルにする」という結論は、本議論の原則と完全に一致。

**フレームワーク**として LangGraph（グラフベース制御）、CrewAI（ロールベース）、AutoGen（会話駆動）が三大基盤。明示的状態遷移を組むなら LangGraph、組織比喩との親和性なら CrewAI。

ただし、以下の組み合わせは既存事例に見当たらず、独自性のある領域として残されている。第一に作家層に意図的に Dense uncensored を据える設計、第二に Dense と MoE の機能的役割分担をアーキテクチャ特性に基づいて設計に組み込むこと、第三に「出版社」層を編集とも作家とも独立した規範発信主体として実装すること。

---

## 4. モデル選定の確定

### 4.1. 作家層：Dense uncensored

**Qwen3.6 27B**（Apache 2.0、Dense、24GB VRAM 一枚で量子化版が動く）と **Gemma 4 31B Dense**（Google、マルチモーダル対応）の両方が候補。Qwen3.6 シリーズには 35B-A3B の MoE 派生もあるが、本家 27B は正規の Dense として確定。Gemma 4 のラインナップは 26B が MoE、31B が Dense という珍しい設計で、両アーキテクチャを揃えている。

abliterated 版として、Qwen3.6 27B は huihui_ai と AEON-7 から複数派生。Gemma 4 31B Dense の abliterated はリリースから日が浅く派生がまだ揃っていない可能性。現時点の派生エコシステムの厚みから、**最初の実装は Qwen3.6 27B abliterated** を推奨。マルチモーダル要件が出てきたら Gemma 4 31B へ。

商用化視野なら Qwen 系の Apache 2.0 が安全で、Gemma は Google 独自ライセンスで用途制限あり。

### 4.2. 編集層：DeepSeek V4 Pro Max

2026年4月24日リリース。1.6T 総パラメータ・49B アクティブの MoE、1M トークンコンテキスト、MIT ライセンス。自己ベンチでは GPT-5.2 や Gemini-3.0-Pro を上回り、GPT-5.4 / Gemini-3.1-Pro にやや劣る位置づけ。価格は入力 $1.74、出力 $3.48 per 1M でフロンティア級では破格。

1M コンテキストにより、長編一冊（通常10万語=約20万トークン）が編集の単一コンテキストに収まる。これは「出版社は個別シーンを読まない、編集は全体を読む」という原則を理論的綻びなく実装できることを意味する。

注意点として、フロンティア級モデルを編集に置くと書き直したくなりすぎる傾向がある。プロンプトで「書き直しはしない、差し戻しと方向提示のみ」を厳格に縛る必要がある。

### 4.3. ハーネス層：Hermes Agent

Nous Research による自己改善エージェント。GitHub NousResearch/hermes-agent。経験からスキルを生成し、使用中に改善、セッション間で知識を蓄積する学習ループを内蔵。サブエージェントの spawn と並列ワークストリーム、execute_code による Programmatic Tool Calling、Honcho による dialectic user modeling、SOUL.md でペルソナ規定、Context Files でプロジェクト規範の発信。OpenRouter 経由で任意の endpoint を叩ける。

「出版社が過去刊行物の経験を蓄積して新人作家に渡す」モデルと驚くほど合致する。創作特化のワークフローは自分で書く必要があり、Skills System で創作用スキル（伏線管理、感情曲線追跡、章間整合性チェック）を自作してインストールする想定。

---

## 5. 既存実装レビュー：tc-newsflow

### 5.1. プロジェクト概要

Go 製の CLI/TUI。RSS、GitHub Releases/Tags/Advisories、npm/PyPI/Crates、NVD などを束ね、LLM に「ニュース番組の編集者」として並べ替え・台本化させる。Bubble Tea でフロー可視化、Ollama 互換レイヤー、フォールバック層を持つ。

### 5.2. 評価できる点

役割分離が綺麗で、developer_news_rank.go の topic judge が編集者（スコアリングと tone 判定）、developer_news_script.go が作家、runner.go のステージ進行管理が出版社のワークフローという三層が見える。

arrangeDeveloperNewsArc で hard_negative を冒頭、constructive を中盤、bright を末尾に置く三幕構成は、組織としての編集判断をコードに落とした教科書的実装。

Ollama 互換レイヤーが整備されており、ローカル Dense uncensored モデルをそのまま接続できる。isOllama() で base URL から自動判定、applyCompatibilityOptions で reasoning_effort=none と think=false を強制。

TUI のフロー可視化（runFlowGrid、runRankingBoard）が編集判定の各段階をリアルタイムで見せる。Hermes Agent のようなブラックボックスに対する透明性の利点。

フォールバックの厚みとして、LLM 出力が要件を満たさない場合にテンプレートベースの日本語スクリプトに置き換える二重防御。shouldRewriteDeveloperNews で再生成判定、finalizeDeveloperNewsScript で出典行を機械的に剥がす。

developer_news_script.go の contract レイヤーは出版社のスタイルガイドそのもの。Hook/Insight/Action の三段構成を契約・最終指示・テンプレートの三層で刷り込み、禁止語リストが具体的、フォーマット間（news-script/podcast/article）の差分が思想的に一貫している。

### 5.3. 改善余地

**dedupe.go の O(n²)**。append([]string{key}, ...) で先頭追加しているが、MaxSeen=2000 で大量処理する場合のボトルネック。末尾追加に変えるか、set+slice の二重構造へ。

**removeRankedDeveloperNewsTopic の破壊性**。append(entries[:index], entries[index+1:]...) が裏側配列を書き換える。現状は呼び出し元でコピーしているが、関数のシグネチャから破壊性が見えない。

**プロンプトの長大化**。同じ趣旨の指示が3〜4回繰り返されている。Qwen3.6 27B には効くが、賢いモデル（DeepSeek V4 Pro Max など）には過剰で、「言われすぎて萎縮した」出力を招く。PromptStrictness 設定で strict/balanced/light を切り替える設計を提案。

**isDeveloperNewsWorkflow の判定が広すぎる**。wf.Agent.Enabled=true で問答無用で発火。将来的に別ジャンル agent を追加する時に衝突する。Workflow.Genre フィールドで明示する設計へ。

**extractJSONObject の堅牢性**。strings.Index 切り出しは文字列中の [] で誤動作。encoding/json.Decoder で最初の有効値だけ読む方が正確。Qwen 系 abliterated は JSON 前後に余計な思考を出しがち。

**Critic が決定的ルールのみ**。shouldRewriteDeveloperNews は速いが文体の質は判定できない。「Markdown ではないが無味乾燥」「禁止語は使っていないが Insight が薄い」を検出できない。LLM critic を editor MoE で挟む価値あり。

**fallback テンプレートの硬さ**。「今日のニュースです。影響の大きい動きから〜」が完全固定で、毎日同じ枕詞が出る。3〜5パターン乱択で揺らぎを足すと体験が向上。

**プロンプトのバージョニング不在**。これだけ精緻な contract は A/B テスト単位として管理する価値があるが、ソースコード直書きなので過去版に戻せない。YAML 外出しを検討。

### 5.4. 拡張提案

第一に**作家と編集を別 LLM プロファイルに分離**。wf.LLM.Editor（MoE、DeepSeek V4 Pro Max）と wf.LLM.Writer（Dense uncensored、Qwen3.6 27B abliterated）。judgeDeveloperNewsTopics は editor を、最終ドラフト生成は writer を呼ぶ。コード変更量は小さく、思想がそのまま設定ファイルに現れる。

第二に**Critic ノードの追加**。shouldRewriteDeveloperNews 通過後に LLM ベース Critic を呼び、{ score: 0-100, reasons: [...] } を返させて 70 未満なら rewrite。ハードルールと美学判断の二段に。

第三に**章間整合性の RAG**。過去の生成原稿をベクトル化保存し、「前回触れたトピックの続報か」を検出。日次配信なら「昨日触れた CVE-X の続報です」と作家に教えるだけで連続性が劇的に上がる。

---

## 6. プロジェクトの真の目的：AIポッドキャスト局

### 6.1. 三番組の構成

**ニュース番組**。事実の翻訳作業で、創造性より正確性と構造が要る。現行コードの延長線上、Instruct モデル＋強い contract が最適。発散させない方が良いジャンル。

**雑談番組**。間と崩れが命で、構造を持ちすぎると死ぬ。「えーと」「いや待って、それさっき言ってたやつと違うくない？」のような冗長性と脱線が魅力。Hook/Insight/Action を入れた瞬間に「ポッドキャストっぽい AI」になる。Dense モデルが効く領域で、二人の話者を別エージェントとして独立にプロンプトする Multi-Agent 構造。uncensored 寄りが望ましい（毒のある冗談、本音の愚痴のため）。

**ボイスドラマ**。感情の振れ幅が命で、ニュース・雑談以上にタブー領域に踏み込めないと作品にならない。怒り、欲望、絶望、性的緊張、死。abliterated Dense モデルが本当に必要になるのはここで、ニュース・雑談では over-engineering 気味。長期一貫性も要るため、character RAG と外部状態管理が必須。

### 6.2. 共通基盤と分岐の設計

出版社（ハーネス）は三番組共通でスケジュール・公開先・シリーズ整合性を管理。編集者（MoE Instruct）もジャンル横断で機能。作家（Dense）のみジャンルで分岐：

ニュース作家は OpenAI/Qwen Instruct で十分（uncensored はむしろ事実曲解の傾向が出るため不要）。雑談作家は Qwen3.6 27B abliterated 級の uncensored Dense、話者ごとに別 context。ドラマ作家は最強の uncensored が必要で、Qwen3.6 27B abliterated か Gemma 4 31B abliterated（マルチモーダル要件次第）。

### 6.3. 音声化レイヤーの存在

ポッドキャストである以上、最終出力は音声。これは設計上の最大の制約。声の確保（雑談で二人分、ドラマで登場人物分）、TTS フレンドリーな台本生成、話者切り替えと感情タグの扱いがすべて必要になる。

「作家は普通に書き、editor が TTS 用に書き直す」二段構成が推奨。台本形式に話者ラベルと感情タグを構造化し、editor が pre-processing で TTS パラメータに展開する。

### 6.4. 段階的ロードマップ

第一段階は**ニュース**を完パケで仕上げる。なぜならニュースは既に動いていて、ドラマは音声化を含めると沼が深く、ニュースで詰まる泥臭い部分（タイミング合わせ、ラウドネス、配信先要件差）は他ジャンルでも同じだから。

第二段階は**雑談**。ニュースの基盤を流用しつつ、Multi-Agent 二話者構成と uncensored Dense を導入。

第三段階は**ボイスドラマ**。character RAG、長期プロット管理、Hermes Agent Skills の本格活用。

第四段階で三番組統合・相互参照・配信統合まで含めた「AIポッドキャスト局」として完成。

---

## 7. ニュース完パケ化の設計

### 7.1. 完成形

news run daily 一発で、台本生成に加えて以下が生成される：完パケ音声ファイル（mp3/m4a）、YouTube アップロード用動画（mp4、静止画＋ビジュアライザ）、Discord 投稿用メッセージ。必要なら自動アップロードまで走る。

完パケ構造は AM ラジオ的伝統フォーマット：イントロジングル（5秒）→ オープニングナレーション（BGM フェードイン）→ トピック1（BGM bed）→ トランジションスティンガー（2秒）→ トピック2 → トランジション → トピック3 → クロージング（BGM フェードアウト）→ アウトロジングル（5秒）。

### 7.2. 追加レイヤー設計

**Asset 層**。jingle、BGM、transition、SE を管理。assets/news/intro.wav、bgm_calm.wav、bgm_serious.wav、transition_short.wav のような配置。BGM はトピックの tone（hard_negative/constructive/bright）で切り替え、既存の編集判定が音響演出に直結する。

**TTS 層**。話者→声→音声ファイル変換を抽象化（次節で詳述）。

**Mixing 層**。台本に従って音声と Asset を時間軸に並べ、ラウドネス正規化と書き出し。Go から ffmpeg を shell out で叩く。セグメントごとに個別 wav にレンダリングし最後に concat する方が制御しやすい。ラウドネスは loudnorm フィルタで -16 LUFS（YouTube）か -14 LUFS（Spotify）に揃える。

**Render 層**。動画生成。ffmpeg -loop 1 -i thumbnail.png -i final.mp3 -c:v libx264 -tune stillimage -shortest output.mp4 で静止画＋音声→mp4。波形ビジュアライザは showwaves フィルタで。

**Publish 層**。YouTube Data API v3（OAuth 必要）、Discord は Webhook（25MB 制限、10分 192kbps mp3 で約 14MB なので無料枠内）。将来的にポッドキャスト配信プラットフォーム（Spotify、Apple Podcasts）も RSS 2.0 + iTunes 名前空間で自前ホスティング。

### 7.3. 構造化台本の必要性

現在の台本はプレーンテキスト。音声化には構造化台本が必須。具体的には JSON 化：

json
{
  "segments": [
    {"type": "intro_jingle", "asset": "intro_v1"},
    {"type": "opening", "voice": "anchor_female", "text": "...", "bgm": "calm", "bgm_volume": 0.15},
    {"type": "transition", "asset": "stinger_short"},
    {"type": "topic", "voice": "anchor_female", "text": "...", "bgm": "serious", "tone": "hard_negative"},
    ...
  ],
  "metadata": {"title": "...", "duration_estimate_sec": 480, "topics_count": 3}
}

LLM に JSON と日本語コピーを同時に書かせると片方が崩れるので、**LLM はプレーンテキスト台本を出し、Go 側でパースして JSON 化**する方が安定する。「まずは、」「続いては、」「最後は、」「以上、今日のニュースでした」のような既知マーカーで segment 境界を検出し、tone は既存の判定結果から引く。現プロジェクトには必要な情報がすでに揃っている。

### 7.4. ディレクトリ構造の拡張

internal/
├── rssflow/        (現状: 台本生成まで)
├── tts/            (新規: エンジン抽象化)
│   ├── engine.go        (interface)
│   ├── irodori.go
│   ├── kokoro.go
│   ├── cosyvoice.go
│   └── fish.go
├── audio/          (新規: 音響処理)
│   ├── normalize.go     (テキスト正規化)
│   ├── segment.go       (台本→音声セグメント分割)
│   ├── mix.go           (ffmpeg ラッパー)
│   └── loudness.go
├── assets/         (新規: jingle/bgm 管理)
│   └── library.go
├── render/         (新規: 動画化)
│   └── video.go
└── publish/        (新規: 配信)
    ├── discord.go
    └── youtube.go

### 7.5. ニュース実装の順序

第一週末で**手作業で1本完パケを作る**。現コード出力を VOICEVOX か Style-Bert-VITS2 にコピペで読ませて wav 化、Audacity でジングル・BGM・トランジションを手で乗せて mp3 書き出し、Discord に貼って聴く。この工程を経ずに自動化すると構造化の判断軸が定まらない。

第二週で**Go から ffmpeg を叩く最小パイプライン**。台本→構造化 JSON→セグメント別 wav 合成→concat→ラウドネス正規化→mp3。news run --produce-audio で output/2026-05-26.mp3 が出るまで。

第三週で**Discord 配信の自動化**。Webhook URL を config 追加、生成完了で Webhook 投稿。

第四週で**YouTube 動画化と自動アップロード**。サムネイル自動生成、ffmpeg で mp4 化、YouTube Data API でアップロード。OAuth トークン管理が一番面倒。

第五週以降で**tone 別 BGM 切り替え、トランジション差し込み、フェード調整**などの音響演出を磨き込み。

### 7.6. 音響演出の本質

ニュース番組の品質は、台本の質よりも音響演出と話速で決まる。聞きやすいラウドネス、適切な間、ジングルと台詞の繋ぎの自然さ、BGM の音量バランス。これは LLM プロンプトでは制御できない、ffmpeg と asset 選定の問題。**ここに時間をかける覚悟があるかが AI ポッドキャスト局の成否を分ける**。

逆に台本は今の品質で十分。完成形を毎朝聴きたくなるかは音響演出にかかっている。

---

## 8. TTS 選定

### 8.1. 候補4モデルの位置づけ

**Irodori-TTS v3**（Aratako/Irodori-TTS-500M-v3、2026年現在最新）が主軸候補として確定。Flow Matching ベース 500M 日本語特化 TTS、Rectified Flow Diffusion Transformer。MIT ライセンス、ローカル動作、48kHz 出力。

**CosyVoice 3**（FunAudioLLM/Fun-CosyVoice3-0.5B-2512）はゼロショット音声クローン特化、Apache 2.0、9言語対応。

**Fish Audio S2 Pro**（fishaudio/fish-speech）は現状最強クラスのマルチリンガル TTS。10M時間の音声、80言語以上。reddit で「best local text-to-speech model, almost perfect Japanese」評。ただしモデルが大きく推論コスト高。

**Kokoro 82M v1.0**（hexgrad/kokoro）は軽量・即応・低コスト。Apache 2.0、82M パラメータで CPU でも回る。

### 8.2. Irodori-TTS v3 を主軸とする根拠

第一に、**日本語専用設計**。多言語 TTS の「日本語もできる」ではなく、llm-jp/llm-jp-3-150m トークナイザで最適化。

第二に、**OpenAI API 互換サーバー**（Aratako/Irodori-TTS-Server）が用意されている。POST /v1/audio/speech 形式で叩け、既存の OpenAIClient 構造を流用して薄いラッパーで統合可能。新クライアントを書く必要がない。

第三に、**絵文字によるスタイル制御**。テキストに 😭 🤧 👂 😮‍💨 🥺 などを埋め込むと感情・スタイル・効果音に反映される。Qwen3-Omni-30B-A3B-Instruct を fine-tune してアノテーション自動生成。Respair 氏の発想がベース。

第四に、**500M という絶妙なサイズ**。Kokoro 82M ほど軽くないが Fish S2 Pro ほど重くもない。RTX 3060 クラスで快適、リアルタイムの1.6倍で合成可能なので日次運用に十分。

第五に、**ゼロショット音声クローン対応**。番組専用の声を作って固定できる。

第六に、**SilentCipher 電子透かし統合**。AI 生成物の出所表示が重要視される文脈でプラス。

第七に、**MIT ライセンス**。商用利用可、改変可。

### 8.3. Irodori-TTS v3 の弱点

漢字読み精度が同サイズ他モデルに比べて弱いと公式に明記。複雑な漢字は事前にひらがな・カタカナ変換が必要で、ニュース用途では固有名詞・新語が多いため**読み仮名辞書の整備が前提**。

絵文字制御の効きがコンテキスト依存で常に一貫しない。本番運用では生成結果を聴いてフィードバック調整するフェーズが半年は必要。

男性アンカーの声がデモを聴く限り女性声に比べてやや弱い印象。男女ペアなら男性声は別モデル併用視野。

まだ若いプロジェクトで Aratako 氏個人の開発。コミュニティが Fish や CosyVoice ほど大きくない。

### 8.4. ジャンル別 TTS 戦略

メインエンジンは Irodori-TTS v3。サブエンジンとして Kokoro 82M を fallback・英語固有名詞用に。将来的に Fish S2 Pro をボイスドラマの「特別回」用に投資。CosyVoice 3 は声クローン用（自分の声で番組、声優ライセンス取得時など）に温存。

### 8.5. モデル非固定化の設計原則

TTS 進化は半年〜1年スパンで連続して起きており、今日のベストが3ヶ月後にも最適である保証はない。よって TTS 層は**インターフェース抽象化が最重要**。

go
type TTSEngine interface {
    Synthesize(ctx context.Context, req SynthesisRequest) (SynthesisResult, error)
    Voices(ctx context.Context) ([]Voice, error)
    Name() string
    Capabilities() Capabilities
}

設定で engine を選択、モデル更新時はアダプタを書き換えるだけで台本生成や ffmpeg 合成のレイヤーは無傷。

エンジン横断で必要な周辺処理として、テキスト正規化（数字・英単語の読み統一）、SSML 風タグ解釈（間の挿入）、長文分割、ピッチ・速度の事後調整（ffmpeg atempo）も抽象化レイヤーに置く。

### 8.6. 絵文字注釈レイヤー（Irodori 固有の設計余地）

現プロジェクトの tone 判定結果を絵文字注釈に変換して台本に機械的に挿入する後処理層。hard_negative には 😟 😔 系、constructive には 🤔 💡 系、bright には ☺️ ✨ 系。

台本生成段階では絵文字を入れず、TTS 前処理段階で挿入する設計が制御しやすい。contract に書く話ではなく、コードで決定的に挿入する後処理として実装。「各トピック1〜2個」「文末に置く」のような制約を持たせる。

---

## 9. 直近の実装着手候補

### 9.1. 短期（今週〜来週）

選択肢A：**絵文字注釈レイヤーの設計と実装**。tone 判定結果から絵文字を機械的に挿入する Go 関数 annotateWithEmojis(script, judgments) を実装。Irodori EMOJI_ANNOTATIONS.md を参照してニュース用途で使える絵文字を選別する作業を一回行う。

選択肢B：**Irodori-TTS-Server の起動と Go クライアント実装**。Docker か直接 Python でローカル起動、<http://localhost>:8000/v1/audio/speech で叩けることを確認、internal/tts/irodori.go に OpenAIClient ベースの薄いラッパー。

選択肢C：**手作業で1本完パケを作る**。VOICEVOX か Style-Bert-VITS2 でコピペ TTS、Audacity で手動編集、Discord に貼って聴く。構造化の判断軸を体験から得る工程。

### 9.2. 中期（2〜4週）

ffmpeg ミキシングパイプライン（internal/audio/mix.go）、構造化台本パーサ（internal/audio/segment.go）、Discord Webhook 配信、YouTube 動画化と自動アップロード。

### 9.3. 長期（数ヶ月）

tone 別 BGM 切り替え・音響演出の磨き込み、雑談番組（Multi-Agent 二話者構成、uncensored Dense 導入）、ボイスドラマ（character RAG、Hermes Agent Skills 活用、Fish S2 Pro 検討）、三番組統合とポッドキャスト配信プラットフォーム対応。

---

## 10. 結論

抽象的な「AIの創造性とハーネス」の議論から始まったが、実体は**実用的な AI ポッドキャスト局の構築**だった。組織比喩（作家・編集・出版社）は単なる比喩ではなく、Dense uncensored × MoE × 自律エージェントという 2026年のオープンソース AI スタックを統合する設計原理として機能する。

既に動作している tc-newsflow が組織モデルの一部を実装しており、これに音声化・配信レイヤーを足すことでニュース番組として完成させる。雑談・ドラマへの拡張は、ニュースで音響演出と配信パイプラインを完成させた後の段階的展開。

TTS は Irodori-TTS v3 を主軸とし、エンジン抽象化レイヤーで他モデル（Kokoro、Fish、CosyVoice）を差し替え可能にする。絵文字注釈レイヤーが既存 tone 判定との接続点になる。

次の一歩は、絵文字注釈レイヤーか、Irodori サーバー統合か、手作業完パケ体験か、いずれか一つから着手する。

第4.2項（編集層）への追記: DeepSeek V4 Pro の 75% 値下げが2026年5月31日付で恒久化決定。当初の promotion 価格（input $1.74 / output $3.48 per 1M）がそのまま継続。月額予算計算が安定し、編集層を API のみで運用する前提が現実的に。

第4項に新項目「4.4 編集層の代替候補：Xiaomi MiMo V2.5」を追加: 2026年5月27日に Xiaomi が対抗値下げを発表、最大99% OFF と TokenPlan Credits 5〜8倍増量・既使用分リセット。日次定常運用にサブスクモデルが適合。日本語性能の実測検証が必要だが、編集層の有力な代替候補として保留。

第10項（結論）への追記: AI モデル価格戦争が2026年5月時点で本格化。プロジェクトの設計原則として、TTS だけでなくLLM プロバイダも抽象化レイヤーで切り替え可能にする方針を追加。OpenAI 互換 API を最大公約数として、DeepSeek・MiMo・Qwen・Ollama を LLMProfile 単位で並走。

どう思うこれ
Worked for 5 分

以下に、追加された内容への所感と補足情報をまとめます。引用はニュース報道や公式発表から得ています。

DeepSeek V4 Pro 75％値下げの恒久化
DeepSeekは2026年5月23日の声明で、フラッグシップモデル「V4‑Pro」のAPI料金を75％値下げしたまま恒久化すると発表しました。これにより価格帯は入力キャッシュヒット時0.003625ドル／100万トークン、通常0.87ドル／100万トークン程度まで下がり、従来の0.0145〜3.48ドルから大幅に割安になりました。ロイターも、中国DeepSeekがAPI価格を0.025〜6元／100万トークン（約0.0035〜0.83ドル）に引き下げたと報じています。
この恒久化により、予算計画の見通しが良くなり、編集層をAPI運用前提にする判断がより現実的になりました。ただし、DeepSeekは中国国内の算出拠点で運用しているため、法規制や海外接続遅延への備えが必要です。
Xiaomi MiMo V2.5 系列の代替候補
Xiaomi MiMoオープンプラットフォームは2026年5月27日0:00（CST）付で、MiMo‑V2.5系モデルのAPI料金を最大99％まで引き下げると発表しました。今回の価格改定では入力長による料金差を廃止し、旧料金比で大幅に下がる点を強調しています。
また、Token Plan（サブスクリプション）のクレジット枠を従来の5～8倍に拡大し、現在有効なToken Plan利用者の使用済みクレジットをリセットすることも発表しています。効果発生日もDeepSeekと同じ5月27日で、事実上DeepSeekの値下げに対抗する動きです。
MiMoシリーズは視覚や音声も扱えるマルチモーダルLLMであり、長文コンテキスト（1Mトークン）にも対応しますが、日本語での指示追従性・編集能力に関する実測データはまだ少ないため、プロジェクトに組み込む前にベンチマークが必要です。
AIモデル価格戦争とアーキテクチャの抽象化
5月末時点でDeepSeekとXiaomiが相次いで大幅な値下げを行ったことから、生成AIプラットフォーム間で激しい価格競争が始まっていることは明らかです。これはプロジェクトにとって好機でもありますが、特定企業に依存し続けるリスクも高まります。
このため、LLMプロバイダを容易に切り替えられる抽象化レイヤー（LLMProfile）の導入は必須です。OpenAI互換APIを共通インタフェースとし、DeepSeek・MiMo・Qwen・Ollamaなど複数のモデルを比較しながら並走させる設計が有効です。こうすることで、価格や性能の変動に応じて最適なモデルを選択できます。
また値下げは多くの場合プロモーション的側面が強く、提供サービスの品質やレート制限は予告なく変更される可能性があるため、運用時にはキャッシュ制御やフォールバックモデルの準備が求められます。
全体的な印象

今回追加された情報は、プロジェクトのコスト構造とモデル選定に直接影響します。DeepSeekの値下げによりAPIのみ運用への移行が現実味を帯び、Xiaomi MiMoは価格とサブスク柔軟性で有力な競合候補となりました。一方で、モデルの日本語性能や安定性の検証がないまま移行するのはリスクが高いので、実際に触ってベンチマークを行い、既存のQwen×MoE構成と比較して判断することが重要です。

情報源
tik-choco-tc-newsflow-8a5edab282632443.txt
ドキュメント
これね
思考時間: 25s

はい。ここで一度ドキュメント化して構造化した方がいいです。
理由は、ここまでで「企画」「要件」「Sprint 1A」「ソース選定」「未検証URL」「設計判断」が混ざり始めています。次に実装へ入る前に、Source Selection Spike v0.1 として独立ドキュメント化するのが正解です。

結論から言うと、A/B/Cへの回答はこうです。

A. リストの方向性はOK。ただしそのまま確定はまだ危険。
特に PingWest /feed は現時点で404を返しているため、初期10本からは外すか代替に回すべきです。机器之心 /rss もRSSではなくログイン導線付きのデータサービスページにリダイレクトされており、実RSSとして使えるかはローカルの feedparser で再確認が必要です。

B. Sprint 1A はAI寄りでよい。
1Aの目的は番組バランスではなく「収集基盤が壊れずに動くか」の検証です。Game/Subculture/Anime は1B以降で足してよいです。ただし、将来的な番組性を考えると、1Aの10本中1本だけでもゲーム/サブカル系を入れておくと、スキーマとカテゴリ集計の検証になります。

C. Hugging Face Daily Papers は初期10本から外す方がよい。
ページ自体は有用で、中国系組織の論文も普通に出ます。実際にTencent、Beijing Institute of Technology、Tsinghua University、ByteDance Seed などがDaily Papers上に表示されています。 ただし、中華圏専門番組の一次ソースではありません。さらに公式RSSが明確に提供されているわけではなく、HFフォーラムでも個人作成のRSSサービスが紹介されている状態です。 したがって、Sprint 1Aでは外し、1B以降に「論文補助ソース」として別枠に置くのが綺麗です。

Source Selection Spike v0.1

## 1. 目的

Sprint 1A の前に、初期収集ソース10本を確定する。

このSpikeの目的は「最良のニュースソースを網羅すること」ではない。目的は、Cookie不要・海外IPから取得可能・RSS/RSSHubで安定取得できる初期ソースを10本選び、収集基盤の検証に使える状態にすることである。

## 2. 判断方針

初期10本は、以下の基準で選ぶ。

Tier1公式を5本。
Tier2ニュースを3本。
Tier3コミュニティを2本。
Cookie必須ルートは含めない。
Playwright、中国IPプロキシ、ログインCookie依存は含めない。
RSSHubルートは使ってよいが、壊れてもfail-openできる前提にする。
AI比率は高めでよい。Game/Subculture/Anime はSprint 1B以降で拡張する。

RSSHubの掘金ルートについては、公式ドキュメント上で /juejin/category/:category があり、ai がカテゴリ値として示されています。したがって <http://localhost>:1200/juejin/category/ai は候補として妥当です。

## 3. A/B/C 判断

A. 現リストの採否

現リストは方向性として正しいが、以下の修正を入れる。

deepseek-github-releases、qwen-github-releases、moonshot-kimi-github、zhipu-glm-github、xiaomi-mimo-github は候補として維持。ただし、GitHub Atom URLはこの環境のブラウザ取得では正しく検証できなかったため、ローカル curl と feedparser で確認する。

jiqizhixin-rss は保留。<https://www.jiqizhixin.com/rss> はRSSとしてではなくデータサービスページへリダイレクトされているため、実取得で使えなければ qbitai やRSSHub経由の別ルートに差し替える。

pingwest-rss は初期候補から外す。<https://www.pingwest.com/feed> は404を返している。

juejin-ai-tag は維持。ただしURLは /juejin/category/ai に修正する。

huggingface-papers-daily は初期10本から外す。中華圏限定ソースではなく、RSSも公式ではないため、1Aではノイズになりやすい。

B. AIに寄りすぎか

Sprint 1Aでは問題ない。むしろAI寄りでよい。

ただし、カテゴリ集計と将来の番組テンプレ検証のため、1本だけ Game/Subculture 系の予備枠を作るのはあり。とはいえ、最初の10本に無理に入れる必要はない。1Aは「取れるか」を見るフェーズで、番組の最終配分は1Bで決める。

C. Hugging Face Daily Papersの扱い

初期10本からは外す。

代わりに、research_context または global_ai_context のような別グループに入れる。1B以降で「中華圏著者・中華圏企業・中国語圏研究機関が含まれる場合のみ採用候補にする」というフィルタを実装する。

## 4. 初期10本 改訂候補

```yaml
sources:
  - id: deepseek-github-releases
    name: DeepSeek GitHub Releases
    url: "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "DeepSeek公式GitHubリリース。単独採用可。ローカル検証必須。"

  - id: qwen-github-releases
    name: Qwen GitHub Releases
    url: "https://github.com/QwenLM/Qwen3/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Alibaba Qwen公式リリース。単独採用可。ローカル検証必須。"

  - id: moonshot-kimi-github
    name: Moonshot Kimi GitHub Releases
    url: "https://github.com/MoonshotAI/Kimi-K2/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Moonshot/Kimi公式リポジトリ。単独採用可。ローカル検証必須。"

  - id: zhipu-glm-github
    name: Zhipu / GLM GitHub Releases
    url: "https://github.com/THUDM/GLM-4/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "GLM系公式/大学発リリース。単独採用可。ローカル検証必須。"

  - id: xiaomi-mimo-github
    name: Xiaomi MiMo GitHub Releases
    url: "https://github.com/XiaomiMiMo/MiMo/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Xiaomi MiMo公式。番組で使うLLMの本家。単独採用可。ローカル検証必須。"

  - id: qbitai-feed
    name: 量子位
    url: "https://www.qbitai.com/feed"
    tier: 2
    category: AI
    enabled: true
    requires_cookie: false
    notes: "机器之心が使えない場合の第一候補。AIニュース中心。ローカル検証必須。"

  - id: jiqizhixin-rss
    name: 机器之心
    url: "https://www.jiqizhixin.com/rss"
    tier: 2
    category: AI
    enabled: false
    requires_cookie: false
    notes: "現時点では/rssがデータサービスページへ遷移するため保留。使える場合のみenabled=true。"

  - id: 36kr-newsflash
    name: 36Kr Newsflash
    url: "https://36kr.com/feed-newsflash"
    tier: 2
    category: Tech
    enabled: true
    requires_cookie: false
    notes: "AI/テック/スタートアップの速報。ノイズが多い場合は後でカテゴリ絞り。ローカル検証必須。"

  - id: huxiu-rss
    name: 虎嗅
    url: "https://www.huxiu.com/rss/0.xml"
    tier: 2
    category: Tech
    enabled: true
    requires_cookie: false
    notes: "PingWest代替。テック・ビジネス寄り。ローカル検証必須。"

  - id: juejin-ai-category
    name: 掘金 AI Category
    url: "http://localhost:1200/juejin/category/ai"
    tier: 3
    category: AI
    enabled: true
    requires_cookie: false
    notes: "RSSHub経由。中国エンジニアコミュニティ。Tier3なので2ソース確認対象。"

  - id: juejin-trending-ai-weekly
    name: 掘金 AI Weekly Trending
    url: "http://localhost:1200/juejin/trending/ai/weekly"
    tier: 3
    category: AI
    enabled: true
    requires_cookie: false
    notes: "RSSHub経由。掘金の週次人気AI記事。通常カテゴリと重複する可能性あり。"
```

注意点として、上は11本あります。jiqizhixin-rss は保留・disabled 扱いなので、enabled=true は10本です。実装上は enabled: false のソースもYAMLに残しておくと、後から切り替えやすいです。

## 5. Spikeで必ず確認すること

確認は1日で終える。やることは3つだけ。

1つ目は、HTTPレベルで応答するか。

```bash
for url in \
  "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom" \
  "https://github.com/QwenLM/Qwen3/releases.atom" \
  "https://github.com/MoonshotAI/Kimi-K2/releases.atom" \
  "https://github.com/THUDM/GLM-4/releases.atom" \
  "https://github.com/XiaomiMiMo/MiMo/releases.atom" \
  "https://www.qbitai.com/feed" \
  "https://36kr.com/feed-newsflash" \
  "https://www.huxiu.com/rss/0.xml" \
  "http://localhost:1200/juejin/category/ai" \
  "http://localhost:1200/juejin/trending/ai/weekly"
do
  echo "=== $url ==="
  curl -L -sI "$url" | head -10
  echo
done
```

2つ目は、feedparser でentryが取れるか。

```python
import feedparser

urls = [
    "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom",
    "https://github.com/QwenLM/Qwen3/releases.atom",
    "https://github.com/MoonshotAI/Kimi-K2/releases.atom",
    "https://github.com/THUDM/GLM-4/releases.atom",
    "https://github.com/XiaomiMiMo/MiMo/releases.atom",
    "https://www.qbitai.com/feed",
    "https://36kr.com/feed-newsflash",
    "https://www.huxiu.com/rss/0.xml",
    "http://localhost:1200/juejin/category/ai",
    "http://localhost:1200/juejin/trending/ai/weekly",
]

for url in urls:
    feed = feedparser.parse(url)
    latest = feed.entries[0].get("published", feed.entries[0].get("updated", "")) if feed.entries else ""
    print(url, "entries=", len(feed.entries), "latest=", latest, "bozo=", feed.bozo)
```

3つ目は、1Aに入れるかどうかの判定。

entries >= 1 なら採用候補。
entries == 0 なら保留。
bozo == 1 でも entries が取れていれば一旦採用可。
HTTP 403/404/timeout は初期候補から外す。
RSSHub系はlocalhostで取れれば採用、本番ではセルフホスト前提。

## 6. この段階でドキュメント化する理由

ここでドキュメント化する理由は、ソース選定が今後の番組品質に直結するからです。

コードはあとから直せますが、ソース選定の思想が曖昧だと、後で「なぜこのネタを拾ったのか」「なぜこのソースを信用したのか」が説明できません。特にこの番組は中国語圏ソースを日本語で翻訳・解説するため、ソースTier、採用条件、噂の扱い、失敗時の挙動を明文化しておく価値が高いです。

## 7. 次の進行

次はこの順番でよいです。

まず、この Source Selection Spike v0.1 を docs/source-selection-spike-v0.1.md として保存する。
次に、ローカルでcurl/feedparser検証を実行する。
その結果を反映して config/sources.yaml の初版を確定する。
その後、Ticket #1 の実装に入る。

つまり、今はまだ pyproject.toml ではなく、docs と sources.yaml の確定が先です。ここを1日で終わらせて、すぐ実装に入るのが一番滑らかです。

要件定義書も作成してください
思考時間: 24s

はい。以下をそのまま docs/requirements-v1.0.md として保存できる形で作成します。
位置づけは、プロジェクト全体の要件定義書 v1.0 です。直後に作る docs/source-selection-spike-v0.1.md や config/sources.yaml は、この要件定義の下位ドキュメントになります。

要件定義書 v1.0
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

### 1.1. 目的

本プロジェクトの目的は、中国語圏の一次情報・準一次情報・コミュニティ情報を収集し、日本語リスナー向けに短時間で理解できるAIポッドキャストとして毎朝届けることである。

特に、英語圏・日本語圏メディアに流れてくる前の、中国AI、中国OSS、中国テック、中国ゲーム、中国サブカルの動きを拾うことを重視する。

### 1.2. 番組コンセプト

日本のオタク・エンジニア・ビジネスマンに向けた、中華圏専門の Discover Daily 形式AIポッドキャスト。

中国語ネイティブの情報源から、まだ英日メディアに流れていないディープでニッチでキャッチーなトピックを、平日朝に5〜10分で届ける。

### 1.3. 番組名

正式名称: 華流テック通信
サブタイトル: HAL Daily Briefing
表記揺れ許容: 華流テック通信 by HAL
キャスター名: HAL

HALは番組から独立したAIキャスター人格として扱う。将来的に別番組へ展開する可能性を残す。

### 1.4. 想定リスナー

主対象は以下。

日本在住のエンジニア。
AI、OSS、ゲーム、サブカルに関心のあるオタク層。
中国語圏の情報を追いたいが、中国語ソースを毎日読む時間がないビジネス層。
日本語メディアに流れてくる前の中国AI・テック情報を早めに掴みたい個人開発者・企画者。

### 1.5. 成功状態

短期的な成功状態は、平日朝に安定して番組台本または音声が生成され、朝の確認工数が5分以内に収まること。

中期的な成功状態は、YouTube限定公開運用から一般公開へ移行し、継続視聴者がつくこと。

長期的な成功状態は、YouTube、Spotify、Apple Podcasts、Note、Xなどへ展開し、中華圏テック・サブカル情報の定点観測メディアとして成立すること。

## 2. スコープ

### 2.1. 初期スコープ

初期スコープは以下。

RSS / RSSHub による情報収集。
SQLiteによる seen 管理、source health 管理、実行ログ保存。
ソースTierに基づく信頼性管理。
収集失敗時の fail-open。
LLMによるトピック選定、スコアリング、アーク配置。
LLMによる日本語Markdown台本生成。
Discord Webhookによる収集サマリー・台本投稿。
TTSによる音声生成。
BGM、ジングル、SEのミックス。
波形ビジュアライザ付き動画生成。
YouTube限定公開アップロード。
AI生成音声であることの明示。

### 2.2. Sprint 1A スコープ

Sprint 1Aでは、LLM、TTS、動画、YouTubeは実装しない。

Sprint 1Aの目的は、ソース定義YAMLからRSS/RSSHubを読み、SQLiteに保存し、seen管理とsource health管理を行い、Discordへ収集サマリーを投稿できる状態を作ることである。

Sprint 1Aの対象は以下。

プロジェクト初期化。
RSSHubセルフホスト用 docker-compose。
sources.yaml の定義。
feedparser/httpxによる取得。
SQLite保存。
source単位fail-open。
source health記録。
Discord Webhookで収集サマリー投稿。
3日間の収集観察。

### 2.3. Sprint 1B スコープ

Sprint 1Bでは、LLMを導入して台本生成まで行う。

対象は以下。

MiMo / DeepSeek のLLM profile設定。
トピック候補のスコアリング。
Tier重み付き選定。
3〜5本の採用トピック選定。
Markdown台本生成。
A/B/C案のLLM役割分担比較。
Discord Webhookによる台本投稿。
音声化なしの番組品質評価。

### 2.4. 初期スコープ外

初期スコープ外は以下。

Playwrightによるスクレイピング。
中国IPプロキシ。
Cookie必須ルートの本格運用。
小红书、微博、知乎のログイン依存収集。
Discord Bot常駐。
リアクション承認フロー。
TTS音声合成。
動画生成。
YouTube自動アップロード。
Spotify / Apple Podcasts申請。
ボイスドラマ。
雑談番組。
Dense uncensoredモデルによる創作番組。
Hermes Agentによる自律運用。

これらはSprint 2以降で段階的に検討する。

## 3. 番組要件

### 3.1. 配信頻度

平日配信を基本とする。

夜23:00 JSTに収集・生成バッチを実行し、翌朝7:00〜7:50に確認する。公開は朝8:00を目標とする。

土日は原則として通常配信しない。将来的に週次まとめ、特別回、実験回を入れる余地は残す。

### 3.2. 尺

基本尺は5〜10分。
最大尺は15分。
初期MVPでは音声化前の台本長から推定尺を算出する。

1トピックあたりの目安は60〜120秒。トピック数は3〜5本。

### 3.3. 話者

初期はAIキャスター「HAL」によるソロ進行。

対話形式、複数話者、パネル形式は初期スコープ外。将来的に雑談番組へ展開する場合に再検討する。

### 3.4. キャスター「HAL」

HALは20代前半、中性的な女性として設計する。声は落ち着いた低めのトーンで、透明感があり、聞き取りやすさを最優先する。

一人称は「ボク」。
基本はニュース読み。
要所で自然な驚きや感心を入れる。
過度なVtuber調、煽り、政治的断定、ナショナリズム表現は避ける。

参照イメージは、緒方恵美、坂本真綾、石川由依、榊原優希の中性的・透明感・低めの方向性。ただし実在声優の声を無断でクローンしない。

### 3.5. トーン

情報の信頼性はNHKニュース寄り。
会話の空気はRebuild.fm / TBS Podcast寄り。
表現は硬すぎず、しかし根拠を曖昧にしない。

番組の基本姿勢は「中国すごい」「日本終わった」ではなく、「中国語圏で何が起きていて、日本側から見ると何が面白いか」を冷静に翻訳・解説すること。

## 4. カバー領域

### 4.1. 優先順位

優先順位は以下。

中国AI
中国AI関連OSS
中国テック
中国ゲーム
中国サブカル
中国OSS非AI
中国アニメ

### 4.2. 初期配分

Sprint 1AではAI寄りでよい。目的は収集基盤の安定性検証であり、番組の最終ジャンルバランスではない。

Sprint 1B以降で、ゲーム、サブカル、アニメ、OSS非AIを徐々に追加する。

### 4.3. 将来の番組内配分

通常回では以下を目標とする。

AI / Tech / OSS: 2
Game / Subculture / Anime: 1

基本テンプレートは以下。

トピック1: AI、モデル、API、価格戦争、研究成果。
トピック2: OSS、開発者ツール、クラウド、スタートアップ。
トピック3: ゲーム、Bilibili、VTuber、サブカル、アニメ、ネット文化。

## 5. 編集ポリシー

### 5.1. ソース優先順位

中国語ネイティブソースを優先する。

英語圏・日本語圏に既に流れている一般ニュースは優先度を下げる。日本語メディアで既出の内容でも、中国語圏ソースに追加情報や現地文脈がある場合は採用可。

### 5.2. 一次情報の扱い

公式・一次情報は単独ソースでも採用可。

対象は以下。

企業公式ブログ。
ラボ公式発表。
GitHub Release。
論文プレプリント。
大学・研究室公式発表。
政府・規制当局の公式発表。
信頼性の高い中華圏ニュースサイト。

### 5.3. コミュニティ情報・噂の扱い

コミュニティ発、未認証情報、噂、リークは単独採用しない。

採用条件は以下。

独立2ソース以上で言及されている。
または、Tier1 / Tier2 ソースで追加確認できる。
または、高信頼アカウントの言及がある。

採用する場合も、「噂レベル」「コミュニティで話題」「未確認」と明示する。

### 5.4. 政治・規制・国際関係の扱い

イデオロギーやナショナリズムには踏み込まない。

ただし、AI規制、ゲーム規制、輸出規制、半導体規制、プラットフォーム規制など、ビジネス・技術への影響が不可分な場合は事実として扱う。

その場合も、番組の主軸は政治評論ではなく「技術・産業・ユーザー体験への影響」に置く。

### 5.5. ネタバレ方針

ゲーム・アニメ本編の重大ネタバレは避ける。

新作発表、売上、運営方針、炎上、イベント、技術的特徴、ファンコミュニティ動向は扱ってよい。

## 6. ソースTier定義

### 6.1. Tier1 公式

定義: ラボ、大学、企業、政府、公式GitHub、公式ブログ、arXiv等の一次情報。

採用条件: 単独採用可。
重み: 最大。
例: DeepSeek公式、Qwen公式、GitHub Release、大学研究室発表。

### 6.2. Tier2 準公式・高信頼メディア

定義: 認証アカウント、高信頼ニュースサイト、業界メディア。

採用条件: 単独採用可。
重み: 高。
例: 36Kr、机器之心、量子位、虎嗅、晚点 LatePost。

### 6.3. Tier3 コミュニティ

定義: 開発者コミュニティ、Bilibili UP主、知乎、掘金、SegmentFault、NGAなど。

採用条件: 独立2ソース、またはTier1/Tier2裏取りが望ましい。
重み: 中。
例: 掘金AIカテゴリ、Bilibili専門UP主、V2EX。

### 6.4. Tier4 噂・未認証

定義: 匿名微博、小红书未認証投稿、リーク系投稿、スクリーンショット由来情報。

採用条件: 原則不採用。採用時は独立2ソース必須かつ「噂」と明示。
重み: 低。

## 7. Source Selection Spike 要件

### 7.1. 目的

Sprint 1Aの前に、初期収集ソース10本を決める。

目的は、最良の情報網を完成させることではなく、収集基盤の検証に使える安定ソースを用意すること。

### 7.2. 初期ソース選定方針

Tier1公式を5本。
Tier2ニュースを3本。
Tier3コミュニティを2本。
Cookie必須ルートは含めない。
Playwright、中国IPプロキシ、ログインCookie依存は含めない。
AI比率は高めでよい。
RSSHubルートは使ってよいが、壊れてもfail-openする。

### 7.3. 初期候補

初期候補は docs/source-selection-spike-v0.1.md で定義する。

初期候補には以下を含める。

DeepSeek GitHub Releases。
Qwen GitHub Releases。
Moonshot Kimi GitHub Releases。
Zhipu / GLM GitHub Releases。
Xiaomi MiMo GitHub Releases。
量子位。
36Kr Newsflash。
虎嗅。
掘金 AI Category。
掘金 AI Weekly Trending。

机器之心 は候補として保持するが、実RSSとして取得できる場合のみ有効化する。
Hugging Face Daily Papers は中華圏限定ソースではないため、Sprint 1Aでは初期10本から外す。

### 7.4. 採用判定

HTTP応答があること。
feedparserで1件以上entryが取れること。
Cookie不要で取得できること。
403、404、timeoutは初期候補から外す。
bozoが立っていてもentryが取れていれば一旦採用可。
RSSHub系はlocalhostのセルフホストで取得できれば採用可。

## 8. 機能要件

### 8.1. 設定管理

FR-001 sources.yaml

システムは config/sources.yaml からソース定義を読み込めること。

各ソースは以下を持つ。

id。
name。
url。
tier。
category。
enabled。
requires_cookie。
notes。

FR-002 環境変数

システムは .env を読み込めること。

初期環境変数は以下。

DISCORD_WEBHOOK_URL。
MIMO_API_KEY。
DEEPSEEK_API_KEY。
ZHIHU_COOKIES placeholder。
RSSHUB_BASE_URL。

Sprint 1Aでは DISCORD_WEBHOOK_URL と RSSHUB_BASE_URL のみ必須。

FR-003 LLM Profile

Sprint 1B以降、config/llm_profiles.yaml でLLM設定を切り替えられること。

MiMo、DeepSeek、OpenRouter、Ollama等を将来的に切替可能にする。

### 8.2. 収集

FR-010 RSS取得

システムはRSS/Atomフィードを取得できること。

feedparserで各entryを内部形式に正規化する。

FR-011 RSSHub取得

システムはRSSHubセルフホスト経由のURLを取得できること。

RSSHubの一部ルートが失敗しても、他ソースの取得を継続する。

FR-012 タイムアウト

各ソース取得は30秒以内にタイムアウトする。

FR-013 リトライ

取得失敗時は最大2回リトライする。

FR-014 User-Agent

HTTPリクエストには明示的なUser-Agentを付与する。

例: karyu-tech-news/0.1

### 8.3. 正規化

FR-020 RawItem

取得結果はRawItemに正規化する。

RawItemは以下を持つ。

item_key。
external_id。
title。
link。
summary。
published_at。
fetched_at。
source_id。
raw_json。
canonical_url_hash。

FR-021 item_key

保存前に必ず空でないitem_keyを生成する。

優先順位は以下。

external_id。
link。
hash(title + published_at + source_id)。

FR-022 canonical_url_hash

同じURLが複数ソースから来た場合に備え、canonical_url_hashを保持する。

ただしSprint 1Aではクロスソース重複排除には使わない。Sprint 1B以降の重複検出・裏取り検出に使う。

### 8.4. 永続化

FR-030 SQLite

システムはSQLiteに状態を保存する。

DBファイルは data/state.db。

FR-031 items テーブル

itemsテーブルは取得アイテムを保存する。

UNIQUE制約は UNIQUE(source_id, item_key) とする。

hash 単体にUNIQUEを張ってはならない。

FR-032 sources テーブル

sourcesテーブルはソース定義を保存または同期する。

FR-033 source_health テーブル

source_healthテーブルは各ソースの健全性を記録する。

保持項目は以下。

source_id。
last_success_at。
last_failure_at。
consecutive_failures。
last_error。

FR-034 collect_runs テーブル

collect_runsテーブルは収集実行単位の記録を保存する。

保持項目は以下。

started_at。
finished_at。
total_sources。
successful_sources。
failed_sources。
total_items。
new_items。

### 8.5. dedupe / seen管理

FR-040 ソース単位seen

同じsource_idとitem_keyの組み合わせは重複保存しない。

FR-041 クロスソース重複

異なるソースから同じURLが来た場合、Sprint 1Aでは別レコードとして扱う。

Sprint 1B以降、canonical_url_hashにより同一ネタ検出を行う。

FR-042 古いアイテム削除

90日以上前のitemは、将来的に定期削除対象とする。

Sprint 1Aでは必須ではない。

### 8.6. source health

FR-050 成功時更新

取得成功時、last_success_atを更新し、consecutive_failuresを0に戻す。

FR-051 失敗時更新

取得失敗時、last_failure_atを更新し、consecutive_failuresを1増やし、last_errorを保存する。

FR-052 連続失敗通知

consecutive_failuresが3以上になったソースはDiscord収集サマリーで警告表示する。

### 8.7. fail-open

FR-060 ソース単位fail-open

1つのソース取得が失敗しても、パイプライン全体を止めない。

FR-061 最低トピック数

Sprint 1B以降、候補トピックが3本未満の場合、エピソード生成をスキップする。

Sprint 1Aでは収集サマリーのみなので、最低トピック数判定は参考値として扱う。

### 8.8. Discord投稿

FR-070 Webhook投稿

システムはDiscord Webhookへ収集サマリーを投稿できること。

FR-071 投稿失敗時

Webhook投稿が失敗しても収集処理は失敗扱いにしない。ログにのみ記録する。

FR-072 添付

Sprint 1Aでは添付ファイルは扱わない。Markdown本文投稿のみ。

Sprint 2以降、mp3/mp4添付またはR2/S3等への外部保存リンク投稿を検討する。

### 8.9. LLM編集・台本生成

Sprint 1B以降の要件。

FR-080 トピックスコアリング

LLMは候補アイテムをスコアリングし、3〜5本を選定できること。

評価軸は以下。

重要度。
新規性。
中華圏らしさ。
日本リスナーへの関係性。
ソースTier。
裏取り状況。
番組アーク上の配置。

FR-081 アーク配置

番組は以下の流れを基本とする。

重要ニュース。
技術・産業的な深掘り。
前向きまたは面白い話題。

FR-082 台本生成

LLMは日本語Markdown台本を生成する。

台本は Hook / Insight / Action を含む。

FR-083 LLM A/B/C検証

初期は以下を比較する。

A案: MiMo Editor → DeepSeek Writer。
B案: MiMo Editor → MiMo Writer。
C案: DeepSeek Editor → MiMo Writer。

評価項目は以下。

採用率。
修正回数。
読み上げ自然さ。
コスト。
JSON安定性。
台本のAI要約臭。

### 8.10. TTS・音声化

Sprint 2以降の要件。

FR-090 TTS抽象化

TTSエンジンを抽象化し、Irodori、Style-Bert-VITS2、AivisSpeech、CosyVoice等を差し替え可能にする。

FR-091 HAL音声

HALの声はTTS非依存のキャラクター定義として管理する。

Irodori-TTSのVoiceDesign → Speaker Inversion固定化は検証項目であり、確定仕様ではない。

FR-092 読み仮名辞書

固有名詞の読みを制御する辞書を用意する。

対象は、中国企業名、中国モデル名、中国人名、ゲーム名、アニメ名、地名。

### 8.11. 音響合成

Sprint 2以降の要件。

FR-100 BGM

Lo-fi + 中華風アンビエントBGMを薄く敷く。

FR-101 ジングル

オープニング、トランジション、エンディングのジングルを扱う。

FR-102 ラウドネス

mp3出力時に聞きやすいラウドネスへ正規化する。

FR-103 ファイル形式

初期音声形式はmp3 192kbpsを想定する。

### 8.12. 動画生成

Sprint 2以降の要件。

FR-110 静止画動画

番組ロゴと音声を組み合わせた動画を生成する。

FR-111 波形ビジュアライザ

ffmpeg showwaves等で簡易波形を表示する。

FR-112 mp4出力

YouTube投稿用にmp4を生成する。

### 8.13. YouTube配信

Sprint 2以降の要件。

FR-120 限定公開

初期2週間はYouTube限定公開で運用テストする。

FR-121 AI開示

AI音声キャスターを使用していることを動画説明欄に明記する。

例: 「本番組はAI音声キャスターHALによる自動生成番組です。」

FR-122 自動アップロード

将来的にYouTube Data APIで自動アップロードする。

Sprint 1A/1Bでは実装しない。

## 9. 非機能要件

### 9.1. メンテナンス性

Python 3.11+で統一する。

Go実装のtc-newsflowからは設計思想のみ継承する。2言語構成にはしない。

依存関係は最小限にする。

### 9.2. 持続可能性

個人運用を前提にする。

朝の確認工数は最終的に5分以内を目標にする。

失敗時に原因が追えることを重視する。

### 9.3. 耐障害性

ソース単位でfail-openする。

Webhook失敗で収集を止めない。

LLM失敗時はリトライし、将来的に別profileへフォールバックする。

TTS失敗時は文単位でリトライする。

### 9.4. 観測可能性

全実行ログを保存する。

source_healthを保存する。

collect_runsを保存する。

Sprint 1B以降はLLM入出力、スコア理由、採用理由を保存する。

### 9.5. セキュリティ

APIキー、Webhook URL、Cookieは .env で管理する。

.env はgit管理しない。

.env.example のみgit管理する。

### 9.6. 法務・規約対応

中国メディア記事の本文転載は禁止する。

出力は要約とHAL自身の解説にする。

BGM/ジングルは商用利用可能素材、または自前生成素材を使う。

YouTube等のAI生成コンテンツポリシーはフェーズ移行時に確認する。

### 9.7. コスト

月額目安は1,500〜3,000円。

上限予算は月1万円以内。

ローカルGPUを基本とし、クラウドGPUは初期不要。

## 10. 技術構成

### 10.1. 実装言語

Python 3.11+。

### 10.2. 主要ライブラリ候補

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

### 10.3. 実行環境

Windows 11。
Intel Core i7 / i9クラス。
RTX 4070 Ti Super。
128GB RAM。
Docker Desktop。
RSSHubセルフホスト。

### 10.4. リポジトリ構成

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

## 11. CLI要件

### 11.1. Sprint 1A CLI

Sprint 1Aで必要なCLIは以下。

python -m karyu_tech_news --help
python -m karyu_tech_news init-db
python -m karyu_tech_news validate-sources
python -m karyu_tech_news collect
python -m karyu_tech_news post-summary

### 11.2. Sprint 1B CLI

Sprint 1B以降で追加するCLIは以下。

python -m karyu_tech_news draft --date today
python -m karyu_tech_news post-discord --date today
python -m karyu_tech_news evaluate --date today

### 11.3. Sprint 2以降 CLI

Sprint 2以降で追加するCLIは以下。

python -m karyu_tech_news synthesize --date today
python -m karyu_tech_news mix --date today
python -m karyu_tech_news render-video --date today
python -m karyu_tech_news upload-youtube --date today

## 12. データベース要件

### 12.1. items

itemsは取得済み記事・リリース・投稿を保存する。

主なカラムは以下。

id。
source_id。
item_key。
external_id。
title。
link。
summary。
published_at。
fetched_at。
raw_json。
canonical_url_hash。

制約は以下。

UNIQUE(source_id, item_key)。

### 12.2. sources

sourcesはソース定義を保存する。

主なカラムは以下。

id。
name。
url。
tier。
category。
enabled。
requires_cookie。
notes。

### 12.3. source_health

source_healthは各ソースの状態を保存する。

主なカラムは以下。

source_id。
last_success_at。
last_failure_at。
consecutive_failures。
last_error。

### 12.4. collect_runs

collect_runsは収集実行の結果を保存する。

主なカラムは以下。

id。
started_at。
finished_at。
total_sources。
successful_sources。
failed_sources。
total_items。
new_items。

### 12.5. future tables

Sprint 1B以降で追加候補。

topic_candidates。
episode_drafts。
llm_runs。
script_versions。
episode_assets。
publish_jobs。

## 13. 運用フロー

### 13.1. Sprint 1A 運用

23:00 JSTにcollectを実行する。

処理は以下。

sources.yaml読み込み。
enabled=trueのソースのみ取得。
各ソースのFetchResult生成。
RawItem正規化。
SQLite保存。
source_health更新。
collect_runs保存。
Discord収集サマリー投稿。

### 13.2. Sprint 1B 運用

23:00 JSTにcollectを実行する。
23:05 JSTにdraftを実行する。
DiscordにMarkdown台本を投稿する。
翌朝に人間が確認する。

### 13.3. Sprint 2 運用

23:00 JSTに収集・台本生成・音声化・動画化まで行う。
翌朝7:00〜7:50に確認する。
8:00に限定公開または公開する。

## 14. Discord投稿要件

### 14.1. Sprint 1A サマリー形式

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

### 14.2. Sprint 1B 台本投稿

投稿内容は以下。

番組タイトル。
生成日時。
採用トピック一覧。
Markdown台本。
ソース一覧。
LLM profile。
推定尺。
注意事項。

## 15. Sprint計画

### 15.1. Sprint 1A

目的: 収集基盤を作る。LLMは使わない。

期間: 5〜10日。

チケットは以下。

プロジェクト初期化とCLIスケルトン。
sources.yamlスキーマと初期ソースリスト。
RSS/RSSHub取得モジュール。
SQLiteスキーマと永続化層。
seen管理とdedupe。
source health管理。
fail-open統合テスト。
Discord Webhookサマリー投稿。
3日連続収集観察。

順番は、#8を#9より先に実装する。観察期間中にDiscordへサマリーが届く状態にする。

Sprint 1A DoD

python -m karyu_tech_news collect が完走する。
10本前後のソースを取得できる。
一部ソースが失敗しても全体が止まらない。
SQLiteにitemsが蓄積される。
同じソースを2回collectしても重複登録されない。
source_healthが更新される。
Discordに収集サマリーが届く。
3日連続で動作する。

### 15.2. Sprint 1B

目的: LLMで台本を作る。音声化はしない。

期間: 5〜7日。

チケット候補は以下。

LLM profile定義。
MiMo / DeepSeek接続確認。
候補アイテム抽出。
Tier重み付きスコアリング。
3〜5トピック選定。
Markdown台本生成。
A/B/C比較ログ保存。
Discord台本投稿。
3日間の台本品質観察。

Sprint 1B DoD

3〜5本のトピックが選ばれる。
Markdown台本が生成される。
ソース一覧が付く。
A/B/CのどのLLM構成で生成したか記録される。
Discordに台本が投稿される。
人間が読んで「音声化する価値がある」水準に近づいている。

### 15.3. Sprint 2

目的: 音声化する。

対象は以下。

TTS抽象化。
Irodori-TTS接続。
文単位合成。
固有名詞読み辞書。
mp3生成。
BGM/ジングル仮ミックス。
Discordへmp3またはリンク投稿。

### 15.4. Sprint 3

目的: 配信ワークフローを作る。

対象は以下。

波形動画生成。
YouTube限定公開アップロード。
AI音声開示文言。
朝確認フロー。
必要ならDiscord Bot化。

## 16. 未確定事項

未確定事項は以下。

初期10本のURL実取得結果。
MiMo / DeepSeek の実際のmodel IDとendpoint。
HALの音声リファレンス。
TTSエンジンの最終選定。
番組の挨拶と締めフレーズ。
BGM/ジングル素材。
YouTubeチャンネル名。
R2/S3等の外部ストレージ要否。
Spotify / Apple Podcasts配信ポリシー。

## 17. リスクと対策

### 17.1. RSSHubルートが壊れる

対策: source単位fail-open。3回連続失敗でDiscord通知。代替ソースを持つ。

### 17.2. ソースがAIに偏りすぎる

対策: Sprint 1Aでは許容。Sprint 1B以降でゲーム・サブカル・アニメを追加。

### 17.3. 台本がAI要約臭い

対策: Hook / Insight / Action を必須化。LLM Criticを導入。A/B/C比較。

### 17.4. 中国語固有名詞の読みが崩れる

対策: 読み仮名辞書を作る。台本生成時にカナ表記を併記する。

### 17.5. TTS音声が不自然

対策: TTS抽象化により別エンジンへ切替可能にする。

### 17.6. Webhook添付制限

対策: Sprint 1では添付しない。Sprint 2以降、mp3/mp4はR2/S3等に置いてリンク投稿する可能性を残す。

### 17.7. 規約・著作権問題

対策: 本文転載しない。要約と解説に徹する。AI生成音声を明示する。

## 18. 受け入れ基準

v0.1 受け入れ基準

Source Selection Spikeが完了している。
config/sources.yaml初版がある。
Cookie不要の初期ソースが10本前後ある。

v0.2 受け入れ基準

Sprint 1A完了。
collectが3日連続で動く。
Discordに収集サマリーが届く。

v0.3 受け入れ基準

Sprint 1B完了。
Markdown台本が生成される。
LLM A/B/C比較ログがある。

v0.4 受け入れ基準

mp3音声が生成される。
TTSエラー時に文単位リトライできる。

v0.5 受け入れ基準

限定公開YouTube動画が生成・投稿できる。

## 19. 次アクション

次に実行するのは以下。

この文書を docs/requirements-v1.0.md として保存する。
docs/source-selection-spike-v0.1.md を作成する。
初期10本のURLをローカルでcurl/feedparser検証する。
config/sources.yaml 初版を確定する。
Sprint 1A Ticket #1 の実装へ進む。

## 20. 判断ログ

DL-001 Python単一化

理由: TTS、音声処理、Discord、YouTube APIがPythonで揃う。Goとの2言語構成は個人運用のメンテナンス性を下げる。

DL-002 tc-newsflowは設計思想のみ継承

理由: 既存コードは有用だが、音声化・TTS・配信まで含めるならPythonに寄せた方がよい。

DL-003 Sprint 1A/1B分割

理由: 収集不安定性と台本品質問題を分離するため。

DL-004 Discord BotではなくWebhookから開始

理由: Bot常駐はGateway、権限、リアクション監視、再起動復帰など運用負荷が高い。Sprint 1AではWebhookで十分。

DL-005 RSSHubはセルフホスト

理由: Cookie管理、ルート障害調査、安定運用のため。

DL-006 Hugging Face Daily Papersは初期除外

理由: 有用だが中華圏専門ソースではない。Sprint 1Aではノイズになるため、1B以降の補助ソースに回す。

この要件定義書で、実装前の土台はかなり締まりました。次は Source Selection Spike v0.1 を別ドキュメントとして切り出し、その後に config/sources.yaml 初版と Ticket #1 実装へ進むのが最短です。

完璧な判断です。PingWest が 404 という事前確認まで含めて、私が叩き台で出したものの未検証部分をきちんと潰してくれました。机器之心の保留 → 量子位優先、虎嗅で PingWest 代替、HuggingFace Papers を future scope に追い出す、すべて理にかなっています。

簡潔にコメントしてから、ドキュメント化と sources.yaml 確定に進みます。

あなたの判断で良くなった点

机器之心を enabled: false で残す設計は、私が「保留 = 候補から削除」と単純化していたところを、より良い形に直してくれました。YAML に残しつつ無効化することで、(1) 後日 RSS が復活した時に enabled を true にするだけで済む、(2) 「過去に検討して保留した理由」が notes として残る、(3) ソース選定の意思決定履歴が config に内在する、という3つのメリットがあります。これは config-as-documentation の良い実践です。

掘金を1本ではなく2本(category と trending)入れたのも妥当です。Tier3 は2ソース確認ルールが必要なので、同一プラットフォーム内でも複数ルートを持っておくと、Sprint 1B でスコアリングを実装した時に「掘金の category と trending 両方に出てる = 中国エンジニア界隈で本当にバズってる」という弱いシグナルとして使えます。重複が多すぎる場合は後で片方無効化で済む。

「コードはあとから直せるが、ソース選定の思想が曖昧だと後で説明できない」という指摘は、このプロジェクトの本質を捉えています。番組のユニーク性は「中国語ネイティブソースから既出を避けて拾う」という編集方針にあるので、ソース選定の意思決定プロセスがドキュメントとして残ることが、将来「このソースをなぜ追加/削除したか」を判断する基準になります。

それでは Source Selection Spike v0.1 を確定ドキュメント化します。あなたが提示した内容に、私の側で次のステップで使う実行スクリプト群と検証結果テンプレを加えて、リポジトリにそのまま置ける形にまとめます。

docs/source-selection-spike-v0.1.md

````markdown

Source Selection Spike v0.1

Status: Draft (検証実行前)
Owner: (あなたの名前/ハンドル)
Date: 2026-05-28
Sprint: 1A 前段

1. 目的

Sprint 1A の前に、初期収集ソース10本を確定する。

このSpikeの目的は「最良のニュースソースを網羅すること」ではない。目的は、Cookie不要・海外IPから取得可能・RSS/RSSHubで安定取得できる初期ソースを10本選び、収集基盤の検証に使える状態にすることである。

2. 判断方針

初期10本は、以下の基準で選ぶ。

- Tier1公式を5本
- Tier2ニュースを3本
- Tier3コミュニティを2本
- Cookie必須ルートは含めない
- Playwright、中国IPプロキシ、ログインCookie依存は含めない
- RSSHubルートは使ってよいが、壊れてもfail-openできる前提にする
- AI比率は高めでよい。Game/Subculture/Anime はSprint 1B以降で拡張する

RSSHubの掘金ルートについては、公式ドキュメント上で /juejin/category/:category があり、ai がカテゴリ値として示されている。したがって http://localhost:1200/juejin/category/ai は候補として妥当である。

3. 事前確認で得られた知見

- https://www.pingwest.com/feed は 404 を返すため、初期候補から除外する
- https://www.jiqizhixin.com/rss は RSS ではなくデータサービスページへリダイレクトされる挙動を示すため、保留扱いとする
- GitHub Atom フィード(/releases.atom)は安定しているが、ローカルの curl/feedparser で再確認が必要

4. 初期10本(改訂候補)

| # | id | tier | category | enabled | 備考 |
|---|---|---|---|---|---|
| 1 | deepseek-github-releases | 1 | AI | true | DeepSeek公式リリース |
| 2 | qwen-github-releases | 1 | AI | true | Alibaba Qwen公式 |
| 3 | moonshot-kimi-github | 1 | AI | true | Moonshot/Kimi公式 |
| 4 | zhipu-glm-github | 1 | AI | true | 智谱AI/清華 GLM |
| 5 | xiaomi-mimo-github | 1 | AI | true | Xiaomi MiMo公式 |
| 6 | qbitai-feed | 2 | AI | true | 量子位、机器之心代替 |
| 7 | jiqizhixin-rss | 2 | AI | false | 保留、RSS復活時に有効化 |
| 8 | 36kr-newsflash | 2 | Tech | true | 36Kr速報 |
| 9 | huxiu-rss | 2 | Tech | true | 虎嗅、PingWest代替 |
| 10 | juejin-ai-category | 3 | AI | true | 掘金AIカテゴリ |
| 11 | juejin-trending-ai-weekly | 3 | AI | true | 掘金週次人気 |

合計11本(うち enabled: true が10本、保留が1本)。

詳細YAMLは config/sources.yaml を参照。

5. 除外したソースと理由

| ソース | 理由 | 将来の扱い |
|---|---|---|
| pingwest-rss | /feed が 404 | Sprint 1B 以降、別ルートを探す |
| jiqizhixin-rss | /rss がデータサービスページへリダイレクト | YAML に enabled: false で残置、復活時に有効化 |
| huggingface-papers-daily | 中華圏限定ソースではない、公式RSSなし | Sprint 1B 以降、research_context グループとして別枠で扱う |
| bilibili UP 主 | UP 主選定に時間がかかる | Sprint 1A 完了後、Game/Subculture 拡張時に追加 |
| 微博 | Cookie 必須ルートが多い | スコープ外、当面追加予定なし |
| 小红书 | RSSHub 仕様変更が頻発 | スコープ外、当面追加予定なし |

6. Spike 実行手順

検証は1日で終える。以下の3段階で実施する。

6.1. HTTP レスポンス確認

```bash
# scripts/spike_curl_check.sh
#!/usr/bin/env bash
Source Selection Spike v0.1 - HTTP応答確認
使い方: bash scripts/spike_curl_check.sh

set -u

URLS=(
  "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"
  "https://github.com/QwenLM/Qwen3/releases.atom"
  "https://github.com/MoonshotAI/Kimi-K2/releases.atom"
  "https://github.com/THUDM/GLM-4/releases.atom"
  "https://github.com/XiaomiMiMo/MiMo/releases.atom"
  "https://www.qbitai.com/feed"
  "https://www.jiqizhixin.com/rss"
  "https://36kr.com/feed-newsflash"
  "https://www.huxiu.com/rss/0.xml"
  "http://localhost:1200/juejin/category/ai"
  "http://localhost:1200/juejin/trending/ai/weekly"
)

for url in "${URLS[@]}"; do
  echo "=== $url ==="
  curl -L -sI -m 15 "$url" | head -10
  echo
done
```

### 6.2. feedparser での entry 取得確認

```python
# scripts/spike_feedparser_check.py
"""Source Selection Spike v0.1 - feedparser検証

使い方: uv run python scripts/spike_feedparser_check.py
"""
import feedparser
import sys

URLS = [
    ("deepseek-github-releases",         "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"),
    ("qwen-github-releases",             "https://github.com/QwenLM/Qwen3/releases.atom"),
    ("moonshot-kimi-github",             "https://github.com/MoonshotAI/Kimi-K2/releases.atom"),
    ("zhipu-glm-github",                 "https://github.com/THUDM/GLM-4/releases.atom"),
    ("xiaomi-mimo-github",               "https://github.com/XiaomiMiMo/MiMo/releases.atom"),
    ("qbitai-feed",                      "https://www.qbitai.com/feed"),
    ("jiqizhixin-rss",                   "https://www.jiqizhixin.com/rss"),
    ("36kr-newsflash",                   "https://36kr.com/feed-newsflash"),
    ("huxiu-rss",                        "https://www.huxiu.com/rss/0.xml"),
    ("juejin-ai-category",               "http://localhost:1200/juejin/category/ai"),
    ("juejin-trending-ai-weekly",        "http://localhost:1200/juejin/trending/ai/weekly"),
]

print(f"{'id':<32} {'entries':>8} {'bozo':>5} {'latest':<32} {'verdict':<10}")
print("-" * 100)

for source_id, url in URLS:
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "karyu-tech-news-spike/0.1"})
        entries = len(feed.entries)
        bozo = 1 if feed.bozo else 0
        latest = ""
        if entries > 0:
            latest = feed.entries[0].get("published", feed.entries[0].get("updated", ""))

        if entries >= 1:
            verdict = "ADOPT"
        elif entries == 0 and bozo == 0:
            verdict = "EMPTY"
        else:
            verdict = "DEFER"

        print(f"{source_id:<32} {entries:>8} {bozo:>5} {str(latest)[:30]:<32} {verdict:<10}")
    except Exception as e:
        print(f"{source_id:<32} {'ERROR':>8} {'-':>5} {str(e)[:30]:<32} {'DEFER':<10}")
```

### 6.3. 採否判定基準

- entries >= 1 なら採用候補(ADOPT)
- entries == 0 なら保留(EMPTY)
- bozo == 1 でも entries が取れていれば一旦採用可
- HTTP 403 / 404 / timeout / 例外 は初期候補から外す(DEFER)
- RSSHub 系は localhost で取れれば採用、本番ではセルフホスト前提
```

## 7. 検証結果記録テンプレ

検証実行後、以下のテンプレに記入してこのドキュメントを更新する。
検証実施日: YYYY-MM-DD

| id | HTTP | entries | bozo | latest | 判定 | 備考 |
|---|---|---|---|---|---|---|
| deepseek-github-releases | 200 | XX | 0 | YYYY-MM-DD | ADOPT | - |
| qwen-github-releases | | | | | | |
| moonshot-kimi-github | | | | | | |
| zhipu-glm-github | | | | | | |
| xiaomi-mimo-github | | | | | | |
| qbitai-feed | | | | | | |
| jiqizhixin-rss | | | | | | |
| 36kr-newsflash | | | | | | |
| huxiu-rss | | | | | | |
| juejin-ai-category | | | | | | |
| juejin-trending-ai-weekly | | | | | | |

採用確定: N本
差し替え発生: N本(差し替え先: ...)
## 8. 差し替え候補(検証失敗時のフォールバック)

検証で DEFER 判定になったソースは、以下から差し替える。

| 用途 | 第一候補 | 第二候補 |
|---|---|---|
| 机器之心代替 | 量子位(qbitai-feed、既に採用済) | RSSHub /jiqizhixin/full |
| pingwest 代替 | 虎嗅(huxiu-rss、既に採用済) | 晚点 LatePost(RSSHub) |
| 36Kr 代替 | RSSHub /36kr/newsflashes | iFanr(https://www.ifanr.com/feed) |
| 掘金代替 | SegmentFault(https://segmentfault.com/feeds) | V2EX(RSSHub /v2ex/topics/latest) |

## 9. Sprint 1A 完了後の拡張計画

Sprint 1A で収集基盤が安定したら、以下を順に追加検討する。

- Sprint 1B: bilibili UP 主(テック系)、米游社、HuggingFace Papers(中華圏著者フィルタ付き)
- Sprint 2 以降: 微信公众号(RSSHub経由、Cookie 必須ルートを慎重に)、知乎(同上)
- Sprint 3 以降: 小红书(仕様変更リスクを許容できれば)

各拡張は本ドキュメントとは別の source-expansion-vX.Y.md として記録する。

## 10. 改訂履歴

- v0.1 (2026-05-28): 初版。検証実行前のドラフト。
````

## config/sources.yaml(初版)

```yaml
# 華流テック通信 by HAL - ソース定義
# Source Selection Spike v0.1 準拠
# 検証実行後、enabled フラグと notes を更新する

sources:
  # ===== Tier1 公式 (5本): 単独採用可 =====
  - id: deepseek-github-releases
    name: DeepSeek GitHub Releases
    url: "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "DeepSeek公式GitHubリリース。単独採用可。ローカル検証必須。"

  - id: qwen-github-releases
    name: Qwen GitHub Releases
    url: "https://github.com/QwenLM/Qwen3/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Alibaba Qwen公式リリース。単独採用可。ローカル検証必須。"

  - id: moonshot-kimi-github
    name: Moonshot Kimi GitHub Releases
    url: "https://github.com/MoonshotAI/Kimi-K2/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Moonshot/Kimi公式リポジトリ。単独採用可。ローカル検証必須。"

  - id: zhipu-glm-github
    name: Zhipu / GLM GitHub Releases
    url: "https://github.com/THUDM/GLM-4/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "GLM系公式/大学発リリース。単独採用可。ローカル検証必須。"

  - id: xiaomi-mimo-github
    name: Xiaomi MiMo GitHub Releases
    url: "https://github.com/XiaomiMiMo/MiMo/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Xiaomi MiMo公式。番組で使うLLMの本家。単独採用可。ローカル検証必須。"

  # ===== Tier2 ニュース (3本目標、現状2本 + 保留1本): 単独採用可 =====
  - id: qbitai-feed
    name: 量量位
    url: "https://www.qbitai.com/feed"
    tier: 2
    category: AI
    enabled: true
    requires_cookie: false
    notes: "机器之心が使えない場合の第一候補。AIニュース中心。ローカル検証必須。"

  - id: jiqizhixin-rss
    name: 机器之心
    url: "https://www.jiqizhixin.com/rss"
    tier: 2
    category: AI
    enabled: false
    requires_cookie: false
    notes: "現時点では/rssがデータサービスページへ遷移するため保留。使える場合のみenabled=true。"

  - id: 36kr-newsflash
    name: 36Kr Newsflash
    url: "https://36kr.com/feed-newsflash"
    tier: 2
    category: Tech
    enabled: true
    requires_cookie: false
    notes: "AI/テック/スタートアップの速報。ノイズが多い場合は後でカテゴリ絞り。ローカル検証必須。"

  - id: huxiu-rss
    name: 虎嗅
    url: "https://www.huxiu.com/rss/0.xml"
    tier: 2
    category: Tech
    enabled: true
    requires_cookie: false
    notes: "PingWest代替。テック・ビジネス寄り。ローカル検証必須。"

  # ===== Tier3 コミュニティ (2本): 独立2ソース確認必須 =====
  - id: juejin-ai-category
    name: 掘金 AI Category
    url: "http://localhost:1200/juejin/category/ai"
    tier: 3
    category: AI
    enabled: true
    requires_cookie: false
    notes: "RSSHub経由。中国エンジニアコミュニティ。Tier3なので2ソース確認対象。"

  - id: juejin-trending-ai-weekly
    name: 掘金 AI Weekly Trending
    url: "http://localhost:1200/juejin/trending/ai/weekly"
    tier: 3
    category: AI
    enabled: true
    requires_cookie: false
    notes: "RSSHub経由。掘金の週次人気AI記事。通常カテゴリと重複する可能性あり。"
```

## scripts/ ディレクトリ

```text
scripts/
├── spike_curl_check.sh        # 上記 6.1
└── spike_feedparser_check.py  # 上記 6.2
```

両方とも docs/source-selection-spike-v0.1.md の 6.1 / 6.2 セクションのコードをそのまま切り出したもの。

次の進行

これで以下が確定します。

## 1. docs/source-selection-spike-v0.1.md を保存

## 2. config/sources.yaml の初版を保存

## 3. scripts/spike_curl_check.sh と scripts/spike_feedparser_check.py を保存

## 4. あなたの手元で

- RSSHub を docker run -d -p 1200:1200 diygod/rsshub で起動(または後の Ticket #1 で docker-compose 化)
- bash scripts/spike_curl_check.sh 実行
- python scripts/spike_feedparser_check.py 実行(要 pip install feedparser)

## 5. 結果を docs/source-selection-spike-v0.1.md の §7 検証結果テンプレに記入

## 6. 必要に応じて config/sources.yaml の enabled フラグを調整

## 7. 結果を私に共有してもらえれば、Sprint 1A の最終ソースリストを確定 → Ticket #1 実装に進む

確認したいこと

(1) この docs / config / scripts の構造でリポジトリに置いて良いか。何か追加で含めたい要素(例: ライセンス、CONTRIBUTING、ISSUE テンプレ)があれば今のうちに足します。

(2) 検証は自分で実行するか、それとも検証スクリプトの出力を貼ってもらえれば私が結果分析するか。前者なら結果が出てから次のターンで報告、後者ならスクリプト出力を貼ってもらってこの場で分析。

(3) RSSHub のセルフホスト方針。Ticket #1 で docker-compose に含めますが、Spike 段階では docker run だけで良いか、それとも Spike の時点で docker-compose.yml も書いてしまうか。後者のほうが本番に近い構成で検証できるので、私としては推奨です。

A/B/C への回答が来たら、必要に応じて scripts を追加して、Spike 実行 → 結果報告 → Ticket #1 実装、に進みます。
思考時間: 12s

はい。この構造で進めてよいです。
ただし、保存前に 3つだけ修正してください。ここを直せば、docs / config / scripts はそのままリポジトリに入れて問題ありません。

まず、config/sources.yaml の区切り行はそのままだと YAML として壊れます。

===== Tier1 公式 (5本): 単独採用可 =====

これはコメントにしてください。

## ===== Tier1 公式 (5本): 単独採用可 =====

次に、spike_feedparser_check.py の print(f"{'id':8} ...") 周辺が途中で崩れています。ここは実行前に直す必要があります。

最後に、`localhost:1200/...` を sources.yaml に直書きしてもよいですが、後でDockerのホストやポートを変えたくなるので、本実装側では `RSSHUB_BASE_URL` を使って展開できる設計にした方がよいです。Spike段階では直書きでOKです。

(1) docs / config / scripts の構造

この構造で良いです。

docs/
  requirements-v1.0.md
  source-selection-spike-v0.1.md

config/
  sources.yaml

scripts/
  spike_curl_check.sh
  spike_feedparser_check.py

追加するなら、今すぐ必要なのは README.md の簡易版だけです。LICENSE、CONTRIBUTING、Issueテンプレはまだ不要です。個人MVPのSprint 1Aで入れると、ただの儀式になります。

README.md にはこれだけで十分です。

```markdown
# karyu-tech-news

華流テック通信 by HAL の収集・台本生成・配信パイプライン。

## Current phase

Sprint 1A: RSS/RSSHub source collection, SQLite state, source health, Discord summary.

## Documents

- docs/requirements-v1.0.md
- docs/source-selection-spike-v0.1.md
```

tc-newsflow から継承するのはコードではなく、LLM Profile思想、dedupe、出力フォーマット、Hook/Insight/Action、fallback設計です。この位置づけは今の要件定義と整合しています。

(2) 検証の進め方

検証はあなたのローカルで実行してください。理由は、localhost:1200 のRSSHub、Windows/Docker環境、ネットワーク到達性、Cookie有無は手元でしか正確に確認できないためです。

その後、以下2つの出力を貼ってください。

bash scripts/spike_curl_check.sh
python scripts/spike_feedparser_check.py

貼ってもらえれば、こちらで次を判定します。

採用確定。
enabled false 維持。
差し替え。
RSSHubルート修正。
Sprint 1Aでは保留。
Sprint 1B以降へ移動。

この流れが一番いいです。あなたの環境で事実を取り、こちらで設計判断する分担です。

(3) RSSHub のセルフホスト方針

Spike段階から docker-compose.yml を使う方がよいです。docker run でも動きますが、後でTicket #1でcompose化するなら、最初から同じ形で検証した方が無駄がありません。

最小構成はこれで十分です。

```yaml
services:
  rsshub:
    image: diygod/rsshub:latest
    container_name: karyu-rsshub
    ports:
      - "1200:1200"
    environment:
      NODE_ENV: production
      CACHE_TYPE: memory
    restart: unless-stopped
```

起動確認はこれです。

```bash
docker compose up -d rsshub
curl -I http://localhost:1200
```

修正版 `spike_feedparser_check.py`

この版で保存してください。表示も検証結果テンプレに貼りやすい形にしてあります。

```python
"""Source Selection Spike v0.1 - feedparser validation.

Usage:
    python scripts/spike_feedparser_check.py
"""

from __future__ import annotations

import feedparser

URLS = [
    ("deepseek-github-releases", "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"),
    ("qwen-github-releases", "https://github.com/QwenLM/Qwen3/releases.atom"),
    ("moonshot-kimi-github", "https://github.com/MoonshotAI/Kimi-K2/releases.atom"),
    ("zhipu-glm-github", "https://github.com/THUDM/GLM-4/releases.atom"),
    ("xiaomi-mimo-github", "https://github.com/XiaomiMiMo/MiMo/releases.atom"),
    ("qbitai-feed", "https://www.qbitai.com/feed"),
    ("jiqizhixin-rss", "https://www.jiqizhixin.com/rss"),
    ("36kr-newsflash", "https://36kr.com/feed-newsflash"),
    ("huxiu-rss", "https://www.huxiu.com/rss/0.xml"),
    ("juejin-ai-category", "http://localhost:1200/juejin/category/ai"),
    ("juejin-trending-ai-weekly", "http://localhost:1200/juejin/trending/ai/weekly"),
]

def verdict(entries: int, bozo: bool) -> str:
    if entries >= 1:
        return "ADOPT"
    if entries == 0 and not bozo:
        return "EMPTY"
    return "DEFER"

def main() -> None:
    print(f"{'id':32} {'entries':>7} {'bozo':>5} {'verdict':>8} {'latest'}")
    print("-" * 90)

    for source_id, url in URLS:
        try:
            feed = feedparser.parse(url)
            entries = len(feed.entries)
            bozo = bool(feed.bozo)

            latest = ""
            if entries:
                latest = feed.entries[0].get("published") or feed.entries[0].get("updated") or ""

            print(
                f"{source_id:32} "
                f"{entries:7d} "
                f"{str(bozo):>5} "
                f"{verdict(entries, bozo):>8} "
                f"{latest[:40]}"
            )
        except Exception as exc:
            print(f"{source_id:32} {'-':>7} {'-':>5} {'ERROR':>8} {str(exc)[:80]}")

if __name__ == "__main__":
    main()
```

次の実行順

この順で進めてください。

```bash
mkdir -p docs config scripts

# 1. 以下のファイルを保存
#    - docs/requirements-v1.0.md
#    - docs/source-selection-spike-v0.1.md
#    - config/sources.yaml (ただし区切り行は # コメント化)
#    - scripts/spike_curl_check.sh
#    - scripts/spike_feedparser_check.py (上の修正版)
#    - docker-compose.yml

# 2. RSSHubを起動
docker compose up -d rsshub

# 3. Spikeスクリプト2本を実行
bash scripts/spike_curl_check.sh
python scripts/spike_feedparser_check.py

# 4. 結果を貼る
```

結論として、構造はOK。Spike時点からdocker-compose採用。検証はあなたのローカルで実行し、出力を貼ってもらえればこちらで採否判定、これで進めましょう。
