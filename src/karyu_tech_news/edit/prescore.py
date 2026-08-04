"""候補抽出 + ローカル事前スコア.

Sprint 1B Ticket T14。LLM を呼ぶ前にキーワード辞書と Tier ボーナスで
候補を安価に絞る (design-inheritance §4.1 `localDeveloperNewsPriority` の継承)。
キーワードは英語圏 (CVE/deprecated) ではなく中華圏テック向けに再設計 (同 §14)。

スコア設計:
- 各バケツ (緊急/規制/リリース) はヒット回数に関わらず 1 回だけ加点
  (同語連発によるスコア インフレを防ぐ)
- source の Tier ボーナスを加算 (editorial-policy §4: Tier1/2 は単独採用可)
- summary が薄い (40 字未満) 候補は減点する (T60, Issue #60: 薄記事が writer の
  全リトライ失敗を招き T18 テンプレへ fail-open する事故の再発防止)
- 直近 RECENTLY_AIRED_LOOKBACK_DAYS 日以内に selected=True で放送済みの item_id は
  候補プールから除外する (Issue #95: 放送済みネタの再選防止。テンプレ放送だった
  ネタも除外対象に含む)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from karyu_tech_news.store.schema import EpisodeDraft, Item, Source, TopicCandidate

logger = logging.getLogger(__name__)

CANDIDATE_LIMIT = 40  # design-inheritance §5: 候補上限 40
DEFAULT_LOOKBACK_HOURS = 48

# 放送済みネタの再選防止 (Issue #95)。直近この日数以内の draft で selected=True に
# なった item_id は、次回以降の候補プールから除外する。T18 テンプレで放送された
# ネタも含めて除外する (Issue #95 記載の許容 trade-off: テンプレで無内容だった
# ネタでも一度取り上げた話題を翌日以降に再選しない方を優先する)。
RECENTLY_AIRED_LOOKBACK_DAYS = 7

# バケツごとの重み。中国語 (簡体字) を主、日本語/英語を従とする。
# 緊急・セキュリティ・障害 (+30)
_URGENT_KEYWORDS = (
    "漏洞", "安全事故", "数据泄露", "紧急", "封禁", "制裁", "停服", "召回", "瘫痪",
    "脆弱性", "緊急", "CVE", "data breach",
)
# 規制・政策・廃止 (+20)
_REGULATION_KEYWORDS = (
    "监管", "新规", "法规", "政策", "备案", "禁令", "退市", "弃用",
    "規制", "監管", "deprecated", "regulation",
)
# リリース・価格・資本 (+10)
_RELEASE_KEYWORDS = (
    "发布", "开源", "上线", "降价", "涨价", "免费", "融资", "收购", "突破", "升级",
    "リリース", "発布", "open source", "release",
)

_BUCKETS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (30, _URGENT_KEYWORDS),
    (20, _REGULATION_KEYWORDS),
    (10, _RELEASE_KEYWORDS),
)

# Tier ボーナス (editorial-policy §4 の信頼性階層をスコアへ反映)
TIER_BONUS: dict[int, int] = {1: 30, 2: 20, 3: 10, 4: 0}

# 薄い summary への減点 (T60, Issue #60)。
# 実例: 2026-08-01 draft #2 で summary が 13 字しかない item が上位選定され、
# writer が意味のある台本を書けず全リトライ失敗 → T18 テンプレへ fail-open し、
# 「今日は○○のニュースを一つ取り上げます」という無内容な枠がそのまま放送された。
# 値の根拠: バケツ加点は 10/20/30、Tier ボーナスは最大 30 (TIER_BONUS[1])。
# -15 は release バケツ (+10) 単体の加点では相殺しきれない一方、urgent バケツ
# (+30) や Tier1 ボーナスと合わさった強い候補までは単独で足切りしない —
# 「明確に順位を下げるが単独では足切りにしない」を満たす値として選定した。
THIN_SUMMARY_CHARS = 40
THIN_SUMMARY_PENALTY = -15


def thin_summary_penalty(summary: str | None) -> int:
    """薄い summary への減点 (0 または THIN_SUMMARY_PENALTY).

    `summary.strip()` が THIN_SUMMARY_CHARS 未満なら減点する。summary が
    None (RSS 側で欠落) の場合も薄い扱い (空文字と同じ) とする。
    """
    text = (summary or "").strip()
    return THIN_SUMMARY_PENALTY if len(text) < THIN_SUMMARY_CHARS else 0


class ScoredCandidate(BaseModel):
    """事前スコア付きの候補トピック. T15 (LLM 編集判定) への入力."""

    item_id: int
    source_id: str
    title: str
    summary: str
    link: str
    published_at: datetime | None
    fetched_at: datetime
    tier: int
    category: str
    canonical_url_hash: str
    prescore: int


def prescore_text(title: str, summary: str) -> int:
    """キーワード辞書によるローカル事前スコア (LLM 不使用)."""
    text = f"{title}\n{summary}"
    score = 0
    for weight, keywords in _BUCKETS:
        if any(kw in text for kw in keywords):
            score += weight
    return score


def _recently_aired_item_ids(
    session: Session, now: datetime, lookback_days: int
) -> set[int]:
    """直近 lookback_days 日以内の draft で selected=True になった item_id 集合を返す
    (Issue #95: 放送済みネタの再選防止)."""
    since = now - timedelta(days=lookback_days)
    rows = session.execute(
        select(TopicCandidate.item_id)
        .join(EpisodeDraft, TopicCandidate.draft_id == EpisodeDraft.id)
        .where(
            TopicCandidate.selected.is_(True),
            EpisodeDraft.created_at >= since,
        )
    ).all()
    return {int(row[0]) for row in rows}


def extract_candidates(
    session: Session,
    now: datetime,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    limit: int = CANDIDATE_LIMIT,
) -> list[ScoredCandidate]:
    """直近 lookback 時間に取得した items を事前スコア順に最大 limit 件返す.

    フィルタは fetched_at 基準 (収集が止まっていた日の翌朝も拾える)。
    並びは prescore 降順 → fetched_at 降順 (新しい方が先)。
    直近 RECENTLY_AIRED_LOOKBACK_DAYS 日以内に selected=True で放送済みの item_id は
    候補プールから除外する (Issue #95)。
    """
    since = now - timedelta(hours=lookback_hours)
    rows = session.execute(
        select(Item, Source)
        .join(Source, Item.source_id == Source.id)
        .where(Item.fetched_at >= since)
    ).all()

    aired_item_ids = _recently_aired_item_ids(
        session, now, RECENTLY_AIRED_LOOKBACK_DAYS
    )

    candidates = []
    excluded_count = 0
    for item, source in rows:
        if int(item.id) in aired_item_ids:
            excluded_count += 1
            continue
        summary = str(item.summary or "")
        tier = int(source.tier)
        score = (
            prescore_text(str(item.title), summary)
            + TIER_BONUS.get(tier, 0)
            + thin_summary_penalty(summary)
        )
        candidates.append(
            ScoredCandidate(
                item_id=int(item.id),
                source_id=str(item.source_id),
                title=str(item.title),
                summary=summary,
                link=str(item.link),
                published_at=item.published_at,
                fetched_at=item.fetched_at,
                tier=tier,
                category=str(source.category),
                canonical_url_hash=str(item.canonical_url_hash or ""),
                prescore=score,
            )
        )

    if excluded_count:
        logger.info(
            "excluded %d recently aired item(s) from candidate pool "
            "(selected within last %d days)",
            excluded_count,
            RECENTLY_AIRED_LOOKBACK_DAYS,
        )

    # prescore 降順、同点は fetched_at 降順 (安定ソートの 2 段重ね)
    ordered = sorted(candidates, key=lambda c: c.fetched_at, reverse=True)
    ordered = sorted(ordered, key=lambda c: c.prescore, reverse=True)
    return ordered[:limit]
