# コーディング規約 — karyu-tech-news

> 役割: 本プロジェクトの**命名規則・コードスタイル・頻出パターン**を、実コードのスニペットで示す。AI/実装者が既存スタイルに一致したコードを書くための参照元。
> 参照: [pyproject.toml](../pyproject.toml) (ruff/mypy 設定の正), [architecture.md](./architecture.md), [domain/collection.md](./domain/collection.md), グローバル `~/.claude/rules/common/coding-style.md`
> 原則: AGENTS.md §12 (Karpathy 4 原則) を遵守。本書と pyproject.toml が矛盾したら **pyproject.toml が正**。

---

## 1. 基本原則 (Karpathy 4 原則の具体化)

- **Simplicity First**: 問題を解く最小コード。単一用途の抽象化を作らない。200 行が 50 行で済むなら書き直す。
- **Surgical Changes**: Ticket スコープ外を触らない。既存スタイルに合わせる (自分の好みで書き換えない)。
- **Immutability** (グローバルルール CRITICAL): 既存オブジェクトを変更せず**新しいオブジェクトを返す**。リスト破壊 (`list.pop`/裏配列書き換え) を避け、新リストを返す。

```python
# WRONG: 引数を破壊
def remove_topic(topics: list[Topic], idx: int) -> None:
    topics.pop(idx)                      # 呼び出し側の list を破壊

# CORRECT: 新リストを返す
def remove_topic(topics: list[Topic], idx: int) -> list[Topic]:
    return [t for i, t in enumerate(topics) if i != idx]
```

## 2. 言語・ツールチェーン

| 項目 | 値 |
|---|---|
| Python | 3.11+ (`from __future__ import annotations` を全モジュール先頭に) |
| パッケージ管理 | `uv` (hatchling ビルド、src-layout) |
| Lint | `ruff check .` (line-length 100, select E/F/W/I/B/UP/N/SIM) |
| 型 | `mypy --strict` (src/ と tests/ 両方) |
| テスト | `pytest` (`addopts = -q`) |

**ruff の意図的除外** ([pyproject.toml](../pyproject.toml)):
- `E501` (行長): line-length=100 を別途設定済みのため
- `B008` (デフォルト引数での関数呼び出し): **typer が `Option()`/`Argument()` を引数デフォルトに使う設計**のため。回避策ではなくイディオム。

## 3. 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| 配布名 (PyPI) | リポジトリ名 | `panda-tech-news` |
| Python モジュール | snake_case | `karyu_tech_news` |
| console script | 短縮形 | `karyu` |
| ソース id (YAML) | lowercase-kebab、`^[a-z0-9][a-z0-9\-]*$` | `deepseek-github-releases` |
| クラス | PascalCase + 役割サフィックス | `SourceConfig`, `FetchResult`, `Settings` |
| Enum | 値の意味で命名 | `SourceTier.OFFICIAL`, `SourceCategory.AI` |
| 関数 | snake_case 動詞始まり | `load_sources`, `enabled_sources`, `from_env` |
| テスト | `test_<対象>_<条件>` | `test_source_config_rejects_bad_id_pattern` |

> モジュール名 `karyu_tech_news` は全ドキュメント/CLI 例と一致する確定事項 ([PROJECT_STATE.md](./PROJECT_STATE.md))。**配布名と混同しない**。

## 4. 文字列の扱い (継承上の最重要規約)

**バイト単位の切り詰めを絶対にしない** ([design-inheritance §6](./design-inheritance-tc-newsflow.md))。Python の `str` はコードポイント単位なので `len(s)` / スライスで安全。tc-newsflow (Go) の唯一の一貫性の傷 (`truncateText` だけ byte 単位) を Python で再現しない。

```python
# CORRECT: str は既にコードポイント単位
def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit]
# プロンプト用: title 180 / description 420 / 台本トピック 300 文字 (1B)
```

中国語固有名詞はカナ化し初出のみ原語併記 (例:「ディープシーク (DeepSeek)」) — これは台本生成 (1B) の規約だが、辞書/正規化を書く際の前提 ([hal-persona.md](./hal-persona.md) §3)。

## 5. Pydantic パターン

スキーマは `BaseModel`。Enum は `IntEnum`/`StrEnum`。検証は `field_validator`。

```python
from enum import IntEnum, StrEnum
from typing import Annotated
from pydantic import BaseModel, Field, field_validator

class SourceTier(IntEnum):      # int 由来 → YAML の tier: 1 を自動強制変換
    OFFICIAL = 1
    SEMI_OFFICIAL = 2
    COMMUNITY = 3
    RUMOR = 4

class SourceConfig(BaseModel):
    id: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*$")]
    tier: SourceTier
    enabled: bool = True           # 既定値で必須/任意を表現

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http(s)://, got: {v!r}")
        return v
```

- 環境変数ロードは `@classmethod from_env()` パターン (`config.py` 参照)。
- 集約レベルの不変条件 (id 重複禁止等) は `SourcesFile` の `field_validator` で。

## 6. typer (CLI) パターン

```python
app = typer.Typer(name="karyu", no_args_is_help=True, add_completion=False)

@app.command("validate-sources")
def validate_sources(
    sources_file: Path = typer.Option(DEFAULT_SOURCES_PATH, "--sources", "-s", help="..."),
) -> None:
    """1行サマリ + Sprint/Ticket 注記を docstring に書く."""
    ...
    raise typer.Exit(code=1)       # エラーは exit code 1、正常は 0
```

- `Option()` を引数デフォルトに置く (B008 は除外済み)。
- 秘密情報は `info` コマンドで `(set)`/`(not set)` のみ表示し、値を出さない。

## 7. エラーハンドリング (fail-open 規約)

| 状況 | 方針 |
|---|---|
| 1ソース取得失敗 | 例外を捕捉し `FetchResult(ok=False, error=...)` に包む。**ループを抜けない** |
| Webhook 投稿失敗 | ログに記録のみ。collect を fail させない (FR-071) |
| YAML/スキーマ不正 | `validate-sources` は exit 1。**起動時に fail-fast** |
| 秘密情報 | 例外メッセージ・ログに Webhook URL 等を出さない |

```python
# fail-open の典型形
try:
    items = fetch_one(source)
    return FetchResult(source_id=source.id, ok=True, items=items, error=None, duration_ms=ms)
except Exception as exc:                          # noqa: BLE001 — fail-open 意図
    logger.warning("fetch failed: %s: %s", source.id, exc)
    return FetchResult(source_id=source.id, ok=False, items=[], error=str(exc), duration_ms=ms)
```

**エラーを握りつぶさない** が、fail-open 層では「例外 → 値に変換して継続」が正しい。広域 catch には意図を `# noqa` コメントで残す。

## 8. ロギング

`logging.basicConfig` で stdout へ構造化出力。ステージ名を安定させ将来の可視化に流用 ([architecture §3](./architecture.md))。

```python
logging.basicConfig(
    level=getattr(logging, level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)      # モジュール毎に取得
```

`print` ではなく logger を使う (CLI のユーザー向け出力は `typer.echo`/`typer.secho`)。

## 9. テスト規約

- **TDD 推奨** (グローバル testing.md): RED → GREEN → REFACTOR。カバレッジ 80% 目標。
- 1 テスト 1 条件。`test_<対象>_<期待>` 命名。
- 意図的な型違反テストは `# type: ignore[arg-type]` を付け、mypy strict を維持。
- 実 `config/sources.yaml` を読む結合テストを 1 本持ち、確定構成 (11本中9有効) を固定する。
- **CLI / `load_dotenv(.env)` を経由するテストで、環境変数を「未設定」として扱いたい場合は `monkeypatch.setenv("VAR", "")` (空文字固定) を使う。`delenv` で削除しない** — `delenv` で削除してしまうと、CLIコマンドの `main_callback` 等で呼ばれる `load_dotenv(.env)` によって、開発者のローカル実ファイル (`.env`) から値が再投入され、テストが環境依存になってしまうため。空文字なら「既に環境変数が存在する」として上書きが skip される (`test_collect_with_post_no_webhook_url` の hermetic 化, 2026-06-03)。

```python
def test_source_config_rejects_bad_id_pattern() -> None:
    with pytest.raises(ValidationError):
        SourceConfig(id="Has_Underscore", name="X", url="https://x/feed",
                     tier=SourceTier.OFFICIAL, category=SourceCategory.AI)
```

## 10. ファイル組成

- **多数の小ファイル > 少数の大ファイル**。1 ファイル 200-400 行 (最大 800)。
- フィーチャ/ドメイン単位で分割 (型別ではない): `collect/fetcher.py` `normalize.py` `runner.py`。
- 大モジュールからユーティリティを抽出。深いネスト (>4 階層) を避ける。
- ドキュメント文字列は日本語可 (既存コードに一致)。モジュール冒頭に Sprint/Ticket を明記。

## 11. コミット前チェックリスト (再掲: AGENTS.md §8.3)

```bash
uv run pytest          # 緑
uv run ruff check .    # クリーン
uv run mypy src tests  # strict クリーン
```

3 つすべて緑になるまで完了としない (Goal-Driven Execution, AGENTS.md §12.4)。
