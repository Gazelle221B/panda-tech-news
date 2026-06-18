"""SQLAlchemy テーブル定義 (DESIGN.md §4)."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy ベースクラス."""

    pass


class Source(Base):
    """sources テーブル."""

    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    tier = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    requires_cookie = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("tier BETWEEN 1 AND 4", name="check_tier_range"),
    )

    items = relationship("Item", back_populates="source")
    health = relationship("SourceHealth", back_populates="source", uselist=False)


class Item(Base):
    """items テーブル."""

    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("source_id", "item_key", name="uq_source_item_key"),
        Index("idx_items_canonical_hash", "canonical_url_hash"),
        Index("idx_items_published", text("published_at DESC")),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)
    item_key = Column(String, nullable=False)
    external_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, nullable=False)
    raw_json = Column(Text, nullable=False)
    canonical_url_hash = Column(String, nullable=False)

    source = relationship("Source", back_populates="items")


class SourceHealth(Base):
    """source_health テーブル."""

    __tablename__ = "source_health"

    source_id = Column(String, ForeignKey("sources.id"), primary_key=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    source = relationship("Source", back_populates="health")


class CollectRun(Base):
    """collect_runs テーブル."""

    __tablename__ = "collect_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    total_sources = Column(Integer, nullable=False)
    successful_sources = Column(Integer, nullable=False)
    failed_sources = Column(Integer, nullable=False)
    total_items = Column(Integer, nullable=False)
    new_items = Column(Integer, nullable=False)


class EpisodeDraft(Base):
    """episode_drafts テーブル (Sprint 1B T19, 要件 §12.5).

    1 回の draft 実行 = 1 行。組み立て済み Markdown とメタを保持する。
    """

    __tablename__ = "episode_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False)
    variant = Column(String, nullable=False)  # A/B/C (ADR-0005)
    title = Column(String, nullable=False)
    estimated_minutes = Column(Integer, nullable=False)
    notices_json = Column(Text, nullable=False)  # JSON list[str]
    markdown = Column(Text, nullable=False)


class TopicCandidate(Base):
    """topic_candidates テーブル (Sprint 1B T19).

    draft 実行ごとの判定済み候補。selected/position で採用と配置順を記録し、
    採用率の振り返り (T20 evaluate) に使う。
    """

    __tablename__ = "topic_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_id = Column(Integer, ForeignKey("episode_drafts.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    prescore = Column(Integer, nullable=False)
    llm_score = Column(Integer, nullable=True)
    tone = Column(String, nullable=True)
    source_tier = Column(Integer, nullable=False)
    corroboration_count = Column(Integer, nullable=False)
    selected = Column(Boolean, nullable=False, default=False)
    position = Column(Integer, nullable=True)  # アーク配置順 (selected のみ)


class LLMRun(Base):
    """llm_runs テーブル (Sprint 1B T19).

    A/B/C 検証の評価軸 (コスト=tokens / JSON 安定性 / 失敗率) を 1 呼び出し 1 行で記録。
    """

    __tablename__ = "llm_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_id = Column(Integer, ForeignKey("episode_drafts.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    variant = Column(String, nullable=False)
    role = Column(String, nullable=False)  # editor | writer
    profile_label = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    ok = Column(Boolean, nullable=False)
    error = Column(Text, nullable=True)
    json_stable = Column(Boolean, nullable=True)  # editor のみ (writer は NULL)


class ScriptVersion(Base):
    """script_versions テーブル (Sprint 1B T19).

    トピック単位の台本本文と生成方法 (llm / llm_retry / template = 修正回数の評価軸)。
    """

    __tablename__ = "script_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_id = Column(Integer, ForeignKey("episode_drafts.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    method = Column(String, nullable=False)  # llm | llm_retry | template
    attempts = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)


class AudioVersion(Base):
    """audio_versions テーブル (Sprint 2 T31, IMPLEMENTATION_PLAN-2 §3).

    1 回の `produce` 実行 = 1 行。完パケ mp3 のメタ (エンジン/尺/ラウドネス/パス) を
    記録し、T32 の音声品質観察や再生成の追跡に使う。音声ファイル本体は data/episodes/
    (git 管理外) に置き、ここにはパスのみ保持する。
    """

    __tablename__ = "audio_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_id = Column(Integer, ForeignKey("episode_drafts.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    engine = Column(String, nullable=False)  # tts エンジン名 (mock/kokoro/irodori-tts-v3)
    duration_sec = Column(Float, nullable=False)
    lufs = Column(Float, nullable=True)  # 無音 fail-open 時は測定不能 (-inf) → NULL 記録
    bitrate = Column(String, nullable=False)
    sample_rate = Column(Integer, nullable=False)
    path = Column(String, nullable=False)
