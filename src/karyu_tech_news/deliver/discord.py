"""Discord Webhook 投稿 (FR-070, FR-071, FR-072)."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from karyu_tech_news.store.schema import CollectRun, Item, Source, SourceHealth

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
DISCORD_CONTENT_LIMIT = 2000  # Discord message content の上限 (コードポイント単位)
DISCORD_FILE_LIMIT_BYTES = 25 * 1024 * 1024  # 無料 Discord の添付上限 25MB (要件 §17.6)
AUDIO_UPLOAD_TIMEOUT = 60.0  # mp3 アップロードは要約投稿より時間がかかる
# @everyone/@here/ロール mention を構造的に無効化する (terra レビュー指摘)。台本文
# (欠落文プレビュー等) を含む content は生成元を信頼できないため、常に付与する。
_NO_MENTIONS: dict[str, list[str]] = {"parse": []}


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
            json={"content": content, "allowed_mentions": _NO_MENTIONS},
            timeout=10.0,
        )
        resp.raise_for_status()
        logger.info("Discord Webhook posted successfully")
        return True
    except httpx.HTTPStatusError as exc:
        # 例外文字列には Webhook URL (トークン込み) が含まれるため、status code のみ記録
        # (要件 §9.5: ログに秘密を出さない。Codex レビュー 2026-06-12 Critical 指摘)
        logger.error("Discord Webhook post failed: HTTP %d", exc.response.status_code)
        return False
    except Exception as exc:  # noqa: BLE001
        # 接続系例外のメッセージにも URL が混ざり得るため、例外型名のみ記録
        logger.error("Discord Webhook post failed: %s", type(exc).__name__)
        return False


def post_audio(webhook_url: str, mp3_path: Path, content: str = "") -> bool:
    """完パケ mp3 を Discord に添付投稿する (T31, FR-071 で fail-open).

    25MB 超は添付できないため、サイズを知らせるメッセージに degrade する
    (外部ストレージ R2/S3 リンクは将来の選択肢, IMPLEMENTATION_PLAN-2 §6)。
    失敗してもログのみで False を返し、produce を止めない。
    """
    if not webhook_url:
        logger.warning("Discord Webhook URL is not set")
        return False
    if not mp3_path.exists():
        logger.error("mp3 が見つかりません: %s", mp3_path.name)
        return False
    size = mp3_path.stat().st_size
    if size > DISCORD_FILE_LIMIT_BYTES:
        mb = size / 1024 / 1024
        logger.warning("mp3 が %s の添付上限超過 (%.1fMB)、メッセージのみ投稿", mp3_path.name, mb)
        notice = f"⚠️ 音声 {mp3_path.name} ({mb:.1f}MB) は 25MB 超のため添付不可。"
        # content 空時に先頭改行が入らないようにする (Copilot 指摘)
        return post_summary(webhook_url, f"{content}\n{notice}" if content else notice)
    try:
        with mp3_path.open("rb") as f:
            # multipart (添付ファイル同梱) では allowed_mentions は plain form field
            # では効かず、payload_json (JSON エンコードした content/allowed_mentions)
            # で渡す必要がある (Discord Webhook API 仕様。terra レビュー指摘)。
            payload_json = (
                json.dumps({"content": content, "allowed_mentions": _NO_MENTIONS})
                if content
                else None
            )
            resp = httpx.post(
                webhook_url,
                data={"payload_json": payload_json} if payload_json else None,
                files={"file": (mp3_path.name, f, "audio/mpeg")},
                timeout=AUDIO_UPLOAD_TIMEOUT,
            )
        resp.raise_for_status()
        logger.info("Discord に mp3 を添付投稿 (%s)", mp3_path.name)
        return True
    except httpx.HTTPStatusError as exc:
        # 例外文字列に Webhook URL (トークン) が含まれるため status code のみ記録
        logger.error("Discord mp3 post failed: HTTP %d", exc.response.status_code)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Discord mp3 post failed: %s", type(exc).__name__)
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
