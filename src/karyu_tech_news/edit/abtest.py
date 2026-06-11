"""A/B/C 検証の集計 (evaluate).

Sprint 1B Ticket T20。T19 が保存したログ (topic_candidates / llm_runs /
script_versions) を variant 別に集計し、ADR-0005 の定量評価軸
(採用率 / 修正回数 / コスト / JSON 安定性) を出す。

読み上げ自然さ・AI 要約臭は人間の主観評価 (Discord 投稿を読んで判断) のため
本集計には含まれない。
"""
from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from karyu_tech_news.store.schema import (
    EpisodeDraft,
    LLMRun,
    ScriptVersion,
    TopicCandidate,
)


class VariantStats(BaseModel):
    """1 variant (A/B/C) 分の集計値."""

    variant: str
    drafts: int
    candidates: int
    selected: int
    adoption_rate: float
    llm_calls: int
    llm_failures: int
    prompt_tokens: int
    completion_tokens: int
    json_stable_rate: float | None  # editor 実行が無い variant は None
    method_counts: dict[str, int]  # llm / llm_retry / template
    avg_attempts: float


def evaluate_variants(session: Session) -> list[VariantStats]:
    """variant 別の集計を返す (variant 名の昇順)."""
    drafts = session.execute(select(EpisodeDraft)).scalars().all()
    if not drafts:
        return []

    variant_by_draft = {int(d.id): str(d.variant) for d in drafts}
    variants = sorted({str(d.variant) for d in drafts})

    candidates = session.execute(select(TopicCandidate)).scalars().all()
    llm_runs = session.execute(select(LLMRun)).scalars().all()
    scripts = session.execute(select(ScriptVersion)).scalars().all()

    stats = []
    for variant in variants:
        draft_ids = {d_id for d_id, v in variant_by_draft.items() if v == variant}

        v_candidates = [c for c in candidates if int(c.draft_id) in draft_ids]
        v_selected = [c for c in v_candidates if bool(c.selected)]

        v_runs = [r for r in llm_runs if str(r.variant) == variant]
        v_failures = [r for r in v_runs if not bool(r.ok)]
        editor_stability = [
            bool(r.json_stable) for r in v_runs if r.json_stable is not None
        ]

        v_scripts = [s for s in scripts if int(s.draft_id) in draft_ids]
        method_counts: dict[str, int] = {}
        for s in v_scripts:
            method = str(s.method)
            method_counts[method] = method_counts.get(method, 0) + 1

        stats.append(
            VariantStats(
                variant=variant,
                drafts=len(draft_ids),
                candidates=len(v_candidates),
                selected=len(v_selected),
                adoption_rate=(
                    len(v_selected) / len(v_candidates) if v_candidates else 0.0
                ),
                llm_calls=len(v_runs),
                llm_failures=len(v_failures),
                prompt_tokens=sum(int(r.prompt_tokens) for r in v_runs),
                completion_tokens=sum(int(r.completion_tokens) for r in v_runs),
                json_stable_rate=(
                    sum(editor_stability) / len(editor_stability)
                    if editor_stability
                    else None
                ),
                method_counts=method_counts,
                avg_attempts=(
                    sum(int(s.attempts) for s in v_scripts) / len(v_scripts)
                    if v_scripts
                    else 0.0
                ),
            )
        )
    return stats


def format_evaluation(stats: list[VariantStats]) -> str:
    """CLI 表示用の日本語サマリーを組み立てる."""
    if not stats:
        return "評価対象の draft がまだなし (まず draft を実行してください)"

    lines = ["A/B/C 検証サマリー (ADR-0005 定量評価軸)", ""]
    for s in stats:
        json_rate = (
            f"{s.json_stable_rate * 100:.0f}%" if s.json_stable_rate is not None else "—"
        )
        methods = (
            ", ".join(f"{k}={v}" for k, v in sorted(s.method_counts.items())) or "—"
        )
        lines.append(f"## 案 {s.variant} (draft {s.drafts} 回)")
        lines.append(
            f"- 採用率: {s.adoption_rate * 100:.0f}% ({s.selected}/{s.candidates} 候補)"
        )
        lines.append(
            f"- 修正回数: 平均 {s.avg_attempts:.1f} 回 (内訳: {methods})"
        )
        lines.append(
            f"- コスト: prompt {s.prompt_tokens} tokens / "
            f"completion {s.completion_tokens} tokens "
            f"(LLM 呼び出し {s.llm_calls} 回, 失敗 {s.llm_failures})"
        )
        lines.append(f"- JSON 安定性: {json_rate}")
        lines.append("")
    lines.append("読み上げ自然さ・AI 要約臭は Discord 投稿を読んで人間が評価する。")
    return "\n".join(lines)
