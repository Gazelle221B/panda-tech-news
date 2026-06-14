"""多様性キャップ付きトピック選定 (決定的コード).

Sprint 1B Ticket T16。判定済みトピックから最終 3-5 本を選ぶ
(design-inheritance §5 `selectDiverseDeveloperNewsCandidates` の継承)。

二重防御:
- 編集ゲート: Tier3-4 は独立 2 ソース未満なら採用しない (editorial-policy §4)。
  LLM にも score を下げるよう指示しているが、ここで決定的に強制する。
- 多様性キャップ: 1 ソース最大 2 本 / 1 カテゴリ最大 2 本。Go 版の 4 パス充填
  (両方厳格 → カテゴリのみ → ソースのみ → 無制約) を踏襲し、候補が偏った日でも
  番組を出すことを優先してキャップを段階的に緩和する。
"""
from __future__ import annotations

from karyu_tech_news.edit.judge import JudgedTopic

SELECT_MAX = 5  # FR-080: 3-5 本。候補が薄い日は少なくなることを許容
SOURCE_CAP = 2
CATEGORY_CAP = 2

# (ソースキャップ適用, カテゴリキャップ適用) の緩和順
_PASSES: tuple[tuple[bool, bool], ...] = (
    (True, True),
    (False, True),
    (True, False),
    (False, False),
)


def _passes_editorial_gate(topic: JudgedTopic) -> bool:
    """Tier1/2 は単独採用可。Tier3/4 は独立 2 ソース必須 (editorial-policy §4)."""
    return topic.candidate.tier <= 2 or topic.corroboration_count >= 2


def select_topics(judged: list[JudgedTopic]) -> list[JudgedTopic]:
    """編集ゲート → スコア順 → 多様性キャップ 4 パスで最大 SELECT_MAX 本を返す.

    入力は変更しない (新リストを返す)。
    """
    eligible = [t for t in judged if _passes_editorial_gate(t)]
    ordered = sorted(
        eligible,
        key=lambda t: (-t.llm_score, -t.candidate.prescore, t.candidate.fetched_at),
    )

    selected: list[JudgedTopic] = []
    selected_ids: set[int] = set()
    selected_hashes: set[str] = set()  # canonical_url_hash 横断の重複記事を排除 (T22 defect)
    source_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for use_source_cap, use_category_cap in _PASSES:
        for topic in ordered:
            if len(selected) >= SELECT_MAX:
                return selected
            item_id = topic.candidate.item_id
            if item_id in selected_ids:
                continue
            # 同一記事が別ソース経由で別 item_id になっても 1 エピソードに 2 回採用しない。
            # 空 hash (link 無し) は裏取り不能なので別記事扱い (judge.py の corroboration と整合)。
            url_hash = topic.candidate.canonical_url_hash
            if url_hash and url_hash in selected_hashes:
                continue
            source_id = topic.candidate.source_id
            category = topic.candidate.category
            if use_source_cap and source_counts.get(source_id, 0) >= SOURCE_CAP:
                continue
            if use_category_cap and category_counts.get(category, 0) >= CATEGORY_CAP:
                continue
            selected.append(topic)
            selected_ids.add(item_id)
            if url_hash:
                selected_hashes.add(url_hash)
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

    return selected
