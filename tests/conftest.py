"""テスト共通フィクスチャ."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_forced_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """端末由来のカラー強制を無効化する.

    Warp 等の端末は FORCE_COLOR / CLICOLOR_FORCE を設定するため、typer/rich が
    CliRunner のキャプチャ出力にも ANSI エスケープを混入させ、`"--engine" in output`
    のような文字列アサーションがトークン内の装飾コードで壊れる (Windows 実測)。
    """
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
