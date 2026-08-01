"""CLI draft / evaluate のユニットテスト (Sprint 1B Ticket T21)."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from karyu_tech_news.main import app

runner = CliRunner()


def test_draft_help() -> None:
    result = runner.invoke(app, ["draft", "--help"])
    assert result.exit_code == 0
    assert "--variant" in result.output
    assert "--dry-run" in result.output


def test_draft_dry_run_lists_candidates_without_llm(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    result = runner.invoke(app, ["draft", "--dry-run", "--db-path", str(db)])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert "editor=openai-luna" in result.output  # variant A の既定 (T64: Issue #70 でキャンペーン枠へ切替)


def test_draft_without_api_key_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # styleguide §9: 未設定は setenv("") で固定 (.env 再投入を防ぐ)
    # T64 (Issue #70): variant A の editor は mimo → openai-luna へ変更済み
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    db = tmp_path / "state.db"

    result = runner.invoke(app, ["draft", "--db-path", str(db)])

    assert result.exit_code == 1
    assert "API key env var not set" in result.output


def test_draft_unknown_variant_exits_1(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    result = runner.invoke(app, ["draft", "--variant", "Z", "--db-path", str(db)])
    assert result.exit_code == 1
    assert "Z" in result.output


def test_evaluate_empty_db(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    result = runner.invoke(app, ["evaluate", "--db-path", str(db)])
    assert result.exit_code == 0
    assert "なし" in result.output


def test_setup_logging_suppresses_httpx_url_logs() -> None:
    """httpx INFO ログは Webhook トークン入り URL を出すため WARNING に抑制 (要件 §9.5)."""
    import logging

    from karyu_tech_news.main import setup_logging

    setup_logging("INFO")
    assert logging.getLogger("httpx").level == logging.WARNING
