"""薄い summary の候補を記事本文フェッチで補強する (T61, Issue #61).

RSS の summary がティザー1行しかない薄記事は writer の素材が不足し、
generate_with_fallback がテンプレへ fail-open する事故 (T60, Issue #60) を招く。
prescore 上位の採用候補のうち薄い summary の候補だけ記事本文ページを取得し、
editor 判定・writer 生成の両方が本文の恩恵を受けられるよう summary を差し替える。

DB の items テーブルは一切変更しない。取得した本文は draft 実行中のメモリ内でのみ
使用する (要件 §9.6 法務: 記事本文の転載禁止、要約素材としてのみ利用)。
"""
from __future__ import annotations

import logging

from karyu_tech_news.collect.article import fetch_article_text
from karyu_tech_news.edit.prescore import (
    THIN_SUMMARY_PENALTY,
    ScoredCandidate,
    thin_summary_penalty,
)

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 15
DEFAULT_MAX_FETCH = 5
# fetch_article_text は既に短すぎる抽出を None にしているが、置換に足る本文かの
# 最終ゲートとしてここでも文字数を確認する (article.MIN_EXTRACTED_CHARS と同値)。
MIN_FETCHED_CHARS = 100
# 置換後 summary の最大文字数。バイト単位ではなく Python str (コードポイント) 単位で
# 切る (design-inheritance-tc-newsflow.md §6, AGENTS.md §3.2 のバイト切り詰め禁止)。
ENRICHED_SUMMARY_CHARS = 600


def _is_thin(candidate: ScoredCandidate) -> bool:
    """T60 の thin_summary_penalty が発火する候補か (= summary が薄い)."""
    return thin_summary_penalty(candidate.summary) != 0


def enrich_thin_candidates(
    candidates: list[ScoredCandidate],
    *,
    top_k: int = DEFAULT_TOP_K,
    max_fetch: int = DEFAULT_MAX_FETCH,
) -> list[ScoredCandidate]:
    """prescore 上位 top_k のうち薄い候補を、最大 max_fetch 件まで本文フェッチで補強する.

    元の candidates リストは変更しない。フェッチに成功し十分な本文長が得られた
    候補は、summary を本文冒頭 ENRICHED_SUMMARY_CHARS 文字に置換し、score から
    THIN_SUMMARY_PENALTY 分を引き戻した新しい ScoredCandidate を返す。
    フェッチ対象外 (top_k 外 / summary が薄くない / max_fetch 超過) の候補と、
    フェッチ失敗・本文不足の候補は元のまま返す (fail-open)。
    """
    enriched: list[ScoredCandidate] = []
    fetch_attempts = 0
    for i, candidate in enumerate(candidates):
        if i >= top_k or fetch_attempts >= max_fetch or not _is_thin(candidate):
            enriched.append(candidate)
            continue

        fetch_attempts += 1
        text = fetch_article_text(candidate.link)
        if text is None or len(text.strip()) < MIN_FETCHED_CHARS:
            enriched.append(candidate)
            continue

        new_summary = text.strip()[:ENRICHED_SUMMARY_CHARS]
        logger.info(
            "enriched thin candidate (item_id=%d, fetched_chars=%d)",
            candidate.item_id,
            len(text),
        )
        enriched.append(
            candidate.model_copy(
                update={
                    "summary": new_summary,
                    "prescore": candidate.prescore - THIN_SUMMARY_PENALTY,
                }
            )
        )
    return enriched
