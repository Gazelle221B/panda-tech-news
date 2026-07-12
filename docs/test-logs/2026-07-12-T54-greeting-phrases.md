# T54 — 番組挨拶フレーズ確定の反映 (Issue #39)

- 日付: 2026-07-12
- ブランチ: `agent/T54-greeting-phrases-impl`
- 実装者: Claude Code
- 参照: [Issue #39](https://github.com/Gazelle221B/panda-tech-news/issues/39), [docs/proposals/greeting-phrases-v0.1.md](../proposals/greeting-phrases-v0.1.md)

## 人間確定内容 (Issue #39 コメント, 2026-07-12)

- **タイトルコール** (案C由来): 「華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。」
  読み上げトーン: 「FM ラジオの DJ パーソナリティっぽいかっこいい感じ」
- **オープニング挨拶** (案B改): 「キャスターのHALです。支度の手を止めずに、今朝の中華圏テック、要点だけボクと一緒に追いかけましょう。」
- **エンディング定型句** (案A由来): 「今日の華流テック通信は以上です。〔明日への引き・可変〕。それでは皆さん、良い一日を。HALでした。」

## 変更内容

### 1. ドキュメント反映

- **`docs/hal-persona.md` §4**: プレースホルダから確定 3 フレーズへ差し替え。タイトルコールの
  「FMラジオDJ調」トーン指定、および caption 制約の調査結果 (下記) を明記。エンディングの
  「〔明日への引き・可変〕」枠は下記理由で今回は反映していない旨も記録 (版管理は本書内で完結,
  §6 の既存方針どおり)。
- **`config/hal_persona.yaml` `phrases`**: 「暫定」注記を除去し確定文言へ更新、`title_call`
  フィールドを新設。**このファイルの `phrases` はコードから未参照** (grep で確認済み、
  `docs/hal-persona.md` の機械可読ミラーとしてのドキュメント専用フィールド)。コードが実際に
  読むのは次項の `config/show_format.yaml` 側。
- **`config/show_format.yaml`**: 新規 `phrases:` セクション (title_call/opening/closing) を追加。
  こちらが `script/generate.py` から実際に読み込まれる (下記)。

### 2. コード配線 (ハードコード禁止・fail-open)

- **`src/karyu_tech_news/script/generate.py`**:
  - `ShowPhrases` (NamedTuple) + `load_show_phrases(path=DEFAULT_SHOW_FORMAT_PATH)` を新設。
    `show_format.yaml` の `phrases` セクションを読み、`title_call`/`opening`/`closing` を返す。
    ファイル欠落・YAML 破損・`phrases` セクション欠落・個別フィールド欠落は、いずれも例外を
    投げず既定値 (確定文言そのもの) へ fail-open する (AGENTS §3.3 の「1箇所の失敗で全体を
    止めない」精神を config 読み込みへ適用)。
  - `DEFAULT_SHOW_FORMAT_PATH` は `karyu_tech_news.config.PROJECT_ROOT` (既存の絶対パス基点)
    を再利用し `config/show_format.yaml` を指す。CWD 非依存で解決できる (既存 `DEFAULT_SOURCES_PATH`
    と同じ設計方針)。
  - 旧来のハードコード定数 `OPENING_PHRASE` / `CLOSING_PHRASE` は削除し、`assemble_episode()`
    が `show_format_path` (既定 `DEFAULT_SHOW_FORMAT_PATH`、キーワード専用引数で追加。既存呼び出し
    元は無変更で動く) を受け取って都度 `load_show_phrases()` を呼ぶ形に変更。生成される Markdown
    の冒頭がタイトルコール行 + オープニング行の 2 行になった (旧: オープニング行のみ 1 行)。
- **`src/karyu_tech_news/script/structure.py`**: `generate.py` から `OPENING_PHRASE`/`CLOSING_PHRASE`
  を静的 import していた箇所を `load_show_phrases`/`DEFAULT_SHOW_FORMAT_PATH` の呼び出しに置換。
  `build_structured_script()` も同様に `show_format_path` キーワード引数を追加。intro segment の
  発話テキストは `f"{title_call}{opening}"` (両フレーズとも「。」で終わるため、`synthesize_script`
  の文分割で自然に2文として読まれる。segment を分割しなくても不自然な連結にならない)。
  **注記**: `build_structured_script`/`StructuredScript` は現行 `produce` CLI からは呼ばれておらず
  (`main.py` は保存済み `draft.markdown` を `strip_markdown_structure` で単一 segment 化する経路を
  使っている)、実際の TTS 音声へは `generate.py::assemble_episode` が生成する markdown 側の変更が
  効く。`structure.py` 側は将来の multi-segment TTS 化に備えた既存コード (テストのみ現存) であり、
  一貫性のため同じ確定フレーズ・同じ fail-open ローダーに揃えた。

### 3. FMラジオDJ調 caption の実現可否調査 (指示どおり persona 記述のみに留める判断)

**結論: 実装しない。別チケット推奨、`docs/hal-persona.md` §4 に調査結果を記録済み。**

調査内容:
- `config/hal_persona.yaml` `tts.caption` は Irodori 600M VoiceDesign 向けの**1エピソード全体で
  単一の自然文指示**。`tts/synthesize.py::synthesize_script()` はこの 1 値を `effective_caption`
  として計算し、`script.segments` の全 segment・全文に同一 caption を渡す (167行目・185行目)。
- 対照的に `emoji_mapping` は tone (segment 単位) で切り替わる仕組みが既にある
  (`annotate_text(sentence, seg.tone, emoji_mapping)`) — つまり「segment 単位で挙動を変える」
  設計パターン自体は存在するが、caption には未実装。
- `tts/engine.py::SynthesisRequest.caption` はエンジン API レベルでは**リクエスト単位**の
  フィールドとして既に存在する (`caption: str | None`) ため、将来 segment 単位の caption 差し替え
  を実装する場合の土台 (エンジン層) は既にある。不足しているのはオーケストレーション層
  (`synthesize_script`) と設定スキーマ (`hal_persona.yaml` の `tts` に segment/tone 別 caption を
  持たせる仕組み、`emoji_annotation` と同様の辞書形式が候補) のみ。
- タイトルコールだけ「FMラジオDJ調」にするには、上記オーケストレーション層 + 設定スキーマの
  両方を拡張する必要があり、「文単位で caption を変える改修」に該当するため、指示どおり本チケットの
  スコープ (確定フレーズの反映) を超えると判断し実装していない。

### 4. テスト

- `tests/test_script_generate.py`: 既存 `test_assemble_episode_builds_markdown` の暫定句アサーションを
  確定句へ更新。新規 7 テスト (`load_show_phrases` の実ファイル読み込み・カスタムパス・ファイル欠落
  fail-open・`phrases` セクション欠落 fail-open・個別フィールド欠落 fail-open・YAML 破損 fail-open、
  および `assemble_episode` の `show_format_path` 経由差し替え = ハードコードでない証明)。
- `tests/test_script_structure.py`: 新規 3 テスト (intro segment のタイトルコール+オープニング連結、
  outro segment の確定クロージング、`show_format_path` 経由差し替え)。

## 品質ゲート (fresh 実行)

```
$ uv run pytest
548 passed, 1 skipped in 4.40s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 82 source files

$ git diff --check
(出力なし = クリーン)
```

pytest は本チケットのブランチ切り出し時点の main (538 passed, 1 skipped) から **+10**
(load_show_phrases 系 7 + assemble_episode 差し替え 1 + structure.py 系 2... 内訳は上記「4. テスト」
参照、実数は生成側 7 + 構造化側 3 の計 10)。

## 保守側に倒した判断

- **`config/hal_persona.yaml` の `phrases` フィールドも更新した**: 指示は `config/show_format.yaml`
  の配線のみを明示していたが、`hal_persona.yaml` は自身のヘッダコメントで「人間可読の解説は
  docs/hal-persona.md を参照」と宣言しておりその機械可読ミラーの位置づけであるため、
  `hal-persona.md` §4 を確定文言へ更新するなら同じ内容を持つ `hal_persona.yaml` の `phrases` も
  更新しないと 2 つの「番組固有フレーズの記録場所」が食い違ったまま残ってしまうと判断した。
  コードからは未参照 (grep 確認済み) のため実行時の挙動には影響しない、ドキュメント一貫性のみの
  変更。
- **案Aの「〔明日への引き・可変〕」枠は未実装**: 現行パイプラインには「翌日のトピック」を示す
  データも動的生成の仕組みも無く、実装すると別途 LLM 呼び出し等が必要な新機能になり本チケットの
  スコープ (確定フレーズの反映) を超えるため、可変枠を持たない固定文のみを反映した。
  `docs/hal-persona.md` §4 に理由を明記済み。将来「明日への引き」を実装する場合は別チケット。
- **FMラジオDJ調 caption**: 指示どおり実装せず、調査結果を `docs/hal-persona.md` §4 と本ログに記録し
  別チケット推奨とした (詳細は上記「3.」)。
- **`script/structure.py` も更新**: 指示の対象は `script/generate.py` の opening/closing 生成のみ
  だったが、`structure.py` が `generate.py` の `OPENING_PHRASE`/`CLOSING_PHRASE` を静的 import して
  おり、この 2 定数を fail-open ローダー方式に置き換えると `structure.py` の import が壊れるため、
  影響を受ける最小範囲として同じ `load_show_phrases` を使うよう追随させた (スコープ外の独立した
  新機能ではなく、直接の破壊的影響を防ぐための必須追随)。
