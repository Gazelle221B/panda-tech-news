# T51 — Game/Subculture 予備ソース IndieNova の追加 (Issue #38)

- 日付: 2026-07-12
- ブランチ: `agent/T51-indienova-source-impl`
- 実装者: Claude Code
- 参照: [Issue #38](https://github.com/Gazelle221B/panda-tech-news/issues/38), [docs/proposals/game-subculture-source-v0.1.md](../proposals/game-subculture-source-v0.1.md)

## 背景

番組アークの締め (`arc.close = bright`) は Game/Subculture 系の明るい話題を要求するが、既存
9 ソースは AI/Tech 系のみで Game 専門ソースが 0 本だった。2026-06-12 の調査・実検証 (Gemini CLI
候補抽出 → Claude Code がセルフホスト RSSHub で実取得検証) で IndieNova (`/indienova/article`)
が HTTP 200・12 件取得成功と確認済み (yystv・gcores は同時検証で 503 のため不採用)。提案時点では
`enabled: false` (人間判断待ち) として起票し、Issue #38 で人間が「追加して」と判断した (2026-07-12)。

## 変更内容

1. `config/sources.yaml` に Tier3 (COMMUNITY, 独立2ソース確認対象) の新セクションを追加し、
   `docs/proposals/game-subculture-source-v0.1.md` の推薦スニペットどおり `indienova-article`
   (IndieNova 文章, category=Game) を `enabled: true` で追加。`notes` に検証日・yystv/gcores 不採用
   理由・Issue #38 決定日を明記。
2. `tests/test_config.py::test_load_real_project_sources`: 実 `config/sources.yaml` の確定構成を
   検証する既存テストが総ソース数 (11本中9有効) を固定していたため、12本中10有効・Tier3×3・
   Game カテゴリ enabled 1本 (`indienova-article`) へ追随。
3. `tests/test_cli.py::test_validate_sources_real_config`: `validate-sources` コマンドの出力文言
   固定値 (`"OK: 11 sources loaded (9 enabled, 2 disabled)"`) を
   `"OK: 12 sources loaded (10 enabled, 2 disabled)"` へ更新。

他に総ソース数を固定しているテスト・コードは `grep` で確認した限り無し。

## 検証

```
$ uv run python -m karyu_tech_news validate-sources
OK: 12 sources loaded (10 enabled, 2 disabled)

Tier breakdown (enabled only):
  Tier1 (OFFICIAL      ): 5
  Tier2 (SEMI_OFFICIAL ): 2
  Tier3 (COMMUNITY     ): 3
  Tier4 (RUMOR         ): 0

Category breakdown (enabled only):
  AI          : 8
  Game        : 1
  Tech        : 1
```

**実スモーク (ネットワーク到達性あり、fail-open 経路も実質確認)**: `docker compose` の RSSHub
(`karyu-rsshub`, healthy) が稼働中だったため、`--dry-run` に加えて実 collect も実行できた
(`data/state.db` は汚さず `/tmp` の一時 DB へ隔離)。

```
$ uv run python -m karyu_tech_news init-db --db-path /tmp/t51_smoke.db
Database initialized: /tmp/t51_smoke.db

$ uv run python -m karyu_tech_news collect --source indienova-article --db-path /tmp/t51_smoke.db
2026-07-12 20:49:09 [INFO] karyu_tech_news.collect.runner: fetching: indienova-article
2026-07-12 20:49:10 [INFO] karyu_tech_news.collect.runner: success: indienova-article (12 items, 12 new)
Collection completed: 1/1 sources, 12 new items
```

`items` テーブルに 12 件挿入、`source_health.consecutive_failures = 0` を sqlite3 で確認 (提案書の
2026-06-12 検証結果「HTTP 200・12件取得成功」と一致)。取得したタイトル例:
「Auriea Harvey & Michaël Samyn 超越游戏 | 非游戏」「2026夏季itch.io独立游戏佳作选（上）」等、
インディーゲーム/サブカル系で bright 枠の趣旨に合致。一時 DB はリポジトリ外 (`/tmp`) のため
`.gitignore` 対応不要、コミット対象にも含めていない。

## 品質ゲート (fresh 実行)

```
$ uv run pytest
538 passed, 1 skipped in 5.74s

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 82 source files

$ git diff --check
(出力なし = クリーン)
```

pytest 件数は T50 マージ前時点 (538 passed, 1 skipped) から変化なし (既存 2 テストの期待値更新の
み、新規テスト関数は追加していない)。

## 保守側に倒した判断

- 提案書の実検証テーブルは `/indienova/article`・`/indienova/news` 両ルートで HTTP 200 (各12件)
  だったが、「推薦」節が明示的に挙げているのは `/indienova/article` の 1 エントリのみだったため、
  本チケットでもそれ 1 本のみを追加した (Issue #38 の回答も "追加して" のみで本数の指定なし)。
  `/indienova/news` を追加するかは別途判断が必要であれば改めて提案する。
- Tier3 なので `edit/select.py` の独立2ソース確認ゲートの対象になる (掘金と同じ扱い)。今回のスコー
  プはソース追加のみで、選定ロジック側の変更は行っていない (既存の Tier3 運用に委ねる)。
