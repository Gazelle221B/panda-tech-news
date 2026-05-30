# テストログ

> 参照: [WORKFLOW.md](./WORKFLOW.md) §14, [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)
> 更新者: OpenCode (実装担当)
> 役割: 各タスクの実装完了時に **実行コマンドと結果** を残し、Codex レビューの証跡とする。

実行ログ本体は `artifacts/test-results/<task-id>-<date>.log` に保存し、本ファイルにはサマリーのみ追記する。

---

## テンプレ (タスク完了ごとに追記)

```markdown
## T<ID> <タスク名>  (実装者: OpenCode / 日付: YYYY-MM-DD)

### 実行コマンド

\`\`\`bash
pytest tests/test_<...>.py -v --cov=src/karyu_tech_news/<...>
\`\`\`

### 結果サマリー

- passed: N / failed: 0
- coverage: NN%
- artifacts: artifacts/test-results/T<ID>-YYYY-MM-DD.log

### 既知制限

- (あれば箇条書き)

### Codex への引き継ぎポイント

- DESIGN.md §X.Y に対応
- 重点的に見てほしい箇所: <ファイル:行>
```

---

## 履歴

## T1 + T3(schema): プロジェクト初期化・CLIスケルトン・ソーススキーマ  (実装: autopilot / 日付: 2026-05-30)

### 実行コマンド

```bash
uv sync
uv run python -m karyu_tech_news --help
uv run python -m karyu_tech_news validate-sources
uv run pytest
uv run ruff check src tests
uv run mypy src
```

### 結果サマリー

- CLI `--help`: サブコマンド version / validate-sources / info を表示。
- `validate-sources`: `OK: 11 sources loaded (9 enabled, 2 disabled)`、Tier 5/2/2/0、disabled 2本(jiqizhixin-rss, huxiu-rss)を黄色注記。exit 0。
- pytest: **24 passed** / failed 0 (test_config.py 17 + test_cli.py 7)。
- ruff check: All checks passed (B008 は typer の Option() デフォルト設計のため除外)。
- mypy --strict: Success, no issues in 4 source files。
- `info` は Webhook URL を `(set)/(not set)` のみ表示し秘密値を出さないことをテストで保証。

### 既知制限

- DB・フェッチャ・Discord は未実装 (Ticket #3 以降)。`collect` / `init-db` / `post-summary` は未提供。
- 実行は **uv 必須**。システム python3 は 3.9 で `StrEnum` 非対応 (requires-python >=3.11)。

### 引き継ぎポイント (Ticket #3 フェッチャ)

- `config.SourcesFile.enabled_sources()` を入力に `FetchResult` のリストを返す (design-inheritance §1, §11)。
- fail-open: 1ソース失敗で全体を止めない。例外は FetchResult に包む。
- 検証データは ADOPT 5本(実 entries) + 監視 4本(entries=0 の正常空振り) + disabled 2本 の3状態を最初から扱える。
