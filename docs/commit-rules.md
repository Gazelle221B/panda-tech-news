# コミット規約と完了ゲート — karyu-tech-news

> 役割: 「コードを書いた」と「コミット/完了」の間に置く**検証ゲート**を一箇所に集約する。**AI が壊れたコードを「完了しました」と宣言・コミットする事故を防ぐ**のが本書の存在理由。
> 参照: AGENTS.md §8 (規約) / §9 (品質ゲート) / §3 (絶対NG) / §12.4 (Goal-Driven), [WORKFLOW.md](./WORKFLOW.md) §10 (DoD), [styleguide.md](./styleguide.md) §9/§11, グローバル `~/.claude/rules/common/git-workflow.md`
> 正の所在: メッセージ書式の正は AGENTS.md §8.1、段階別 DoD の正は WORKFLOW.md §10。本書はそれらへのゲート集約であり、矛盾時はそれらが正。

---

## 1. 完了宣言ゲート (最重要・本書の核)

**「完了しました」と言う前、コミットする前に、下記3つすべてが緑であることを *その場で実行した出力* で確認する。記憶・推測・「さっき通った」で代用しない。**

```bash
uv run pytest          # 全 pass (現状 48/48)
uv run ruff check .    # クリーン
uv run mypy src tests  # strict クリーン
```

判断ルール:
- 1つでも赤なら **未完了**。完了と報告してはならない (AGENTS.md §12.4 Goal-Driven Execution)。
- テストを通すために**まず実装の誤りを疑う**。テストを書き換えて緑にする (テストを壊す) のは禁止 — 仕様が間違っている確証があり、かつ人間に確認した場合のみ。
- 「ローカルで動いた気がする」は完了の根拠にならない。fresh な実行出力を `docs/TEST_LOG.md` に証跡として残す。
- 既存の lint/型エラーが**自分の変更由来か既存かを切り分ける** (例: `git stash` で退避して再実行)。既存の赤を新規変更の言い訳にしない。

> なぜこのゲートが要るか: LLM は「もっともらしい完了報告」を生成しがちで、検証なしに done と言う失敗様式がある。本ゲートは「宣言」を「検証済み事実」に縛る。

## 2. コミットメッセージ規約

書式の正は AGENTS.md §8.1 (Conventional Commits)。要点のみ再掲:

```
<type>: <description>

<optional body>
```

- `type`: `feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `perf` / `ci`
- secret (Webhook URL / API キー) をメッセージ・本文に残さない。
- `--no-verify` / `--no-gpg-sign` 等の **hook スキップ禁止** (AGENTS.md §3.1)。
- 例: `feat: T3 RSS/RSSHub フェッチャ (fail-open)`, `docs: add commit gate`

## 3. コミット前チェックリスト

AGENTS.md §8.3 を実行手順として再掲 (上から順に):

- [ ] §1 完了宣言ゲート (pytest / ruff / mypy strict) を **fresh 出力**で確認
- [ ] `docs/TEST_LOG.md` に実行コマンドと結果を追記
- [ ] `docs/PROJECT_STATE.md` を最新化 (現フェーズ・次アクション・人間判断待ち)
- [ ] AGENTS.md §3「絶対NG」に抵触していないか自己点検
- [ ] `git status` で `.env` / 秘密情報 / 生成 `*.mp3`・`*.mp4`・`*.db` を含めていないか確認
- [ ] 変更が Ticket スコープに直接トレースできるか (無関係な整形・リファクタを混ぜない, AGENTS.md §12.3)

## 4. 「完了」の定義 (DoD)

段階別 DoD の正は [WORKFLOW.md](./WORKFLOW.md) §10。Sprint 1A 全体の DoD は AGENTS.md §9 / [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)「完了の定義」。

| 段階 | 完了条件 (要約) | 証跡 |
|---|---|---|
| 実装完了 | コード変更 + ローカルテスト緑 + 変更要約 | `docs/TEST_LOG.md` |
| レビュー合格 | Codex が Critical/High 指摘ゼロ判定 | `docs/REVIEW_REPORT.md` (証跡欄必須) |
| 検収可能 | Antigravity が DESIGN/差分/テスト/README の整合確認 | `docs/QA_REPORT.md` |
| 完了 | 上記すべて + **人間が merge 承認** | — |

**各段階の DoD を満たさない限り次工程に進めない。**「一応動いた」を完了扱いしない (WORKFLOW §10)。

## 5. ブランチ / merge ゲート

詳細は AGENTS.md §8.2:
- 実装は `agent/T<N>-impl` ブランチ。**`main` への直接 push 禁止**。
- merge は **Codex レビュー PASS + Antigravity QA PASS + 人間承認** の三条件を満たした後のみ。
- **AI エージェントは merge しない** (例外は明示的人間許可のみ, WORKFLOW §12)。

## 6. 境界 (Boundaries) — コミット前に侵していないか

完全な禁止リストは AGENTS.md §3。コミット前に特に確認する3観点:

| 観点 | 内容 | 参照 |
|---|---|---|
| 触れてはいけない | `.env` (commit 禁止) / `main` (直接 push 禁止) / 他 Ticket スコープ外のファイル | §3.1, §12.3 |
| 要確認 (人間判断待ち) | 依存追加 / スキーマ変更 / スコープ拡大 / dead code 削除 → エスカレーション | §7, §11 |
| 絶対禁止 | `hash` 単体 UNIQUE / `item_key` 空 INSERT / バイト切り詰め / fail-open 違反 / Sprint 越境 / 中国記事本文転載 | §3.2〜§3.6 |

---

> 本書はゲートの**集約点**であり規約の二重定義ではない。各正本 (AGENTS.md §8/§9/§3, WORKFLOW.md §10) が更新されたら本書の参照も同期する。
