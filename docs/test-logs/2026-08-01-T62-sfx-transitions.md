# T62 — SFX・トランジション導入 スコープA (Issue #65)

- 日付: 2026-08-01
- ブランチ: `agent/T62-sfx-transitions-impl`
- 実装者: Claude Code
- 参照: Issue #65 (スコープA: パイプラインの受け皿。音源生成・採用はスコープB, 別作業)

## 背景

番組にトピック間トランジション SFX を導入する。音源生成は Stable Audio 3 Small-SFX
(`stabilityai/stable-audio-3-small-sfx`, Stability Community License) を採用予定だが、
音源そのものは HF ライセンス同意・試聴確認 (人間作業, スコープB) 待ちのため、本チケットは
音源が無くても実装・テスト可能な受け皿 (セグメント分割・ffmpeg 挿入配線・生成スクリプト・
設定・素材置き場) のみを作る。

## 変更内容

### 1. トピック境界のセグメント分割 (`src/karyu_tech_news/tts/normalize.py`)

- `split_markdown_topics(markdown: str) -> list[str]` を `strip_markdown_structure` の隣に追加。
  `## ` 見出し (レベル2) で「イントロ部 (最初の `## ` より前)」+「各 `## ` セクション (見出し行
  から次の `## ` 見出し直前まで)」に分割し、各パートへ既存 `strip_markdown_structure` を適用する。
- `### ソース一覧` 等のレベル3見出しは `^## ` (2つの `#` の直後に空白を要求) にマッチしないため
  誤って境界扱いされない。末尾トピックは締めの挨拶・ソース一覧・注意事項も同じパートに含むが、
  いずれも `strip_markdown_structure` が発話対象外として除去する (outro segment は新設しない)。
- `## ` 見出しが1つも無い旧形式の台本は、従来どおり全体を1パートとして返す (後方互換)。
- strip 後に空文字になったパート (見出し直後に本文が無いセクション等) は除外する。

### 2. produce のセグメント別合成 + SFX 連結配線 (`src/karyu_tech_news/main.py`)

- `produce` コマンド: 保存済み markdown を `split_markdown_topics` で複数 `Segment` (kind="topic",
  tone/bgm は従来どおり "neutral") に構造化するよう変更 (旧: 全体を 1 segment に平坦化)。
- `synthesize_script` を **segment ごとに個別呼び出し** (1-segment の `StructuredScript` を都度
  組んで渡す)。attempted/synthesized/skipped/asr_retried の各カウンタは全 segment 合算し、
  従来と同じ fail-fast 判定 (skipped>0 で中止、synthesized==0 で中止) をそのまま維持する。
  ASR ゲート (`asr_backend`) も各呼び出しへ従来どおり伝搬する。
- 新規 CLI オプション `--show-format` (既定 `config/show_format.yaml`) を追加。`sfx.enabled` が
  true かつ `sfx.transition` の実ファイルが存在するときだけ、そのパスを
  `concat_with_transitions` へ渡す。ファイル欠落・YAML 破損は persona 読み込みと同じ fail-open
  流儀 (WARN ログ + SFX なしで続行)。既定 (`enabled: false`) では `sfx_path=None` のままとなり、
  SFX 挿入は一切発生しない (音声出力への影響なし)。
- segment wav のリストを `concat_with_transitions` で 1 本に連結してから、従来どおり
  `analyze_wav_signal` (無音・無音区間長ゲート) → `mix_bgm` → `master_to_mp3` へ渡す。

### 3. SFX トランジション挿入 (`src/karyu_tech_news/mix/transitions.py`, 新規)

- `concat_with_transitions(segment_wavs: list[bytes], sfx_path: Path | None, *, sfx_gain_db: float = -6.0) -> bytes`。
- `sfx_path` が None/欠落、または segment が1個以下なら ffmpeg を使わない単純連結 (SFX なし)。
- **依存方向の遵守 (architecture.md §1 / IMPLEMENTATION_PLAN-2.md §3 `script → tts → mix`
  一方向)**: mix 層は tts/script を import しない設計のため、`tts/synthesize.py` の
  `_concat_wav_with_stats` (private) を再利用せず、同等ロジック (先頭 chunk のパラメータを基準に
  不一致/壊れた chunk を fail-open で skip、有効 chunk ゼロなら無音 wav) を本モジュール内に
  独立して実装した。
- SFX 挿入時は ffmpeg concat フィルタを使用: `[seg0, sfx, seg1, sfx, ..., segN-1]` の順に
  同一 SFX ファイルを複数回 `-i` する単純な構成 (filter label の暗黙 fan-out には頼らない)。
  SFX は先頭セグメントの format (サンプルレート/チャンネル数) へ `aformat`/`aresample` で自動
  整合し、`volume={sfx_gain_db}dB` (既定 -6dB) を適用。トピック間のみに挿入 (先頭前・末尾後には
  入れない)。
- ffmpeg 未導入・非0終了・タイムアウトは WARN ログの上で SFX なし単純連結へ fail-open する。

### 4. 設定 (`config/show_format.yaml`)

```yaml
sfx:
  enabled: false        # T62: トピック間トランジション。音源採用後に true へ
  transition: assets/sfx/transition.wav
```

既定 `enabled: false` により、produce の音声出力は本チケット導入前と一切変わらない。

### 5. 生成スクリプト (`scripts/gen_sfx.py`, 新規)

- Stable Audio 3 Small-SFX で transition/opening/ending の候補 SFX を生成する CLI
  (`argparse` ベース。`scripts/generate_bgm.py` の流儀を踏襲、typer ではない)。
- `--out assets/sfx/ --kind transition|opening|ending --count 3 --duration 2.5 --seed N
  [--prompt "..."]`。既定プロンプトは kind ごとの英語定数、`--prompt` で上書き可。
  出力ファイル名は `{kind}_{候補ごとの実 seed}.wav`。
- `stable_audio_3` は関数内で遅延 import。未導入時は「`uv sync --extra sfx` が必要」、
  HF 401/gated 系エラー時は「https://huggingface.co/stabilityai/stable-audio-3-small-sfx
  でライセンス同意 + `hf auth login` が必要」という明確なメッセージで exit 1 にする
  (`GenSfxError` に正規化)。
- ネットワークと実モデルを要するためユニットテスト対象外 (チケット指示どおり)。ruff/mypy は
  個別に緑を確認 (下記「品質ゲート」参照。`scripts/` は `mypy src tests` の対象外のため単体実行)。

### 6. `assets/sfx/` (新規)

- `.gitkeep` (追跡用の空ファイル) と `README.md` (音源の由来・Stability Community License の
  要点・採用手順を記載)。
- `.gitignore` に `assets/sfx/*` (+`!assets/sfx/README.md`) を追加し、`assets/jingles/*` /
  `assets/bgm/*` / `assets/voice_reference/*` と同じ「素材本体はコミットしない」流儀に揃えた
  (生成 wav 自体は既存の `*.wav` グローバル ignore でも既にカバーされるが、ディレクトリ単位の
  一貫性のため明示的にも追加)。

## `stable-audio-3` の依存解決方法

**PyPI には公開されていない** (`https://pypi.org/pypi/stable-audio-3/json` → 404 を確認)。
GitHub リポジトリ `Stability-AI/stable-audio-3` 自体が独立した `pyproject.toml`
(`name = "stable-audio-3"`, hatchling ビルド, `requires-python >= 3.10`) を持つプロジェクトの
ため、git 依存として追加した:

```toml
[project.optional-dependencies]
sfx = ["stable-audio-3"]

[tool.uv.sources]
stable-audio-3 = { git = "https://github.com/Stability-AI/stable-audio-3" }
```

`uv add "stable-audio-3 @ git+https://github.com/Stability-AI/stable-audio-3" --optional sfx`
で解決 (torch 2.7.1 / torchaudio 2.7.1 / transformers 5.14.1 等、重量級の連鎖依存込みで
126 パッケージに solve)。`qa-asr` extra と同じく CI の既定 (dev group) には入れず、
`uv sync --extra sfx` を実行した環境でのみ有効化される。`uv sync` (extra 無し) で
torch/stable-audio-3 一式が正しくアンインストールされ、コアパイプラインへ一切漏れないことを
確認済み。

API 呼び出し (`StableAudioModel.from_pretrained("small-sfx")` /
`model.generate(prompt=..., duration=..., seed=..., batch_size=1)` /
`torchaudio.save(path, audio[0].cpu(), model.model.sample_rate)`) は、リポジトリ本体の
`stable_audio_3/cli.py` (`_save_output` 関数) の実装を直接参照して確認した (README の
サンプルコードは保存部分を明示していなかったため)。

## テスト

### 新規: `tests/test_mix_transitions.py` (18件)

`concat_with_transitions` のユニットテスト。SFX 無し単純連結 (ffmpeg 不要、常時実行): 単一
segment は sfx_path を無視・sfx_path=None/欠落は単純連結・空リストは有効な無音 wav・壊れた/
パラメータ不一致 chunk の fail-open skip。ffmpeg 呼び出し fail-open (`subprocess.run` を
モックし実 ffmpeg 不要): ffmpeg 未導入・非0終了・タイムアウト・先頭 segment 不正で
ffmpeg を呼ばず即フォールバック。実 ffmpeg 統合 (`shutil.which("ffmpeg")` 不在で skipif,
`test_mix_master.py` の流儀): トピック間のみへの SFX 挿入 (RMS で無音区間/信号区間を確認)・
`sfx_gain_db` の実減衰確認・wav コンテナ妥当性。

### 更新: `tests/test_tts_normalize.py` (+6件)

`split_markdown_topics` のユニットテスト: 見出しなし (単一パート、後方互換)・イントロのみ
(見出しゼロ)・複数見出し (イントロ+トピック2件へ分割、末尾トピックに締め挨拶が畳み込まれる
ことと `### ソース一覧` 等のレベル3見出し・リンク行が正しく除去されることを確認)・空セクション
の除外・全体が空になる入力の空リスト化。

### 更新: `tests/test_produce_pipeline.py` (+5件)

produce 統合テスト (mock エンジン): 複数 `## ` 見出しで segment ごとに `synthesize_script` が
呼ばれ、見出し行/生成メタが合成対象に含まれないこと (`master_to_mp3` をモックし ffmpeg 非依存)。
欠落文の集計が全 segment 合算で行われ従来どおり fail-fast すること。`show_format.yaml` 破損時に
SFX なしへ fail-open すること。`sfx.enabled: true` + 実在する transition ファイルで実 ffmpeg
concat 経路まで通り mp3 が生成されること (`shutil.which("ffmpeg")` 不在で skipif)。既存の全
produce テスト (見出し無し markdown を使う従来のテスト群) は無改修のまま全緑を維持 — これが
「`sfx.enabled: false` の既定で挙動不変」の実証になっている。

## 品質ゲート (fresh 実行, `sfx` extra 無しの既定環境)

```
$ uv run pytest -v
668 passed, 11 skipped in 12.18s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 94 source files

$ uv run mypy scripts/gen_sfx.py
Success: no issues found in 1 source file
(scripts/ は `mypy src tests` の対象外のため、チケット指示どおり個別実行で確認)

$ uv lock --check
Resolved 126 packages (差分なし)

$ git diff --check
(出力なし = クリーン)
```

`uv run pytest -q` の progress 出力は、この環境固有の現象で最終サマリー行が `-q` では
表示されない (`-v` では正常表示、exit code は両方とも 0)。`-v` で `668 passed, 11 skipped`
を fresh に確認済み。

## 仕様から外れた判断・不確かな点

- **`--show-format` CLI オプションの新設**: チケット文面は「produce が show_format を読む経路を
  確認して配線 (読んでいなければ persona と同じ fail-open 流儀で新規に読む)」だったが、
  produce は元々 show_format.yaml を読んでいなかった。`persona_file` / `bgm_dir` 等、既存の
  設定パスが全て `typer.Option` になっている慣例に合わせ、`--show-format` (既定
  `config/show_format.yaml`) を新設した。CLI 引数を増やさず固定パス読み込みにする案もあったが、
  テスト容易性 (実 `config/show_format.yaml` に依存しない tmp_path 差し替え) を優先した。
- **セグメント分割は `sfx.enabled` に関わらず常時有効**: Issue #65 の「パイプラインの受け皿」
  という位置づけ (スコープA全体が「音源が無くても実装・テスト可能」な基盤整備) から、トピック
  境界セグメント分割・segment 別合成は `sfx.enabled` の値に関係なく常に行う設計にした。
  `sfx.enabled: false` の既定で保証されるのは「SFX 音声が挿入されないこと (音声出力が不変)」
  であり、「segment 分割という内部構造が変わらないこと」ではない。この解釈は DoD の
  「produce 統合テスト (... sfx.enabled: false の既定で挙動不変)」を「既存 (見出し無し
  markdown を使う) テスト群が無改修のまま全緑」という形で満たすことで担保した。
- **`concat_with_transitions` は `tts/synthesize.py` の `_concat_wav_with_stats` を再利用せず
  独立実装**: チームリード指示に明記された依存方向の制約 (mix 層は tts/script を import
  しない) を優先した判断。ロジックの重複は生まれるが、レイヤー境界を跨がない設計を優先した
  (styleguide §1 Surgical Changes)。
- **SFX 挿入の ffmpeg コマンド構成**: 同一 SFX ファイルをトピック間の数だけ複数回 `-i` する
  構成にした (filter label を複数回参照する fan-out 構成も可能だが、ffmpeg のドキュメント上の
  挙動があいまいなため、確実に動作する単純な構成を優先)。
- **`asr_failed_sentences` の集計は行わない**: 旧 produce コードもこのフィールドを表示に
  使っておらず (`asr_retried_sentences` と `skipped_sentences` のみ使用)、集計しても未使用な
  ため、segment ループでの集計対象から意図的に除外した (mypy strict の未使用変数を避ける意図
  もある)。
