"""候補抽出 + ローカル事前スコア.

Sprint 1B Ticket T14。LLM を呼ぶ前にキーワード辞書と Tier ボーナスで
候補を安価に絞る (design-inheritance §4.1 `localDeveloperNewsPriority` の継承)。
キーワードは英語圏 (CVE/deprecated) ではなく中華圏テック向けに再設計 (同 §14)。

スコア設計:
- 各バケツ (緊急/規制/リリース) はヒット回数に関わらず 1 回だけ加点
  (同語連発によるスコア インフレを防ぐ)
- source の Tier ボーナスを加算 (editorial-policy §4: Tier1/2 は単独採用可)
"""
from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from karyu_tech_news.store.schema import Item, Source

CANDIDATE_LIMIT = 40  # design-inheritance §5: 候補上限 40
DEFAULT_LOOKBACK_HOURS = 48

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
    prescore: int


def prescore_text(title: str, summary: str) -> int:
    """キーワード辞書によるローカル事前スコア (LLM 不使用)."""
    text = f"{title}\n{summary}"
    score = 0
    for weight, keywords in _BUCKETS:
        if any(kw in text for kw in keywords):
            score += weight
    return score


def extract_candidates(
    session: Session,
    now: datetime,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    limit: int = CANDIDATE_LIMIT,
) -> list[ScoredCandidate]:
    """直近 lookback 時間に取得した items を事前スコア順に最大 limit 件返す.

    フィルタは fetched_at 基準 (収集が止まっていた日の翌朝も拾える)。
    並びは prescore 降順 → fetched_at 降順 (新しい方が先)。
    """
    since = now - timedelta(hours=lookback_hours)
    rows = session.execute(
        select(Item, Source)
        .join(Source, Item.source_id == Source.id)
        .where(Item.fetched_at >= since)
    ).all()

    candidates = []
    for item, source in rows:
        summary = str(item.summary or "")
        tier = int(source.tier)
        score = prescore_text(str(item.title), summary) + TIER_BONUS.get(tier, 0)
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
                prescore=score,
            )
        )

    # prescore 降順、同点は fetched_at 降順 (安定ソートの 2 段重ね)
    ordered = sorted(candidates, key=lambda c: c.fetched_at, reverse=True)
    ordered = sorted(ordered, key=lambda c: c.prescore, reverse=True)
    return ordered[:limit]
