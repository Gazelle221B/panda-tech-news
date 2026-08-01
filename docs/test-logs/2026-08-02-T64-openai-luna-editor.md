# T64 — editor を GPT-5.6 Luna へ切替 (Issue #70)

- 日付: 2026-08-02
- ブランチ: `agent/T64-openai-luna-editor-impl`
- 実装者: Claude Code
- 参照: [Issue #70](https://github.com/Gazelle221B/panda-tech-news/issues/70) (プロダクトオーナー指示 2026-08-02、OpenAI データ共有キャンペーン枠)

## 背景

editor ロール (現 MiMo v2.5-pro) を OpenAI GPT-5.6 Luna へ切り替える。データ共有キャンペーン
(API 入出力の共有と引き換えに日次無料トークン) の枠で利用する意図。editor が送る内容は公開 RSS
のニュース見出し・要約のみで共有可能。2026-08-02 の実機スモークで判明した互換性制約
(`max_tokens` 不可 → `max_completion_tokens` 必須 / `temperature` 指定不可、既定 1 のみ)
を吸収するため、`LLMProfile`/`LLMClient` をプロファイル駆動のパラメータ調整に拡張した。

## 変更内容

### 1. `src/karyu_tech_news/llm/profile.py`

`LLMProfile` に optional フィールドを3つ追加 (既存プロファイルは無指定でデフォルト値が適用され
挙動不変):

- `token_param: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"`
- `send_temperature: bool = True`
- `seed: int | None = None`

### 2. `src/karyu_tech_news/llm/client.py`

`LLMClient.chat()` のボディ構築をプロファイル駆動に変更:

- `max_tokens` 固定キーではなく `self.profile.token_param` をキーに使う (`{token_param: max_tokens}`)。
- `send_temperature` が `True` のときのみ `temperature` を body に含める。`False` の場合は
  呼び出し側が `temperature=` 引数を明示していても完全に無視して省略する (Issue の要求どおり)。
- `profile.seed` が `None` でないときのみ `seed` を body に付与する。

### 3. `config/llm_profiles.yaml`

- プロファイル `openai-luna` を新規追加 (`mimo` セクションの直後、`mimo-openrouter` の前に配置):
  `provider: openai_compatible` / `api_key_env: OPENAI_API_KEY` /
  `base_url: https://api.openai.com/v1` / `model: gpt-5.6-luna` / `max_tokens: 1800` /
  `token_param: max_completion_tokens` / `temperature: 1.0` (未送信・形式上の保持) /
  `send_temperature: false` / `seed: 42` / `notes` にキャンペーン経緯と決定性トレードオフを明記。
- `ab_test.A.editor` を `mimo` → `openai-luna` に変更。`mimo` プロファイル自体はフォールバックとして
  残置 (B/C 案は変更なし)。
- 既存の手書き YAML の書式・インラインコメント流儀を保持 (yaml 再ダンプ禁止の指示どおり、Edit で
  該当ブロックのみ挿入・書き換え)。

### 4. `.env.example`

- `OPENAI_API_KEY=` を `MIMO_API_KEY` / `DEEPSEEK_API_KEY` と同じ「Sprint 1B 以降」セクションに
  追加 (新プロファイルが参照する `api_key_env` のドキュメント化。既存の他キーと同じ 1 行コメント
  + 空値の流儀)。Issue #70 の実装1〜3には明記されていないが、既存の各プロファイルのキーが全て
  ここに列挙されている慣例に直接トレースできる最小追加のため実施した。

### 5. `T15` の決定性トレードオフ (design-inheritance §4.2)

editor 判定は T15 で temperature=0 固定の設計だったが、`openai-luna` は `send_temperature: false`
のため、`edit/judge.py` が渡す `temperature=JUDGE_TEMPERATURE` 引数は client 側で無視・省略される。
決定性は `seed=42` の best-effort に弱まる (OpenAI 側の `system_fingerprint` は `None` 想定)。
judge の JSON 崩れは既存の fail-open ロジック (`edit/judge.py`) が吸収するため追加対応は不要と判断。
この判断は Issue #70 本文と本ログに記録済み。

## テスト

### `tests/test_llm_profile.py` (+6件)

- `test_llm_profile_new_fields_default_for_backward_compat`: 無指定時のデフォルト値
  (`token_param="max_tokens"`, `send_temperature=True`, `seed=None`) を固定 (後方互換)。
- `test_llm_profile_accepts_max_completion_tokens_send_temperature_false_and_seed`: 新フィールド
  3つを明示指定した場合の値保持を確認。
- `test_llm_profile_rejects_unknown_token_param`: `token_param` の `Literal` 外の値を拒否。
- `test_load_real_llm_profiles_yaml` (既存テストを更新): labels 一覧に `openai-luna` を追加、
  `ab_test["A"].editor == "openai-luna"` を確認、`openai-luna` プロファイルの
  `token_param`/`send_temperature`/`seed` が実 YAML の値と一致することを確認。

### `tests/test_llm_client.py` (+4件)

DoD の「client のボディ構築テスト (token_param 切替 / temperature 省略 / seed 付与 /
既存プロファイル無変更)」に対応する4系統:

- `test_chat_token_param_switches_body_key`: `token_param="max_completion_tokens"` のプロファイルで
  body に `max_completion_tokens` キーが立ち `max_tokens` キーが存在しないことを確認。
- `test_chat_send_temperature_false_omits_temperature_even_with_override`: `send_temperature=False`
  のとき、呼び出し側が `temperature=0.0` を明示指定しても body に `temperature` キーが現れないことを
  確認。
- `test_chat_seed_is_added_when_profile_specifies_it`: `profile.seed=42` のとき body に
  `seed=42` が付与されることを確認。
- `test_chat_existing_profile_without_new_fields_is_unchanged`: 新フィールド無指定の既存
  プロファイルで body が従来どおり (`max_tokens` キー / `temperature` 送信 / `seed` 無し) である
  ことを確認 (後方互換の直接検証)。

いずれも実 API は呼ばず、既存の `httpx.post` モック流儀 (`unittest.mock.patch`) を踏襲した。

### `tests/test_cli_1b.py` (既存テストの更新、2件)

`ab_test.A.editor` の変更に伴う直接的な副作用:

- `test_draft_dry_run_lists_candidates_without_llm`: dry-run 出力の期待値を
  `"editor=mimo"` → `"editor=openai-luna"` に更新。
- `test_draft_without_api_key_exits_1`: 未設定時に exit 1 させる対象キーを `MIMO_API_KEY` から
  `OPENAI_API_KEY` に変更 (variant A の editor が openai-luna になったため、実際にチェックされる
  環境変数もこちらに変わった。旧テストは worktree に `.env` が無く `OPENAI_API_KEY` がそもそも
  未設定だったため偶然パスしていたが、意図を正しく反映する形に修正した)。

## 品質ゲート (fresh 実行)

```
$ uv run pytest -v
685 passed, 11 skipped in 20.35s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 94 source files

$ git diff --check
(出力なし = クリーン)
```

`uv run pytest -q` は素の exit code で確認 (EXITCODE:0)。件数の内訳確認は `-v` で実施。

## 仕様から外れた判断・不確かな点

- **`.env.example` への `OPENAI_API_KEY` 追加**: Issue #70 の実装1〜3には明記されていないが、
  既存の全プロファイルの `api_key_env` がこのファイルに列挙されている慣例に直接トレースできる
  1行追加のため実施した (Surgical Changes の範囲内と判断)。
- **`temperature: 1.0` の設定値**: `send_temperature: false` のため実際には送信されないが、
  Pydantic スキーマ上 `temperature` は必須フィールドのままなので、Issue 記載の「既定 1 のみ許可」
  に合わせて `1.0` を形式上の値として設定した (未送信である旨をインラインコメントで明記)。
- **`tests/test_cli_1b.py` の既存2テストの更新**: Issue の DoD には直接列挙されていないが、
  `ab_test.A.editor` を変更した直接的な副作用としてこれらのテストが赤くなった (dry-run 出力文言 /
  未設定キー判定) ため、「既存 pytest 全緑」を満たすために必要な修正として実施した。
- **`openai-luna` プロファイルの YAML 内配置**: `mimo` (editor 旧第一候補) の直後、
  `mimo-openrouter` (フォールバック) の前に配置した。プロファイル一覧の意味的なグルーピング
  (writer 候補 → editor 候補 → editor 新候補 → フォールバック → オフライン検証) を優先した判断で、
  Issue 本文に配置順の指定はない。

---

## 追記 (同日, フォローアップ): 無料枠内運用の方針を notes に追記

オーケストレータから追加指示 (プロダクトオーナー確認済み、2026-08-02): OpenAI のデータ共有が
有効化され、complimentary daily tokens への enrollment が確認できたとのこと。
`config/llm_profiles.yaml` の `openai-luna` プロファイルの `notes` に、日次無料トークン枠内での
運用が前提であること・バルク利用禁止を追記した (既存の notes 文へ2文追加、他のフィールド・
実装内容は変更なし)。

### 品質ゲート (fresh 実行, 再検証)

```
$ uv run pytest -q
685 passed, 11 skipped (exit code 0)

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 94 source files

$ git diff --check
(出力なし = クリーン)
```
