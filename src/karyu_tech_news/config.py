"""ソース定義 YAML のスキーマと環境変数ロード.

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
from pydantic import BaseModel, Field, field_validator


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
        localhost (RSSHub) も許容する。
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
