検証完了です。以下が2段階チェックの結果です。

curl check（HTTP応答確認）
| ソース                | 状態               | 備考                                          |
| --------------------- | ------------------ | --------------------------------------------- |
| GitHub Releases (5社) | 200 / HTTP/2 200   | DeepSeekのみ1件、他4社は0件（リリース未発行） |
| 机器之心 (jiqizhixin) | 302 → data-service | **DEFER** — RSS以外へリダイレクト             |
| 量子位 (qbitai)       | 403 Forbidden      | feedparser側では200で取得できた模様           |
| 36kr-newsflash        | 200 OK             | 正常                                          |
| 虎嗅 (huxiu)          | 確認済             | feedparserでboゾ                              |
| 掘金 (juejin ×2)      | 200 OK             | RSSHub経由で正常                              |
feedparser check（フィード構造検証）
| id                        | entries | bozo | verdict   |
| ------------------------- | ------- | ---- | --------- |
| deepseek-github-releases  | 1       | 0    | **ADOPT** |
| qwen-github-releases      | 0       | 0    | EMPTY     |
| moonshot-kimi-github      | 0       | 0    | EMPTY     |
| zhipu-glm-github          | 0       | 0    | EMPTY     |
| xiaomi-mimo-github        | 0       | 0    | EMPTY     |
| qbitai-feed               | 10      | 0    | **ADOPT** |
| jiqizhixin-rss            | 0       | 1    | **DEFER** |
| 36kr-newsflash            | 20      | 0    | **ADOPT** |
| huxiu-rss                 | 0       | 1    | **DEFER** |
| juejin-ai-category        | 20      | 0    | **ADOPT** |
| juejin-trending-ai-weekly | 20      | 0    | **ADOPT** |
判断

ADOPT（5ソース）: deepseek-github-releases、qbitai-feed、36kr-newsflash、juejin-ai-category、juejin-trending-ai-weekly

EMPTY（4ソース）: GitHub ReleasesのQwen/Moonshot/Zhipu/Xiaomi — リリース未発行の新規リポジトリ。監視対象として維持し、リリース発生時に自動的に拾う。

DEFER（2ソース）: 机器之心（RSS廃止/リダイレクト）、虎嗅（フィード構造エラー）



RSSHub (http://localhost:1200) は正常起動・稼働中です。

こんな感じですね
完璧な検証データです。一つずつ判定していきます。結論から言うと、Sprint 1A は今すぐ着手可能で、ソースリストの微調整だけ入れて Ticket #1 に進めます。

検証結果の分析
ADOPT 5本: 確定
deepseek-github-releases(1件)、qbitai-feed(10件)、36kr-newsflash(20件)、juejin-ai-category(20件)、juejin-trending-ai-weekly(20件)。合計71件取れている時点で、Sprint 1A の収集基盤検証としては十分量です。

EMPTY 4本: 監視維持で正しい
Qwen/Moonshot/Zhipu/Xiaomi の GitHub Atom が 0 件なのは、フィード自体は正常応答(HTTP 200、bozo=0)で entries が空、つまり「正しく動いているがリリース履歴がない/少ない」状態。これは enabled: true のまま残すのが正解です。理由を3つ:

リポジトリ名が新世代に切り替わっている可能性(Qwen3 → Qwen3.5 や Qwen-Next 等)。これは Sprint 1A 観察期間中に Qwen 公式が新リリースを切ったタイミングで自然に拾える
監視対象として残しておけば、来週リリースされた瞬間に拾える。今外すと、外したことを忘れて後で気づけない
fail-open 設計のテスト材料として、「0件返すソース」が混ざっている状態は良い検証になる
ただし、fallback URL を notes に追記しておくと将来の自分が楽です。例えば Qwen は QwenLM/Qwen3 が空なら QwenLM/Qwen や QwenLM/Qwen2.5 の方が活発、みたいな情報。これは Sprint 1A 観察期間中に「3日連続で 0 件のリポジトリ」を見つけたら、リポジトリ名を見直すという運用ルールに落とせます。

DEFER 2本: 扱いを分ける
机器之心(jiqizhixin): HTTP 302 で data-service へ、feedparser でも bozo=1。これは RSS 自体が廃止された可能性が濃厚。enabled: false のまま維持で OK。RSSHub 経由(/jiqizhixin/full)の代替を Sprint 1B 以降で試す。

虎嗅(huxiu): curl では確認済みになっているが feedparser で bozo=1 で entries=0。これは XML として壊れているか、Content-Type が text/html を返しているか、エンコーディングが Shift_JIS 系の罠を踏んでいる可能性。enabled: false に落として、RSSHub 経由の代替を入れる方が良いです。

ソースリストの微調整提案
Sprint 1A の有効ソース数を維持するため、以下の差し替えを提案します。

huxiu の代替: 差し替え候補表で挙げていた「晚点 LatePost(RSSHub)」を採用。RSSHub ルートは /latepost/news または /latepost/feed 系で取れる想定。これも Spike 検証要。

保険として SegmentFault も追加: 掘金 2本だけだと Tier3 が同一プラットフォーム集中なので、SegmentFault を入れて Tier3 を 3本に増やすと、Sprint 1B の「同一ネタが複数 Tier3 で言及」判定がより意味を持ちます。

ただしこれは「やってもいい」程度で、Sprint 1A の目的(収集基盤の検証)からすると 現状 ADOPT 5本 + EMPTY 監視 4本 + DEFER 2本 = 計11本 のままでも十分動きます。差し替えは Sprint 1A 観察期間中に並行検証する選択肢もあります。

私の推奨判断
Sprint 1A は 現状のソースリストのまま着手し、Ticket #1 の実装に入る。理由:

ADOPT 5本(71件/日)で収集基盤の検証は十分可能
EMPTY 4本は fail-open の挙動確認に良い材料(エラーではないが結果が空のケース)
DEFER 2本は enabled: false のまま、Sprint 1A 完了後の振り返りで差し替え判断
huxiu の代替や SegmentFault 追加は Sprint 1A 観察期間中に並行 Spike しても良いが、今すぐ着手の妨げにはしない
ソースの差し替えで Ticket #1 着手を遅らせるのは、また「情報源調査プロジェクト」の罠に戻ってしまいます。

更新差分(最小限)
config/sources.yaml の huxiu を enabled: false に変更:

Copy  - id: huxiu-rss
    name: 虎嗅
    url: "https://www.huxiu.com/rss/0.xml"
    tier: 2
    category: Tech
    enabled: false  # ← true から変更
    requires_cookie: false
    notes: "feedparser bozo=1、entries=0。XML破損または Content-Type 不一致の可能性。Sprint 1A 後に RSSHub 経由 (/huxiu/article) で再検証。"
docs/source-selection-spike-v0.1.md の §7 に検証結果を記入:

Copy### 検証実施日: 2026-05-28

| id | HTTP | entries | bozo | latest | 判定 | 備考 |
|---|---|---|---|---|---|---|
| deepseek-github-releases | 200 | 1 | 0 | - | ADOPT | - |
| qwen-github-releases | 200 | 0 | 0 | - | ADOPT (監視) | リリース未発行、enabled維持 |
| moonshot-kimi-github | 200 | 0 | 0 | - | ADOPT (監視) | リリース未発行、enabled維持 |
| zhipu-glm-github | 200 | 0 | 0 | - | ADOPT (監視) | リリース未発行、enabled維持 |
| xiaomi-mimo-github | 200 | 0 | 0 | - | ADOPT (監視) | リリース未発行、enabled維持 |
| qbitai-feed | 200* | 10 | 0 | - | ADOPT | curl 403 だが feedparser で取得可能 |
| jiqizhixin-rss | 302 | 0 | 1 | - | DEFER | data-service へリダイレクト、enabled=false |
| 36kr-newsflash | 200 | 20 | 0 | - | ADOPT | - |
| huxiu-rss | 200 | 0 | 1 | - | DEFER | フィード構造エラー、enabled=false に変更 |
| juejin-ai-category | 200 | 20 | 0 | - | ADOPT | RSSHub経由 |
| juejin-trending-ai-weekly | 200 | 20 | 0 | - | ADOPT | RSSHub経由 |

採用確定: 5本(ADOPT) + 4本(ADOPT 監視)= 9本
差し替え発生: 0本(huxiu と jiqizhixin は disabled で残置、Sprint 1A 完了後に差し替え判断)
Sprint 1A 着手: 可能
確認したいこと
(1) Sprint 1A 着手の判断: 上記の「現状のまま Ticket #1 に進む」案で良いか、それとも huxiu の差し替えだけ先にやってから着手したいか。

(2) config/sources.yaml の huxiu 修正: enabled: false に落とす案で良いか。

(3) Ticket #1 の進め方: 次のターンで以下を一気に出します。準備して良いか。

pyproject.toml(uv + Python 3.11+、依存: feedparser, sqlalchemy, pydantic, pyyaml, httpx, python-dotenv, typer)
src/karyu_tech_news/__main__.py(CLI スケルトン、collect init-db post-summary のサブコマンド枠)
src/karyu_tech_news/__init__.py
.env.example(DISCORD_WEBHOOK_URL, RSSHUB_BASE_URL のプレースホルダ)
.gitignore(.env, __pycache__, *.db, .venv, data/episodes/ など)
docker-compose.yml の修正(必要なら、現状版でも OK)
これに加えて、Ticket #2 のソース YAML スキーマ(Pydantic モデル)も一緒に書いておくと、Ticket #3 のフェッチャー実装で型が使えて滑らかになります。

A/B/C に答えてもらえれば、次のターンで Ticket #1 の全コードを出します。

進め方は 現状のまま Ticket #1 に進む で良いです。huxiu の差し替えを先にやる必要はありません。

理由は明確で、Sprint 1A の目的は「最強ソース網の完成」ではなく「収集・保存・health・fail-open の実装検証」だからです。現時点で ADOPT 5本 + EMPTY監視4本があり、RSSHubも正常稼働しています。これだけで基盤検証には十分です。ここで代替ソース探しに戻ると、またソース調査で足が止まります。

回答

(1) Sprint 1A 着手判断

Ticket #1 に進んでください。

huxiu の代替、SegmentFault追加、LatePost追加は Sprint 1A 観察期間中またはSprint 1A完了後で十分です。

現時点の採用状態はこう扱います。

* ADOPT: 通常収集対象
* ADOPT (監視): enabled=true のまま。ただし entries=0 は失敗ではなく「正常空振り」
* DEFER: enabled=false。configには残す

この状態はむしろ良いです。Sprint 1Aで以下の3パターンを同時に検証できます。

* 正常に記事が取れるソース
* 正常応答だが記事が0件のソース
* config上に存在するが disabled のソース

この3つを最初から扱えるので、実装として強くなります。

(2) huxiu の扱い

enabled: false に落とす案でOKです。

huxiu-rss は削除せず、disabledで残すのが正しいです。

- id: huxiu-rss
  name: 虎嗅
  url: "https://www.huxiu.com/rss/0.xml"
  tier: 2
  category: Tech
  enabled: false
  requires_cookie: false
  notes: "feedparser bozo=1、entries=0。XML破損またはContent-Type不一致の可能性。Sprint 1A後にRSSHub経由または代替ソースで再検証。"

jiqizhixin-rss も同様に enabled: false のままでよいです。

- id: jiqizhixin-rss
  name: 机器之心
  url: "https://www.jiqizhixin.com/rss"
  tier: 2
  category: AI
  enabled: false
  requires_cookie: false
  notes: "302でdata-serviceへリダイレクト。通常RSSとしては利用不可。Sprint 1A後にRSSHub経由または代替ルートを再検証。"

(3) Ticket #1 の進め方

次のターンで Ticket #1 + Ticket #2 の土台まで一気に出してよい です。

つまり、出すべきものはこれです。

pyproject.toml
.env.example
.gitignore
docker-compose.yml
README.md
src/karyu_tech_news/__init__.py
src/karyu_tech_news/__main__.py
src/karyu_tech_news/main.py
src/karyu_tech_news/config.py
config/sources.yaml

ここで config.py まで入れるのが良いです。Ticket #1だけだとCLI枠しかできませんが、Ticket #2のPydanticスキーマを軽く入れておけば、次のfetcher実装が滑らかになります。

ただし、まだDBやfetcherは入れなくていいです。Ticket #1/#2の境界はこう切るのが安全です。

Ticket #1 で作る

* プロジェクト初期化
* CLIスケルトン
* .env 読み込み
* RSSHub docker-compose
* --help が動く
* validate-sources コマンドの枠

Ticket #2 の先行分として作る

* SourceConfig / SourcesFile のPydanticモデル
* config/sources.yaml をロードしてバリデーション
* python -m karyu_tech_news validate-sources が通る

ここまでできると、次のTicket #3で collect を実装する時に、すでに型付きのソース一覧が使えます。

確定版の現ソース状態

今の sources.yaml はこの状態で確定してよいです。

enabled=true:
- deepseek-github-releases
- qwen-github-releases
- moonshot-kimi-github
- zhipu-glm-github
- xiaomi-mimo-github
- qbitai-feed
- 36kr-newsflash
- juejin-ai-category
- juejin-trending-ai-weekly
enabled=false:
- jiqizhixin-rss
- huxiu-rss

有効ソースは9本です。元の「10本」に厳密にこだわらなくていいです。ADOPT実取得が5本、監視空振りが4本あればSprint 1Aには十分です。

もしどうしてもenabled=trueを10本にしたいなら、今は急がず、Ticket #3実装後に SegmentFault か V2EX を追加してください。今やる必要はありません。

次のターンで出すコード方針

次はこう進めるのが最適です。

1. pyproject.toml は uv 前提
2. CLIは typer
3. 設定ロードは pydantic + pyyaml
4. .env は python-dotenv
5. RSSHubは docker-compose.yml
6. DBはまだ作らない
7. validate-sources でYAML検証だけ通す

コマンドの完成イメージはこれです。

uv sync
docker compose up -d rsshub
python -m karyu_tech_news --help
python -m karyu_tech_news validate-sources

この4つが通れば Ticket #1 は完了扱いでいいです。

結論。huxiuをenabled=falseにして、ソース差し替えは後回し。次はTicket #1 + sources schemaまで実装に進む。

とのことです
了解です。Sprint 1A 着手、Ticket #1 + sources schema まで一気に実装します。

「現状のソース状態(ADOPT/ADOPT監視/DEFER の3パターン)をむしろ良いと捉える」という観点は、私の発想を1段引き上げてくれました。最初から多様な状態を持つ config で開発すると、fetcher 実装時の edge case を後から追加で考えなくて済みます。

それでは Ticket #1 + sources schema の全コードです。

Ticket #1 + sources schema 実装
pyproject.toml
Copy[project]
name = "karyu-tech-news"
version = "0.1.0"
description = "華流テック通信 by HAL - 中華圏特化 AI ポッドキャストの収集・台本生成・配信パイプライン"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
    { name = "karyu-tech-news maintainers" },
]
dependencies = [
    "typer>=0.12.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "feedparser>=6.0.11",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
    "types-PyYAML>=6.0.12",
]

[project.scripts]
karyu = "karyu_tech_news.__main__:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/karyu_tech_news"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
Copy
.env.example
Copy# 華流テック通信 by HAL - 環境変数サンプル
# このファイルをコピーして .env を作成し、実際の値を埋めること
# cp .env.example .env

# ===== Discord =====
# 収集サマリーやエラー通知を投稿する Discord Webhook URL
# 取得方法: Discord サーバー設定 > 連携サービス > Webhook を作成
DISCORD_WEBHOOK_URL=

# エラー通知用の別 Webhook (任意、未指定なら DISCORD_WEBHOOK_URL を使用)
DISCORD_ERROR_WEBHOOK_URL=

# ===== RSSHub =====
# RSSHub のベース URL (docker-compose で起動する場合は localhost:1200)
RSSHUB_BASE_URL=http://localhost:1200

# ===== LLM (Sprint 1B 以降で使用) =====
# DEEPSEEK_API_KEY=
# MIMO_API_KEY=

# ===== ログレベル =====
# DEBUG / INFO / WARNING / ERROR
LOG_LEVEL=INFO
.gitignore
Copy# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.venv/
venv/
env/
ENV/

# uv
.uv-cache/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.mypy_cache/
.ruff_cache/

# Project-specific
data/
!data/.gitkeep
spike_curl_result.txt
spike_feedparser_result.txt
*.db
*.db-journal
logs/
docker-compose.yml
Copyservices:
  rsshub:
    image: diygod/rsshub:latest
    container_name: karyu-rsshub
    ports:
      - "1200:1200"
    environment:
      NODE_ENV: production
      CACHE_TYPE: memory
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:1200"]
      interval: 30s
      timeout: 5s
      retries: 3
README.md
Copy# karyu-tech-news

華流テック通信 by HAL の収集・台本生成・配信パイプライン。

## Current phase

**Sprint 1A**: RSS/RSSHub source collection, SQLite state, source health, Discord summary.

## Quick start

```bash
# 1. 依存インストール
uv sync

# 2. .env 作成
cp .env.example .env
# DISCORD_WEBHOOK_URL を埋める

# 3. RSSHub 起動 (掘金など RSSHub 経由ソース用)
docker compose up -d rsshub

# 4. ソース定義の検証
uv run python -m karyu_tech_news validate-sources

# 5. ヘルプ確認
uv run python -m karyu_tech_news --help
Documents
docs/requirements-v1.0.md - 要件定義書 v1.0
docs/source-selection-spike-v0.1.md - ソース選定 Spike
Sprint progress
 Sprint 1A Ticket #1: プロジェクト初期化、CLI スケルトン
 Sprint 1A Ticket #2 (先行): ソース YAML スキーマ、validate-sources
 Sprint 1A Ticket #3: RSS/RSSHub 取得モジュール
 Sprint 1A Ticket #4: SQLite スキーマ
 Sprint 1A Ticket #5: seen 管理と dedupe
 Sprint 1A Ticket #6: source health 管理
 Sprint 1A Ticket #7: fail-open 統合テスト
 Sprint 1A Ticket #8: 3日連続観察
 Sprint 1A Ticket #9: Discord Webhook で収集サマリー
License
MIT

Copy
---

## `src/karyu_tech_news/__init__.py`

```python
"""華流テック通信 by HAL - パイプライン本体."""

__version__ = "0.1.0"
src/karyu_tech_news/__main__.py
Copy"""CLI エントリポイント.

使い方:
    python -m karyu_tech_news --help
    python -m karyu_tech_news validate-sources
"""
from karyu_tech_news.main import app

if __name__ == "__main__":
    app()
src/karyu_tech_news/config.py
Copy"""ソース定義 YAML のスキーマと環境変数ロード.

Sprint 1A の Ticket #2 先行実装。
config/sources.yaml をロードし、Pydantic でバリデーションする。
"""
from __future__ import annotations

import os
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Annotated

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceTier(IntEnum):
    """ソースの信頼性階層.

    - 1: 公式 (ラボ、大学、企業、政府公式)、単独採用可
    - 2: 準公式 (認証アカウント、高信頼ニュースサイト)、単独採用可
    - 3: コミュニティ (掘金、知乎、bilibili UP 主、SegmentFault)、独立2ソース要
    - 4: 噂 (匿名、未認証、リーク系)、独立2ソース必須かつ「噂」明示
    """

    OFFICIAL = 1
    SEMI_OFFICIAL = 2
    COMMUNITY = 3
    RUMOR = 4


class SourceCategory(StrEnum):
    """ソースの主カテゴリ."""

    AI = "AI"
    TECH = "Tech"
    GAME = "Game"
    SUBCULTURE = "Subculture"
    OSS = "OSS"
    ANIME = "Anime"


class SourceConfig(BaseModel):
    """個別ソースの定義."""

    id: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*$")]
    name: Annotated[str, Field(min_length=1, max_length=128)]
    url: Annotated[str, Field(min_length=1)]
    tier: SourceTier
    category: SourceCategory
    enabled: bool = True
    requires_cookie: bool = False
    notes: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """URL が http(s) で始まることだけ確認.

        feedparser に渡るので厳密な URL バリデーションは不要。
        localhost も許容する。
        """
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {v!r}")
        return v


class SourcesFile(BaseModel):
    """sources.yaml のトップレベルスキーマ."""

    sources: list[SourceConfig]

    @field_validator("sources")
    @classmethod
    def validate_unique_ids(cls, v: list[SourceConfig]) -> list[SourceConfig]:
        """id の重複を禁止."""
        seen: set[str] = set()
        for source in v:
            if source.id in seen:
                raise ValueError(f"Duplicate source id: {source.id!r}")
            seen.add(source.id)
        return v

    def enabled_sources(self) -> list[SourceConfig]:
        """enabled=true のソースのみを返す."""
        return [s for s in self.sources if s.enabled]

    def by_tier(self, tier: SourceTier) -> list[SourceConfig]:
        """指定 Tier のソースのみを返す (enabled/disabled 問わず)."""
        return [s for s in self.sources if s.tier == tier]


class Settings(BaseModel):
    """環境変数ベースの設定."""

    discord_webhook_url: str = ""
    discord_error_webhook_url: str = ""
    rsshub_base_url: str = "http://localhost:1200"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        """環境変数から設定をロード."""
        return cls(
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            discord_error_webhook_url=os.getenv("DISCORD_ERROR_WEBHOOK_URL", ""),
            rsshub_base_url=os.getenv("RSSHUB_BASE_URL", "http://localhost:1200"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def load_sources(path: Path) -> SourcesFile:
    """sources.yaml をロードして Pydantic でバリデーションする.

    Raises:
        FileNotFoundError: ファイルが存在しない
        yaml.YAMLError: YAML パースエラー
        pydantic.ValidationError: スキーマバリデーションエラー
    """
    if not path.exists():
        raise FileNotFoundError(f"Sources file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SourcesFile.model_validate(raw)


def load_settings(env_file: Path | None = None) -> Settings:
    """環境変数をロードして Settings を返す.

    .env ファイルが存在すれば読み込み、その後 os.environ から構築する。
    """
    if env_file is None:
        env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    return Settings.from_env()


# プロジェクトルートを基準とした既定パス
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SOURCES_PATH = PROJECT_ROOT / "config" / "sources.yaml"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
Copy
src/karyu_tech_news/main.py
Copy"""CLI 本体. typer ベース.

Sprint 1A の Ticket #1 + Ticket #2 先行分。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from pydantic import ValidationError

from karyu_tech_news import __version__
from karyu_tech_news.config import (
    DEFAULT_ENV_PATH,
    DEFAULT_SOURCES_PATH,
    SourceTier,
    load_settings,
    load_sources,
)

app = typer.Typer(
    name="karyu",
    help="華流テック通信 by HAL のパイプライン CLI",
    no_args_is_help=True,
    add_completion=False,
)


def setup_logging(level: str = "INFO") -> None:
    """ロギング初期化."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@app.callback()
def main_callback(
    ctx: typer.Context,
    env_file: Path = typer.Option(
        DEFAULT_ENV_PATH,
        "--env-file",
        help=".env ファイルのパス",
        show_default=True,
    ),
) -> None:
    """共通初期化処理: .env ロードとロギング設定."""
    settings = load_settings(env_file=env_file)
    setup_logging(settings.log_level)
    ctx.obj = settings


@app.command()
def version() -> None:
    """バージョンを表示."""
    typer.echo(f"karyu-tech-news {__version__}")


@app.command("validate-sources")
def validate_sources(
    sources_file: Path = typer.Option(
        DEFAULT_SOURCES_PATH,
        "--sources",
        "-s",
        help="sources.yaml のパス",
        show_default=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="各ソースの詳細を表示",
    ),
) -> None:
    """config/sources.yaml をロードしてスキーマ検証する.

    Sprint 1A Ticket #2 先行実装。
    エラーがあれば終了コード 1、なければ 0。
    """
    try:
        sources_data = load_sources(sources_file)
    except FileNotFoundError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except ValidationError as exc:
        typer.secho("ERROR: Validation failed", fg=typer.colors.RED, err=True)
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.secho(f"ERROR: {type(exc).__name__}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    enabled = sources_data.enabled_sources()
    disabled = [s for s in sources_data.sources if not s.enabled]

    # サマリー出力
    typer.secho(
        f"OK: {len(sources_data.sources)} sources loaded "
        f"({len(enabled)} enabled, {len(disabled)} disabled)",
        fg=typer.colors.GREEN,
    )

    # Tier 別集計
    typer.echo("\nTier breakdown (enabled only):")
    for tier in SourceTier:
        tier_sources = [s for s in enabled if s.tier == tier]
        typer.echo(f"  Tier{tier.value} ({tier.name:<14}): {len(tier_sources)}")

    # Category 別集計
    typer.echo("\nCategory breakdown (enabled only):")
    categories: dict[str, int] = {}
    for s in enabled:
        categories[s.category.value] = categories.get(s.category.value, 0) + 1
    for cat, count in sorted(categories.items()):
        typer.echo(f"  {cat:<12}: {count}")

    # 詳細出力
    if verbose:
        typer.echo("\nAll sources:")
        for s in sources_data.sources:
            status = "ENABLED " if s.enabled else "disabled"
            cookie = " [cookie]" if s.requires_cookie else ""
            typer.echo(
                f"  [{status}] T{s.tier.value} {s.category.value:<10} {s.id:<32}{cookie}"
            )
            if s.notes:
                typer.echo(f"            notes: {s.notes}")

    # Disabled ソースの警告 (失敗ではない)
    if disabled:
        typer.echo("")
        typer.secho(
            f"Note: {len(disabled)} source(s) are disabled (kept in config for future re-enabling):",
            fg=typer.colors.YELLOW,
        )
        for s in disabled:
            typer.echo(f"  - {s.id}: {s.notes or '(no notes)'}")


@app.command()
def info(ctx: typer.Context) -> None:
    """環境設定の確認."""
    settings = ctx.obj
    typer.echo(f"karyu-tech-news {__version__}")
    typer.echo(f"Sprint phase: 1A (Ticket #1 + #2 schema)")
    typer.echo("")
    typer.echo("Settings:")
    typer.echo(f"  RSSHUB_BASE_URL:           {settings.rsshub_base_url}")
    typer.echo(
        f"  DISCORD_WEBHOOK_URL:       "
        f"{'(set)' if settings.discord_webhook_url else '(not set)'}"
    )
    typer.echo(
        f"  DISCORD_ERROR_WEBHOOK_URL: "
        f"{'(set)' if settings.discord_error_webhook_url else '(not set)'}"
    )
    typer.echo(f"  LOG_LEVEL:                 {settings.log_level}")


if __name__ == "__main__":
    app()
Copy
config/sources.yaml (更新版)
Copy# 華流テック通信 by HAL - ソース定義
# Source Selection Spike v0.1 準拠
# 検証実施日: 2026-05-28

sources:
  # ===== Tier1 公式 (5本): 単独採用可 =====
  - id: deepseek-github-releases
    name: DeepSeek GitHub Releases
    url: "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "DeepSeek公式GitHubリリース。検証: ADOPT (entries=1)。"

  - id: qwen-github-releases
    name: Qwen GitHub Releases
    url: "https://github.com/QwenLM/Qwen3/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Alibaba Qwen公式リリース。検証: ADOPT監視 (entries=0、正常空振り)。新リリース発生時に拾う。"

  - id: moonshot-kimi-github
    name: Moonshot Kimi GitHub Releases
    url: "https://github.com/MoonshotAI/Kimi-K2/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Moonshot/Kimi公式リポジトリ。検証: ADOPT監視 (entries=0、正常空振り)。"

  - id: zhipu-glm-github
    name: Zhipu / GLM GitHub Releases
    url: "https://github.com/THUDM/GLM-4/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "GLM系公式/清華大学発リリース。検証: ADOPT監視 (entries=0、正常空振り)。"

  - id: xiaomi-mimo-github
    name: Xiaomi MiMo GitHub Releases
    url: "https://github.com/XiaomiMiMo/MiMo/releases.atom"
    tier: 1
    category: AI
    enabled: true
    requires_cookie: false
    notes: "Xiaomi MiMo公式。番組で使うLLMの本家。検証: ADOPT監視 (entries=0、正常空振り)。"

  # ===== Tier2 ニュース (現状2本有効 + 保留1本): 単独採用可 =====
  - id: qbitai-feed
    name: 量子位
    url: "https://www.qbitai.com/feed"
    tier: 2
    category: AI
    enabled: true
    requires_cookie: false
    notes: "AIニュース中心。検証: ADOPT (entries=10)。curl 403 だが feedparser で取得可能。"

  - id: jiqizhixin-rss
    name: 机器之心
    url: "https://www.jiqizhixin.com/rss"
    tier: 2
    category: AI
    enabled: false
    requires_cookie: false
    notes: "302でdata-serviceへリダイレクト。通常RSSとしては利用不可。Sprint 1A後にRSSHub経由または代替ルートを再検証。"

  - id: 36kr-newsflash
    name: 36Kr Newsflash
    url: "https://36kr.com/feed-newsflash"
    tier: 2
    category: Tech
    enabled: true
    requires_cookie: false
    notes: "AI/テック/スタートアップの速報。検証: ADOPT (entries=20)。"

  - id: huxiu-rss
    name: 虎嗅
    url: "https://www.huxiu.com/rss/0.xml"
    tier: 2
    category: Tech
    enabled: false
    requires_cookie: false
    notes: "feedparser bozo=1、entries=0。XML破損またはContent-Type不一致の可能性。Sprint 1A後にRSSHub経由または代替ソースで再検証。"

  # ===== Tier3 コミュニティ (2本): 独立2ソース確認必須 =====
  - id: juejin-ai-category
    name: 掘金 AI Category
    url: "http://localhost:1200/juejin/category/ai"
    tier: 3
    category: AI
    enabled: true
    requires_cookie: false
    notes: "RSSHub経由。中国エンジニアコミュニティ。検証: ADOPT (entries=20)。Tier3なので2ソース確認対象。"

  - id: juejin-trending-ai-weekly
    name: 掘金 AI Weekly Trending
    url: "http://localhost:1200/juejin/trending/ai/weekly"
    tier: 3
    category: AI
    enabled: true
    requires_cookie: false
    notes: "RSSHub経由。掘金の週次人気AI記事。検証: ADOPT (entries=20)。"
Copy
Ticket #1 完了基準の確認
これを保存したら、以下の4つが全部通れば Ticket #1 + sources schema は完了です。

Copy# 1. 依存インストール
uv sync

# 2. RSSHub 起動
docker compose up -d rsshub
curl -I http://localhost:1200
# → HTTP/1.1 200 が返ること

# 3. --help が動く
uv run python -m karyu_tech_news --help
# → サブコマンド一覧 (version, validate-sources, info) が表示

# 4. validate-sources が通る
uv run python -m karyu_tech_news validate-sources
# → OK: 11 sources loaded (9 enabled, 2 disabled) が表示

# おまけ: 詳細表示
uv run python -m karyu_tech_news validate-sources --verbose

# おまけ: 環境設定確認
uv run python -m karyu_tech_news info
補足説明
いくつかの実装判断について:

SourceTier を IntEnum、SourceCategory を StrEnum にした理由は、YAML から数値で書ける tier と文字列で書ける category の入力フォーマットを自然に保つためです。Pydantic が自動的に変換してくれます。

url のバリデーションを HttpUrl ではなく緩い文字列にした理由は、http://localhost:1200/... のような RSSHub のローカル URL を HttpUrl が(バージョンによっては)弾くケースを避けるためと、最終的には feedparser に渡るだけなので厳密性が不要だからです。

SourcesFile.enabled_sources() と by_tier() をモデルにメソッドとして生やしたのは、Ticket #3 の fetcher から「有効ソースだけ取りたい」「Tier1 だけ取りたい」というアクセスが必ず出るからです。これで fetcher 側のコードが綺麗になります。

Settings を環境変数ベースの単純な BaseModel にした理由は、Pydantic Settings(別パッケージ)を入れると Sprint 1A のスコープ外の機能(設定ファイル階層、型変換の細かい制御など)が増えるからです。Sprint 2 以降で複雑化したらそのとき切り替えます。

typer.Context の ctx.obj で Settings を引き回しているのは、各コマンドが個別に環境変数読まなくて済むようにするためです。info コマンドで実際に使っています。

info コマンドで Discord Webhook URL を (set) / (not set) だけ表示して値を出していないのは、ターミナルでうっかり貼って漏らさないためです。地味だけど大事。

次のターン以降の進め方:

これが手元で動いたら、Ticket #3(fetcher 実装)に進みます。fetcher は SourcesFile.enabled_sources() を受け取って FetchResult のリストを返す形にする想定で、fail-open の中核になります。

何か動かない箇所や、設計判断について議論したい点があれば言ってください。動いたら次のターンで Ticket #3 + Ticket #4 (SQLite スキーマ) まで進めます。