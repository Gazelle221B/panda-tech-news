# T55 — daily_pipeline の事前資源チェック + IRODORI_TIMEOUT 既定引き上げ (Issue #49)

- 日付: 2026-07-13
- ブランチ: `agent/T55-resource-preflight-impl`
- 実装者: Claude Code
- 参照: [Issue #49](https://github.com/Gazelle221B/panda-tech-news/issues/49)（repo 側恒久対応の候補 2., 3. のうち 2. と、暫定運用ガイドの timeout 目安を反映）

## 背景

2026-07-12 深夜〜07-13 朝の実運用で、swap 22.5GB (実RAM 16GB) に達した状態で produce を実行し、
600M モデルの TTS 合成が 132s → 923s (最大 10 倍) まで劣化。`IRODORI_TIMEOUT=300` ではクライアント
がまだ計算中のリクエストへ再試行し、サーバが 503 を返す連鎖に陥り、T36 の 1 文欠落ゲートにより
produce 全体が fail-fast した (6 時間戦って収束)。

Issue #49 の「根本原因」節が指摘するとおり、load average だけでは検知できないケース
(load 10 でも 13分/文) があるため、swap と load の両方を見る必要がある。

## 変更内容

### 1. `scripts/daily_pipeline.sh` — produce 前の資源プリフライトチェック

- `get_swap_used_mb()` / `get_load_1min()`: それぞれ `KARYU_SWAP_USED_MB` / `KARYU_LOAD_1MIN`
  が env で設定されていればそれを使い (契約テストの注入経路)、未設定なら
  `sysctl -n vm.swapusage` の `used = N.NNM` / `sysctl -n vm.loadavg` の `{ N.NN N.NN N.NN }`
  先頭値 (1分) をそれぞれ解析して取得する (macOS 専用出力形式、本プロジェクトは launchd 前提の
  macOS 運用のため既存コードと同じ前提)。
- `resources_ok()`: 上記 2 値を `KARYU_MAX_SWAP_MB` (既定 12000) / `KARYU_MAX_LOAD` (既定 25)
  と比較し、いずれか超過なら `1` (false) を返す。値取得に失敗した場合 (sysctl 非対応環境など)
  は fail-open で `0` (true) を返し、産出物ゼロで止まらないようにした
  (`log` に WARNING を残す)。
- 呼び出し側: `collect` / `draft` は軽量なので対象外 (常に実行、指示どおり)。`produce` の直前で
  `resources_ok` を呼び、false の場合は `run_step "produce" ...` 自体を実行せず、
  `PRODUCE_RC=97` (sentinel、実 produce 失敗の rc と混同しないための専用値) を設定する。
  既存の `notify_failure` をそのまま再利用し、label に資源不足の詳細
  (`資源不足のため produce をスキップ (swap=XXXXM, load=YY)`) を渡すことで Discord へ通知する
  (既存関数の実装は変更せず、呼び出し引数のみで要件を満たした = Surgical Changes)。
  `FINAL_RC` へ 97 が伝播するため、スクリプト全体は非 0 で終了する (音声ゼロを success 扱い
  しない既存方針を維持)。

### 2. `IRODORI_TIMEOUT` 既定引き上げ (300 → 1800)

Issue #49 の暫定運用ガイド「観測された最悪合成時間の 2 倍」の実測 (07-13 朝の最悪実測 1211s) に
対する余裕を持たせた値。`env` 上書きの既存機構は無変更で維持。

### 3. テスト

- `tests/test_daily_pipeline.py`:
  - `_run_daily_pipeline()` に `swap_used_mb` / `load_1min` / `max_swap_mb` / `max_load` の
    注入用キーワード引数を追加 (未指定なら env を pop し実 sysctl 経路に委ねる)。
  - 既存 3 テスト (publish 系) は produce の実行そのものを前提にしているため、ホストマシンの
    実 swap/load に左右されないよう安全な値 (`swap_used_mb="500", load_1min="1"`) を明示注入する
    よう更新 (`_SAFE_RESOURCE_KWARGS`)。**このマシンの実測 swap (~12.4GB) が新しい既定閾値
    12000M 付近/超過していることを smoke で確認済み** — 注入なしでは資源チェックが「不足」と
    判定してしまい既存テストが不安定になるため必須の追随。
  - 新規 4 テスト:
    1. `test_produce_skipped_when_swap_exceeds_threshold` — swap 超過時に produce (fake uv) が
       呼ばれず rc 非 0 + 通知ログ (`資源不足のため produce をスキップ`, `swap=13000M`,
       `Discord failure alert: sent`)。
    2. `test_produce_skipped_when_load_exceeds_threshold` — load 超過時も同様。
    3. `test_produce_runs_when_resources_within_threshold` — 両方閾値内なら produce が呼ばれ
       rc 0 で完走 (`資源チェック OK` ログを確認)。
    4. `test_resource_thresholds_are_env_overridable` — `KARYU_MAX_SWAP_MB` を低い値へ上書き
       すると、既定閾値内の swap でもスキップされることを確認 (env 上書きが効くことの証明)。
- `tests/test_produce_pipeline.py`:
  `test_daily_pipeline_returns_nonzero_when_produce_fails_after_alert` (T50 由来の既存テスト)
  も同じ理由 (実 sysctl 依存だと本マシンの swap 実測で produce がスキップされ `rc=97` になり
  期待値 `rc=7` と食い違う) で `KARYU_SWAP_USED_MB=500` / `KARYU_LOAD_1MIN=1` を明示注入する
  よう追随修正した。

## 手動 smoke (fake uv, `KARYU_UV=/bin/echo`, scratchpad 上で実行)

1. swap 超過 (`KARYU_SWAP_USED_MB=15000`) → produce 未呼び出し、ログに
   `資源不足のため produce をスキップ (swap=15000M [閾値 12000M] / load=5 [閾値 25])`、
   `rc=97`。
2. load 超過 (`KARYU_LOAD_1MIN=30`) → 同様に `rc=97`、ログに `load=30 [閾値 25]`。
3. 両方閾値内 (`swap=500, load=3`) → `資源チェック OK` ログ、`produce 開始`/`produce 成功` の
   ログが出力され `rc=0`。

## 品質ゲート (fresh 実行)

```
$ uv run pytest
571 passed, 2 skipped in 5.68s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 83 source files

$ shellcheck scripts/daily_pipeline.sh
(出力なし = クリーン)

$ git diff --check
(出力なし = クリーン)
```

### レビュー指摘 3 件の反映 (2026-07-13, Codex 独立レビュー)

1. **[High] IRODORI_TIMEOUT フォールバック不整合**: pipeline 既定を 1800 にしても、
   `src/karyu_tech_news/tts/irodori.py` の `TIMEOUT_SECONDS = 300.0` が unset 時既定かつ不正
   env 値のフォールバック先として残っており、「回避対象の 300 秒」が不正 env で復活する経路が
   あった。`TIMEOUT_SECONDS` を **1800.0** へ引き上げ、pipeline と整合させた。既存テスト
   `test_irodori_default_timeout_is_300` → `test_irodori_default_timeout_is_1800` に改名・
   期待値更新、不正値フォールバックのパラメタライズテスト (7 ケース) の期待値も 1800.0 へ。
   docstring/コメントの 300 言及も同期 (`IRODORI_TIMEOUT`/`300` を grep で全域確認済み)。
2. **[Medium] 資源値・閾値の数値検証**: `is_nonneg_number()` (bash 正規表現
   `^[0-9]+([.][0-9]+)?$` — 負数/nan/inf/空/非数値を弾く) を追加し、`resources_ok()` で
   比較前に 4 変数すべてを検証するようにした。
   - 閾値 (`KARYU_MAX_SWAP_MB` / `KARYU_MAX_LOAD`) の不正値 → **既定値 (12000 / 25) へ置換 +
     WARN ログ**。旧実装では `KARYU_MAX_SWAP_MB=abc` が awk の文字列比較となり
     (数字は英字より辞書順で小さい)、チェックが黙って無効化され produce が走っていた。
   - 資源注入値 (`KARYU_SWAP_USED_MB` / `KARYU_LOAD_1MIN`) の不正値 → **sysctl 実測へ
     フォールバック + WARN ログ** (= 既定の取得経路。注入は契約テスト用の上書きなので、
     不正なら「未設定と同じ」扱いが安全側)。sysctl 由来の値も最終検証し、数値を得られない
     場合は従来どおり WARN + fail-open。
   - awk 比較も `v + 0 > max + 0` の明示数値化に変更 (二重防御)。
   - 回帰テスト `test_invalid_threshold_falls_back_to_default`: `KARYU_MAX_SWAP_MB=abc` +
     swap 13000M で、WARN ログが出て既定閾値 12000M で判定されスキップ (rc=97) することを固定。
   - 手動 smoke: `KARYU_SWAP_USED_MB=abc` → WARN + sysctl 実測 (13436.81M) へフォールバックし、
     実測が既定閾値超過だったため正しくスキップ (rc=97) されることを確認。
3. **[Low] rc=97 契約の固定**: 資源スキップ系テスト 3 件の assert を `rc != 0` から
   `rc == 97` へ変更 (外部監視が「資源不足スキップ」と「実 produce 失敗」を rc で識別する
   契約の固定)。

fresh ゲート (レビュー反映後):

```
$ uv run pytest
572 passed, 2 skipped in 51.44s   # +1: 不正閾値回帰テスト

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 83 source files

$ shellcheck scripts/daily_pipeline.sh
(出力なし = クリーン)

$ git diff --check
(出力なし = クリーン)
```

## 保守側に倒した判断

- **rc=97 の sentinel 値**: 「実 produce 失敗」と「資源不足によるスキップ」を Discord 通知・ログ・
  外部監視の rc から区別できるよう、既存の produce の実失敗 rc (呼び出し先の CLI が返す任意の値、
  実測では 1 や 7 など) と衝突しにくい値として選んだ。厳密な「専用 rc の値」の指定は指示に無かった
  ため、実装判断として決めた (通常の CLI 失敗 rc は 1 桁が多く、97 は Issue の意図する「資源不足=
  リトライではなく延期」を rc からも識別可能にする)。
- **`notify_failure` 関数自体は変更しない**: 「既存の notify_failure 相当の経路」という指示を、
  関数のシグネチャ変更ではなく label 引数の内容で実現する形で満たした。Surgical Changes
  (AGENTS.md §12.3) — 触るのは必要な箇所だけ、の原則に沿う。
- **既存 4 テスト (publish 系 3 + T50 produce 系 1) への安全値注入**: 指示には無い追随修正だが、
  新規閾値の既定値 (swap 12000M) がこの開発機の実測 swap (~12.4GB) に極めて近く、注入なしでは
  ホスト状態次第で既存テストが unstable/red になることを fresh ゲート実行で確認したため、
  Ticket スコープの直接の帰結として最小限の修正を行った (無関係なリファクタは含めていない)。
- **load average の取得元は `sysctl -n vm.loadavg`**: Issue #49 の暫定運用ガイドは `uptime` を
  例示していたが、`sysctl -n vm.loadavg` の方が出力形式が安定しておりパースが単純
  (`{ N.NN N.NN N.NN }` の第2フィールド固定) なため、同種の情報を返すこちらを採用した。
  スクリプトは既に `sysctl` (swap) を使っており、依存コマンドを増やさない利点もある。
