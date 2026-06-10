"""draft パイプラインの統合ランナー.

Sprint 1B Ticket T21。候補抽出 → 編集判定 → 選定/アーク配置 → 台本生成 →
永続化を 1 回の draft 実行として束ねる (collect/runner.py の 1B 版)。

fail-open:
- editor の JSON が崩れた日も neutral 判定にフォールバックして番組を出す
  (json_stable=False を llm_runs に記録し、A/B/C 評価に反映)
- writer の違反は generate_with_fallback (T18) がテンプレで吸収する
"""
from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from karyu_tech_news.edit.arc import arrange_arc
from karyu_tech_news.edit.judge import (
    ChatClient,
    JudgedTopic,
    JudgeError,
    Tone,
    corroboration_counts,
    judge_topics,
)
from karyu_tech_news.edit.prescore import (
    DEFAULT_LOOKBACK_HOURS,
    ScoredCandidate,
    extract_candidates,
)
from karyu_tech_news.edit.select import select_topics
from karyu_tech_news.llm.client import LLMError, LLMResponse
from karyu_tech_news.llm.profile import ResolvedRoles
from karyu_tech_news.script.fallback import generate_with_fallback
from karyu_tech_news.script.generate import EpisodeScript, assemble_episode
from karyu_tech_news.store.repo import (
    create_episode_draft,
    insert_script_versions,
    insert_topic_candidates,
    record_llm_run,
)

logger = logging.getLogger(__name__)


class DraftRunResult(BaseModel):
    """draft 実行 1 回分の結果サマリー."""

    draft_id: int
    episode: EpisodeScript
    candidate_count: int
    judged_count: int
    selected_count: int
    method_counts: dict[str, int]
    editor_json_stable: bool


class _RecordingClient:
    """LLM 使用量 (tokens / 呼び出し / 失敗) を集計するラッパー (llm_runs 記録用)."""

    def __init__(self, inner: ChatClient) -> None:
        self._inner = inner
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.calls = 0
        self.errors = 0

    def chat(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> LLMResponse:
        self.calls += 1
        try:
            response = self._inner.chat(
                system=system, user=user, json_mode=json_mode, temperature=temperature
            )
        except LLMError:
            self.errors += 1
            raise
        self.prompt_tokens += response.prompt_tokens
        self.completion_tokens += response.completion_tokens
        return response


def _judge_with_neutral_fallback(
    editor: ChatClient,
    candidates: list[ScoredCandidate],
    corroborations: dict[int, int],
) -> tuple[list[JudgedTopic], bool]:
    """編集判定する. editor が崩れたら neutral 判定で続行 (番組を止めない).

    返り値の bool は JSON 安定性 (一発で契約どおり返ったか)。
    """
    try:
        return judge_topics(editor, candidates, corroborations), True
    except (JudgeError, LLMError) as exc:
        logger.warning("editor judgment failed, neutral fallback: %s", exc)
        judged = [
            JudgedTopic(
                candidate=c,
                llm_score=min(100, c.prescore),
                tone=Tone.NEUTRAL,
                corroboration_count=corroborations.get(c.item_id, 1),
            )
            for c in candidates
        ]
        return judged, False


def run_draft(
    session: Session,
    *,
    editor: ChatClient,
    writer: ChatClient,
    roles: ResolvedRoles,
    variant: str,
    now: datetime,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
) -> DraftRunResult | None:
    """draft を 1 回実行し、結果を SQLite に保存して返す.

    候補ゼロ / 編集ゲート全滅の日は None (draft 行を作らない)。
    """
    candidates = extract_candidates(session, now=now, lookback_hours=lookback_hours)
    if not candidates:
        logger.info("no candidates in last %dh, draft skipped", lookback_hours)
        return None

    corroborations = corroboration_counts(session, candidates)
    editor_rec = _RecordingClient(editor)
    writer_rec = _RecordingClient(writer)

    judged, json_stable = _judge_with_neutral_fallback(
        editor_rec, candidates, corroborations
    )
    arranged = arrange_arc(select_topics(judged))
    if not arranged:
        logger.warning("all candidates dropped by editorial gate, draft skipped")
        return None

    results = [(topic, generate_with_fallback(writer_rec, topic)) for topic in arranged]
    episode = assemble_episode(
        [(topic, result.body) for topic, result in results], variant, now
    )

    draft = create_episode_draft(session, episode)
    draft_id = int(draft.id)
    positions = {
        topic.candidate.item_id: i for i, topic in enumerate(arranged, start=1)
    }
    insert_topic_candidates(session, draft_id, judged, positions)
    insert_script_versions(
        session,
        draft_id,
        [(topic.candidate.item_id, result) for topic, result in results],
        now=now,
    )
    record_llm_run(
        session,
        draft_id=draft_id,
        variant=variant,
        role="editor",
        profile_label=roles.editor.label,
        model=roles.editor.model,
        prompt_tokens=editor_rec.prompt_tokens,
        completion_tokens=editor_rec.completion_tokens,
        ok=editor_rec.errors == 0,
        error=f"errors={editor_rec.errors}" if editor_rec.errors else None,
        json_stable=json_stable,
        now=now,
    )
    record_llm_run(
        session,
        draft_id=draft_id,
        variant=variant,
        role="writer",
        profile_label=roles.writer.label,
        model=roles.writer.model,
        prompt_tokens=writer_rec.prompt_tokens,
        completion_tokens=writer_rec.completion_tokens,
        ok=writer_rec.errors == 0,
        error=f"errors={writer_rec.errors}" if writer_rec.errors else None,
        now=now,
    )
    session.commit()

    method_counts: dict[str, int] = {}
    for _, result in results:
        method_counts[result.method] = method_counts.get(result.method, 0) + 1

    return DraftRunResult(
        draft_id=draft_id,
        episode=episode,
        candidate_count=len(candidates),
        judged_count=len(judged),
        selected_count=len(arranged),
        method_counts=method_counts,
        editor_json_stable=json_stable,
    )
