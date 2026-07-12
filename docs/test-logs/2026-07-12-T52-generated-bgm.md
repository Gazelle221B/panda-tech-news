# T52 — コード生成 BGM の暫定導入 (Issue #36)

- 日付: 2026-07-12
- ブランチ: `agent/T52-generated-bgm-impl`
- 実装者: Claude Code
- 参照: [Issue #36](https://github.com/Gazelle221B/panda-tech-news/issues/36)

## 背景

BGM/ジングル素材のライセンス確認 (Issue #36) が未確定のまま Sprint 2 で `mix/mixer.py` (T29)
を「素材非依存」設計にし、`assets/bgm/` が空なら passthrough する経路を用意していた。人間判断
(2026-07-12, Issue #36 コメント)「Algorave やライブコーディングみたいなコードで音楽作るやつで
一旦代用して」に基づき、ライセンス問題のない自前コード生成 BGM で暫定代用する。

## 変更内容

1. **`scripts/generate_bgm.py` 新規作成**: stdlib のみ (`wave` / `math` / `random` / `struct`。
   numpy 等の新規依存は追加しない, AGENTS §5 依存最小) で algorave 風のミニマルループ BGM を
   決定的に (seed 固定) 合成する。
   - 構成: 120 BPM・16 小節 (既定, `--bars` で 8〜16 の範囲で変更可)、A minor の簡易コード進行
     (i-VI-III-VII, 4小節ごとに切替) 上のナイーブなトライアングル波アルペジオ (16分音符グリッド)
     + 控えめな合成キック (1・3拍目) + 合成ハイハット (裏拍16分、ノイズバースト)。
   - 全イベントを加算合成した後、ピークが `-12dBFS` になるよう正規化 (`normalize_to_peak_dbfs`)。
     `mix/mixer.py` の `DEFAULT_BGM_GAIN_DB=-18dB` でさらに減衰されるため、トークの邪魔にならない
     控えめな最終音量になる (要求どおり)。
   - **ループ結合クリック対策**: `mix_bgm` は BGM をバックトゥバックで連結してループさせる
     (`bed = (bgm * loops)[:len(voice)]`) ため、連結境界 = ループ境界。先頭・末尾に短い
     (5ms, 業界標準の1〜10msレンジ) 線形 declick フェードを掛け、連結境界の不連続 (クリック) を
     防ぐ。個々の音符/キック/ハイハット自体にも短いアタック/ディケイのエンベロープを持たせ、
     ステップ間の不連続も避ける。
   - CLI: `uv run python scripts/generate_bgm.py [--out] [--bpm] [--bars] [--sample-rate] [--seed]
     [--peak-dbfs]`。既定出力先は `assets/bgm/generated_loop.wav` (`mix/mixer.py` の
     `find_bgm()` 既定ディレクトリと一致)。出力先の親ディレクトリが無ければ自動作成する。
   - **生成物 (wav) はコミットしない**: `assets/bgm/*` は `.gitignore` 対象 (`!assets/**/.gitkeep`
     の例外のみ)。各環境でスクリプトを実行してローカルに用意する運用とする。
2. **`tests/test_generate_bgm.py` 新規作成**: `scripts/` は非パッケージのため `importlib` で
   ファイルパスから動的 import してテストする。
   - 純ロジック (18 テスト中 17): `midi_to_hz` の基準点、`synth_tone`/`synth_kick`/`synth_hat`
     の長さ・declick エンベロープ・範囲・決定性、`normalize_to_peak_dbfs`・`apply_declick_fade`
     の数値的振る舞い、`build_arrangement` の決定性・長さ・ピーク音量、`samples_to_pcm16` の
     丸め込み/クランプ、`write_wav`/`main` の RIFF コンテナ・親ディレクトリ自動作成。
   - 統合テスト (1件、`@pytest.mark.skipif` で pydub/ffmpeg 不在時のみ関数単位 skip):
     生成 wav を実際に `mix/mixer.py::mix_bgm` に通し、RIFF 妥当性・出力長がボイス長に一致・
     ループが機能 (中間区間の RMS > 閾値)・ループ結合境界の跳躍量が小さい (クリック近似検証) こと
     を確認する。`tests/test_mix_mixer.py` と異なり、モジュール冒頭の
     `pytest.importorskip("pydub")` は使わず (それだと純ロジックテストまで巻き込んで skip される
     ため) `@pytest.mark.skipif(not (pydub入 and ffmpeg入))` で当該テストのみ skip する設計にした。
3. **README.md**: Quick start に `uv run python scripts/generate_bgm.py` の 1 行を追記
   (`init-db` の直後、`collect` の直前)。

## 検証

- `uv run python scripts/generate_bgm.py --out /tmp/t52_smoke.wav`:
  `生成完了: /tmp/t52_smoke.wav (32.0s, 48000Hz, peak=-12.0dBFS, seed=42)`
- 生成 wav を直接デコードして数値検証:
  `channels=1, sampwidth=2, framerate=48000, nframes=1536000` (32.0s と一致)、
  実測ピーク dBFS ≈ **-11.9997dBFS** (目標 -12.0dBFS と一致)、先頭サンプル `0`→漸増、
  末尾10サンプルは全て `0` (declick フェードが機能)。
- **pydub/ffmpeg 導入下での実ミックス統合テスト**: `uv sync --extra tts` で一時的に導入して
  `tests/test_generate_bgm.py` を実行し、`mix_bgm` 実経路を通る 18/18 テストが緑であることを
  確認 (`18 passed`)。確認後 `uv sync` (無 extra) に戻し、以降の品質ゲートは既定の依存構成
  (base) で実行している。

## 品質ゲート (fresh 実行, base 依存構成)

```
$ uv run pytest
555 passed, 2 skipped in 19.49s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 83 source files

$ uv run mypy scripts/generate_bgm.py --strict
Success: no issues found in 1 source file

$ git diff --check
(出力なし = クリーン)

$ uv lock --check
Resolved 66 packages in 23ms
```

pytest は main 時点 (538 passed, 1 skipped) から **+18** (純ロジック17 + pydub/ffmpeg 不在時に
skip される統合テスト1)。skip 件数は既存の `test_mix_mixer.py` 分 (1) + 本チケット分 (1) で計2。
mypy は `src tests` コマンド自体には `scripts/` が含まれないため、`scripts/generate_bgm.py`
単体を `--strict` で追加確認した (Success)。

## 保守側に倒した判断

- 提案書レベルの音楽的な仕様書は無いため、team-lead 指示の目安 (120BPM前後・8〜16小節・
  シンプルなアルペジオ+控えめなパーカッション・-12dBFS程度) をそのままパラメータの既定値とし、
  「音楽的な凝りより破綻なく無限ループできる控えめな背景音を優先」という指示どおり、和音進行は
  A minor の最も基本的な i-VI-III-VII (いわゆる "4 chords" 進行) に留めた。フィルタ・ディレイ等の
  音響処理は行わず (numpy/scipy 非依存の制約と整合)、ナイーブ波形合成 + 加算エンベロープのみで
  構成している。
- BGM ディレクトリ `assets/bgm/` 自体 (及び `.gitkeep`) は今回のコミットに含めていない
  (既存 `.gitignore` の `!assets/**/.gitkeep` 例外パターンに対応する実ファイルが元々存在しない
  状態だったが、これは本チケットのスコープ外の pre-existing gap と判断し、スクリプト側で
  `Path.mkdir(parents=True, exist_ok=True)` して実行時に解決する設計にした)。
- `mix/mixer.py` 側の呼び出しコード (`main.py` の `find_bgm(bgm_dir)` 呼び出し等) は無変更。
  生成 BGM はあくまで `assets/bgm/` に置く「素材」の 1 つとして機能する設計であり、恒久的な
  BGM 実装 (ライセンス確定素材への差し替え等) は別途人間判断・別チケットとする。
