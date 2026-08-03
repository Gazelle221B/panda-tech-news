# T67 — irodori オプションのパススルーと設定ゲート付き短文マージ (v4 移行トラック Phase 2-a, Issue #89)

- 日付: 2026-08-03
- ブランチ: `agent/T67-irodori-options-impl`
- 実装者: Claude Code (Opus, 委任実行)
- 参照: [Issue #89](https://github.com/Gazelle221B/panda-tech-news/issues/89)、[Issue #88](https://github.com/Gazelle221B/panda-tech-news/issues/88) (v4 移行トラック全体計画)

## 背景

Issue #88 の P0 診断で、v4 の幻話は duration predictor の短文過大予測が根本原因と確定し、
`irodori.seconds` 固定で解消することを実証済み。本チケットはこれをパイプラインから制御
可能にする第一弾で、以下 3 点を実装した。

1. `SynthesisRequest.irodori_options` のパススルー
2. `synthesize_script` の `min_sentence_chars` (設定ゲート付き短文マージ、既定 off)
3. `synthesize_script` の `sentence_options_fn` per-sentence フック (シャドーランナー用の口)

## 実装

### 1. irodori_options パススルー

- `tts/engine.py`: `SynthesisRequest` に `irodori_options: dict[str, Any] | None = None` を追加。
- `tts/irodori.py`: `IrodoriTTSEngine.synthesize()` で `caption` と `irodori_options` を同じ
  `body["irodori"]` オブジェクトへマージする。`caption` を先に入れてから `irodori_options` で
  `update()` するため、理論上キーが競合すれば `irodori_options` が勝つ (実運用では別キー集合の
  想定なので競合しない)。どちらも無ければ `irodori` キー自体を送らない (既存の 500M 無害挙動を
  維持)。非対応エンジン (mock/kokoro) は `irodori_options` を単に無視する (Protocol 上、
  合成に使うかどうかは各エンジン実装次第)。

### 2. min_sentence_chars 短文マージ

- `tts/synthesize.py` にモジュール関数 `_merge_short_sentences(sentences, min_chars, max_chars)`
  を追加し、`synthesize_script` の **`split_sentences` 直後・絵文字注釈や ASR ゲートより前**
  (segment ごとのループ内) で適用する。これにより:
  - マージ後の文がそのまま絵文字注釈前の `sentence` (= ASR ゲートの期待文) になる。
  - segment (topic) 単位の分割済みリストにのみ適用するため、topic 境界は構造的に越えない
    (テストで実証、後述)。
- マージ規則: 空白除去後 `min_chars` 未満の文は **次文優先** で前方へ連結し続け、末尾に残った
  短文だけ前文へマージする。マージ後の文字数が `max_chars` を超える場合はマージを見送る
  (安全側、Issue の要求どおり)。
- `min_sentence_chars=0` (既定) は早期 return で入力をそのまま返す no-op。
- `config/hal_persona.yaml` の `tts` ブロックに `min_sentence_chars: 0` をコメント付きで追加
  (v4 では 20 目安、Issue #88 参照)。
- `main.py` の `produce` が persona から `tts.min_sentence_chars` を読み、`int(... or 0)` で
  正規化して各 segment の `synthesize_script` 呼び出しへ伝搬する (既存の `caption` /
  `asr_gate` と同じ読み込み流儀)。

### 3. sentence_options_fn フック

- `synthesize_script` に `sentence_options_fn: Callable[[str], dict[str, Any] | None] | None = None`
  を追加。(マージ後・絵文字注釈前の) `sentence` ごとに呼び出し、戻り値をそのまま
  `SynthesisRequest.irodori_options` として初回合成・ASR リトライ合成の**両方**に渡す
  (どちらも同じ `sentence_options` 変数を再利用するため呼び出しごとにブレない)。
  `None` (既定) なら呼び出し自体を一切行わず、`irodori_options` は `None` のまま
  (後方互換)。

## 互換性の実証 (既定値 3 点の組で完全後方互換)

`min_sentence_chars=0` (既定) / `sentence_options_fn=None` (既定) / `irodori_options=None`
(既定) の組で、**既存テストを 1 行も改修せず**全緑であることを確認した (下記ゲート参照)。
唯一触れた既存コードは `tests/test_tts_synthesize.py` の `_recording_engine` ヘルパーへの
`max_chars: int = 100` オプション引数追加のみで、これは全既存呼び出し元が省略するため
挙動不変 (`git diff` で確認: 既存アサーション行は 1 行も変更していない)。

## テスト (新規 16 件)

### irodori_options パススルー (`tests/test_tts_irodori.py`, 4件)

- `test_irodori_options_passed_through_in_body`: options が body の `irodori` にそのまま乗る
- `test_irodori_options_none_omits_irodori_key`: None (かつ caption 無し) なら `irodori` キー自体を送らない
- `test_irodori_options_merge_with_caption`: caption と options が同じ `irodori` オブジェクトへ合流
- `test_irodori_options_without_caption_still_sends_irodori_key`: caption 無しでも options だけで送る

### 短文マージ (`tests/test_tts_synthesize.py`, 6件)

- `test_synthesize_script_no_merge_when_min_sentence_chars_default` / `_explicit_zero`: 無効時完全互換
- `test_synthesize_script_merges_short_sentence_with_next`: 20 (テストでは5) 指定で次文優先マージ
- `test_synthesize_script_merges_trailing_short_sentence_backward`: 末尾短文は前文へマージ
- `test_synthesize_script_merge_respects_max_chars_safety`: マージ後 max_chars 超過ならマージ回避
- `test_synthesize_script_merge_does_not_cross_segment_boundary`: topic 境界不越境

### sentence_options_fn フック (`tests/test_tts_synthesize.py`, 4件)

- `test_synthesize_script_no_sentence_options_fn_omits_irodori_options`: 未指定なら None のまま
- `test_synthesize_script_sentence_options_fn_passes_irodori_options`: 文ごとに呼び出し伝搬
- `test_synthesize_script_sentence_options_fn_sees_merged_sentence`: マージ後の文がフックに渡る
- `test_synthesize_script_sentence_options_fn_propagates_to_asr_retry`: ASR リトライにも同じ options

### main.py persona 配線 (`tests/test_produce_pipeline.py`, 2件)

- `test_produce_min_sentence_chars_default_zero_no_merge`: persona 未設定 = 0 (マージしない)
- `test_produce_min_sentence_chars_from_persona_merges_short_sentences`: persona の値が伝搬しマージされる

いずれも実 API は呼ばない (httpx モック / `MockTTSEngine` / 独自 recording engine)。

## 品質ゲート (fresh 実行)

```
$ PYTHONUTF8=1 uv run pytest -q --junitxml=...
(パイプなし・素実行で exit code を直接確認)
EXIT_CODE=0
<testsuite errors="0" failures="0" skipped="11" tests="762" time="28.874" .../>
# skipped 11 件は test_daily_pipeline.py の Windows 限定スキップ (既存、本チケット無関係)

$ uv run ruff check .
(1件の import 整形指摘 → 手動で複数行 import へ分割し修正 → 再実行で)
All checks passed!

$ uv run mypy src tests
Success: no issues found in 96 source files

$ git diff --check
(出力なし = クリーン)
```

## 保守側に倒した判断

- **irodori_options のキー検証はしない**: Issue の指示どおり「対応キー・検証はサーバ側仕様」
  として、`tts/irodori.py` 側では型 (`dict[str, Any]`) 以外の制約を課さずそのまま送る。
  将来サーバ側の対応キーが増減しても本チケットのコードは変更不要。
- **短文マージの適用単位を segment 単位に限定**: `synthesize_script` の既存ループ構造
  (`for seg in script.segments: ... for sentence in split_sentences(...)`) にそのまま
  乗せることで、「topic 境界を越えない」という要件を新たなガード条件を書かずに構造的に
  満たした (テストで実証)。
- **sentence_options_fn の引数はマージ後・絵文字注釈前の sentence**: 絵文字はスタイル制御
  トークンで発話されないため、duration 推定 (シャドーランナーの用途) に絵文字混じりの
  文字数を渡すと歪む。ASR ゲートの期待文と同じ変数を再利用することで一貫性を保った。
- **main.py への `sentence_options_fn` 配線は見送り**: Issue #89 の実装範囲はフックの提供
  までで、呼び出し側 (シャドーランナー) は Issue #88 の別チケットで実装される想定のため、
  本チケットでは `synthesize_script` のシグネチャ追加に留めた (スコープ膨張回避)。
