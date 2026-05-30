# 設計: karyu-tech-news Sprint 1A 収集基盤

> 参照: [requirements-v1.0.md](./requirements-v1.0.md), [WORKFLOW.md](./WORKFLOW.md), [source-selection-spike-v0.1.md](./source-selection-spike-v0.1.md)
> 作成: アーキテクト (Claude Code / Opus)
> ステータス: Sprint 1A 確定版 (実装着手可)
> 改訂: 仕様変更時に追補し、ADR に判断を残す

本書は Sprint 1A における **単一の真実の源 (Single Source of Truth)** である。実装者・レビュアー・QA は本書を基準に作業し、本書に反する判断を発見した場合は実装を止めてエスカレーションする (`WORKFLOW.md` §4)。

---

## 1. 設計方針

Sprint 1A の目的は「収集基盤が壊れずに動くか」を検証することであり、**最小構成・fail-open・状態の外部永続化** の3点に集中する。

- **言語**: Python 3.11+ 単一。`tc-newsflow` (Go) の設計思想のみ継承し、コード移植はしない (ADR-0001)。
- **永続化**: SQLite (`data/state.db`)。スキーマは要件 §12 を厳守し、`UNIQUE(source_id, item_key)` を不変条件とする。
- **耐障害性**: ソース単位 fail-open。1ソースの失敗でパイプライン全体を止めない。Webhook 失敗も収集を fail させない。
- **外部依存最小化**: feedparser / httpx / pydantic / sqlalchemy / pyyaml / python-dotenv / typer / pytest。Sprint 1A では LLM・TTS・動画系を一切含めない。
- **設定駆動**: ソース・LLM プロファイル・HAL ペルソナ・番組フォーマットを YAML 化し、コード変更なしに切替可能にする。

## 2. 検討した代替案と採用理由

| 案 | 長所 | 短所 | 採否 |
|---|---|---|---|
| Go (tc-newsflow拡張) | 既存資産流用、性能 | TTS/Discord/YouTube エコシステムが薄く2言語化する | 不採用 (ADR-0001) |
| Python 単一 | エコシステム最厚、個人運用持続性 | 性能はGoに劣るが本用途には十分 | **採用** |
| Node.js | RSS/Discord系充実 | TTS/動画系で別言語必要 | 不採用 |
| Discord Bot 常駐 | リアクション承認可 | Gateway/権限/再起動復帰など運用負荷 | 不採用 (ADR-0003): Webhook で開始 |
| RSSHub Public | セルフホスト不要 | Cookie 管理・ルート障害調査不能 | 不採用 (ADR-0004): セルフホスト |
| Playwright 収集 | Cookie/JS必須ルートも取得可 | 個人運用で破綻 | Sprint 1A 対象外 |

## 3. API / インターフェース境界

### 3.1 CLI (typer)

```
python -m karyu_tech_news --help
python -m karyu_tech_news init-db          # スキーマ作成
python -m karyu_tech_news validate-sources # sources.yaml 構文検証 + URL HEAD
python -m karyu_tech_news collect [--dry-run] [--source <id>]
python -m karyu_tech_news post-summary [--run-id <id>]
```

### 3.2 内部モジュール境界

```
src/karyu_tech_news/
├── config/         # YAML / .env ローダ (純関数)
├── collect/        # RSS/RSSHub取得 → RawItem 正規化
│   ├── fetcher.py      # httpx + feedparser
│   ├── normalize.py    # entry → RawItem
│   └── runner.py       # ソース横断オーケストレーション
├── store/          # SQLAlchemy: items / sources / source_health / collect_runs
├── deliver/
│   └── discord.py      # Webhook POST + サマリー整形
├── cli.py          # typer エントリ
└── main.py         # python -m 起点
```

逆向き依存を禁止する。`collect` は `store` を import してよいが `deliver` は import しない。`deliver` は `store` の読み取り API のみ参照。

### 3.3 主要データ型 (pydantic)

```python
class RawItem(BaseModel):
    item_key: str            # FR-021: 必須・空不可
    external_id: str | None
    title: str
    link: str
    summary: str | None
    published_at: datetime | None
    fetched_at: datetime
    source_id: str
    canonical_url_hash: str  # FR-022
    raw_json: dict           # 取得時の生データ

class FetchResult(BaseModel):
    source_id: str
    ok: bool
    items: list[RawItem]
    error: str | None
    duration_ms: int
```

## 4. データ構造・スキーマ

要件 §12 を実装に落とす。**`hash` 単体に UNIQUE を張ってはならない** (FR-031)。

```sql
CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 4),
  category TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  requires_cookie INTEGER NOT NULL DEFAULT 0,
  notes TEXT
);

CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL REFERENCES sources(id),
  item_key TEXT NOT NULL,
  external_id TEXT,
  title TEXT NOT NULL,
  link TEXT NOT NULL,
  summary TEXT,
  published_at TIMESTAMP,
  fetched_at TIMESTAMP NOT NULL,
  raw_json TEXT NOT NULL,
  canonical_url_hash TEXT NOT NULL,
  UNIQUE (source_id, item_key)
);
CREATE INDEX idx_items_canonical_hash ON items(canonical_url_hash);
CREATE INDEX idx_items_published ON items(published_at DESC);

CREATE TABLE source_health (
  source_id TEXT PRIMARY KEY REFERENCES sources(id),
  last_success_at TIMESTAMP,
  last_failure_at TIMESTAMP,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);

CREATE TABLE collect_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  total_sources INTEGER NOT NULL,
  successful_sources INTEGER NOT NULL,
  failed_sources INTEGER NOT NULL,
  total_items INTEGER NOT NULL,
  new_items INTEGER NOT NULL
);
```

### 4.1 item_key 生成順序 (FR-021)

```
external_id があれば → external_id
なければ link
なければ sha256(title|published_at|source_id)
```

`item_key` が空のレコードを **書き込んではならない**。書き込み直前にアサート。

### 4.2 canonical_url_hash (FR-022)

`urllib.parse.urlsplit` で正規化 (scheme/host 小文字化、末尾スラッシュ除去、UTMパラメータ除去) してから sha256。Sprint 1A では検出には使わない、保持のみ。

## 5. 変更が及ぶ範囲

新規プロジェクトのため既存影響なし。生成成果物:

- `src/karyu_tech_news/**` (新規)
- `config/sources.yaml`, `config/llm_profiles.yaml`, `config/hal_persona.yaml`, `config/show_format.yaml`
- `data/state.db` (実行時生成、git管理外)
- `docker-compose.yml` (RSSHub セルフホスト)
- `.env.example`
- `tests/**`

## 6. リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| RSSHub ルート破壊 | 掘金カテゴリ取れず | 3回連続失敗で Discord 警告 (FR-052)、代替ソース保持 |
| GitHub Atom レート制限 | 5本一斉失敗 | リトライ最大2回 (FR-013)、TZ分散実行を将来検討 |
| SQLite ロック | 並行 collect 競合 | Sprint 1A は単一プロセス。複数同時実行を禁止 |
| Webhook URL漏洩 | スパム投稿可能 | `.env` 管理、`.gitignore` 徹底、`.env.example` のみ commit |
| feedparser bozo 誤検知 | 取得失敗扱い | bozo=1 でも entries>=1 なら採用 (Spike §6) |
| タイムアウト無し | プロセス停止 | 各取得 30 秒 (FR-012)、collect 全体 5 分 |
| クロスソース重複 | 同一記事が複数行 | Sprint 1A は許容、1B で `canonical_url_hash` 活用 |

## 7. 実装上の禁止事項

- **`hash` 単体 UNIQUE を張ってはならない** (要件 FR-031 明示)。
- **`item_key` が空のまま INSERT してはならない**。
- **`.env` を commit してはならない**。`.env.example` のみ。
- **収集中の Webhook 失敗で run を fail させてはならない** (FR-071)。
- **main への直接 push 禁止** (WORKFLOW §11)。実装は `agent/<task-id>-impl` ブランチで。
- **mainへのmerge は人間承認後のみ** (WORKFLOW §12)。
- **中国メディア記事本文の転載は禁止**。Sprint 1B 以降の LLM 段で要約に強制。
- **Playwright / 中国IPプロキシ / Cookie必須ルートを Sprint 1A で導入してはならない**。
- **Sprint 1A で LLM・TTS・動画・YouTube 統合を入れてはならない** (スコープ膨張防止)。

## 8. 非機能要件への対応

| 要件 | 対応 |
|---|---|
| メンテナンス性 (§9.1) | Python 単一、依存最小、純関数優先 |
| 持続可能性 (§9.2) | 朝5分以内の確認工数、Discord 1メッセージに集約 |
| 耐障害性 (§9.3) | ソース単位 fail-open、Webhook 例外捕捉 |
| 観測可能性 (§9.4) | `collect_runs` + `source_health` を必ず更新、stdout に構造化ログ |
| セキュリティ (§9.5) | `.env` 管理、`.env.example` のみ commit、git secret scan を CI で |
| 法務 (§9.6) | 本文転載禁止を LLM プロンプトで強制 (1B)。Sprint 1A は影響なし |
| コスト (§9.7) | Sprint 1A は LLM/TTS なしで 0 円 |

## 9. 段階的展開と境界

| 段階 | 含む | 含まない |
|---|---|---|
| Sprint 1A | 収集・SQLite・Discord サマリー | LLM / TTS / 動画 / YouTube |
| Sprint 1B | LLM 編集・Markdown台本 | TTS / 配信 |
| Sprint 2 | TTS / BGM / mp3 | 動画 / YouTube |
| Sprint 3 | 動画 / YouTube 限定公開 | Spotify / Apple |

スプリント越境を禁止する。Sprint 1A の DoD (要件 §15.1) を満たさない限り 1B に進まない。

## 10. オープン論点 (Sprint 1B 以降で判断)

- LLM A/B/C 比較 (FR-083) の実測値次第で Editor/Writer の組合せ確定。
- HAL のリファレンス音声生成: VoiceDesign キャプション案 (要件 §3.4 参照イメージ) を Sprint 2 開始時に確定。
- Discord 添付サイズ問題 (25MB) を超える場合の R2/S3 リンク投稿は Sprint 2 で再検討 (要件 §17.6)。
- 90日超アイテムの定期削除 (FR-042) は Sprint 1B で実装判断。

---

## Appendix A. 関連ADR

- [ADR-0001](./adr/ADR-0001-python-single-language.md) Python 単一化
- [ADR-0002](./adr/ADR-0002-sprint-1a-1b-split.md) Sprint 1A/1B 分割
- [ADR-0003](./adr/ADR-0003-discord-webhook-first.md) Discord は Webhook 起点
- [ADR-0004](./adr/ADR-0004-rsshub-self-host.md) RSSHub セルフホスト
