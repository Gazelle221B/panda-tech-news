# T68 — v4 シャドーランナー (日次影レンダリング + 三層測定 + メトリクス蓄積) (v4 移行トラック Phase 2-b, Issue #91)

- 日付: 2026-08-03
- ブランチ: `agent/T68-shadow-runner-impl`
- 実装者: Claude Code (Opus, 委任実行)
- 参照: [Issue #91](https://github.com/Gazelle221B/panda-tech-news/issues/91)、[Issue #88](https://github.com/Gazelle221B/panda-tech-news/issues/88) (v4 移行トラック全体計画・P0 診断)、[Issue #86](https://github.com/Gazelle221B/panda-tech-news/issues/86) (短文終端幻話の実測)、[PR #90](https://github.com/Gazelle221B/panda-tech-news/pull/90) (T67, 前提チケット)

## 背景

Issue #88 の P0 診断で、v4 短文幻話の根本原因は duration predictor の短文過大予測と確定し、
`irodori.seconds` 固定で解消することを実証済み。T67 (PR #90) で `SynthesisRequest.irodori_options`
のパススルーと `synthesize_script(min_sentence_chars=, sentence_options_fn=)` フックが整った。
本チケットはこれらを使い、本番 (v3, port 8088) を無停止・無変更のまま、当日の実台本 + 固定回帰
セットをシャドー (v4, port 8089) で毎日レンダリングし、Sol 設計の三層測定でメトリクスを蓄積する
(15 運用+600/300 文の昇格判定に向けたデータ収集)。

## 実装

### 1. `scripts/shadow_v4_run.py` (新規)

Issue #91 の 1〜6 をそのまま実装。engine 抽象 (`TTSEngine`) は経由せず、per-request の irodori
オプション制御 (`seconds`/`seed`) が主目的のため直接 httpx で `POST /v1/audio/speech` を叩く
(v3: 8088 / v4 シャドー: 8089)。文セット構築 (辞書適用・分割・マージ) は repo モジュール
(`tts/normalize.py::prepare_tts_text`/`split_markdown_topics`、`tts/synthesize.py::split_sentences`)
をそのまま再利用し、短文マージ (`_merge_short_sentences`, private) も T67 でテスト済みのロジックを
そのまま呼び出す (独自再実装しない)。

主な構成:

1. **前提確認**: v3 (8088) health 必須。無ければ即 abort (return 1)。v4 シャドー (8089) が down
   なら `~/tools/Irodori-TTS-Server-v4` で起動し (`uv run --no-sync python -m irodori_openai_tts
   --host 127.0.0.1 --port <port>`)、`/health` の `"loaded":true` を最大 180s ポーリングする。
   起動失敗・health タイムアウトは fail-open (`v4_available=False` を記録して続行、個別文の測定は
   スキップ)。本ジョブが起動した場合のみ終了時に停止する (daily_pipeline.sh と同じ流儀)。
2. **文セット構築 (三層)**: ①最新 episode_drafts の markdown → `split_markdown_topics` →
   `prepare_tts_text` (自動+手動の二層辞書マージ, T56 と同じ流儀) → `split_sentences` →
   `_merge_short_sentences` (既定 `min_sentence_chars=20`)。②既知失敗文・③層化回帰セットは
   `scripts/data/shadow_regression_sentences.yaml` に固定し、マージは適用しない (短文の
   duration predictor 挙動をそのまま観測するのが層化回帰セットの目的のため、①のみマージ対象)。
3. **各文の処理** (`process_sentence`): v3 合成 (`irodori.seed` 固定) → `tts/quality.py::
   analyze_wav_signal` で実測尺 dur3 → v4 合成 (`irodori_options={"seconds": dur3+0.25,
   "seed": 固定}`) → 両方を `tts/asr_gate.py::WhisperAsrBackend` (turbo, CPU, 遅延ロード) で
   書き起こし → メトリクス計算。1 文の失敗は記録して次の文へ continue (fail-open)。
   `AsrUnavailableError` (whisper 未導入) だけは揉み消さず呼び出し元 (`main`) まで伝播させ、
   ラン全体を中断する (全文が同じ理由で失敗するため個別 skip に意味がない)。
4. **メトリクス**:
   - (a) 正規化類似度・(d) v3/v4 書き起こし同士の類似度: いずれも `difflib.SequenceMatcher.ratio()`
     (期待文でなく v3⇄v4 の書き起こし同士を比較するのが (d) のポイント)。
   - (b) Kana-CER 近似 (`compute_kana_cer`): `get_opcodes()` で insert/delete/replace を分離集計。
     `replace` opcode は短い側の長さを置換、余剰を insert/delete に振り分ける近似。
     `cer = (insertions+deletions+substitutions) / 期待文長`。
   - (c) 幻話疑い (`detect_hallucination_suspicion`): `(長さ比 > 1.15) or (末尾 diff が insert で
     3 文字以上)`。閾値は `LENGTH_RATIO_SUSPICION_THRESHOLD`/`TRAILING_INSERTION_MIN_CHARS` として
     定数化 (Issue #91 指定値)。
   - 正規化は asr_gate と同じ方針 (小文字化+空白/句読点除去) だが、`asr_gate._normalize` (private)
     への直接結合は避け、本モジュールで独立定義した (2 行の軽量ロジックのため複製の方がモジュール
     間結合を減らせると判断。マージ規則の再利用とは異なり、複製コストが極小)。
5. **出力**: `data/shadow_v4/report_YYYYMMDD_HHMM.json` (全文詳細 + summary + config + config_hash) +
   `data/shadow_v4/history.jsonl` に集計 1 行追記 (run_id, 文数, エラー数, 幻話疑い数, CER 中央値,
   config_hash, config_changed, v4_available)。
6. **Issue #88 へのコメント投稿**: `gh issue comment` を subprocess 経由で呼ぶ (fail-open、失敗して
   もラン自体は成功扱い)。`--report-issue`/`--no-report-issue` (`argparse.BooleanOptionalAction`,
   既定 on) で制御。本文は 7〜8 行に収め、10 行以内の指定を満たす。
7. **構成変更検知**: `ShadowConfig` (whisper_model/seed/min_sentence_chars/voice/model/
   v4_server_rev (`git -C <dir> rev-parse HEAD`, fail-open)/v4_ref_audio_sha256
   (`voices/hal.wav` の sha256, fail-open) + 閾値定数) を JSON 正規化して sha256 化し、
   history.jsonl の直近行と比較。変わっていれば history 行に `config_changed: true` を記録し、
   Issue コメントにも「⚠️ 構成変更を検知 → 昇格カウントリセット」を明記する (Sol 指針)。

### 2. `scripts/data/shadow_regression_sentences.yaml` (新規)

- `known_failures` (10 文): Issue #86 の実測 2 文 (「キャスターのハルです。」「今日の華流テック
  通信は以上です。」) + 番組固定フレーズ (`config/hal_persona.yaml`/`docs/hal-persona.md` の
  title_call/opening/closing/topic_transitions/rumor_marker から派生)。毎エピソード必ず読まれる
  短文で、v4 の duration predictor 過大予測の実害が最も大きいカテゴリ。
- `stratified` (4 バケット × 6 カテゴリ = 24 文): 4-8/9-12/13-16/17-24 字 (読み辞書適用後の目安の
  字数) × baseline/digits/ascii_abbrev/chinese_name/parens/quote。番組の実文体で自作。
  digits カテゴリの 1 文 (「来年の2027年に発表される見込みです。」) は `tts/asr_gate.py`
  docstring に記載の実測誤読パターン (2027年→2017年) をそのまま採用した。

### 3. `.gitignore` の修正 (Issue 発見・スコープ内対応)

`data/` (非アンカー) が `scripts/data/` も意図せず除外することを `git check-ignore -v` で発見。
Issue #91 は本フィクスチャを「新規作成、レビュー可能な形」と明記しており、git 追跡が必須のため、
`!scripts/data/` で明示的に復元した (既存の `!data/.gitkeep`/`!assets/sfx/transition.wav` 等と
同じ「ignore の中の例外」パターン)。

## テスト (新規 58 件, `tests/test_shadow_v4_run.py`)

`scripts/` はパッケージ化されていないため、`generate_bgm.py` のテストと同じ importlib 動的
import を使う。**Python 3.12 の `dataclasses(slots=True)` は `sys.modules[cls.__module__]` の
存在を要求する**ため (`SentenceItem` 等が `slots=True`)、`exec_module` 前に `sys.modules` へ
登録する 1 行を追加した (`generate_bgm.py` には slots dataclass が無いため踏んでいなかった不具合。
未対応のまま importlib ロードすると `AttributeError: 'NoneType' object has no attribute
'__dict__'` で全滅することを実機で確認済み)。

- **文セット構築** (10件): トピック境界分割・マージのトピック境界不越境・トピック内マージ・
  読み辞書適用・source_id 追跡可能性 (daily_draft)。回帰セット読込の件数/バケット/カテゴリ・
  source_id 一意性・マージ非適用・読み辞書適用・不正 YAML 形状の reject (known_failure)。
  三層結合 (build_sentence_set)。
- **メトリクス計算** (10件): Kana-CER の完全一致/末尾挿入/削除/置換 (数字誤読) 分離集計。
  幻話疑い判定の末尾挿入/長さ比/完全一致/閾値未満 (誤検出しないこと)。v3/v4 書き起こし一致度。
- **構成ハッシュ** (4件): 同一入力での安定性、seed/server_rev/ref_audio_hash 変化での可変性。
- **ハッシュ/subprocess ユーティリティ** (8件): sha256_file の存在/非存在、git_rev の成功/非ゼロ
  終了/OSError (いずれも `subprocess.run` をモックし実 git は呼ばない)。
- **health チェック** (7件): `httpx.MockTransport` で 200/非200/loaded true・false/接続エラー、
  `wait_for_health` の即成功/タイムアウト (実サーバは使わない)。
- **process_sentence** (4件): 正常系 (v3実測尺+0.25s が v4 seconds に伝わる・CER/幻話/一致度が
  計算される)、v3 失敗の fail-open、v4 失敗時も v3 測定は保持、`AsrUnavailableError` の伝播。
  いずれも `httpx.MockTransport` + fake ASR backend で完結し実サーバに依存しない
  (Issue #91 は「ランナー本体は実サーバ依存のため単体テスト対象外でよい」としているが、
  fake client/backend で完結できる `process_sentence` の分岐は品質向上のため追加した。
  実プロセス起動・停止を伴う `run_shadow`/`main` のオーケストレーション本体はテスト対象外の
  ままとした)。
- **レポート/history I/O** (7件): summary 集計 (件数・幻話疑い数・CER中央値・None フォールバック)、
  JSON ファイル書き出し、history round-trip、複数行時の最終行取得、欠落/破損 JSON の fail-open。
- **Issue コメント** (4件): 10 行以内、構成変更警告の有無、v4 利用不可時の NG 表示。
- **post_issue_comment** (4件): 成功、非ゼロ終了・タイムアウト・OSError での fail-open
  (いずれも `subprocess.run` をモックし実 `gh` は呼ばない)。

## 品質ゲート (fresh 実行)

```
$ PYTHONUTF8=1 uv run pytest -q --junitxml=...
(パイプなし・素実行で exit code を直接確認)
EXIT_CODE=0
<testsuite errors="0" failures="0" skipped="11" tests="820" .../>
# skipped 11 件は test_daily_pipeline.py の Windows 限定スキップ (既存、本チケット無関係)
# 762 (T67時点) → 820 (+58, 本チケット追加分)

$ uv run ruff check .
(1件: tests/test_shadow_v4_run.py の SIM117 ネスト with 指摘 → `with (a as b, c):` へ統合し再実行)
All checks passed!

$ PYTHONUTF8=1 uv run mypy src tests scripts/shadow_v4_run.py
Success: no issues found in 98 source files
# 96 (T67時点) → 98 (+2, shadow_v4_run.py / test_shadow_v4_run.py)

$ git diff --check
(出力なし = クリーン)
```

## 保守側に倒した判断 (仕様から外れた/補足した点)

- **`_normalize_for_metrics` を独立定義**: `asr_gate._normalize` (private) を import せず、同じ
  正規化規則 (小文字化+句読点/空白除去) を本モジュールに複製した。短文マージ (`_merge_short_
  sentences`) は「T67 でテスト済みのロジックとの乖離防止」が独自再実装しない理由として明確だが、
  正規化は 2 行の軽量ロジックであり、private シンボルへの結合を避ける方が長期的な保守性が高いと
  判断した (Simplicity First / Surgical Changes)。
- **②③レイヤーにはマージを適用しない**: Issue #91 の記述 (①のみ `min_sentence_chars=20` 適用と
  明記) どおり。層化回帰セットは「短文の duration predictor 挙動をそのまま観測する」ことが目的
  のため、マージで短文が消えると層化の意味が失われる。
- **`process_sentence` の fake-client テストを追加**: Issue はランナー本体を単体テスト対象外として
  よいとしているが、`httpx.MockTransport` + fake ASR backend で実サーバなしに完結できる範囲
  (fail-open 分岐・v3実測尺→v4秒指定の伝播・`AsrUnavailableError` 伝播) は固定した方が安全と判断。
  実プロセス起動/停止・health ポーリングを伴う `run_shadow`/`main` は対象外のまま。
- **v3/v4 で同一 `--voice`/`--model` を使う**: 両サーバの `voices.json`/`model_name` 設定が
  同一想定であるため単一 CLI フラグにまとめた (Sol 設計・daily_pipeline.sh の既存運用と整合)。
  将来 v4 側が異なる voice/model 設定を採る場合は CLI 引数を分離する必要がある。
- **リトライなし**: `tts/irodori.py::IrodoriTTSEngine` と異なり `synthesize_wav` は一過性エラーを
  リトライしない (Simplicity First。実運用でシャドーの偽陽性率が高いようならリトライ追加を検討)。
- **`.gitignore` に `!scripts/data/` を追加**: 上記「実装」節に既述。Ticket スコープ外の広範な
  リファクタは行わず、本チケットの成果物 (回帰セット YAML) が git 追跡されるための最小差分に
  留めた。
- **実サーバでの実走は行っていない**: 依頼どおり、モック単体テストまでの実装に留め、実 Irodori
  v3/v4 サーバへの接続・`gh issue comment` の実投稿は行っていない (オーケストレータ側の担当)。

## 変更ファイル一覧

- 新規: `scripts/shadow_v4_run.py`, `scripts/data/shadow_regression_sentences.yaml`,
  `tests/test_shadow_v4_run.py`, `docs/test-logs/2026-08-03-T68-shadow-runner.md`
- 変更: `.gitignore` (`!scripts/data/` 追加)
