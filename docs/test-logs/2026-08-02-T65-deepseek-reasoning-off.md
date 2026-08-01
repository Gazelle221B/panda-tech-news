# T65 — deepseek-v4-flash の reasoning 垂れ流しで writer が全滅する退行の修正 (Issue #73)

- 日付: 2026-08-02
- ブランチ: `agent/T65-deepseek-reasoning-off-impl`
- 実装者: Claude Code
- 参照: [Issue #73](https://github.com/Gazelle221B/panda-tech-news/issues/73) (T64 の続きの文脈、緊急対応)

## 背景

検証 draft #3 で writer (deepseek-v4-flash) が全5トピック template 落ちする退行を検出。原因調査で
content 先頭が `"The user wants me to write..."` から始まる英語 chain-of-thought (4377字) であることが
判明した。deepseek-v4-flash は reasoning モデルで、単純プロンプトでは思考が `reasoning_content`
フィールドに分離されるが、実 writer プロンプト (長い指示) のような複雑プロンプトでは、その思考が
`content` に直接垂れ流される。結果として本文が異常に長くなり、300字予算の検証を全滅させていた
(検証違反「300 文字超過 (空白除く 3304 文字)」)。

オーケストレータの実機検証で、リクエスト body に `reasoning_effort: "none"` を付与すると思考が完全に
消え、正常な長さの出力に戻ることを確認済み (`thinking: {"type":"disabled"}` も同様に有効な代替)。

## 変更内容

### 1. `src/karyu_tech_news/llm/profile.py`

`LLMProfile` に汎用 optional フィールド `extra_body: dict[str, Any] | None = None` を追加
(既存プロファイルは無指定でデフォルト `None` となり挙動不変)。T64 で追加した `token_param` 等の
個別フィールドは温存し、今後増えうるプロバイダ固有の隠しパラメータ全般を吸収する汎用機構として
新設した (チームリード指示どおり)。

### 2. `src/karyu_tech_news/llm/client.py`

`LLMClient.chat()` のボディ構築の最後 (ollama の `think=False` 付与の直後) に、
`profile.extra_body` があれば `body.update(profile.extra_body)` でマージする処理を追加。
`extra_body` が `None`/未指定なら何もしない。既存キー (`model`/`token_param` キー/`temperature`/
`seed`/`response_format`/`think` 等) と衝突する場合は `extra_body` 側が最後に上書きするため勝つ。

**ollama の既存 reasoning 抑制処理との整合性確認**: `body["think"] = False` は `extra_body` マージの
直前に実行されるため、`extra_body` を指定した ollama プロファイルがあれば `think` キーも
`extra_body` 側で上書き可能になる (現状 `local-ollama` プロファイルは `extra_body` 未指定のため、
今回の変更で `think=False` の付与は一切変わらない。将来 ollama 側にも `extra_body` を使う場合の
拡張性のみ確保した)。

### 3. `config/llm_profiles.yaml`

`deepseek` プロファイルに `extra_body: { reasoning_effort: "none" }` を追記
(`temperature` の直後、`notes` の直前。実測経緯をインラインコメント1行で明記)。既存の手書き YAML の
書式・インラインコメント流儀を保持。

## テスト

### `tests/test_llm_profile.py` (+2件, 既存1件更新)

- `test_llm_profile_extra_body_defaults_to_none_for_backward_compat`: 無指定時のデフォルト値
  `None` を固定 (後方互換)。
- `test_llm_profile_accepts_extra_body_dict`: 明示指定した `dict` の値保持を確認。
- `test_load_real_llm_profiles_yaml` (既存テストを更新): 実 YAML の `deepseek` プロファイルの
  `extra_body == {"reasoning_effort": "none"}` を確認するアサーションを追加。

### `tests/test_llm_client.py` (+4件)

DoD の「extra_body がボディにマージされる / None で無変化 / 衝突時 extra_body 優先 /
既存プロファイル無指定で挙動不変」に対応する4系統:

- `test_chat_extra_body_merges_into_body`: `extra_body={"reasoning_effort": "none"}` のプロファイルで
  body に `reasoning_effort` キーが立ち、既存の `max_tokens` 等は維持されることを確認。
- `test_chat_extra_body_none_leaves_body_unchanged`: `extra_body` 無指定 (既定 `None`) のプロファイルで
  body のキー集合が従来どおり (`model`/`messages`/`max_tokens`/`temperature`/`stream` の5つのみ) で
  あることを確認。
- `test_chat_extra_body_wins_on_key_conflict`: `extra_body={"max_tokens": 999, "stream": True}` を
  指定し、既存キーとの衝突時に `extra_body` 側の値が採用されることを確認。
- `test_chat_existing_profile_without_extra_body_field_is_unchanged`: T64 で追加済みの
  `openai-luna` 系プロファイル (`_luna_profile()`、`extra_body` 未指定) で `reasoning_effort` が
  body に現れず、T64 時点の挙動 (`max_completion_tokens`/`seed` 付与) がそのまま保たれることを確認
  (T64→T65 の積み上げに対する後方互換の直接検証)。

いずれも実 API は呼ばず、既存の `httpx.post` モック流儀 (`unittest.mock.patch`) を踏襲した。

## 品質ゲート (fresh 実行)

```
$ uv run pytest -v
702 passed, 11 skipped in 11.53s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 94 source files

$ git diff --check
(出力なし = クリーン)
```

`uv run pytest -q` は素の exit code で確認 (PYTEST_EXIT:0)。件数の内訳確認は `-v` で実施。

## 仕様から外れた判断・不確かな点

- **`extra_body` マージの挿入位置**: ollama の `think=False` 付与の**後**に配置した。理由は
  依頼文の「ollama プロバイダ既存の reasoning 抑制処理があれば整合を確認 (壊さない)」という
  指示を、`extra_body` が最終的に全キーに優先する (＝ollama の `think` すら将来上書き可能にする)
  設計として解釈したため。現状 `local-ollama` プロファイルは `extra_body` 未指定のため実害はない。
- **`extra_body` の型を `dict[str, Any] | None`** とし、値の型を限定しなかった: 依頼文の型定義
  `dict[str, Any] | None = None` をそのまま採用。プロバイダ固有パラメータは文字列・真偽値・数値など
  多様なため、これ以上の制約は将来の拡張を阻害すると判断した。
- **`deepseek` 以外のプロファイルには `extra_body` を追加しなかった**: Issue #73 の対象は
  deepseek-v4-flash の実測不具合のみであり、他プロファイル (mimo / openai-luna / mimo-openrouter /
  local-ollama) は同様の症状が実機観測されていないため、Surgical Changes の原則に従い変更対象を
  deepseek のみに限定した。
