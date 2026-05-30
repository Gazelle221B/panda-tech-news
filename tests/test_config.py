"""config モジュールのユニットテスト (Sprint 1A Ticket #2 先行)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from karyu_tech_news.config import (
    DEFAULT_SOURCES_PATH,
    Settings,
    SourceCategory,
    SourceConfig,
    SourcesFile,
    SourceTier,
    load_settings,
    load_sources,
)

# ---------- SourceConfig ----------

def test_source_config_minimal_valid() -> None:
    s = SourceConfig(id="deepseek-x", name="DeepSeek", url="https://example.com/feed", tier=1, category="AI")
    assert s.tier is SourceTier.OFFICIAL
    assert s.category is SourceCategory.AI
    assert s.enabled is True
    assert s.requires_cookie is False


def test_source_config_tier_coerced_from_int() -> None:
    s = SourceConfig(id="x", name="X", url="https://x/feed", tier=3, category="AI")
    assert s.tier is SourceTier.COMMUNITY


def test_source_config_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        SourceConfig(id="x", name="X", url="ftp://x/feed", tier=1, category="AI")


def test_source_config_allows_localhost_rsshub_url() -> None:
    s = SourceConfig(id="x", name="X", url="http://localhost:1200/juejin/category/ai", tier=3, category="AI")
    assert s.url.startswith("http://localhost:1200")


def test_source_config_rejects_bad_id_pattern() -> None:
    with pytest.raises(ValidationError):
        SourceConfig(id="Has_Underscore_AndCaps", name="X", url="https://x/feed", tier=1, category="AI")


def test_source_config_rejects_unknown_tier() -> None:
    with pytest.raises(ValidationError):
        SourceConfig(id="x", name="X", url="https://x/feed", tier=9, category="AI")


def test_source_config_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        SourceConfig(id="x", name="X", url="https://x/feed", tier=1, category="Politics")


# ---------- SourcesFile ----------

def _mk(id_: str, tier: int = 1, enabled: bool = True) -> SourceConfig:
    return SourceConfig(id=id_, name=id_, url="https://x/feed", tier=tier, category="AI", enabled=enabled)


def test_sources_file_unique_ids_enforced() -> None:
    with pytest.raises(ValidationError):
        SourcesFile(sources=[_mk("dup"), _mk("dup")])


def test_enabled_sources_filters() -> None:
    sf = SourcesFile(sources=[_mk("a"), _mk("b", enabled=False), _mk("c")])
    ids = {s.id for s in sf.enabled_sources()}
    assert ids == {"a", "c"}


def test_by_tier_includes_disabled() -> None:
    sf = SourcesFile(sources=[_mk("a", tier=1), _mk("b", tier=2, enabled=False), _mk("c", tier=2)])
    tier2_ids = {s.id for s in sf.by_tier(SourceTier.SEMI_OFFICIAL)}
    assert tier2_ids == {"b", "c"}  # disabled も含む


# ---------- load_sources ----------

def test_load_sources_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_sources(tmp_path / "nope.yaml")


def test_load_sources_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "s.yaml"
    p.write_text(
        yaml.safe_dump(
            {"sources": [{"id": "a", "name": "A", "url": "https://a/feed", "tier": 1, "category": "AI"}]}
        ),
        encoding="utf-8",
    )
    sf = load_sources(p)
    assert len(sf.sources) == 1
    assert sf.sources[0].id == "a"


def test_load_real_project_sources() -> None:
    """実 config/sources.yaml が検証を通り、確定構成 (11本中9有効) であること."""
    sf = load_sources(DEFAULT_SOURCES_PATH)
    assert len(sf.sources) == 11
    assert len(sf.enabled_sources()) == 9
    disabled_ids = {s.id for s in sf.sources if not s.enabled}
    assert disabled_ids == {"jiqizhixin-rss", "huxiu-rss"}
    # Tier 構成: Tier1×5, Tier2×4(2有効), Tier3×2
    assert len(sf.by_tier(SourceTier.OFFICIAL)) == 5
    assert len([s for s in sf.enabled_sources() if s.tier is SourceTier.SEMI_OFFICIAL]) == 2
    assert len(sf.by_tier(SourceTier.COMMUNITY)) == 2


# ---------- Settings ----------

def test_settings_defaults() -> None:
    s = Settings()
    assert s.rsshub_base_url == "http://localhost:1200"
    assert s.log_level == "INFO"
    assert s.discord_webhook_url == ""


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord/webhook")
    monkeypatch.setenv("RSSHUB_BASE_URL", "http://rsshub:1200")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    s = Settings.from_env()
    assert s.discord_webhook_url == "https://discord/webhook"
    assert s.rsshub_base_url == "http://rsshub:1200"
    assert s.log_level == "DEBUG"


def test_load_settings_without_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    s = load_settings(env_file=tmp_path / "absent.env")
    assert s.discord_webhook_url == ""
