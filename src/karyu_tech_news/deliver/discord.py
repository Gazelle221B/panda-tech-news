"""Discord Webhook 投稿 (FR-070, FR-071, FR-072)."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from karyu_tech_news.store.schema import CollectRun, Item, Source, SourceHealth

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
DISCORD_CONTENT_LIMIT = 2000  # Discord message content の上限 (コードポイント単位)


def format_summary(session: Session, run: CollectRun) -> str:
    """CollectRun から Discord 投稿用のサマリーテキストを生成 (§14.1)."""
    started_jst = run.started_at.astimezone(JST) if run.started_at.tzinfo else run.started_at.replace(tzinfo=UTC).astimezone(JST)
    finished_jst = run.finished_at.astimezone(JST) if run.finished_at and run.finished_at.tzinfo else (run.finished_at.replace(tzinfo=UTC).astimezone(JST) if run.finished_at else None)

    duration_sec = 0.0
    if finished_jst:
        duration_sec = (finished_jst - started_jst).total_seconds()

    lines = [
        "📰 華流テック通信 - 収集レポート",
        f"日時: {started_jst.strftime('%Y-%m-%d %H:%M')} JST",
        f"実行時間: {duration_sec:.1f}秒",
        f"✅ 成功: {run.successful_sources}/{run.total_sources} ソース",
        f"❌ 失敗: {run.failed_sources}/{run.total_sources} ソース",
    ]

    unhealthy = session.execute(
        select(SourceHealth).where(SourceHealth.consecutive_failures >= 3)
    ).scalars().all()
    if unhealthy:
        lines.append("⚠️ 要対応:")
        for health in unhealthy:
            lines.append(f"- {health.source_id}: consecutive_failures={health.consecutive_failures}")

    lines.append(f"📥 新規アイテム: {run.new_items}件")

    tier_counts: dict[int, int] = defaultdict(int)
    category_counts: dict[str, int] = defaultdict(int)

    query = select(Item.source_id).where(Item.fetched_at >= run.started_at)
    if run.finished_at:
        query = query.where(Item.fetched_at <= run.finished_at)
    items = session.execute(query).scalars().all()

    if items:
        sources = session.execute(
            select(Source.id, Source.tier, Source.category).where(Source.id.in_(items))
        ).all()
        source_map = {s.id: (s.tier, s.category) for s in sources}

        for source_id in items:
            if source_id in source_map:
                tier, category = source_map[source_id]
                tier_counts[tier] += 1
                category_counts[category] += 1

    lines.append("Tier別:")
    tier_names = {1: "Tier1 公式", 2: "Tier2 ニュース", 3: "Tier3 コミュニティ", 4: "Tier4 噂"}
    for tier in sorted(tier_counts.keys()):
        lines.append(f"- {tier_names.get(tier, f'Tier{tier}')}: {tier_counts[tier]}件")

    lines.append("カテゴリ別:")
    for category in sorted(category_counts.keys()):
        lines.append(f"- {category}: {category_counts[category]}")

    return "\n".join(lines)


def post_summary(webhook_url: str, content: str) -> bool:
    """Discord Webhook に投稿. 失敗時はログのみで False を返す (FR-071)."""
    if not webhook_url:
        logger.warning("Discord Webhook URL is not set")
        return False

    try:
        resp = httpx.post(
            webhook_url,
            json={"content": content},
            timeout=10.0,
        )
        resp.raise_for_status()
        logger.info("Discord Webhook posted successfully")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Discord Webhook post failed: %s", exc)
        return False


def _split_for_discord(content: str, limit: int = DISCORD_CONTENT_LIMIT) -> list[str]:
    """content を Discord の上限以下のチャンクに分割する (行境界優先).

    1 行が上限を超える場合のみ行内で強制分割 (コードポイント単位、バイト切り禁止)。
    """
    chunks: list[str] = []
    current = ""
    for line in content.splitlines():
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def post_markdown(webhook_url: str, content: str) -> bool:
    """Markdown 台本を Discord Webhook に投稿する (Sprint 1B T21, 要件 §14.2).

    2000 文字を超える台本は行境界でチャンク分割して順に投稿する。
    失敗時はログのみで False を返す (FR-071 と同じ fail-open)。
    """
    if not webhook_url:
        logger.warning("Discord Webhook URL is not set")
        return False
    if not content.strip():
        logger.warning("Discord post skipped: empty content")
        return False

    ok = True
    for chunk in _split_for_discord(content):
        if not post_summary(webhook_url, chunk):
            ok = False
    return ok
