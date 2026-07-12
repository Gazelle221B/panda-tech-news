# ADR-0008: 追記型共有ログを1チケット1ファイルへシャーディングする

- 日付: 2026-07-11
- ステータス: Accepted (発効: [PR #33](https://github.com/Gazelle221B/panda-tech-news/pull/33) の人間マージ時点)
- 決定者: 人間 (プロダクトオーナー) + Claude Code (アーキテクト)
- 関連: [AGENTS.md](../../AGENTS.md) §8.3, [WORKFLOW.md](../WORKFLOW.md) §14, [commit-rules.md](../commit-rules.md), T49

## 背景

`docs/TEST_LOG.md` / `docs/REVIEW_REPORT.md` / `docs/QA_REPORT.md` は WORKFLOW.md §14 の DoD 証跡として、実装完了時に OpenCode が、レビュー合格時に Codex が、検収時に Antigravity が、それぞれ同一ファイルの末尾に追記する運用になっている。

しかし複数チケットが並行して `agent/T<N>-impl` ブランチで進行すると、全ブランチが同じ 3 ファイルの同じ末尾行を追記対象にするため、**Git 上は必然的に同一ハンクへの競合編集**になる。実際に PR #29〜#32 が並行した際、1 件マージするたびに残りの全 PR がこれら追記型ファイルでコンフリクトを起こす事象が発生した。これは特定の実装ミスではなく、「複数ブランチが同一ファイルの末尾に追記する」という構造そのものが原因であり、ブランチ運用を変えない限り再発し続ける。

## 検討した案

| 案 | 長所 | 短所 |
|---|---|---|
| (a) `.gitattributes` に `merge=union` を設定 | 設定のみで導入でき、コード変更不要 | `union` は git 組み込みの merge driver だが、GitHub の PR マージ判定・Web UI マージはリポジトリの `.gitattributes` の `merge` 属性 (union もカスタム driver も) を尊重しない[^1]。ローカル `git merge` でしか効かず、本プロジェクトの「人間が GitHub 上で merge 承認」する運用 (AGENTS.md §3.1) の解決にならない |
| (b) PR を直列運用する (常に 1 本ずつ完了させてから次を着手) | コンフリクトが原理的に起きない | 並行実装によるスループットが失われる。マルチエージェント運用 (AGENTS.md §7) の前提と矛盾し、チケット数が増えるほど待ち行列が伸びる |
| (c) 既存ログの全面移行 (過去分も含め全チケットをファイル分割し直す) | 一貫した粒度になる | 巨大な diff による履歴・blame の破壊、過去の PR レビュー時点のリンク切れ、移行作業自体のリスクが対策の目的に見合わない |
| (d) 新規追記分のみ「1 チケット1ファイル」にシャーディングし、既存ログは凍結して残す (採用) | 既存履歴を一切壊さず、以後の並行 PR で追記対象ファイルが重ならなくなる。ディレクトリ一覧が時系列インデックスを兼ねる | 過去ログと新ログで参照先が二重になる (凍結注記でリンクし解消) |

## 決定

**追記型共有ログ (`docs/TEST_LOG.md` / `docs/REVIEW_REPORT.md` / `docs/QA_REPORT.md`) への新規追記を 2026-07-11 で凍結し、以後は `docs/test-logs/` / `docs/review-reports/` / `docs/qa-reports/` の3ディレクトリへ「1チケット (=1 impl ブランチ) 1ファイル」でシャーディングする。**

- ファイル命名規則: `YYYY-MM-DD-T<NN>-<slug>.md` (例: `docs/test-logs/2026-07-11-T49-log-sharding.md`)。
- 各ディレクトリに**共有インデックスファイルは意図的に作らない**。インデックスファイル自体が「全ブランチが同じファイルの同じ行に追記する」という、今回解消しようとしている構造をそのまま再生産する新たな衝突点になるため。ディレクトリの `ls` 結果 (ファイル名が日付+チケット番号を含む) が時系列インデックスを兼ねる。
- 既存の `docs/TEST_LOG.md` / `docs/REVIEW_REPORT.md` / `docs/QA_REPORT.md` は内容を一切移行・削除せず、冒頭に凍結注記のみ追加する。

## 根拠

- 「1 impl ブランチ = 1 新規ファイル」にすると、並行する複数ブランチが異なるパスの新規ファイルを作成することになり、Git の観点では「新規ファイルの追加」同士が衝突する状況はほぼ発生しない (同じチケット番号を複数エージェントが同時に取らない限り)。これは AGENTS.md §7 が要求する「並列エージェントは独立ファイルに限定」の原則そのものであり、証跡ログにも同じ原則を適用する形になる。
- 共有インデックスを作らない判断は、まさに本 ADR が解消しようとしている問題 (追記型共有ファイルへの並行書き込み) を新しい場所で再発させないため。ディレクトリ一覧という Git ネイティブな機構で代替できるので、追加の同期コストを払う理由がない。
- 過去ログを凍結のみに留め移行しないのは、Karpathy 4原則の Surgical Changes (AGENTS.md §12.3): 触るのは必要な箇所だけ、既存の証跡を破壊しない。

## 影響

- 実装・他ドキュメントへの反映: `AGENTS.md` §6/§8.3/§10、`docs/PROJECT_STATE.md` 冒頭、`docs/commit-rules.md`、`docs/WORKFLOW.md`、`docs/ORCHESTRATION_RUNBOOK.md`、`prompts/implement.md` / `prompts/review.md` / `prompts/qa.md` の証跡書き先の記述を本 ADR に合わせて更新する (T49 で実施済み)。
- 今後の impl ブランチは `docs/PROJECT_STATE.md` を編集しない (マージ後に main から切る docs ブランチでオーケストレーターがまとめて更新する)。緊急の人間判断待ち追記は単独の docs PR で行ってよい。
- **本 ADR を導入する PR #33 自身について**: PR #33 のブランチは main から切った docs 専用ブランチであり (impl チケットではなく、`src/`/`tests/` には一切触れない)、その中で行う `PROJECT_STATE.md` への注記追加は「impl ブランチでは編集しない」という本運用ルール自体の導入作業として行うもの。したがって本 PR は自らが定めるルールと矛盾しない。
- 将来スプリント: 新規チケットの証跡は本 ADR の命名規則に従う。既存 3 ファイルへの新規追記は行わない。

## 不採用案

- **(a) `.gitattributes` merge=union**: 「いつか GitHub が `.gitattributes` の merge 属性を尊重するようになるかもしれない」という期待に依存する解決策であり、現状の GitHub PR マージ (Web UI / squash) では機能しない[^1]。設定を残しても実効性がないため採用しない。実測としても、本リポジトリでは並行 PR (#29〜#32) のコンフリクトが繰り返し発生しており、GitHub 上の人間マージ運用 (AGENTS.md §3.1) を変えられない以上、ファイル構造側で解決する必要がある。
- **(b) PR 直列運用**: 「そのうちチケット数が減れば問題にならない」という楽観に依存し、マルチエージェント運用の並行性という本プロジェクトの前提そのものを縮小させる。今回の問題はログファイルの構造起因であり、開発プロセス側 (直列化) で吸収するのは対症療法として過大。
- **(c) 既存ログ全面移行**: 「今のうちに全部きれいにしておきたい」という先回りの整備欲求。過去 PR のレビュー証跡・リンクを壊すリスクがシャーディングそのものの効果を上回り、Simplicity First (AGENTS.md §12.2) にも反する。

[^1]: 一次資料 (確認日 2026-07-11): GitHub 公式 community discussion [Pull request conflicts: Support `merge=union` in .gitattributes file (community#9288)](https://github.com/orgs/community/discussions/9288) — GitHub は PR マージでユーザー定義の `.gitattributes` を考慮せず (GitHub 自身の変更不可能な `.gitattributes` を使う)、`union` merge driver も未サポート。回避策はローカル clone でのマージのみと明言されている。実例: [kubernetes/kubernetes#70576](https://github.com/kubernetes/kubernetes/pull/70576) は「GitHub doesn't support it」を理由に union merge driver 指定を削除した。
