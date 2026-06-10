"""LLM 編集判定 (score / tone / corroboration).

Sprint 1B Ticket T15。事前スコア済み候補を editor LLM に temp=0 で採点させる
(design-inheritance §4.2 `judgeDeveloperNewsTopics` の継承)。

役割分離 (IMPLEMENTATION_PLAN-1B §8):
- 採点 (score/tone) = LLM。JSON だけを返させる (台本と同時に書かせない)。
- corroboration (独立ソース数) = 決定的コード (canonical_url_hash のクロスソース一致)。
- 並べ替え (アーク配置) は T16 の決定的コードで行い、LLM には並べさせない。
"""
from __future__ import annotations

import json
import logging
from enum import StrEnum
from typing import Annotated, Any, Protocol

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.llm.client import LLMResponse
from karyu_tech_news.store.schema import Item

logger = logging.getLogger(__name__)

JUDGE_TEMPERATURE = 0.0  # 採点は決定性最優先 (design-inheritance §4.2)
PROMPT_TITLE_LIMIT = 180  # styleguide §4 (コードポイント単位)
PROMPT_SUMMARY_LIMIT = 420


class JudgeError(Exception):
    """編集判定の失敗 (JSON 抽出不能・スキーマ不正)."""


class Tone(StrEnum):
    """トピックの tone. アーク配置 (T16) の入力になる."""

    HARD_NEGATIVE = "hard_negative"
    CONSTRUCTIVE = "constructive"
    BRIGHT = "bright"
    NEUTRAL = "neutral"


class TopicJudgment(BaseModel):
    """LLM が返す 1 トピック分の判定."""

    index: Annotated[int, Field(ge=1)]
    score: Annotated[int, Field(ge=0, le=100)]
    tone: Tone


class _JudgmentsPayload(BaseModel):
    """LLM 応答のトップレベル JSON スキーマ."""

    topics: list[TopicJudgment]


class JudgedTopic(BaseModel):
    """候補 + LLM 判定 + 裏取り数. T16 (選定・アーク配置) への入力."""

    candidate: ScoredCandidate
    llm_score: Annotated[int, Field(ge=0, le=100)]
    tone: Tone
    corroboration_count: Annotated[int, Field(ge=1)]


class ChatClient(Protocol):
    """judge が必要とする最小の LLM クライアント面 (LLMClient が満たす)."""

    def chat(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = ...,
        temperature: float | None = ...,
    ) -> LLMResponse: ...


def _truncate(text: str, limit: int) -> str:
    """コードポイント単位の切り詰め (バイト切り禁止, styleguide §4)."""
    return text if len(text) <= limit else text[:limit]


def extract_json_object(text: str) -> dict[str, Any]:
    """LLM 出力から JSON オブジェクトを頑健に取り出す (design-inheritance §10).

    1. まず素直に json.loads
    2. 失敗したら ```json フェンスを剥がし、最外の {...} を切り出して再試行
    """
    try:
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass

    stripped = text.replace("```json", "").replace("```", "")
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise JudgeError("LLM output contains no JSON object")
    try:
        loaded = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise JudgeError(f"LLM output JSON parse failed: {exc}") from exc
    if not isinstance(loaded, dict):
        raise JudgeError("LLM output JSON is not an object")
    return loaded


def parse_judgments(text: str) -> list[TopicJudgment]:
    """LLM 応答テキストを TopicJudgment のリストに検証付きで変換する."""
    data = extract_json_object(text)
    try:
        payload = _JudgmentsPayload.model_validate(data)
    except ValidationError as exc:
        raise JudgeError(f"judgment schema validation failed: {exc}") from exc
    return payload.topics


def build_judge_prompts(
    candidates: list[ScoredCandidate], corroborations: dict[int, int]
) -> tuple[str, str]:
    """編集判定の (system, user) プロンプトを組み立てる.

    system は editorial-policy §1/§4/§10 の要旨。本文転載はせず
    title/summary を切り詰めて渡す (プロンプト用 180/420 文字)。
    """
    system = (
        "あなたはニュース番組「華流テック通信」の編集判定器。"
        "与えられた候補トピックを採点し、JSON だけを返す。説明文・前置きを書かない。\n"
        "採点基準 (score 0-100): 公共性、影響範囲、緊急性、新事実性、"
        "日本の開発者・リスナーへの関連性が高いほど高く。\n"
        "tone はトピックの性質: hard_negative (事故・規制・障害・封禁), "
        "constructive (解決策・技術深掘り), bright (明るい・面白い), neutral (その他)。\n"
        "tier 3-4 (コミュニティ・噂) で corroboration が 2 未満のものは score を大きく下げる。\n"
        "国家・民族への一般化や「中国すごい/日本終わった」型の評価断定を含む判定をしない。\n"
        '出力スキーマ: {"topics":[{"index":1,"score":90,"tone":"hard_negative"}]}\n'
        "index は入力番号に対応させ、全候補分を必ず返す。"
    )
    lines = []
    for i, cand in enumerate(candidates, start=1):
        title = _truncate(cand.title, PROMPT_TITLE_LIMIT)
        summary = _truncate(cand.summary, PROMPT_SUMMARY_LIMIT)
        corroboration = corroborations.get(cand.item_id, 1)
        lines.append(
            f"{i}. [tier={cand.tier} corroboration={corroboration} "
            f"category={cand.category}] {title}\n{summary}"
        )
    user = "候補トピック:\n\n" + "\n\n".join(lines)
    return system, user


def corroboration_counts(
    session: Session, candidates: list[ScoredCandidate]
) -> dict[int, int]:
    """候補ごとの独立ソース数を返す (canonical_url_hash のクロスソース一致).

    hash が空 (link 無し) のものは裏取り照合できないので 1 (自分自身のみ)。
    """
    hashes = {c.canonical_url_hash for c in candidates if c.canonical_url_hash}
    counts_by_hash: dict[str, int] = {}
    if hashes:
        rows = session.execute(
            select(Item.canonical_url_hash, func.count(func.distinct(Item.source_id)))
            .where(Item.canonical_url_hash.in_(hashes))
            .group_by(Item.canonical_url_hash)
        ).all()
        counts_by_hash = {str(h): int(n) for h, n in rows}

    return {
        c.item_id: counts_by_hash.get(c.canonical_url_hash, 1) if c.canonical_url_hash else 1
        for c in candidates
    }


def judge_topics(
    client: ChatClient,
    candidates: list[ScoredCandidate],
    corroborations: dict[int, int],
) -> list[JudgedTopic]:
    """候補を editor LLM に採点させ、候補と判定を突き合わせて返す.

    LLM が返さなかった/未知の index は警告ログを出してスキップする
    (落ちた候補は採用されないだけで、パイプラインは止めない)。
    """
    if not candidates:
        return []

    system, user = build_judge_prompts(candidates, corroborations)
    response = client.chat(system=system, user=user, json_mode=True, temperature=JUDGE_TEMPERATURE)
    judgments = parse_judgments(response.content)

    by_index = {j.index: j for j in judgments}
    judged = []
    for i, cand in enumerate(candidates, start=1):
        judgment = by_index.pop(i, None)
        if judgment is None:
            logger.warning("judge missing index=%d (item_id=%d), dropped", i, cand.item_id)
            continue
        judged.append(
            JudgedTopic(
                candidate=cand,
                llm_score=judgment.score,
                tone=judgment.tone,
                corroboration_count=corroborations.get(cand.item_id, 1),
            )
        )
    for unknown in by_index:
        logger.warning("judge returned unknown index=%d, ignored", unknown)
    return judged
