# 設計継承メモ: tc-newsflow (Go) → karyu-tech-news (Python)

> 出典: [tik-choco-tc-newsflow-8a5edab282632443.md](./tik-choco-tc-newsflow-8a5edab282632443.md) のコード全読
> 方針: 要件 §9.1 / DL-002 / ADR-0001 に基づき、**コードは移植せず設計思想のみ継承する**。
> 役割: Sprint 1B 以降の実装者が「Go の何を Python でどう再現するか」を判断する基準。

本書は Go 実装 `tic-choco/rssflow` を全読して抽出した、**Python 版に移植すべき設計パターン**の一覧である。各項目に「Go の実体 → Python での再現方針 → 落とすと壊れる点」を併記する。コードのコピーではなく、思想の再構築を目的とする。

---

## 1. レイヤー分離 (cmd → rssflow → tui)

**Go**: `cmd/news` (CLI) → `internal/rssflow` (ドメイン) → `internal/tui` (表示)。TUI は rssflow を参照するが逆依存なし。

**Python 再現**: `cli.py` → `collect/edit/script/...` (ドメイン) → (将来 TUI/表示)。逆向き依存を禁止 ([DESIGN.md](./DESIGN.md) §3.2)。`deliver` は `store` の読み取りのみ参照。

**落とすと壊れる点**: 表示層がドメインを汚染すると CLI とバッチで挙動が割れる。

## 2. LLMProfile 抽象 (最重要継承対象)

**Go**: `Config.LLMProfiles []LLMProfile` + `Workflow.LLM.Profile` で参照、`ResolveWorkflow` → `mergeLLM(profile, override)` で重ね合わせ。`NewOpenAIClient(llm)` は `provider/api_key_env/base_url/model/max_tokens/temperature` だけ知る。

**Python 再現**: [config/llm_profiles.yaml](../config/llm_profiles.yaml) の `profiles[]` を pydantic でロード。`api_key_env` は**環境変数名**を保持し実キーは `.env`。editor/writer を別 profile に割り当てられる構造にし、A/B/C 切替 ([ADR-0005](./adr/ADR-0005-llm-roles-ab-test.md)) をコード変更なしで行う。

**落とすと壊れる点**: profile を workflow にハードコードすると、価格戦争 (DeepSeek/MiMo 値下げ合戦) でモデルを差し替えるたびに再実装になる。

## 3. 出力フォーマット切替 (news-script / podcast / article)

**Go**: `NormalizeOutputFormat` が日本語/英語の表記揺れ (「ポッドキャスト」「読み原稿」「記事」…) を3定数へ正規化。`Next/PreviousOutputFormat` で循環。

**Python 再現**: `OutputFormat = Literal["news-script","podcast","article"]` + 正規化関数。本番組は `podcast` を既定とする。フォーマットごとにテンプレと fallback を分岐 (§7)。

**落とすと壊れる点**: 正規化を一カ所に集約しないと、YAML 由来の曖昧な値が各所で分岐し寿命が縮む (tc-newsflow が長生きしている理由がこの正規化集約)。

## 4. トピックスコアリング → tone → アーク配置 (番組の核)

二段構えになっている。**この三段パイプラインが developer-news の心臓部**。

### 4.1 ローカル事前スコア (`localDeveloperNewsPriority`)
キーワード辞書で安価に優先度を付ける。security/breaking/CVE 系 +30、deprecated/regulation 系 +20、release/pricing 系 +10、source_type が advisory/nvd なら +30。**LLM を呼ぶ前に候補を絞る**ためのもの。

### 4.2 LLM 編集判定 (`judgeDeveloperNewsTopics`)
`temperature=0` で各トピックを採点。返却 JSON スキーマ:
```json
{"topics":[{"index":1,"score":90,"tone":"hard_negative","constructive":false}]}
```
- `score`: 0-100 (公共性・影響範囲・緊急性・新事実で高く)
- `tone`: `hard_negative` / `constructive` / `bright` / `neutral`
- system プロンプトは「ニュース番組の編集判定器。JSONだけ返す」。

### 4.3 アーク配置 (`arrangeDeveloperNewsArc`)
3本未満ならそのまま。3本以上なら:
1. `hard_negative` 最高スコアを**先頭**に
2. `bright` (なければ constructive) を**末尾**に
3. `constructive` を**中盤の midpoint** に挿入
→ 「重要ニュース → 解決策・深掘り → 明るい話題」の三幕構成。

**Python 再現**: [config/show_format.yaml](../config/show_format.yaml) の `arc:` がこの思想。中華圏向けに lead=規制/価格戦争, middle=技術解説, close=ゲーム/サブカル と読み替え。tone は MiMo (editor) に出させ、配置は決定的コードで行う。

**落とすと壊れる点**: tone を LLM に「並べさせる」と不安定。**採点は LLM、並べ替えは決定的コード**の分離を守る。

### 4.4 中華圏向けの拡張 (Sprint 1B)
`developerNewsTopicJudgment` に **`source_tier` (1-4)** と **`corroboration_count` (独立ソース数)** を足す (meeting 提案)。これで「Tier1 公式は単独可、Tier3-4 は2ソース必須」([editorial-policy.md](./editorial-policy.md) §4) をスコアに反映できる。

## 5. 候補の多様性確保 (`selectDiverseDeveloperNewsCandidates`)

**Go**: 候補上限 40 / 台本入力上限 16。選定時に **source あたり `limit/3`、category あたり `limit/4`** の上限を課し、4パス (source+category厳格 → category厳格 → source厳格 → 無制約) で埋める。

**Python 再現**: 同じ多様性キャップを実装。1ソースが大量投稿しても番組が偏らない。中華圏では「掘金が10本来ても採用は数本」を保証する。

**落とすと壊れる点**: 多様性キャップを落とすと、更新頻度の高い1ソース (例: 36Kr 速報) が番組を埋め尽くす。

## 6. テキスト切り詰めは必ず rune ベース

**Go**: `truncatePromptText` / `truncateJapaneseScript` / `truncatePlain` はすべて `[]rune` で数える。`japaneseScriptCharCount` は空白を除いた rune 数。

**Python 再現**: `len(s)` (Python str は既にコードポイント単位なので安全) を使い、**バイト単位の切り詰めを絶対にしない**。tc-newsflow の唯一の一貫性の傷 (`truncateText` だけ byte 単位だった) を Python では作らない。プロンプト用は title 180 / description 420 文字、台本トピックは 300 文字。

**落とすと壊れる点**: バイト切りすると中国語・日本語が文字化けする。

## 7. 多段フォールバック (LLM 失敗時の二重防御)

**Go**: `fallbackDeveloperNews{Podcast,NewsScript,Article}` がテンプレベースで台本を生成。Hook/Insight/Action 相当の定型文 (`fallbackInsightSentence` 等)、出典行の機械除去 (`stripDeveloperNewsSourceLines`)、トピック文字数制限。`shouldRewriteDeveloperNews` で再生成判定 → `finalizeDeveloperNewsScript`。

**Python 再現**: LLM 出力が要件 (Hook/Insight/Action、文字数、禁止表現) を満たさなければ、(a) 再生成、(b) それも失敗ならテンプレ fallback。要件 §9.3「LLM失敗時はリトライ→別profileフォールバック」と接続。**fallback テンプレは3-5パターンを乱択**し、毎日同じ枕詞を避ける (meeting 改善提案)。

**落とすと壊れる点**: fallback が無いと LLM が JSON を崩した日に番組が出ない。

## 8. プロンプト契約 (Hook / Insight / Action)

**Go**: `DeveloperNewsInstructions()` (config.go) + `developerNewsOutputContract` (binary file だが test が内容を保証)。契約の必須要素:
- 出力は news-script/podcast/article のいずれか。**要約・箇条書きダイジェスト・調査メモにしない**
- 各トピックに Hook (何が起きたか) / Insight (なぜ重要か) / Action (次に何を見るか) = **事実・示唆・行動**
- 重要ニュース先頭 → 中盤に解決策 → 明るい話題で締め
- 未確認・噂・プレリリースは明示
- **出典URL・Source行は最終出力に入れない** (照合用にのみ使う)
- 「以下は要約です」等のボイラープレート禁止、絵文字禁止 (台本生成段階では)
- 台本/ポッドキャストのトピックは **300文字以内**

**Python 再現**: [prompts/](../prompts/) ではなく、編集者 LLM の system 指示として [editorial-policy.md](./editorial-policy.md) §11 + 本契約を転写。中華圏向けに「中国語固有名詞はカナ化、初出のみ原語併記」「本文転載禁止・要約と解説のみ」を追加 ([hal-persona.md](./hal-persona.md))。

**落とすと壊れる点**: 契約を緩めると「AI 要約臭い」台本になる (要件 §17.3)。

## 9. Ollama / OpenAI 互換の吸収

**Go**: `isOllama()` が base_url で判定、`applyCompatibilityOptions` が `reasoning_effort=none` / `think=false` を強制。SSE パースは delta/text/content/reasoning/thinking/output[] と**多数のフィールドを順に試す**頑健設計。

**Python 再現**: OpenAI 互換を最大公約数とし、base_url で Ollama / reasoning モデルを判定して body を出し分け。ストリーミングは複数フィールドを順に拾う。ローカル Qwen 検証 (要件) で効く。

**落とすと壊れる点**: reasoning モデルは `reasoning_content` に本文を吐くことがあり、`content` だけ見ると空になる。

## 10. JSON 抽出の頑健化 (`extractJSONObject`)

**Go**: ```` ```json ```` フェンス除去、`[` / `{` の最初〜最後で切り出し。

**Python 再現**: 同等。ただし tc-newsflow の弱点 (文字列中の `[]` で誤動作) は、まず素直に `json.loads`、失敗時のみ最外 `{...}` 抽出、という順で堅くする。abliterated/reasoning モデルは JSON 前後に思考を吐きがち。

## 11. dedupe / seen 管理 (Python では SQLite へ)

**Go**: `FilterNewItems` が `state.Seen[label]` (YAML) でソースラベル単位 seen 管理、`itemKey` は ID→Link→hash(title+source) の順、`MaxSeen` で打ち切り。**注意: 先頭追加 `append([]string{key}, ...)` は O(n²)** (meeting で指摘済み)。

**Python 再現**: state は YAML ではなく **SQLite** ([DESIGN.md](./DESIGN.md) §4)。`item_key` 生成順は同じ (external_id→link→hash)。`UNIQUE(source_id, item_key)` で dedupe し、`MaxSeen` 概念は不要。O(n²) の先頭追加は**踏襲しない** (末尾追加 or DB 制約に任せる)。

**落とすと壊れる点**: `hash` 単体に UNIQUE を張るとクロスソース重複が別レコードにできない ([DESIGN.md](./DESIGN.md) §7 禁止事項)。

## 12. ランナーのステージ可視化

**Go**: `RunWorkflowStreamProgress` が `collect → state → filter → has-new → dry-run → client → generate → save-check → save → done` を `emitProgress` で逐次通知。TUI がカード表示。

**Python 再現**: Sprint 1A は `collect → store → health → summary` の各ステージを構造化ログ (要件 §9.4)。将来 TUI/Discord 進捗表示に流用できるよう、ステージ名を安定させる。

## 13. 既知の改善余地 (Python では最初から直す)

meeting のコードレビューで挙がった、tc-newsflow の弱点。**Python では再現しない**:

| Go の問題 | Python での対処 |
|---|---|
| `dedupe` の O(n²) 先頭追加 | SQLite + 末尾追加 |
| `removeRankedDeveloperNewsTopic` が裏配列破壊 | 新リストを返す (immutable, ユーザールール) |
| `isDeveloperNewsWorkflow` が label に "news"/"rss" を含むだけで発火 | `Workflow.genre` / `mode` を**明示フィールド**化 |
| プロンプトが Go コード直書き → 再ビルド必要 | プロンプトを YAML / 設定外出し |
| `truncateText` だけ byte 単位 | 全て文字 (rune/str) 単位で統一 |
| プロンプトのバージョニング不在 | A/B テスト単位で版管理 (llm_profiles + 履歴) |
| Critic が決定的ルールのみ | LLM Critic を editor (MiMo) で挟む (Sprint 1B) |

## 14. 継承しないもの (Sprint 1A スコープ外)

GitHub Advisories / npm / PyPI / Crates / NVD ソース束 (`SourcesConfig`)、TUI (Bubble Tea)、developer-news の英語圏向けキーワード辞書。これらは tc-newsflow が「開発者ニュース」向けだった名残。本番組は**中華圏テック/AI/サブカル**向けにソースとカテゴリを再設計する ([editorial-policy.md](./editorial-policy.md) §9)。

---

## 付録: Go の主要シンボル → Python 対応表

| Go | Python (予定) | 層 |
|---|---|---|
| `Item{ID,Title,Link,Description,Published,Source,SourceType}` | `RawItem` (pydantic, [DESIGN.md](./DESIGN.md) §3.3) | collect |
| `FetchFeeds` / `fetchFeed` | `collect/fetcher.py` (feedparser+httpx) | collect |
| `FilterNewItems` / `itemKey` | `store/repo.py` (SQLite) | store |
| `localDeveloperNewsPriority` | `edit/prescore.py` | edit (1B) |
| `judgeDeveloperNewsTopics` | `edit/judge.py` | edit (1B) |
| `arrangeDeveloperNewsArc` | `edit/arc.py` | edit (1B) |
| `selectDiverseDeveloperNewsCandidates` | `edit/select.py` | edit (1B) |
| `buildSystemPrompt` / `buildUserPrompt` | `script/prompts.py` | script (1B) |
| `fallbackDeveloperNews*` | `script/fallback.py` | script (1B) |
| `NewOpenAIClient` / `applyCompatibilityOptions` | `llm/client.py` | llm (1B) |
| `RunWorkflow` ステージ | `collect/runner.py` (1A) → pipeline (1B+) | runner |
