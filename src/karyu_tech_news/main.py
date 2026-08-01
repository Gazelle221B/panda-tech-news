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

MIN_LUFS_REQUIRED_DURATION_SEC = 5.0
MAX_TTS_SILENCE_SEC = 3.0
MAX_TRUE_PEAK_DBTP = -1.0


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
    profiles_file: Path | None = typer.Option(
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

    import yaml
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

        # 自動読み辞書パス (T56, Issue #52): 既定は data/reading_dict.auto.yaml。
        # config/hal_persona.yaml の tts.auto_reading_dict で上書き可能
        # (produce の reading_dict 読み込みと同じ流儀)。
        auto_reading_dict_path = Path("data/reading_dict.auto.yaml")
        persona_file = Path("config/hal_persona.yaml")
        if persona_file.exists():
            try:
                persona = yaml.safe_load(persona_file.read_text(encoding="utf-8")) or {}
                tts_cfg = persona.get("tts") or {}
                if tts_cfg.get("auto_reading_dict"):
                    auto_reading_dict_path = Path(tts_cfg["auto_reading_dict"])
            except Exception as exc:  # noqa: BLE001
                typer.secho(
                    f"WARN: persona 読み込み失敗 (既定で続行): {type(exc).__name__}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )

        result = run_draft(
            session,
            editor=editor,
            writer=writer,
            roles=roles,
            variant=variant,
            now=now,
            lookback_hours=lookback_hours,
            auto_reading_dict_path=auto_reading_dict_path,
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
            f"dropped={result.dropped_count}, "
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


@app.command()
def produce(
    ctx: typer.Context,
    db_path: Path = typer.Option(
        Path("data/state.db"), "--db-path", "-d", help="SQLite DB パス", show_default=True
    ),
    draft_id: int | None = typer.Option(
        None, "--draft-id", help="対象 episode_draft の id (未指定で最新)"
    ),
    engine_name: str | None = typer.Option(
        None, "--engine", help="TTS エンジン名 (未指定で config primary_engine。ローカルは kokoro)"
    ),
    persona_file: Path = typer.Option(
        Path("config/hal_persona.yaml"), "--persona", help="hal_persona.yaml のパス"
    ),
    show_format_file: Path = typer.Option(
        Path("config/show_format.yaml"),
        "--show-format",
        help="show_format.yaml のパス (sfx トランジション設定)",
    ),
    bgm_dir: Path = typer.Option(
        Path("assets/bgm"), "--bgm-dir", help="BGM 素材ディレクトリ (無ければ素通し)"
    ),
    out_dir: Path = typer.Option(
        Path("data/episodes"), "--out-dir", help="mp3 出力先 (git 管理外)"
    ),
    post: bool = typer.Option(False, "--post", "-p", help="完パケ mp3 を Discord に添付投稿"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="mp3 は生成するが DB 記録・Discord 投稿はしない"
    ),
) -> None:
    """保存済み台本から 1 エピソードの完パケ mp3 を生成 (Sprint 2 T29/T30/T31, T62)。

    structure → トピック境界セグメント分割 (T62) → segment ごとに文単位合成 →
    SFX トランジション挿入 (sfx.enabled 時, T62) → BGM ミックス(素材があれば) →
    -16 LUFS 正規化 + mp3 → audio_versions 記録 → (Discord 添付)。文単位合成は
    segment ごとに最後まで試して欠落数を集計するが、全 segment 合算で欠落文がある
    完パケは produce 境界で fail-fast する。SFX/BGM 無し・Discord 失敗は fail-open。
    ローカルで実音声を出すには `--engine kokoro` を指定する。
    """
    import math
    from datetime import UTC, datetime

    import yaml
    from sqlalchemy.orm import Session

    from karyu_tech_news.deliver.discord import post_audio
    from karyu_tech_news.mix.master import MasteringError, master_to_mp3
    from karyu_tech_news.mix.mixer import find_bgm, mix_bgm
    from karyu_tech_news.mix.transitions import concat_with_transitions
    from karyu_tech_news.script.ruby import load_auto_readings
    from karyu_tech_news.script.structure import Segment, StructuredScript
    from karyu_tech_news.store.repo import (
        create_db_engine,
        get_latest_episode_draft,
        insert_audio_version,
    )
    from karyu_tech_news.store.repo import init_db as init_database
    from karyu_tech_news.store.schema import EpisodeDraft
    from karyu_tech_news.tts.annotate import load_emoji_annotation
    from karyu_tech_news.tts.asr_gate import AsrUnavailableError, WhisperAsrBackend
    from karyu_tech_news.tts.coverage import analyze_coverage, format_coverage_summary
    from karyu_tech_news.tts.engine import TTSError, select_engine
    from karyu_tech_news.tts.normalize import load_reading_dict, split_markdown_topics
    from karyu_tech_news.tts.quality import analyze_wav_signal
    from karyu_tech_news.tts.synthesize import synthesize_script

    settings = ctx.obj

    # config/hal_persona.yaml の `tts` ブロックから primary_engine と reading_dict を読む。
    # (構造は `tts: {primary_engine, reading_dict}`。Codex 指摘で `voice` 誤読を修正)
    eng_name = engine_name
    reading_path = Path("config/reading_dict.yaml")
    auto_reading_path = Path("data/reading_dict.auto.yaml")  # T56, Issue #52
    caption: str | None = None  # VoiceDesign 話法キャプション (T34, 対応エンジンのみ使用)
    asr_gate_enabled = False  # ASR 品質ゲート (T58, Issue #54)。既定 false
    if persona_file.exists():
        try:
            persona = yaml.safe_load(persona_file.read_text(encoding="utf-8")) or {}
            tts_cfg = persona.get("tts") or {}
            eng_name = eng_name or tts_cfg.get("primary_engine")
            if tts_cfg.get("reading_dict"):
                reading_path = Path(tts_cfg["reading_dict"])
            if tts_cfg.get("auto_reading_dict"):
                auto_reading_path = Path(tts_cfg["auto_reading_dict"])
            caption = tts_cfg.get("caption") or None
            asr_gate_enabled = bool(tts_cfg.get("asr_gate", False))
        except Exception as exc:  # noqa: BLE001
            typer.secho(
                f"WARN: persona 読み込み失敗 (既定で続行): {type(exc).__name__}",
                fg=typer.colors.YELLOW,
                err=True,
            )
    eng_name = eng_name or "kokoro"

    db_engine = create_db_engine(db_path)
    init_database(db_engine)
    now = datetime.now(UTC)
    with Session(db_engine) as session:
        draft = (
            session.get(EpisodeDraft, draft_id)
            if draft_id is not None
            else get_latest_episode_draft(session)
        )
        if draft is None:
            typer.secho(
                "ERROR: 対象の episode_draft がありません (先に draft を実行)",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        # ORM 属性 (plain Column) を plain 値へ変換してから下流に渡す (mypy strict 境界)
        draft_pk = int(draft.id)
        variant = str(draft.variant)
        markdown = str(draft.markdown)
        title = str(draft.title)

        # 保存済み markdown をトピック境界 (`## ` 見出し) で複数 segment に構造化する
        # (T62, Issue #65)。JudgedTopic は非永続のため markdown 再パースに頼るが、
        # 見出し無しの旧形式は split_markdown_topics が単一パートで返し従来と等価。
        # 見出し (中国語原文タイトル) と生成メタは発話しない (要件 §9.6・editorial §1/§10、
        # 各パートへ strip_markdown_structure 適用済み)。文分割は synthesize 側。
        segments = [
            Segment(kind="topic", text=text, tone="neutral", bgm="neutral")
            for text in split_markdown_topics(markdown)
        ]
        # 読み辞書の二層マージ (T56, Issue #52): auto は writer LLM のインラインルビ由来の
        # 自動蓄積、manual は人間が確認済みの読み。競合時は manual を常に優先する。
        manual_reading_dict = load_reading_dict(reading_path) if reading_path.exists() else {}
        auto_reading_dict = load_auto_readings(auto_reading_path)
        reading_dict = {**auto_reading_dict, **manual_reading_dict}
        # 読み辞書カバレッジ観測 (T46): TTS 合成前の情報出力のみ。既存の成功条件・
        # fail-fast 挙動には影響しない (失敗しても合成は続行する, 観測は fail-open)。
        try:
            # 全セグメントを結合して観測する (T62 で multi-segment 化済み。先頭だけに
            # 縮退しないよう全 segment のテキストを結合する)。
            coverage_text = "\n".join(seg.text for seg in segments)
            coverage = analyze_coverage(coverage_text, reading_dict)
            typer.echo(format_coverage_summary(coverage))
        except Exception as exc:  # noqa: BLE001
            typer.secho(
                f"WARN: 読み辞書カバレッジ観測に失敗 (続行): {type(exc).__name__}",
                fg=typer.colors.YELLOW,
                err=True,
            )
        # tone 別絵文字スタイル (T27/T33+): エンジンが対応する場合のみ synthesize 内で文単位適用
        emoji_mapping = load_emoji_annotation(persona_file) if persona_file.exists() else None
        try:
            tts = select_engine(eng_name)
        except TTSError as exc:
            typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        # ASR 品質ゲート (T58, Issue #54): 明示的に有効化した場合のみ構築する。
        # WhisperAsrBackend の構築自体は常に安全 (whisper 実体は transcribe 時に遅延
        # ロードするため)。未導入で有効化された場合は synthesize_script 内から
        # AsrUnavailableError が伝播し、ここで fail-fast する (黙って無効化しない)。
        asr_backend = WhisperAsrBackend() if asr_gate_enabled else None

        # segment ごとに synthesize_script を個別呼び出しする (T62, Issue #65)。
        # per-sentence QA・ASR ゲートは各呼び出し内で従来どおり働き、attempted/
        # synthesized/skipped/asr_retried/asr_failed は全 segment 合算で従来の
        # fail-fast 判定を維持する。segment wav は SFX 挿入 (concat_with_transitions)
        # のためリストで保持する。
        segment_wavs: list[bytes] = []
        attempted_sentences = 0
        synthesized_sentences = 0
        skipped_sentences = 0
        asr_retried_sentences = 0
        try:
            for seg in segments:
                seg_script = StructuredScript(variant=variant, generated_at=now, segments=[seg])
                seg_synth = synthesize_script(
                    seg_script,
                    tts,
                    reading_dict,
                    emoji_mapping=emoji_mapping,
                    caption=caption,
                    asr_backend=asr_backend,
                )
                segment_wavs.append(seg_synth.audio)
                attempted_sentences += seg_synth.attempted_sentences
                synthesized_sentences += seg_synth.synthesized_sentences
                skipped_sentences += seg_synth.skipped_sentences
                asr_retried_sentences += seg_synth.asr_retried_sentences
        except AsrUnavailableError as exc:
            typer.secho(
                f"ERROR: ASR ゲートが有効ですが ASR が利用できません: {exc}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1) from exc
        if asr_retried_sentences:
            typer.echo(f"ASR ゲート: {asr_retried_sentences} 文をリトライで復旧")
        if skipped_sentences:
            typer.secho(
                "ERROR: TTS 合成で欠落文があります "
                f"{skipped_sentences}/{attempted_sentences} 文 "
                "。不完全な mp3 の生成を中止します。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        if synthesized_sentences == 0:
            typer.secho(
                "ERROR: TTS 合成成功文が 0 件です。無音 mp3 の生成を中止します。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        # sfx.enabled (show_format.yaml, T62) が true かつ transition ファイルが実在する
        # ときだけ実パスを渡す。既定 (enabled: false) では sfx_path=None のままとなり、
        # concat_with_transitions は SFX なしの単純連結に縮退する (挙動不変)。
        # ファイル欠落・YAML 破損は fail-open で SFX なし続行 (persona 読み込みと同じ流儀)。
        sfx_path: Path | None = None
        if show_format_file.exists():
            try:
                show_format_cfg = (
                    yaml.safe_load(show_format_file.read_text(encoding="utf-8")) or {}
                )
                sfx_cfg = show_format_cfg.get("sfx") or {}
                transition_value = sfx_cfg.get("transition")
                if bool(sfx_cfg.get("enabled", False)) and transition_value:
                    candidate = Path(str(transition_value))
                    sfx_path = candidate if candidate.exists() else None
            except Exception as exc:  # noqa: BLE001
                typer.secho(
                    f"WARN: show_format 読み込み失敗 (SFX なしで続行): {type(exc).__name__}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
        combined_audio = concat_with_transitions(segment_wavs, sfx_path)

        signal = analyze_wav_signal(combined_audio)
        if not signal.has_pcm_signal:
            typer.secho(
                "ERROR: TTS 合成結果が無音です。mp3 配信を中止します。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        if signal.max_silence_sec >= MAX_TTS_SILENCE_SEC - 1e-6:
            typer.secho(
                "ERROR: TTS 音声に "
                f"{MAX_TTS_SILENCE_SEC:.1f} 秒以上の無音区間があります "
                f"(max={signal.max_silence_sec:.1f}s)。mp3 配信を中止します。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        mixed = mix_bgm(combined_audio, bgm_path=find_bgm(bgm_dir))

        stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
        out_path = out_dir / f"episode_{draft_pk}_{stamp}.mp3"
        try:
            result = master_to_mp3(mixed, out_path)
        except MasteringError as exc:
            typer.secho(f"ERROR: マスタリング失敗: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        lufs = result.measured_lufs if math.isfinite(result.measured_lufs) else None
        if lufs is None and result.duration_sec >= MIN_LUFS_REQUIRED_DURATION_SEC:
            out_path.unlink(missing_ok=True)
            typer.secho(
                "ERROR: 実運用尺の音声で LUFS を測定できません。mp3 配信を中止します。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        true_peak = result.true_peak_dbtp if math.isfinite(result.true_peak_dbtp) else None
        if result.duration_sec >= MIN_LUFS_REQUIRED_DURATION_SEC:
            if true_peak is None:
                out_path.unlink(missing_ok=True)
                typer.secho(
                    "ERROR: 実運用尺の音声で true peak を測定できません。mp3 配信を中止します。",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
            if true_peak > MAX_TRUE_PEAK_DBTP:
                out_path.unlink(missing_ok=True)
                typer.secho(
                    "ERROR: mp3 の true peak が高すぎます "
                    f"({true_peak:.1f} dBTP > {MAX_TRUE_PEAK_DBTP:.1f} dBTP)。"
                    "mp3 配信を中止します。",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
        lufs_str = f"{lufs:.1f} LUFS" if lufs is not None else "測定不能"
        tp_str = f"{true_peak:.1f} dBTP" if true_peak is not None else "TP測定不能"
        typer.echo(
            f"完パケ: {out_path} ({result.duration_sec:.1f}s, "
            f"{result.bitrate}/{result.sample_rate}Hz, {lufs_str}, tp={tp_str}, "
            f"max_silence={signal.max_silence_sec:.1f}s) engine={tts.name()}"
        )
        if dry_run:
            typer.echo("[DRY RUN] DB 記録・Discord 投稿はスキップ")
            return

        insert_audio_version(
            session,
            draft_pk,
            engine=tts.name(),
            duration_sec=result.duration_sec,
            lufs=lufs,
            bitrate=result.bitrate,
            sample_rate=result.sample_rate,
            path=str(out_path),
            now=now,
        )
        session.commit()
        if post:
            ok = post_audio(settings.discord_webhook_url, out_path, content=f"🎙️ {title}")
            typer.echo("Discord 投稿: " + ("成功" if ok else "失敗 (fail-open)"))


@app.command()
def publish(
    ctx: typer.Context,
    db_path: Path = typer.Option(
        Path("data/state.db"), "--db-path", "-d", help="SQLite DB パス", show_default=True
    ),
    audio_id: int | None = typer.Option(
        None, "--audio-id", help="対象 audio_version の id (未指定で最新)"
    ),
    logo_file: Path = typer.Option(
        Path("assets/logo.png"), "--logo", help="番組ロゴ画像 (無ければ単色背景に縮退)"
    ),
    out_dir: Path = typer.Option(
        Path("data/videos"), "--out-dir", help="mp4 出力先 (git 管理外)"
    ),
    privacy: str = typer.Option(
        "unlisted",
        "--privacy",
        help="YouTube privacyStatus (unlisted/private。public は approve のみ, FR-120)",
        show_default=True,
    ),
    post: bool = typer.Option(False, "--post", "-p", help="Discord に朝確認メッセージを投稿"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="mp4 生成まで (アップロード・DB 記録・Discord 投稿はしない)"
    ),
) -> None:
    """完パケ mp3 から波形動画を生成し YouTube に限定公開アップロード (Sprint 3 T38-T40)。

    audio_versions の mp3 → showwaves 波形 + ロゴ mp4 (FR-110/111/112) →
    YouTube unlisted (FR-120/122, AI 開示は FR-121 で強制) → video_versions 記録 →
    (Discord 朝確認)。アップロード失敗は fail-fast、Discord 通知失敗は fail-open。
    公開 (public) への切り替えは人間が `karyu approve` で行う。
    """
    from datetime import UTC, datetime, timedelta, timezone

    from sqlalchemy.orm import Session

    from karyu_tech_news.deliver.discord import post_markdown
    from karyu_tech_news.deliver.youtube import (
        YouTubeCredentials,
        YouTubeError,
        refresh_access_token,
        upload_video,
    )
    from karyu_tech_news.store.repo import (
        create_db_engine,
        get_audio_version,
        get_latest_audio_version,
        insert_video_version,
    )
    from karyu_tech_news.store.repo import init_db as init_database
    from karyu_tech_news.store.schema import EpisodeDraft
    from karyu_tech_news.video.render import VideoRenderError, render_video

    settings = ctx.obj

    if privacy not in ("unlisted", "private"):
        typer.secho(
            "ERROR: publish で指定できる privacy は unlisted / private のみです "
            "(public 化は人間確認後の `karyu approve`, IMPLEMENTATION_PLAN-3 §8)",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    db_engine = create_db_engine(db_path)
    init_database(db_engine)
    now = datetime.now(UTC)
    with Session(db_engine) as session:
        audio = (
            get_audio_version(session, audio_id)
            if audio_id is not None
            else get_latest_audio_version(session)
        )
        if audio is None:
            typer.secho(
                "ERROR: 対象の audio_version がありません (先に produce を実行)",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        audio_pk = int(audio.id)
        draft_pk = int(audio.draft_id)
        mp3_path = Path(str(audio.path))
        if not mp3_path.exists():
            typer.secho(
                f"ERROR: mp3 が見つかりません: {mp3_path} (audio_version id={audio_pk})",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        draft = session.get(EpisodeDraft, draft_pk)
        title = str(draft.title) if draft is not None else "華流テック通信"

        stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
        out_path = out_dir / f"episode_{draft_pk}_{stamp}.mp4"
        try:
            video = render_video(mp3_path, out_path, logo_path=logo_file)
        except VideoRenderError as exc:
            typer.secho(f"ERROR: 動画生成失敗: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(
            f"動画生成: {video.path} ({video.width}x{video.height}, "
            f"{video.size_bytes / 1024 / 1024:.1f}MB, "
            f"{'ロゴあり' if video.used_logo else '単色背景 (ロゴ素材なし)'})"
        )

        if dry_run:
            typer.echo("[DRY RUN] YouTube アップロード・DB 記録・Discord 投稿はスキップ")
            return

        jst = timezone(timedelta(hours=9))
        date_str = now.astimezone(jst).strftime("%Y-%m-%d")
        description = f"華流テック通信 — HAL Daily Briefing\n配信日: {date_str} JST"
        try:
            creds = YouTubeCredentials.from_env()
            token = refresh_access_token(creds)
            result = upload_video(
                token,
                Path(video.path),
                title=title,
                description=description,
                privacy=privacy,
            )
        except YouTubeError as exc:
            typer.secho(f"ERROR: YouTube アップロード失敗: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        typer.secho(
            f"YouTube アップロード成功 ({result.privacy_status}): {result.url}",
            fg=typer.colors.GREEN,
        )
        # アップロード (外部副作用) は確定済み。以降の DB 記録失敗で動画を見失わない
        # よう、失敗時は復旧に必要な情報を明示して非 0 終了する (Codex レビュー Medium)。
        try:
            insert_video_version(
                session,
                draft_pk,
                audio_pk,
                path=video.path,
                youtube_video_id=result.video_id,
                youtube_url=result.url,
                privacy_status=result.privacy_status,
                now=now,
            )
            session.commit()
        except Exception as exc:  # noqa: BLE001
            typer.secho(
                "ERROR: video_versions への記録に失敗しました "
                f"({type(exc).__name__})。YouTube には既に {result.privacy_status} で"
                f"アップロード済みです: video_id={result.video_id} / {result.url}\n"
                "再 publish すると重複アップロードになるため、YouTube Studio で当該動画を"
                "確認してから対応してください。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1) from exc

        if post:
            message = "\n".join(
                [
                    "🎬 本日のエピソードを YouTube に限定公開でアップロードしました",
                    f"📺 {result.title}",
                    f"🔗 {result.url}",
                    "",
                    "朝確認フロー (要件 §15.4):",
                    "✅ 公開してよければ: `uv run karyu approve`",
                    "🔁 作り直す: `uv run karyu produce` → `uv run karyu publish`",
                    "❌ 見送る: そのまま (限定公開のまま残ります)",
                ]
            )
            ok = post_markdown(settings.discord_webhook_url, message)
            typer.echo("Discord 朝確認投稿: " + ("成功" if ok else "失敗 (fail-open)"))


@app.command()
def approve(
    ctx: typer.Context,
    db_path: Path = typer.Option(
        Path("data/state.db"), "--db-path", "-d", help="SQLite DB パス", show_default=True
    ),
    video_id: int | None = typer.Option(
        None, "--video-id", help="対象 video_version の id (未指定で最新アップロード済み)"
    ),
    post: bool = typer.Option(False, "--post", "-p", help="公開完了を Discord に通知"),
) -> None:
    """限定公開の動画を public へ切り替える (朝確認フロー ✅, Sprint 3 T40)。

    人間が限定公開 URL を試聴・確認した後にのみ実行する想定 (FR-120 の
    2 週間限定公開運用中は実行しない)。
    """
    from sqlalchemy.orm import Session

    from karyu_tech_news.deliver.discord import post_summary
    from karyu_tech_news.deliver.youtube import (
        YouTubeCredentials,
        YouTubeError,
        refresh_access_token,
        set_privacy_status,
    )
    from karyu_tech_news.store.repo import (
        create_db_engine,
        get_latest_uploaded_video,
        get_video_version,
        update_video_privacy,
    )
    from karyu_tech_news.store.repo import init_db as init_database

    settings = ctx.obj

    db_engine = create_db_engine(db_path)
    init_database(db_engine)
    with Session(db_engine) as session:
        video = (
            get_video_version(session, video_id)
            if video_id is not None
            else get_latest_uploaded_video(session)
        )
        if video is None or video.youtube_video_id is None:
            typer.secho(
                "ERROR: アップロード済みの video_version がありません (先に publish を実行)",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        yt_video_id = str(video.youtube_video_id)
        yt_url = str(video.youtube_url or f"https://www.youtube.com/watch?v={yt_video_id}")
        try:
            creds = YouTubeCredentials.from_env()
            token = refresh_access_token(creds)
            new_status = set_privacy_status(token, yt_video_id, "public")
        except YouTubeError as exc:
            typer.secho(f"ERROR: 公開切り替え失敗: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        # YouTube 側の public 化は確定済み。DB 更新失敗時は乖離を明示する (Codex レビュー Medium)。
        try:
            update_video_privacy(session, video, new_status)
            session.commit()
        except Exception as exc:  # noqa: BLE001
            typer.secho(
                "ERROR: DB の privacy_status 更新に失敗しました "
                f"({type(exc).__name__})。YouTube 側は既に {new_status} です: {yt_url}\n"
                "DB は unlisted のまま乖離しています。再実行すれば整合します "
                "(YouTube への再変更は冪等)。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1) from exc
        typer.secho(f"公開に切り替えました ({new_status}): {yt_url}", fg=typer.colors.GREEN)

        if post:
            ok = post_summary(settings.discord_webhook_url, f"✅ 公開しました: {yt_url}")
            typer.echo("Discord 通知: " + ("成功" if ok else "失敗 (fail-open)"))


@app.command("youtube-auth")
def youtube_auth(
    client_id: str = typer.Option(
        "", "--client-id", envvar="YOUTUBE_CLIENT_ID", help="OAuth クライアント ID"
    ),
    client_secret: str = typer.Option(
        "",
        "--client-secret",
        envvar="YOUTUBE_CLIENT_SECRET",
        help="OAuth クライアントシークレット",
    ),
    port: int = typer.Option(
        8765, "--port", help="loopback リダイレクトの待受ポート", show_default=True
    ),
    manual: bool = typer.Option(
        False,
        "--manual",
        help="ブラウザのリダイレクト先 URL を手貼りする (loopback 待受が使えない環境向け)",
    ),
) -> None:
    """YouTube OAuth の refresh token を取得する (初回のみ人間が実行, Sprint 3 T39)。

    前提: GCP プロジェクトで YouTube Data API v3 を有効化し、OAuth クライアント
    (種類: デスクトップアプリ) を作成しておく (README「YouTube 配信セットアップ」)。
    表示された refresh token は .env の YOUTUBE_REFRESH_TOKEN に貼る (値は git 管理外)。
    """
    from karyu_tech_news.deliver.youtube import (
        YouTubeError,
        build_auth_url,
        exchange_code_for_refresh_token,
        extract_code,
        wait_for_oauth_code,
    )

    if not client_id or not client_secret:
        typer.secho(
            "ERROR: --client-id / --client-secret (または .env の YOUTUBE_CLIENT_ID / "
            "YOUTUBE_CLIENT_SECRET) が必要です",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    redirect_uri = f"http://127.0.0.1:{port}"
    typer.echo("以下の URL をブラウザで開き、YouTube チャンネルの Google アカウントで認可してください:")
    typer.echo("")
    typer.echo(build_auth_url(client_id, redirect_uri))
    typer.echo("")
    try:
        if manual:
            pasted = typer.prompt("リダイレクト先の URL (または code パラメータの値)")
            code = extract_code(pasted)
        else:
            typer.echo(f"認可後のリダイレクトを {redirect_uri} で待っています (最大 300 秒)...")
            code = wait_for_oauth_code(port)
        refresh_token = exchange_code_for_refresh_token(
            client_id, client_secret, code, redirect_uri
        )
    except YouTubeError as exc:
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho("refresh token を取得しました。.env に次の行を追加してください:", fg=typer.colors.GREEN)
    typer.echo(f"YOUTUBE_REFRESH_TOKEN={refresh_token}")


if __name__ == "__main__":
    app()
