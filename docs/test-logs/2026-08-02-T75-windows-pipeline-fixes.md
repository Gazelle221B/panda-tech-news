# T75 — daily_pipeline.sh の Windows 残課題修正 + RSSHub Docker 検証 (Issue #75)

- 日付: 2026-08-02
- ブランチ: `agent/T75-windows-pipeline-fixes-impl`
- 実装者: Claude Code (Opus, 委任実行)
- 参照: [Issue #75](https://github.com/Gazelle221B/panda-tech-news/issues/75)
- 実行環境: Windows 11 Pro + Git Bash (MINGW64), `uname -a` = `MINGW64_NT-10.0-26200 ... Msys`

## 背景

2026-08-01 の Windows 初フル実走 (`data/logs/daily_20260801_235522.log`, main チェックアウト側)
で 2 件の WARNING が観測された (いずれも fail-open で配信自体には rc=0 で影響なし)。

1. `state.db バックアップ失敗`
2. `資源チェック値を取得できず (swap=N/A, load=N/A)`

## 1. state.db バックアップ失敗 — 根本原因と修正

### 根本原因 (実測で特定)

実ログの 3 行目に生の原因が残っていた:

```
Error: cannot open "/d/_Development/Github/panda-tech-news/data/backups/state_20260801_235522.db"
```

Issue の推測 (「Mac 専用コマンド依存」) は誤りだった。sqlite3 CLI 自体は本機に winget 経由で
導入済みで (`sqlite3 -version` → 3.53.3)、`.backup` ドットコマンドの構文自体は macOS 専用ではない。
実際の原因は **Git Bash (MSYS) のパス自動変換の抜け穴**:

- 旧実装: `sqlite3 "$db" ".backup '${dest}'"`
- `$db` は独立した argv トークンなので MSYS が `/d/...` → `D:/...` に自動変換するが、
  `".backup '${dest}'"` は 1 個の文字列引数の**中に**パスが埋め込まれているため MSYS の自動
  変換の対象にならない。結果、ネイティブ Windows 版 `sqlite3.exe` に Unix 形式パスがそのまま
  渡り `Error: cannot open "/d/..."` で失敗する。

再現テスト (このジョブの scratchpad で実施):

```
$ sqlite3 repro_src.db ".backup '/c/Users/.../repro_dest.db'"
Error: cannot open "/c/Users/.../repro_dest.db"   # 再現確認
```

一方、Python の `sqlite3` モジュールへ同じ Unix 形式パスを **argv 経由**で渡すと、MSYS の自動
変換が効いてネイティブ Windows Python でも正しく開けることを確認した。

### 修正

`backup_state_db()` を sqlite3 CLI の `.backup` ドットコマンドから、Python の
`sqlite3.Connection.backup()` (SQLite Online Backup API — `.backup` CLI と同じ C API で WAL 中
でも安全という既存実装の意図を維持) へ置き換えた。呼び出しは `notify_failure()` で既に使われて
いる `"$UV" run python - <args> <<'PY' ... PY` パターンを踏襲 (新規パターン追加ではなく既存
スタイルへの追随)。`$UV` は全段で既に必須依存のため新規依存は増えない。sqlite3 CLI 自体への
依存も無くなるため、CLI 不在環境でも動く副次的な利点がある。Mac 側の挙動は変更なし (同じ
Online Backup API・同じ fail-open 分岐)。

## 2. 資源プリフライト (T55) の Windows 対応

### 方針

- **swap**: Windows でも「swap 枯渇 → TTS 劣化」という T55 の本質的リスクは同じなので実装する。
  PowerShell `Get-CimInstance Win32_PageFileUsage` の `CurrentUsage` (MB) 合計を取得
  (`get_swap_used_mb_windows()`)。ページファイル使用量は macOS の `vm.swapusage` used と同じ
  「仮想メモリのコミット済み使用量 (MB)」という意味の指標であり、既存の `KARYU_MAX_SWAP_MB`
  閾値をそのまま流用できる。レイテンシは実測 0.28s 程度で許容範囲。
- **load average**: Windows に直接の等価指標が無い。CPU 使用率やプロセッサキュー長を代用値と
  すると、Unix load average 前提でチューニングされた既定閾値 `KARYU_MAX_LOAD=25` と意味が
  食い違い、閾値が実質無効化される/誤検知するリスクがある。**無理に実装せず**、Windows では
  常に N/A のままとし、ログレベルを WARNING → INFO に格下げして「既知の制約」と明記した
  (指示の「取得不能なら fail-open を維持しつつ WARNING ではなく INFO に格下げ」に対応)。

### `resources_ok()` のロジック変更

旧実装は「swap/load いずれかが不正・未取得なら**両方**を諦めて fail-open で `produce` を実行」
という all-or-nothing だった。この仕様のままだと、Windows で load が常に N/A になる限り、
新しく実装した swap チェックが**永久に無効化される** (swap が分かっていても無視される) ため、
Windows 対応の実質的な意味が無くなってしまう。そこで「取得できた指標のみで判定する」部分判定へ
変更した:

- swap・load それぞれ独立に `known` フラグを持ち、両方 unknown の場合のみ従来どおり fail-open
  (WARNING + 続行)。
- 片方だけ known なら、known な方だけで閾値判定する (unknown 側は「超過していない」扱い)。
- Windows で load が unknown な場合は INFO ログ、それ以外 (Mac 側で万一 sysctl が失敗した場合)
  は従来どおり WARNING ログ。

この変更は Mac 側の実運用パス (sysctl が通常どおり成功する限り) には影響しない。契約テスト
`tests/test_daily_pipeline.py` は `KARYU_SWAP_USED_MB` / `KARYU_LOAD_1MIN` を**常に両方明示注入**
しているため、既存 8 テストのアサーションには影響しない (下記「品質ゲート」参照)。

## 手動 smoke (bash -x 相当、関数抽出実行)

`daily_pipeline.sh` を丸ごと実行すると LLM/TTS 費用が発生するため、`backup_state_db` /
`resources_ok` の関数定義だけを awk で抽出し (Irodori サーバ起動・多重起動ロックなど副作用のある
top-level コードは含めない)、ジョブ scratchpad 上で個別に呼び出して検証した。

| # | シナリオ | 結果 |
|---|---|---|
| 1 | `backup_state_db` (state.db あり、3 行 insert) | バックアップ成功ログ、コピー先の行数一致 (PASS) |
| 2 | `backup_state_db` (state.db 無し) | 「state.db 未作成 — バックアップをスキップ」(PASS) |
| 3 | `resources_ok` (実測、env 注入なし) | swap=224M (PowerShell 実測) / load=N/A (INFO ログ) → 閾値内で OK (PASS) |
| 4 | `resources_ok` (`KARYU_SWAP_USED_MB=13000`, 閾値 12000, load 注入なし) | load=N/A でも swap 単独超過でスキップ (rc=1) (PASS) |
| 5 | `resources_ok` (swap=500/load=1 両方注入、閾値内) | 「資源チェック OK」(PASS) |
| 6 | `resources_ok` (`KARYU_MAX_SWAP_MB=abc` 不正値、swap=13000) | 既定 12000 へ置換 WARN + スキップ (PASS) |

全 6 シナリオ PASS。

## RSSHub (Docker) 検証

- `docker --version` → 29.6.1 / `docker compose version` → v5.3.0 (クライアントは導入済み)。
- 初回 `docker compose up -d rsshub` はデーモン未起動で失敗
  (`failed to connect to ... dockerDesktopLinuxEngine`)。
- `Docker Desktop.exe` を起動しデーモン起動を待機 (約 5〜10s で `docker info` 成功)。
- 再度 `docker compose up -d rsshub` → 既存の `karyu-rsshub` コンテナ (直前の起動で作成済み)
  との名前衝突ログが出たが、コンテナ自体は `Up ... (healthy)` で正常稼働。
- `curl -s http://localhost:1200` → **HTTP 200**、`Welcome to RSSHub!` を確認。疎通成功。
- 指示どおり**起動したままにしている** (`docker compose down` は未実行)。

結論: この Windows 機では Docker 経由で RSSHub を問題なく起動・運用できる。Windows での日次
運用固定化を検討する場合、`daily_pipeline.sh` からの `docker compose up -d rsshub` 呼び出し
追加は本チケットのスコープ外 (Issue #75 は「検討」までが依頼) のため見送り、Issue へ結果を
コメントする。

## 品質ゲート (fresh 実行)

```
$ bash -n scripts/daily_pipeline.sh
(構文エラーなし)

$ shellcheck scripts/daily_pipeline.sh
(shellcheck 未導入のためスキップ。bash -n のみ実施)

$ uv run pytest -q --junitxml=...
tests=713 errors=0 failures=0 skipped=11 (13.27s)
# skipped 11 件は tests/test_daily_pipeline.py の
# `pytestmark = pytest.mark.skipif(sys.platform == "win32" ...)` による既知の Windows 限定
# スキップ (同ファイルの docstring: WSL bash 経由になり Windows パスを解釈できないため)。
# 本チケットの変更はこのファイルの assert 文字列 (資源チェック / バックアップの成功ログ文言)
# を変更していないため、Mac/Linux 実行時も従来どおり緑になる想定 (このマシンでは実行不可のため
# 上記の関数抽出 smoke で代替検証済み)。

$ git diff --check
(出力なし = クリーン)
```

Python ファイルは変更していないため ruff / mypy は対象外 (AGENTS.md §8.3 準拠、シェルスクリプト
のみの変更)。

## 保守側に倒した判断

- **load average を Windows で代替値を捏造しない**: CPU 使用率等の似て非なる指標を
  `KARYU_MAX_LOAD` にそのまま当てはめると、閾値の意味が変わってしまい「常に超過判定」または
  「常に非超過判定」という静かな誤動作を招くリスクがあった。指示の「実装コストと信頼性で判断」
  に従い、意味の合う swap のみ実装し、load は明示的に N/A + INFO ログに留めた。
- **`resources_ok()` を all-or-nothing から部分判定へ変更**: Windows 対応 (swap のみ既知) を
  実質的に機能させるために必要な変更。契約テストは常に両方注入するため既存アサーションに
  影響しないことを読み込みで確認済み。
- **sqlite3 CLI 依存を撤廃し Python 経由に統一**: Mac / Windows 両対応を uname 分岐で作り込む
  よりも、両OSで動作確認済みの Python (`$UV`) 経由の 1 実装に統一する方が保守コストが低く、
  MSYS パス変換の落とし穴を構造的に踏まなくなる。
- **RSSHub の daily_pipeline.sh への組み込みは見送り**: Issue #75 の依頼は Docker 起動検証まで。
  日次運用への組み込みは「Windows に固定するなら」という条件付きの提案であり、恒久運用判断は
  AGENTS.md §3.4 のスコープ膨張 NG / 人間判断待ちの対象。今回は検証結果を Issue にコメントし、
  実装はスコープ外として見送った。
