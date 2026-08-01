# T66 — ASR 検査の曖昧域を LLM 判定に (表記ゆれ吸収と数字誤読検出) (Issue #76)

- 日付: 2026-08-02
- ブランチ: `agent/T66-llm-asr-judge-impl`
- 実装者: Claude Code
- 参照: [Issue #76](https://github.com/Gazelle221B/panda-tech-news/issues/76)

## 背景

T58 の ASR ゲート (`tts/asr_gate.py`) は Whisper 書き起こしと期待文を difflib 類似度 +
長さ比で突き合わせているが、表記ゆれ (エーアイ↔AI 等) を吸収できず類似度閾値を 0.5 まで
緩めており、数字の誤読 (「2027年」→「2017年」) を原理的に検出できない限界があった。
本チケットは Issue #76 の 2 段構え設計 (fast path 機械比較 + 曖昧域のみ LLM 判定) を実装する。

## 変更内容

### 1. `src/karyu_tech_news/tts/asr_gate.py`

- 閾値定数 `FAST_PATH_SIMILARITY = 0.85` を新設 (既存の `SIMILARITY_MISMATCH_THRESHOLD = 0.5` /
  `LENGTH_RATIO_INSERTION_THRESHOLD = 1.6` は変更なし)。
- `AsrJudge` Protocol (`runtime_checkable`) を新設: `judge(expected, transcript) ->
  AsrVerdictStatus | None`。None は判定不能を意味し fail-open のシグナルとする。
- `verify_sentence` に keyword-only `judge: AsrJudge | None = None` を追加し、3 段分岐に変更:
  1. 類似度 < 0.5 → `mismatch` (judge 不呼出)
  2. 類似度 >= 0.85 かつ長さ比 <= 1.6 → `ok` (fast path、judge 不呼出)
  3. それ以外 (曖昧域) → `judge` があれば委譲し、None を返せば従来の機械判定
     (長さ比のみで ok/insertion) にフォールバック。`judge` 未指定時も同じ機械判定。
- `judge` 未指定時の挙動は完全に従来と同一 (既存テスト全件が無変更で通ることを確認済み、
  後方互換の直接証跡)。

### 2. `src/karyu_tech_news/tts/synthesize.py`

- `synthesize_script` に `asr_judge: AsrJudge | None = None` を追加し、初回合成・ASR リトライの
  両方の `verify_sentence` 呼び出しへ `judge=asr_judge` としてそのまま中継。
- `AsrJudge` の import を追加 (`AsrBackend` と同じ `tts.asr_gate` から)。

### 3. `src/karyu_tech_news/llm/asr_judge.py` (新規)

`tts.asr_gate.AsrJudge` Protocol の LLM 実装。**tts 層は本モジュールを import しない**
(逆方向: 本モジュールが `tts.asr_gate` から型 `AsrVerdictStatus` のみを参照する片方向)。

- `ASR_JUDGE_SYSTEM_PROMPT`: 表記ゆれ (カナ↔英字/漢数字↔算用数字) は ok 扱い、数字の値の
  相違は mismatch 最優先、台本にない発話の挿入は insertion、と明記した system プロンプト
  (全文は本ログ末尾)。`json_mode=True` + `temperature=0.0` (edit/judge.py の
  `JUDGE_TEMPERATURE` と同じ流儀) で `{"verdict": "ok|mismatch|insertion", "reason": "..."}`
  を要求する。
- `_extract_json_object`: edit/judge.py の頑健 JSON 抽出ロジックを移植 (llm 層から edit 層への
  逆依存を避けるため、共有化はせずローカルへ複製)。
- `LLMAsrJudge.judge()`: LLM 呼び出し失敗 (`LLMError`)・JSON 抽出失敗・pydantic スキーマ不正
  (`ValidationError`、未知の verdict 値含む) をすべて捕捉し WARN ログの上 `None` を返す
  (fail-open)。
- `build_llm_asr_judge(profile_label)`: `config/llm_profiles.yaml` からプロファイル解決 +
  `LLMClient` 構築を行う。プロファイル未解決 (`ValueError`)・API キー未設定 (`LLMError`) など
  構築時失敗も種類を問わず fail-open で `None` を返す (persona 読み込み失敗時と同じ
  「WARN + 続行」の流儀)。

### 4. `src/karyu_tech_news/main.py` (`produce` コマンド)

- persona の `tts.asr_judge_profile` (既定 `"openai-luna"`) を読み、`asr_gate_enabled` が
  真のときのみ `build_llm_asr_judge()` を呼んで `asr_judge` を構築する。`asr_gate_enabled` が
  偽なら judge を構築しない (既存の `asr_backend` 構築と同じ条件分岐)。
- segment ループ内の `synthesize_script(...)` 呼び出しへ `asr_judge=asr_judge` を追加。
- import は `karyu_tech_news.llm.asr_judge` から遅延 import (既存の他モジュール import と
  同じくコマンド関数内)。

### 5. `config/hal_persona.yaml`

`tts.asr_gate: true` の直後に `tts.asr_judge_profile: openai-luna` を追記。既存プロファイルは
T64 で editor 用に採用済みの OpenAI データ共有キャンペーン枠 (無料) を流用する旨、呼び出し
頻度が曖昧域のみ (数文/日) で枠を圧迫しない旨、`deepseek` 等へ変更可能な旨をコメントで明記
(手書き YAML の書式・コメント密度を維持)。

## テスト

### `tests/test_tts_asr_gate.py` (+7件、既存は無変更)

- `test_fake_judge_satisfies_protocol`: fake judge が `AsrJudge` Protocol を満たすことを確認
  (`AsrBackend` の既存パターンを踏襲)。
- `test_verify_sentence_fast_path_does_not_call_judge`: 高類似度・正常長さ比では judge が
  一切呼ばれないことを固定 (誤判定を返す fake judge を仕込んでも無視される)。
- `test_verify_sentence_definite_mismatch_does_not_call_judge`: 類似度 < 0.5 の壊滅的不一致でも
  judge 不呼出のまま即 mismatch。
- `test_verify_sentence_ambiguous_zone_calls_judge_and_uses_its_verdict`: 曖昧域
  (「AI」↔「エーアイ」、類似度 0.5〜0.85 未満) で judge が呼ばれ、その戻り値が採用される
  ことを確認 (機械判定のみなら ok になるはずの文を、judge が mismatch と判定したケース)。
- `test_verify_sentence_judge_none_falls_back_to_mechanical_status`: judge が None (判定不能)
  を返したら機械判定にフォールバックすることを固定 (fail-open)。
- `test_verify_sentence_ambiguous_zone_without_judge_uses_mechanical_status`: judge 未指定の
  後方互換を明示的に再確認。
- `test_verify_sentence_ambiguous_zone_number_mismatch_detected_via_judge`: 「2027年。」→
  「2017年」が機械判定のみでは曖昧域で `ok` になってしまう (数字誤読を拾えない実測) ことを
  先に確認した上で、fake judge を注入すると `mismatch` になることを固定 (T66 の主目的)。

### `tests/test_llm_asr_judge.py` (新規、14件)

- `_extract_json_object` の素直な JSON / フェンス付き / 不正入力の3系統。
- `LLMAsrJudge.judge()` の ok / mismatch / insertion の3系統 (fake `ChatClient`、
  `edit/judge.py` の `_mock_client` パターンを踏襲)。
- JSON 崩れ (`test_llm_asr_judge_broken_json_fails_open_to_none`) と未知の verdict 値
  (`test_llm_asr_judge_unknown_verdict_value_fails_open_to_none`) がいずれも `None` に
  fail-open することを固定。
- `LLMError` 発生時の fail-open (`test_llm_asr_judge_llm_error_fails_open_to_none`)。
- `json_mode=True` / `temperature=0.0` が渡ることの契約テスト。
- `build_llm_asr_judge` の未知プロファイル (`ValueError` 経由 fail-open) と API キー未設定
  (`LLMError` 経由 fail-open、`monkeypatch.delenv("OPENAI_API_KEY")`) の2系統。
- `test_number_mismatch_detected_end_to_end_via_verify_sentence`: fake LLM 応答
  (`{"verdict": "mismatch", ...}`) を注入した `LLMAsrJudge` を `verify_sentence` に渡し、
  数字誤読 (2027年→2017年) が end-to-end で `mismatch` として検出されることを確認する統合テスト
  (Issue #76 DoD の該当項目)。

### 既存 produce テストの hermetic 性

`tests/test_produce_pipeline.py` の既存 produce テストは `persona.yaml` に
`tts:\n  primary_engine: mock\n` (asr_gate 未設定→既定 false) または明示 `asr_gate: false` を
渡すもののみで、`asr_gate_enabled` が真になるテストは3件 (`test_produce_asr_gate_enabled_
constructs_backend` / `test_produce_asr_gate_unavailable_fails_fast`)。これらは
`WhisperAsrBackend` 構築直後・ASR 到達前 (zero-frame audio による skip、または
`AsrUnavailableError` 伝播) で produce が exit するため、`asr_judge.judge()` (LLM 呼び出し) には
到達しない。`build_llm_asr_judge()` 自体は呼ばれるが、実 `config/llm_profiles.yaml` を読んで
`LLMClient` を構築するだけ (ネットワーク呼び出しなし) であり、`OPENAI_API_KEY` 未設定でも
`LLMError` を捕捉して `None` を返す fail-open のため、既存アサーション (exit_code / 出力文字列 /
`backend_cls.call_count`) はすべて無変更で成立することを確認済み。

## 品質ゲート (fresh 実行)

```
$ uv run pytest --no-header -rN
723 passed, 11 skipped in 14.15s

$ uv run pytest -q  (素の exit code 確認、パイプ不使用)
exit code: 0

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 96 source files

$ git diff --check
(出力なし = クリーン)
```

## LLM judge プロンプト全文 (`llm/asr_judge.py` `ASR_JUDGE_SYSTEM_PROMPT`)

```text
あなたは日本語ニュース番組の TTS 読み上げ QA 判定器。台本の期待文と ASR (音声認識) の書き起こしを突き合わせ、読み上げとして忠実かどうかを判定する。JSON だけを返し、説明・前置きを書かない。
判定基準:
- 表記ゆれ (カナ↔英字表記、例:「AI」↔「エーアイ」/ 漢数字↔算用数字表記、例:「二千二十七年」↔「2027年」) は同一の内容とみなし ok。
- 数字の値そのものが相違している場合 (例: 期待文の「2027年」に対し書き起こしが「2017年」) は mismatch。年号・件数・金額など意味が変わる数字の誤読を最優先で拾う。
- 台本に無い発話が語頭・語尾などに挿入されている場合は insertion。
- 上記いずれにも該当せず、読み上げとして意味が保たれていれば ok。
出力スキーマ (JSON): {"verdict": "ok" または "mismatch" または "insertion", "reason": "20字程度の日本語理由"}
```

user プロンプトは `期待文 (台本): {expected}\nASR書き起こし: {transcript}` の固定テンプレート。

## 仕様から外れた判断・不確かな点

- **fast path 閾値の副作用**: `2027年。`→`2017年` のような 1 桁差の数字誤読は、周辺文が長いと
  類似度が容易に 0.85 以上になり fast path で LLM 未経由のまま `ok` 判定される (実測: 短い文
  「2027年。」のみだと類似度 0.8 で曖昧域に入るが、「来年の2027年に発表される見込みです。」の
  ような長文では類似度 0.947 で fast path に入ってしまう)。これは Issue #76 が明示的に指定した
  fast path 条件 (「類似度 >= 0.85 かつ長さ比正常 → 即 ok」) をそのまま実装した結果であり、
  仕様どおりの trade-off として受け入れた (閾値変更は依頼スコープ外、コスト試算・実測に基づく
  人間判断が必要と判断)。テスト (`test_verify_sentence_ambiguous_zone_number_mismatch_detected_
  via_judge`) では曖昧域に確実に入る短文例を選定して主目的 (曖昧域での LLM 判定が機能すること)
  を固定した。
- **`_extract_json_object` の共有化を見送り**: `edit/judge.py` に同等のロジックが既にあるが、
  `AGENTS.md` §5 のディレクトリ構成 (collect/store/deliver/llm/edit/script の順) と、
  `edit` が `llm` に依存する既存の向き (edit/judge.py が llm.client を import) から、`llm` 層が
  `edit` 層に依存するのは逆向きの疑いがあると判断し、Surgical Changes の原則に従い小さな
  ヘルパーをローカル複製するに留めた (共通化するなら別チケットで両方から参照可能な位置への
  切り出しが妥当)。
- **`llm/asr_judge.py` が `tts.asr_gate.AsrVerdictStatus` 型を import している点**: Issue #76 の
  制約は「tts 層が llm 層を import しない」(一方向) であり、逆方向 (llm 層が tts 層の型を
  参照する) は明示的に禁止されていない。`AsrJudge` Protocol は構造的部分型のため実行時には
  この import は不要だが、mypy strict での戻り値型の正確性のために採用した。tts → llm の
  機能依存は発生していないことを import grep で確認済み。
- **produce に `--profiles-file` 相当のオーバーライドオプションを追加しなかった**: Issue #76 は
  `config/llm_profiles.yaml` からの解決のみを求めており、`draft` コマンドにある
  `profiles_file` オプションのような CLI 差し替え口は言及がないため、スコープ膨張を避け
  `DEFAULT_LLM_PROFILES_PATH` 固定とした。
