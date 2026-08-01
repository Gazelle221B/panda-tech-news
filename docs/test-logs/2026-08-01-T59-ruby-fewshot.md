# T59 — writer ルビ指示に few-shot 例と書き分けを追加 (Issue #59)

- 日付: 2026-08-01
- ブランチ: `agent/T59-ruby-fewshot-impl`
- 実装者: Claude Code
- 参照: [Issue #59](https://github.com/Gazelle221B/panda-tech-news/issues/59) ([[T56]] の追跡)

## 背景

T56 で writer プロンプトに `[[表記|カナ読み]]` ルビ指示を追加したが、実運用の
deepseek-chat が全く追従せず、2026-08-01 draft #2 では注釈ゼロで旧流儀
「アンソロピック (Anthropic)」形式のみが出力された。配線は健全 (extract_ruby 側は
T56 で検証済み) であり、プロンプト追従性のみの問題と特定。

原因分析: 既存の「カナ表記+括弧原語併記」指示には具体例 (`ディープシーク
(DeepSeek)`) があるのに対し、`[[表記|カナ読み]]` 指示には具体例が無く、フォーマット
指示として弱かった。2 指示が対象範囲で重複気味のため、モデルは具体例のある旧流儀に
引きずられていたと推定。

## 変更内容

`src/karyu_tech_news/script/generate.py` の `build_writer_prompts` の system
プロンプトのみを変更。

- `[[表記|カナ読み]]` 指示に **few-shot 例を 2 つ** 追加:
  `[[零一万物|リンイーワンウー]]が新たな資金調達を発表した。` /
  `[[MoWorld|モワールド]]は新製品を披露した。`
- 既存の「カナ表記+括弧原語併記」指示と `[[表記|カナ読み]]` 指示の**優先関係を明文化**
  する 1 項目を追加: 定着済み固有名詞はカナ表記+括弧併記のみ、読みが自明でない新出語
  だけ `[[表記|カナ読み]]` を使う、同じ語に両方を重ねない。
- 箇条書きの位置・全体構成は変更なし。`WRITER_CHAR_BUDGET` (system プロンプト内の
  260 字予算指示) 自体は不変更。system プロンプトはトピック本文の文字数予算の対象外
  (予算はトピック本文 (writer 出力) にのみ適用され、system プロンプトの長さには
  影響しない) のため、例文追加によるバジェット指示との矛盾は無い。

## テスト

`tests/test_script_generate.py`:

- 既存 `test_writer_prompts_include_ruby_instruction` は無変更 (フォーマット指示・
  簡体字・AI/IT 除外例の存在確認は引き続き成立)。
- 新規 `test_writer_prompts_ruby_instruction_has_few_shot_examples`: 追加した 2 つの
  few-shot 例文字列と「使い分け」の書き分け文言が system プロンプトに含まれることを
  アサート。

## 品質ゲート (fresh 実行)

```
$ uv run pytest -v
630 passed, 11 skipped in 9.53s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 88 source files

$ git diff --check
(出力なし = クリーン)
```

補足: この環境では `uv run pytest -q` (addopts 既定) の最終サマリー行が標準出力に
出ない既知の表示崩れがある ([[T56]] のログで既報)。`-v` 実行で正しくサマリーが出る
ことを確認し、上記実測値はそちらから取得した。

## 仕様から外れた判断・不確かな点

- 実運用 LLM (deepseek-chat) への再検証は本チケットのスコープ外 (次回 draft 実行時の
  人間観察待ち)。プロンプト文面の改善と、その意図をアサートで固定するユニットテスト
  までを本チケットの完了範囲とした。
