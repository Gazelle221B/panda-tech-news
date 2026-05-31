# Ticket #3: RSS/RSSHub フェッチャ実装計画

## 概要

Sprint 1A の Ticket #3 (IMPLEMENTATION_PLAN T4) を実装する。
RSS/RSSHub からフィードを取得し、RawItem に正規化するモジュール。

## 実装対象ファイル

```
src/karyu_tech_news/collect/
├── __init__.py      (空 or docstring のみ)
├── normalize.py     (RawItem, FetchResult, item_key生成, canonical_url_hash)
└── fetcher.py       (httpx + feedparser, retry, timeout, fail-open)

tests/
├── test_normalize.py
└── test_fetcher.py
```

## 型定義 (DESIGN.md §3.3)

### RawItem

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
```

### FetchResult

```python
class FetchResult(BaseModel):
    source_id: str
    ok: bool
    items: list[RawItem]
    error: str | None
    duration_ms: int
```

## normalize.py 仕様

### item_key 生成 (FR-021, architecture §2.2)

優先順:
1. `external_id` があれば → `external_id`
2. なければ `link`
3. なければ `sha256(title|published_at|source_id)`

**空の item_key を返してはならない**。

### canonical_url_hash (FR-022)

```python
def compute_canonical_url_hash(url: str) -> str:
    """URL を正規化して sha256。

    正規化:
    - scheme/host 小文字化
    - 末尾スラッシュ除去
    - UTM パラメータ除去 (utm_*)
    - クエリパラメータソート
    """
```

### feedparser entry → RawItem 変換

```python
def normalize_entry(entry: dict, source_id: str, fetched_at: datetime) -> RawItem:
    """feedparser の entry dict を RawItem に変換。

    - entry.id → external_id
    - entry.link → link
    - entry.title → title
    - entry.summary / entry.description → summary
    - entry.published_parsed / entry.updated_parsed → published_at (time_struct → datetime)
    - entry 全体 → raw_json
    """
```

## fetcher.py 仕様

### 定数

```python
USER_AGENT = "karyu-tech-news/0.1"  # FR-014
TIMEOUT_SECONDS = 30                 # FR-012
MAX_RETRIES = 2                      # FR-013
```

### fetch_one (単一ソース取得)

```python
def fetch_one(source: SourceConfig, rsshub_base_url: str) -> FetchResult:
    """1ソースを取得して FetchResult を返す。

    - source.url の localhost:1200 を rsshub_base_url で置換 (ADR-0004)
    - httpx で GET (timeout=30s, User-Agent 明示)
    - 失敗時リトライ最大2回
    - feedparser.parse でパース
    - bozo=1 でも entries>=1 なら採用 (Spike §6, architecture §2.4)
    - 例外は捕捉して FetchResult(ok=False, error=...) に包む (fail-open)
    - duration_ms を計測
    """
```

### RSSHub URL 展開 (ADR-0004)

```python
def expand_rsshub_url(url: str, rsshub_base_url: str) -> str:
    """http://localhost:1200/... を rsshub_base_url で置換。"""
```

### fail-open (FR-060, styleguide §7)

```python
try:
    items = _fetch_and_parse(source, rsshub_base_url)
    return FetchResult(source_id=source.id, ok=True, items=items, error=None, duration_ms=ms)
except Exception as exc:  # noqa: BLE001 — fail-open 意図
    logger.warning("fetch failed: %s: %s", source.id, exc)
    return FetchResult(source_id=source.id, ok=False, items=[], error=str(exc), duration_ms=ms)
```

## テストケース

### test_normalize.py

1. `test_item_key_from_external_id` — external_id 優先
2. `test_item_key_from_link` — external_id なし → link
3. `test_item_key_from_hash` — external_id/link なし → hash
4. `test_item_key_never_empty` — 空文字列を渡しても空にならない
5. `test_canonical_url_hash_strips_utm` — UTM パラメータ除去
6. `test_canonical_url_hash_normalizes_case` — scheme/host 小文字化
7. `test_canonical_url_hash_strips_trailing_slash` — 末尾スラッシュ除去
8. `test_normalize_entry_basic` — 基本変換
9. `test_normalize_entry_published_parsed` — time_struct → datetime
10. `test_normalize_entry_no_summary` — summary なし → None

### test_fetcher.py

1. `test_fetch_one_success` — モックフィードで取得成功
2. `test_fetch_one_timeout_retries_then_succeeds` — タイムアウト → リトライ → 成功
3. `test_fetch_one_timeout_retries_exhausted` — タイムアウト × 3回 → 失敗
4. `test_fetch_one_bozo_with_entries_adopted` — bozo=1 + entries>=1 → 採用
5. `test_fetch_one_bozo_no_entries_failed` — bozo=1 + entries=0 → 失敗
6. `test_fetch_one_fail_open_wraps_exception` — 例外 → FetchResult(ok=False)
7. `test_expand_rsshub_url` — localhost:1200 置換
8. `test_expand_rsshub_url_no_match` — 非 RSSHub URL はそのまま
9. `test_user_agent_header_sent` — User-Agent 確認

## 禁止事項 (AGENTS.md §3, DESIGN.md §7)

- ❌ `hash` 単体 UNIQUE (今回は DB なしなので該当なし)
- ❌ `item_key` 空での INSERT (normalize で防止)
- ❌ バイト単位の文字列切り詰め (str はコードポイント単位)
- ❌ タイムアウト未指定の HTTP 呼び出し
- ❌ fail-open 違反 (例外でループを抜けない)
- ❌ Sprint 1A スコープ外 (LLM/TTS/動画) 導入
- ❌ `print` 使用 (logger を使う)
- ❌ 引数を破壊するコード (Immutability)

## 完了条件

- [ ] pytest: 全テスト pass (既存 24 + 新規 ~19 = ~43)
- [ ] ruff check: clean
- [ ] mypy strict: clean
- [ ] TEST_LOG.md に実行ログ追記
- [ ] PROJECT_STATE.md 更新

## 実装順序

1. `collect/__init__.py` 作成
2. `collect/normalize.py` 実装
3. `tests/test_normalize.py` 作成・実行
4. `collect/fetcher.py` 実装
5. `tests/test_fetcher.py` 作成・実行
6. 品質ゲート (pytest + ruff + mypy)
7. ドキュメント更新
