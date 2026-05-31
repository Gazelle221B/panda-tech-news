"""CLI 本体. typer ベース.

Sprint 1A の Ticket #1 + Ticket #2 先行分。
"""
from __future__ import annotations

import logging
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

    # Tier 別集計 (enabled のみ)
    typer.echo("\nTier breakdown (enabled only):")
    for tier in SourceTier:
        tier_sources = [s for s in enabled if s.tier == tier]
        typer.echo(f"  Tier{tier.value} ({tier.name:<14}): {len(tier_sources)}")

    # Category 別集計 (enabled のみ)
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

    # Disabled ソースの注記 (失敗ではない — fail-open の思想を config にも適用)
    if disabled:
        typer.echo("")
        typer.secho(
            f"Note: {len(disabled)} source(s) are disabled "
            "(kept in config for future re-enabling):",
            fg=typer.colors.YELLOW,
        )
        for s in disabled:
            typer.echo(f"  - {s.id}: {s.notes or '(no notes)'}")


@app.command()
def info(ctx: typer.Context) -> None:
    """環境設定の確認 (秘密情報は set/not set のみ表示)."""
    settings = ctx.obj
    typer.echo(f"karyu-tech-news {__version__}")
    typer.echo("Sprint phase: 1A (Ticket #4 SQLite)")
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


@app.command("init-db")
def init_db(
    db_path: Path = typer.Option(
        Path("data/state.db"),
        "--db-path",
        "-d",
        help="SQLite データベースのパス",
        show_default=True,
    ),
) -> None:
    """SQLite データベースを初期化 (テーブル作成).

    Sprint 1A Ticket #4 実装。
    冪等: 2回実行しても壊れない。
    """
    from karyu_tech_news.store.repo import create_db_engine
    from karyu_tech_news.store.repo import init_db as init_database

    engine = create_db_engine(db_path)
    init_database(engine)
    typer.secho(f"Database initialized: {db_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
