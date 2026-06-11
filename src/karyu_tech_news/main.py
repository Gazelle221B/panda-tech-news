"""CLI 本体. typer ベース.

Sprint 1A コマンド: version / info / validate-sources / init-db / collect。
Sprint 1B コマンド: draft / evaluate (T21)。
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
    # httpx の INFO ログはリクエスト URL 全体 (Discord Webhook トークン含む) を
    # 出力するため抑制する (要件 §9.5 / styleguide §7: ログに秘密を出さない)
    logging.getLogger("httpx").setLevel(logging.WARNING)


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
    typer.echo("Sprint phase: 1B implementation (T12-T21 implemented)")
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


@app.command()
def collect(
    ctx: typer.Context,
    sources_file: Path = typer.Option(
        DEFAULT_SOURCES_PATH,
        "--sources",
        "-s",
        help="sources.yaml のパス",
        show_default=True,
    ),
    db_path: Path = typer.Option(
        Path("data/state.db"),
        "--db-path",
        "-d",
        help="SQLite データベースのパス",
        show_default=True,
    ),
    source_ids: list[str] | None = typer.Option(
        None,
        "--source",
        help="収集するソースID (複数指定可能、未指定時は全enabledソース)",
    ),
    post: bool = typer.Option(
        False,
        "--post",
        "-p",
        help="収集後に Discord に投稿",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="実際の収集・投稿をスキップ",
    ),
) -> None:
    """RSS/RSSHub から収集して SQLite に保存.

    Sprint 1A Ticket #9 (T10) 実装。
    fail-open: 1ソースの失敗で全体を止めない。
    """
    from sqlalchemy.orm import Session

    from karyu_tech_news.collect.runner import run_collect
    from karyu_tech_news.deliver.discord import format_summary, post_summary
    from karyu_tech_news.store.repo import (
        create_db_engine,
        upsert_source,
    )
    from karyu_tech_news.store.repo import (
        init_db as init_database,
    )

    settings = ctx.obj

    try:
        sources_data = load_sources(sources_file)
    except Exception as exc:
        typer.secho(f"ERROR: Failed to load sources: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    enabled = sources_data.enabled_sources()
    if not enabled:
        typer.secho("WARNING: No enabled sources found", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    if source_ids:
        enabled_ids = {s.id for s in enabled}
        invalid_ids = [sid for sid in source_ids if sid not in enabled_ids]
        if invalid_ids:
            typer.secho(
                f"ERROR: Invalid or disabled source IDs: {', '.join(invalid_ids)}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        enabled = [s for s in enabled if s.id in source_ids]

    if dry_run:
        typer.echo(f"[DRY RUN] Would collect from {len(enabled)} sources:")
        for s in enabled:
            typer.echo(f"  - {s.id} ({s.name})")
        if post:
            typer.echo("[DRY RUN] Would post to Discord")
        raise typer.Exit(code=0)

    engine = create_db_engine(db_path)
    init_database(engine)

    with Session(engine) as session:
        for source in enabled:
            upsert_source(session, source)
        session.commit()

        run = run_collect(session, enabled, settings.rsshub_base_url)

        typer.echo("")
        typer.secho(
            f"Collection completed: {run.successful_sources}/{run.total_sources} sources, "
            f"{run.new_items} new items",
            fg=typer.colors.GREEN if run.failed_sources == 0 else typer.colors.YELLOW,
        )

        if post:
            if not settings.discord_webhook_url:
                typer.secho(
                    "WARNING: DISCORD_WEBHOOK_URL not set, skipping Discord post",
                    fg=typer.colors.YELLOW,
                )
            else:
                summary = format_summary(session, run)
                if post_summary(settings.discord_webhook_url, summary):
                    typer.secho("Discord post sent successfully", fg=typer.colors.GREEN)
                else:
                    typer.secho(
                        "WARNING: Discord post failed (continuing due to fail-open)",
                        fg=typer.colors.YELLOW,
                    )


@app.command()
def draft(
    ctx: typer.Context,
    db_path: Path = typer.Option(
        Path("data/state.db"),
        "--db-path",
        "-d",
        help="SQLite データベースのパス",
        show_default=True,
    ),
    profiles_file: Path = typer.Option(
        None,
        "--profiles",
        help="llm_profiles.yaml のパス (未指定時は config/llm_profiles.yaml)",
    ),
    variant: str = typer.Option(
        "A",
        "--variant",
        help="A/B/C 検証の構成 (ADR-0005。初期既定は A)",
        show_default=True,
    ),
    lookback_hours: int = typer.Option(
        48,
        "--lookback-hours",
        help="候補に含める収集時刻の遡り時間",
        show_default=True,
    ),
    post: bool = typer.Option(
        False,
        "--post",
        "-p",
        help="生成後に Discord へ台本を投稿",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="LLM を呼ばず候補一覧のみ表示",
    ),
) -> None:
    """SQLite の候補から LLM で 3-5 本を選び Markdown 台本を生成 (Sprint 1B T21).

    fail-open: editor が崩れた日も neutral 判定で番組を出し、
    writer の違反はテンプレ fallback が吸収する。
    """
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from karyu_tech_news.deliver.discord import post_markdown
    from karyu_tech_news.edit.prescore import extract_candidates
    from karyu_tech_news.llm.client import LLMClient, LLMError
    from karyu_tech_news.llm.profile import DEFAULT_LLM_PROFILES_PATH, load_llm_profiles
    from karyu_tech_news.script.runner import run_draft
    from karyu_tech_news.store.repo import create_db_engine
    from karyu_tech_news.store.repo import init_db as init_database

    settings = ctx.obj

    try:
        profiles = load_llm_profiles(profiles_file or DEFAULT_LLM_PROFILES_PATH)
        roles = profiles.resolve_roles(variant)
    except Exception as exc:
        typer.secho(f"ERROR: Failed to load LLM profiles: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    engine = create_db_engine(db_path)
    init_database(engine)
    now = datetime.now(UTC)

    with Session(engine) as session:
        if dry_run:
            candidates = extract_candidates(session, now=now, lookback_hours=lookback_hours)
            typer.echo(
                f"[DRY RUN] 候補 {len(candidates)} 件 / variant {variant} "
                f"(editor={roles.editor.label}, writer={roles.writer.label})"
            )
            for c in candidates[:10]:
                typer.echo(f"  [prescore={c.prescore:>3} T{c.tier} {c.category}] {c.title}")
            raise typer.Exit(code=0)

        try:
            editor = LLMClient(roles.editor)
            writer = LLMClient(roles.writer)
        except LLMError as exc:
            typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
            typer.secho(
                "API キーを .env に設定するか、--dry-run で候補のみ確認してください",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(code=1) from exc

        result = run_draft(
            session,
            editor=editor,
            writer=writer,
            roles=roles,
            variant=variant,
            now=now,
            lookback_hours=lookback_hours,
        )
        if result is None:
            typer.secho(
                "draft を生成できません: 候補がないか、全候補が編集ゲートで不採用 "
                "(先に collect を実行するか --lookback-hours を伸ばす。詳細はログ参照)",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(code=0)

        typer.echo(result.episode.markdown)
        typer.echo("")
        methods = ", ".join(f"{k}={v}" for k, v in sorted(result.method_counts.items()))
        typer.secho(
            f"Draft #{result.draft_id} 生成完了: 候補 {result.candidate_count} → "
            f"採用 {result.selected_count} 本 (生成方法: {methods}, "
            f"editor JSON 安定: {'yes' if result.editor_json_stable else 'no'})",
            fg=typer.colors.GREEN,
        )

        if post:
            if not settings.discord_webhook_url:
                typer.secho(
                    "WARNING: DISCORD_WEBHOOK_URL not set, skipping Discord post",
                    fg=typer.colors.YELLOW,
                )
            elif post_markdown(settings.discord_webhook_url, result.episode.markdown):
                typer.secho("Discord post sent successfully", fg=typer.colors.GREEN)
            else:
                typer.secho(
                    "WARNING: Discord post failed (continuing due to fail-open)",
                    fg=typer.colors.YELLOW,
                )


@app.command()
def evaluate(
    db_path: Path = typer.Option(
        Path("data/state.db"),
        "--db-path",
        "-d",
        help="SQLite データベースのパス",
        show_default=True,
    ),
) -> None:
    """A/B/C 検証の定量サマリーを表示 (Sprint 1B T21, ADR-0005)."""
    from sqlalchemy.orm import Session

    from karyu_tech_news.edit.abtest import evaluate_variants, format_evaluation
    from karyu_tech_news.store.repo import create_db_engine
    from karyu_tech_news.store.repo import init_db as init_database

    engine = create_db_engine(db_path)
    init_database(engine)
    with Session(engine) as session:
        typer.echo(format_evaluation(evaluate_variants(session)))


if __name__ == "__main__":
    app()
