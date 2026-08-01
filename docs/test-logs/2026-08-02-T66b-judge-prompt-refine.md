# T66b — judge プロンプトの判定基準を精緻化 (同音異字の誤検出対応) (Issue #76)

- 日付: 2026-08-02
- ブランチ: `agent/T66b-judge-prompt-refine-impl` (origin/main から新規、T66 の PR #79 マージ後)
- 実装者: Claude Code
- 参照: [Issue #76](https://github.com/Gazelle221B/panda-tech-news/issues/76) (T66 の続き、実戦投入フィードバック)

## 背景

T66 (PR #79) の LLM ASR 判定を実戦投入し、draft #5 の produce を実行したところ、曖昧域
6 文の判定内訳で 2 件の誤検出 (mismatch 1件・insertion 疑い 1件) が確認された:

- **ok が正解**: 「ハルです」↔「春です」/「ジーメン(ジーモン)」↔「G-Men G-Mon」/
  「ハルでした」↔「春でした」(いずれも正しく ok 判定)
- **誤検出 mismatch**: 「実需を測る」↔「実需を図る」(同音異字 はかる) /
  「四半期決算」↔「市販機決算」(同音 しはんき) — 音声は正しいのに Whisper が同音の
  別漢字を当てた ASR 側のゆれ
- **誤検出疑い insertion**: 「強制製品認証（シーシーシー認証）」↔「強制製品認証各区、
  CCC認証」— 括弧の読み下しに伴う聞き取りノイズ
- **真陽性疑い (このままで良い)**: 「半導体市況」↔「半導体ガシモン」(同音ではない →
  TTS の実誤読の可能性)

いずれも `LLMAsrJudge` の system プロンプト (`ASR_JUDGE_SYSTEM_PROMPT`) の判定基準が粗く、
ASR (Whisper) 特有の同音異字誤変換や括弧読み下しノイズを考慮していなかったことが原因。
本チケットは `llm/asr_judge.py` の system プロンプトのみを精緻化する (判定ロジック・
`verify_sentence` の分岐・fast path 数字整合ガードなど T66 本体のコードは変更しない)。

## 変更内容

### `src/karyu_tech_news/llm/asr_judge.py` (`ASR_JUDGE_SYSTEM_PROMPT` のみ)

1. 冒頭に「書き起こしは不完全な ASR の出力であり、TTS が台本どおり正しく読み上げていても
   認識ゆれ (同音異字の誤変換、助詞・読点の聞き取りゆれ等) が生じうる」ことを明示。
2. ok の基準に追加:
   - **同音・類音の漢字違い** (例:「測る」↔「図る」、「四半期」↔「市販機」)。
   - 助詞・読点の聞き取りゆれ。
   - 括弧「（）」の読み下しに伴う軽微な語の増減
     (例:「強制製品認証（シーシーシー認証）」↔「強制製品認証各区、CCC認証」)。
3. mismatch の定義を厳格化: 数字の値の相違 (既存、最優先のまま維持) /
   **同音・類音では説明できない**単語レベルの明確な相違
   (例:「半導体市況」↔「半導体ガシモン」) / 文そのものの欠落。
4. insertion の定義を厳格化: 台本に無い**文・フレーズ単位**の追加発話に限定し、
   単語 1 個程度の聞き取りゆれは insertion にしないことを明記。
5. 既存の判定基準 (カナ↔英字表記ゆれ、漢数字↔算用数字表記ゆれ、数字誤読の最優先検出) は
   維持 (変更なし)。

判定ロジック側 (`LLMAsrJudge.judge()` の parse/fail-open 処理、`build_llm_asr_judge()`、
`verify_sentence` の fast path / 数字整合ガード) は無変更。プロンプト文言のみの変更のため
`tests/test_tts_asr_gate.py` 側の追加・変更もない。

## テスト (`tests/test_llm_asr_judge.py`, +9件)

プロンプトが実際にこれらのケースを正しく判定するかは実 API でしか検証できないため、
(a) プロンプト文言の存在アサート (実測4ケースの語彙・基準がプロンプトに含まれること) と、
(b) fake LLM 応答を注入した場合に `LLMAsrJudge` がその verdict をそのまま通す配線確認
(既存の `_mock_client` パターンを踏襲、実 API は呼ばない) の 2 系統で固定した。

### (a) プロンプト文言の存在アサート (5件)

- `test_prompt_mentions_transcript_is_imperfect_asr_output`: 「不完全な ASR」の明示。
- `test_prompt_treats_homophone_kanji_variance_as_ok`: 「測る」/「図る」/「四半期」/
  「市販機」が基準文に含まれること。
- `test_prompt_treats_parenthetical_readout_noise_as_ok`: 「括弧」および実例
  「シーシーシー認証」が含まれること。
- `test_prompt_mismatch_definition_requires_non_homophone_difference`: 「同音」および
  実例「半導体市況」「半導体ガシモン」が含まれること。
- `test_prompt_insertion_definition_restricted_to_phrase_or_sentence_level`:
  「フレーズ単位」「単語 1 個」(単語単位を insertion にしない明記) が含まれること。

### (b) judge 動作の配線確認 (fake LLM 応答、4件)

- `test_llm_asr_judge_homophone_kanji_hakaru_returns_ok`: 「実需を測る。」↔「実需を図る」
  で fake 応答 ok → `judge()` が `"ok"` を返す。
- `test_llm_asr_judge_homophone_shihanki_returns_ok`: 「四半期決算。」↔「市販機決算」で
  fake 応答 ok → `"ok"`。
- `test_llm_asr_judge_parenthetical_readout_noise_returns_ok`:
  「強制製品認証（シーシーシー認証）。」↔「強制製品認証各区、CCC認証」で fake 応答 ok
  → `"ok"`。
- `test_llm_asr_judge_true_misread_gashimon_returns_mismatch`: 「半導体市況。」↔
  「半導体ガシモン」で fake 応答 mismatch → `"mismatch"` (真陽性疑いはそのまま検出される
  ことの回帰防止)。

## 品質ゲート (fresh 実行)

```
$ uv run pytest --no-header -rN
735 passed, 11 skipped in 36.23s

$ uv run pytest -q  (素の exit code 確認、パイプ不使用)
exit code: 0

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 96 source files

$ git diff --check
(出力なし = クリーン)
```

## 仕様から外れた判断・不確かな点

- **プロンプト精緻化の実効性は実 API でのみ検証可能**: 本チケットのテストはプロンプトの
  文言存在とコード側の配線 (fake 応答の通過) のみを固定しており、実際に LLM (openai-luna)
  がこれらの基準に従って正しく判定するかどうかは実 produce 実行での再検証が必要。次回
  produce 実行時の曖昧域判定ログでの確認を推奨 (人間判断・運用側のフォローアップ)。
- **判定ロジック・閾値は変更しない**: 依頼が「system プロンプトのみ」と明示していたため、
  `FAST_PATH_SIMILARITY` / `SIMILARITY_MISMATCH_THRESHOLD` / 数字整合ガード等の T66 本体の
  ロジックには一切触れていない。
