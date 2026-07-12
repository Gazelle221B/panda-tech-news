"""CLI (validate-sources / version / info) のテスト (Sprint 1A Ticket #1)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from karyu_tech_news.main import app

runner = CliRunner()


def test_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("validate-sources", "version", "info"):
        assert cmd in result.output


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "karyu-tech-news" in result.output


def test_validate_sources_real_config() -> None:
    """実 config/sources.yaml が検証を通り、10 enabled / 2 disabled を報告する.

    T51 (Issue #38) で IndieNova (Game, enabled) を追加し 11 本 → 12 本、9 enabled → 10 enabled。
    """
    result = runner.invoke(app, ["validate-sources"])
    assert result.exit_code == 0
    assert "OK: 12 sources loaded (10 enabled, 2 disabled)" in result.output


def test_validate_sources_verbose_shows_disabled() -> None:
    result = runner.invoke(app, ["validate-sources", "--verbose"])
    assert result.exit_code == 0
    assert "jiqizhixin-rss" in result.output
    assert "huxiu-rss" in result.output


def test_validate_sources_missing_file_exits_1(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate-sources", "--sources", str(tmp_path / "nope.yaml")])
    assert result.exit_code == 1


def test_validate_sources_duplicate_id_exits_1(tmp_path: Path) -> None:
    p = tmp_path / "dup.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {"id": "dup", "name": "A", "url": "https://a/feed", "tier": 1, "category": "AI"},
                    {"id": "dup", "name": "B", "url": "https://b/feed", "tier": 1, "category": "AI"},
                ]
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate-sources", "--sources", str(p)])
    assert result.exit_code == 1


def test_validate_sources_bad_url_exits_1(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        yaml.safe_dump(
            {"sources": [{"id": "x", "name": "X", "url": "ftp://x/feed", "tier": 1, "category": "AI"}]}
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate-sources", "--sources", str(p)])
    assert result.exit_code == 1


def test_info_masks_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord/secret-xyz")
    result = runner.invoke(app, ["--env-file", str(tmp_path / "absent.env"), "info"])
    assert result.exit_code == 0
    # 秘密値そのものは出力されない
    assert "secret-xyz" not in result.output
    assert "(set)" in result.output
