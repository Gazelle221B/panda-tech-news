"""SQLAlchemy テーブル定義 (DESIGN.md §4)."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
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
