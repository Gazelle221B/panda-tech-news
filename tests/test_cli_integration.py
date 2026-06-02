"""CLI統合テスト (T10)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from karyu_tech_news.collect.normalize import RawItem
from karyu_tech_news.main import app
from karyu_tech_news.store.repo import create_db_engine, init_db

runner = CliRunner()


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    engine = create_db_engine(db_path)
    init_db(engine)
    return db_path


@pytest.fixture
def temp_sources_file(tmp_path: Path) -> Path:
    sources_path = tmp_path / "sources.yaml"
    sources_path.write_text(
        """sources:
  - id: test-source
    name: Test Source
    url: https://example.com/feed.xml
    tier: 1
    category: AI
    enabled: true
  - id: disabled-source
    name: Disabled Source
    url: https://example.com/disabled.xml
    tier: 1
    category: AI
    enabled: false
""",
        encoding="utf-8",
    )
    return sources_path


def _make_raw_item(source_id: str, key: str) -> RawItem:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return RawItem(
        item_key=key,
        external_id=None,
        title=f"Title {key}",
        link=f"https://{source_id}/{key}",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id=source_id,
        canonical_url_hash=f"hash-{source_id}-{key}",
        raw_json={"k": "v"},
    )


def test_collect_help() -> None:
    result = runner.invoke(app, ["collect", "--help"])
    assert result.exit_code == 0
    assert "collect" in result.output
    assert "--post" in result.output
    assert "--dry-run" in result.output


def test_collect_dry_run(temp_sources_file: Path, temp_db: Path) -> None:
    result = runner.invoke(
        app,
        [
            "collect",
            "--sources",
            str(temp_sources_file),
            "--db-path",
            str(temp_db),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output
    assert "test-source" in result.output


def test_collect_dry_run_with_post(temp_sources_file: Path, temp_db: Path) -> None:
    result = runner.invoke(
        app,
        [
            "collect",
            "--sources",
            str(temp_sources_file),
            "--db-path",
            str(temp_db),
            "--dry-run",
            "--post",
        ],
    )
    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output
    assert "Would post to Discord" in result.output


def test_collect_no_enabled_sources(tmp_path: Path, temp_db: Path) -> None:
    sources_path = tmp_path / "empty.yaml"
    sources_path.write_text(
        """sources:
  - id: disabled-source
    name: Disabled
    url: https://example.com/feed.xml
    tier: 1
    category: AI
    enabled: false
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["collect", "--sources", str(sources_path), "--db-path", str(temp_db)],
    )
    assert result.exit_code == 0
    assert "No enabled sources" in result.output


def test_collect_success(temp_sources_file: Path, temp_db: Path) -> None:
    with patch("karyu_tech_news.collect.runner.run_collect") as mock_run:
        mock_run.return_value = MagicMock(
            successful_sources=1,
            total_sources=1,
            new_items=1,
            failed_sources=0,
        )
        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
            ],
        )

    assert result.exit_code == 0
    assert "Collection completed" in result.output
    assert "1/1 sources" in result.output
    assert "1 new items" in result.output


def test_collect_with_post_success(
    temp_sources_file: Path, temp_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/webhook/test")

    mock_run_result = MagicMock(
        successful_sources=1,
        total_sources=1,
        new_items=1,
        failed_sources=0,
    )

    with (
        patch("karyu_tech_news.collect.runner.run_collect") as mock_run,
        patch("karyu_tech_news.deliver.discord.format_summary") as mock_format,
        patch("karyu_tech_news.deliver.discord.post_summary") as mock_post,
    ):
        mock_run.return_value = mock_run_result
        mock_format.return_value = "test summary"
        mock_post.return_value = True

        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
                "--post",
            ],
        )

    assert result.exit_code == 0
    assert "Discord post sent successfully" in result.output
    mock_post.assert_called_once()


def test_collect_with_post_no_webhook_url(
    temp_sources_file: Path, temp_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    mock_run_result = MagicMock(
        successful_sources=1,
        total_sources=1,
        new_items=1,
        failed_sources=0,
    )

    with patch("karyu_tech_news.collect.runner.run_collect") as mock_run:
        mock_run.return_value = mock_run_result
        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
                "--post",
            ],
        )

    assert result.exit_code == 0
    assert "DISCORD_WEBHOOK_URL not set" in result.output


def test_collect_with_post_failure(
    temp_sources_file: Path, temp_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/webhook/test")

    mock_run_result = MagicMock(
        successful_sources=1,
        total_sources=1,
        new_items=1,
        failed_sources=0,
    )

    with (
        patch("karyu_tech_news.collect.runner.run_collect") as mock_run,
        patch("karyu_tech_news.deliver.discord.format_summary") as mock_format,
        patch("karyu_tech_news.deliver.discord.post_summary") as mock_post,
    ):
        mock_run.return_value = mock_run_result
        mock_format.return_value = "test summary"
        mock_post.return_value = False

        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
                "--post",
            ],
        )

    assert result.exit_code == 0
    assert "Discord post failed" in result.output


def test_collect_with_failures(temp_sources_file: Path, temp_db: Path) -> None:
    mock_run_result = MagicMock(
        successful_sources=0,
        total_sources=1,
        new_items=0,
        failed_sources=1,
    )

    with patch("karyu_tech_news.collect.runner.run_collect") as mock_run:
        mock_run.return_value = mock_run_result
        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
            ],
        )

    assert result.exit_code == 0
    assert "Collection completed" in result.output
    assert "0/1 sources" in result.output


def test_collect_with_source_option(temp_sources_file: Path, temp_db: Path) -> None:
    with patch("karyu_tech_news.collect.runner.run_collect") as mock_run:
        mock_run.return_value = MagicMock(
            successful_sources=1,
            total_sources=1,
            new_items=1,
            failed_sources=0,
        )
        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
                "--source",
                "test-source",
            ],
        )

    assert result.exit_code == 0
    assert "Collection completed" in result.output
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert len(call_args[0][1]) == 1
    assert call_args[0][1][0].id == "test-source"


def test_collect_with_invalid_source_option(temp_sources_file: Path, temp_db: Path) -> None:
    result = runner.invoke(
        app,
        [
            "collect",
            "--sources",
            str(temp_sources_file),
            "--db-path",
            str(temp_db),
            "--source",
            "nonexistent-source",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid or disabled source IDs" in result.output
    assert "nonexistent-source" in result.output


def test_collect_with_partial_invalid_sources(temp_sources_file: Path, temp_db: Path) -> None:
    result = runner.invoke(
        app,
        [
            "collect",
            "--sources",
            str(temp_sources_file),
            "--db-path",
            str(temp_db),
            "--source",
            "test-source",
            "--source",
            "nonexistent-source",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid or disabled source IDs" in result.output
    assert "nonexistent-source" in result.output


def test_collect_with_disabled_source(temp_sources_file: Path, temp_db: Path) -> None:
    result = runner.invoke(
        app,
        [
            "collect",
            "--sources",
            str(temp_sources_file),
            "--db-path",
            str(temp_db),
            "--source",
            "disabled-source",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid or disabled source IDs" in result.output
    assert "disabled-source" in result.output


def test_collect_with_multiple_valid_sources(temp_sources_file: Path, temp_db: Path) -> None:
    with patch("karyu_tech_news.collect.runner.run_collect") as mock_run:
        mock_run.return_value = MagicMock(
            successful_sources=1,
            total_sources=1,
            new_items=1,
            failed_sources=0,
        )
        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
                "--source",
                "test-source",
                "--source",
                "test-source",
            ],
        )

    assert result.exit_code == 0
    assert "Collection completed" in result.output


def test_collect_dry_run_no_db_write(temp_sources_file: Path, temp_db: Path) -> None:
    from sqlalchemy import create_engine, text

    result = runner.invoke(
        app,
        [
            "collect",
            "--sources",
            str(temp_sources_file),
            "--db-path",
            str(temp_db),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output

    engine = create_engine(f"sqlite:///{temp_db}")
    with engine.connect() as conn:
        sources_count = conn.execute(text("SELECT COUNT(*) FROM sources")).scalar()
        items_count = conn.execute(text("SELECT COUNT(*) FROM items")).scalar()
        collect_runs_count = conn.execute(text("SELECT COUNT(*) FROM collect_runs")).scalar()

    assert sources_count == 0
    assert items_count == 0
    assert collect_runs_count == 0


def test_collect_updates_db_state(temp_sources_file: Path, temp_db: Path) -> None:
    from datetime import UTC, datetime

    from sqlalchemy import create_engine, text

    from karyu_tech_news.collect.normalize import FetchResult, RawItem

    now = datetime.now(UTC)
    item = RawItem(
        item_key="test-key",
        external_id=None,
        title="Test Title",
        link="https://example.com/test",
        summary=None,
        published_at=now,
        fetched_at=now,
        source_id="test-source",
        canonical_url_hash="hash-test",
        raw_json={"k": "v"},
    )

    mock_fetch_result = FetchResult(
        source_id="test-source",
        ok=True,
        items=[item],
        error=None,
        duration_ms=100,
    )

    with patch("karyu_tech_news.collect.runner.fetch_one") as mock_fetch:
        mock_fetch.return_value = mock_fetch_result

        result = runner.invoke(
            app,
            [
                "collect",
                "--sources",
                str(temp_sources_file),
                "--db-path",
                str(temp_db),
            ],
        )

    assert result.exit_code == 0

    engine = create_engine(f"sqlite:///{temp_db}")
    with engine.connect() as conn:
        sources_count = conn.execute(text("SELECT COUNT(*) FROM sources")).scalar()
        items_count = conn.execute(text("SELECT COUNT(*) FROM items")).scalar()
        collect_runs_count = conn.execute(text("SELECT COUNT(*) FROM collect_runs")).scalar()
        source_health_count = conn.execute(text("SELECT COUNT(*) FROM source_health")).scalar()

    assert sources_count == 1
    assert items_count == 1
    assert collect_runs_count == 1
    assert source_health_count == 1
