"""CRUD 操作."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, event, select
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session

from karyu_tech_news.collect.normalize import FetchResult, RawItem
from karyu_tech_news.config import SourceConfig
from karyu_tech_news.edit.judge import JudgedTopic
from karyu_tech_news.script.fallback import TopicScriptResult
from karyu_tech_news.script.generate import EpisodeScript
from karyu_tech_news.store.schema import (
    AudioVersion,
    CollectRun,
    EpisodeDraft,
    Item,
    LLMRun,
    ScriptVersion,
    Source,
    SourceHealth,
    TopicCandidate,
    VideoVersion,
)


def create_db_engine(db_path: Path) -> Engine:
    """SQLite エンジン作成."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = sa_create_engine(f"sqlite:///{db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: object, connection_record: object) -> None:
        cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    """スキーマ初期化（冪等）."""
    from karyu_tech_news.store.schema import Base

    Base.metadata.create_all(engine)


def upsert_source(session: Session, config: SourceConfig) -> Source:
    """ソース追加/更新."""
    existing = session.get(Source, config.id)
    if existing:
        existing.name = config.name  # type: ignore[assignment]
        existing.url = config.url  # type: ignore[assignment]
        existing.tier = config.tier.value  # type: ignore[assignment]
        existing.category = config.category.value  # type: ignore[assignment]
        existing.enabled = config.enabled  # type: ignore[assignment]
        existing.requires_cookie = config.requires_cookie  # type: ignore[assignment]
        existing.notes = config.notes  # type: ignore[assignment]
        return existing
    source = Source(
        id=config.id,
        name=config.name,
        url=config.url,
        tier=config.tier.value,
        category=config.category.value,
        enabled=config.enabled,
        requires_cookie=config.requires_cookie,
        notes=config.notes,
    )
    session.add(source)
    return source


def insert_items(session: Session, items: list[RawItem]) -> int:
    """アイテム追加（dedupe: UNIQUE制約で自動スキップ）. 新規追加数を返す."""
    new_count = 0
    for item in items:
        if not item.item_key:
            msg = f"item_key is empty for source={item.source_id}"
            raise ValueError(msg)
        existing = session.execute(
            select(Item).where(
                Item.source_id == item.source_id,
                Item.item_key == item.item_key,
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db_item = Item(
            source_id=item.source_id,
            item_key=item.item_key,
            external_id=item.external_id,
            title=item.title,
            link=item.link,
            summary=item.summary,
            published_at=item.published_at,
            fetched_at=item.fetched_at,
            raw_json=json.dumps(item.raw_json, ensure_ascii=False),
            canonical_url_hash=item.canonical_url_hash,
        )
        session.add(db_item)
        new_count += 1
    return new_count


def update_source_health_success(session: Session, source_id: str, now: datetime) -> None:
    """成功時: consecutive_failures=0 にリセット."""
    health = session.get(SourceHealth, source_id)
    if not health:
        health = SourceHealth(source_id=source_id, consecutive_failures=0)
        session.add(health)
    health.last_success_at = now  # type: ignore[assignment]
    health.last_failure_at = None  # type: ignore[assignment]
    health.consecutive_failures = 0  # type: ignore[assignment]
    health.last_error = None  # type: ignore[assignment]


def update_source_health_failure(
    session: Session, source_id: str, error: str, now: datetime
) -> None:
    """失敗時: consecutive_failures += 1, last_error 保存."""
    health = session.get(SourceHealth, source_id)
    if not health:
        health = SourceHealth(source_id=source_id, consecutive_failures=0)
        session.add(health)
    health.last_failure_at = now  # type: ignore[assignment]
    health.consecutive_failures = (health.consecutive_failures or 0) + 1  # type: ignore[assignment]
    health.last_error = error  # type: ignore[assignment]


def create_collect_run(session: Session, total_sources: int) -> CollectRun:
    """収集実行記録作成."""
    run = CollectRun(
        started_at=datetime.now(UTC),
        total_sources=total_sources,
        successful_sources=0,
        failed_sources=0,
        total_items=0,
        new_items=0,
    )
    session.add(run)
    session.flush()
    return run


def finish_collect_run(
    session: Session,
    run: CollectRun,
    results: list[FetchResult],
    new_items: int,
) -> None:
    """収集実行記録完了."""
    if run.total_sources != len(results):
        msg = (
            f"total_sources mismatch: run.total_sources={run.total_sources}, "
            f"len(results)={len(results)}"
        )
        raise ValueError(msg)
    run.finished_at = datetime.now(UTC)  # type: ignore[assignment]
    successful = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    run.successful_sources = len(successful)  # type: ignore[assignment]
    run.failed_sources = len(failed)  # type: ignore[assignment]
    run.total_items = sum(len(r.items) for r in results)  # type: ignore[assignment,misc]
    run.new_items = new_items  # type: ignore[assignment]


# ---------- Sprint 1B (T19) ----------

def create_episode_draft(session: Session, episode: EpisodeScript) -> EpisodeDraft:
    """draft 実行 1 回分を episode_drafts に保存する."""
    draft = EpisodeDraft(
        created_at=episode.generated_at,
        variant=episode.variant,
        title=episode.title,
        estimated_minutes=episode.estimated_minutes,
        notices_json=json.dumps(episode.notices, ensure_ascii=False),
        markdown=episode.markdown,
    )
    session.add(draft)
    session.flush()
    return draft


def insert_topic_candidates(
    session: Session,
    draft_id: int,
    judged: list[JudgedTopic],
    selected_positions: dict[int, int],
) -> None:
    """判定済み候補を topic_candidates に保存する.

    selected_positions: item_id → アーク配置順 (採用分のみ)。未採用は selected=False。
    """
    for topic in judged:
        position = selected_positions.get(topic.candidate.item_id)
        session.add(
            TopicCandidate(
                draft_id=draft_id,
                item_id=topic.candidate.item_id,
                prescore=topic.candidate.prescore,
                llm_score=topic.llm_score,
                tone=topic.tone.value,
                source_tier=topic.candidate.tier,
                corroboration_count=topic.corroboration_count,
                selected=position is not None,
                position=position,
            )
        )


def record_llm_run(
    session: Session,
    *,
    draft_id: int,
    variant: str,
    role: str,
    profile_label: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    ok: bool,
    error: str | None = None,
    json_stable: bool | None = None,
    now: datetime,
) -> None:
    """LLM 呼び出し 1 回分を llm_runs に記録する (A/B/C 評価軸の元データ)."""
    session.add(
        LLMRun(
            draft_id=draft_id,
            created_at=now,
            variant=variant,
            role=role,
            profile_label=profile_label,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            ok=ok,
            error=error,
            json_stable=json_stable,
        )
    )


def insert_script_versions(
    session: Session,
    draft_id: int,
    results: list[tuple[int, TopicScriptResult]],
    *,
    now: datetime,
) -> None:
    """トピック台本 (item_id, 生成結果) を script_versions に保存する."""
    for item_id, result in results:
        session.add(
            ScriptVersion(
                draft_id=draft_id,
                item_id=item_id,
                created_at=now,
                method=result.method,
                attempts=result.attempts,
                body=result.body,
            )
        )


def get_latest_episode_draft(session: Session) -> EpisodeDraft | None:
    """最新の episode_draft を返す (produce の既定対象). 無ければ None."""
    return session.execute(
        select(EpisodeDraft).order_by(EpisodeDraft.id.desc()).limit(1)
    ).scalar_one_or_none()


def insert_audio_version(
    session: Session,
    draft_id: int,
    *,
    engine: str,
    duration_sec: float,
    lufs: float | None,
    bitrate: str,
    sample_rate: int,
    path: str,
    now: datetime,
) -> AudioVersion:
    """完パケ mp3 のメタを audio_versions に1行記録する (T31)."""
    row = AudioVersion(
        draft_id=draft_id,
        created_at=now,
        engine=engine,
        duration_sec=duration_sec,
        lufs=lufs,
        bitrate=bitrate,
        sample_rate=sample_rate,
        path=path,
    )
    session.add(row)
    session.flush()  # id 採番
    return row


def get_latest_audio_version(session: Session) -> AudioVersion | None:
    """最新の audio_version を返す (publish の既定対象). 無ければ None."""
    return session.execute(
        select(AudioVersion).order_by(AudioVersion.id.desc()).limit(1)
    ).scalar_one_or_none()


def get_audio_version(session: Session, audio_version_id: int) -> AudioVersion | None:
    """id 指定で audio_version を返す. 無ければ None."""
    return session.get(AudioVersion, audio_version_id)


def insert_video_version(
    session: Session,
    draft_id: int,
    audio_version_id: int,
    *,
    path: str,
    youtube_video_id: str | None,
    youtube_url: str | None,
    privacy_status: str | None,
    now: datetime,
) -> VideoVersion:
    """波形動画とアップロード結果を video_versions に1行記録する (T40)."""
    row = VideoVersion(
        draft_id=draft_id,
        audio_version_id=audio_version_id,
        created_at=now,
        path=path,
        youtube_video_id=youtube_video_id,
        youtube_url=youtube_url,
        privacy_status=privacy_status,
    )
    session.add(row)
    session.flush()  # id 採番
    return row


def get_latest_uploaded_video(session: Session) -> VideoVersion | None:
    """YouTube にアップロード済みの最新 video_version を返す (approve の既定対象)."""
    return session.execute(
        select(VideoVersion)
        .where(VideoVersion.youtube_video_id.is_not(None))
        .order_by(VideoVersion.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_video_version(session: Session, video_version_id: int) -> VideoVersion | None:
    """id 指定で video_version を返す. 無ければ None."""
    return session.get(VideoVersion, video_version_id)


def update_video_privacy(
    session: Session, video_version: VideoVersion, privacy_status: str
) -> None:
    """video_versions の privacy_status を更新する (approve フロー)."""
    video_version.privacy_status = privacy_status  # type: ignore[assignment]
    session.flush()
