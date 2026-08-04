"""draft パイプラインの統合ランナー.

Sprint 1B Ticket T21。候補抽出 → 編集判定 → 選定/アーク配置 → 台本生成 →
永続化を 1 回の draft 実行として束ねる (collect/runner.py の 1B 版)。

fail-open:
- 薄い summary の上位候補は記事本文フェッチで補強を試みるが、失敗しても元の
  candidate のまま続行する (T61, Issue #61: edit/enrich.py)
- editor の JSON が崩れた日も neutral 判定にフォールバックして番組を出す
  (json_stable=False を llm_runs に記録し、A/B/C 評価に反映)
- writer の違反は generate_with_fallback (T18) がテンプレで吸収する
- writer が本文に埋め込んだインライン読み注釈 (T56, Issue #52) の抽出失敗は
  当該トピックの本文をそのまま残して続行する (_extract_ruby_from_results)
- T18 テンプレ (無内容な最終防衛) が生成されたトピックは、合計本数が MIN_TOPICS
  を割らない範囲で episode markdown / ソース一覧から除外する (T60, Issue #60:
  薄記事 → writer 全滅 → 無内容テンプレがそのまま放送された事故対策)。Issue #95
  で all-or-nothing (1本でも床値割れなら全部残す) から部分ドロップへ変更し、
  床値を割らない範囲で position 順の後ろからテンプレを 1 本ずつ落とす。
  script_versions には除外分も監査証跡として残す (_drop_overflow_templates)
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.orm import Session

from karyu_tech_news.edit.arc import arrange_arc
from karyu_tech_news.edit.enrich import enrich_thin_candidates
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
from karyu_tech_news.script.fallback import (
    METHOD_TEMPLATE,
    TopicScriptResult,
    generate_with_fallback,
)
from karyu_tech_news.script.generate import EpisodeScript, assemble_episode
from karyu_tech_news.script.ruby import (
    DEFAULT_AUTO_READING_DICT_PATH,
    append_auto_readings,
    extract_ruby,
)
from karyu_tech_news.store.dto import (
    EpisodeDraftInput,
    ScriptVersionInput,
    TopicCandidateInput,
)
from karyu_tech_news.store.repo import (
    create_episode_draft,
    insert_script_versions,
    insert_topic_candidates,
    record_llm_run,
)

logger = logging.getLogger(__name__)

# 番組として成立する最低本数 (T60, Issue #60)。show_format の標準本数は 5 本
# (edit/select.py SELECT_MAX)。無内容テンプレ枠のドロップはこの床値を割らない
# 範囲でのみ行う (番組を出すこと自体を最優先する fail-open の精神を維持)。
MIN_TOPICS = 3


class DraftRunResult(BaseModel):
    """draft 実行 1 回分の結果サマリー.

    selected_count / method_counts はテンプレ除外 (T60) 後の値ではなく、
    method_counts は生成試行全件 (除外分含む) の内訳。selected_count は
    実際に episode.markdown に残ったトピック数 (除外後)。dropped_count は
    無内容テンプレとして除外した本数。
    """

    draft_id: int
    episode: EpisodeScript
    candidate_count: int
    judged_count: int
    selected_count: int
    dropped_count: int
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


def _neutral_judgment(
    candidate: ScoredCandidate, corroborations: dict[int, int]
) -> JudgedTopic:
    """LLM 判定が無い候補の neutral 判定 (prescore を score として流用)."""
    return JudgedTopic(
        candidate=candidate,
        llm_score=min(100, candidate.prescore),
        tone=Tone.NEUTRAL,
        corroboration_count=corroborations.get(candidate.item_id, 1),
    )


def _judge_with_neutral_fallback(
    editor: ChatClient,
    candidates: list[ScoredCandidate],
    corroborations: dict[int, int],
) -> tuple[list[JudgedTopic], bool]:
    """編集判定する. editor が崩れた/部分的にしか返さない日も番組を止めない.

    - 全体失敗 (JudgeError/LLMError): 全候補を neutral 判定で続行
    - 部分欠落 (一部 index 未返却): 欠落分のみ neutral 充填 (E2E 2026-06-11 で実測した
      「1/40 件しか判定しない」ケースの対策。T18 の fallback 思想と同じ失敗クラス)
    返り値の bool は JSON 安定性 (一発で全候補をカバーしたか)。
    """
    try:
        judged = judge_topics(editor, candidates, corroborations)
    except (JudgeError, LLMError) as exc:
        logger.warning("editor judgment failed, neutral fallback: %s", exc)
        return [_neutral_judgment(c, corroborations) for c in candidates], False

    judged_ids = {t.candidate.item_id for t in judged}
    missing = [c for c in candidates if c.item_id not in judged_ids]
    if not missing:
        return judged, True
    logger.warning(
        "editor judged %d/%d candidates, neutral fill for %d",
        len(judged),
        len(candidates),
        len(missing),
    )
    filled = judged + [_neutral_judgment(c, corroborations) for c in missing]
    return filled, False


def _extract_ruby_from_results(
    results: list[tuple[JudgedTopic, TopicScriptResult]],
) -> tuple[list[tuple[JudgedTopic, TopicScriptResult]], dict[str, str]]:
    """各トピック本文のインライン読み注釈 `[[表記|カナ読み]]` (Issue #52) を抽出し、
    本文からは表記だけを残してクリーン化する.

    表記が複数トピックにまたがって重複する場合は最初に出現した読みを採用する
    (extract_ruby のテキスト内優先ルールを draft 全体に拡張)。ルビ処理自体の
    失敗 (想定外の例外) は当該トピックの本文をそのまま残して続行する
    (fail-open, WARN ログ。draft 全体を止めない)。
    """
    mapping: dict[str, str] = {}
    cleaned_results: list[tuple[JudgedTopic, TopicScriptResult]] = []
    for topic, result in results:
        try:
            cleaned_body, pairs = extract_ruby(result.body)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ruby extraction failed (item_id=%d), keep body as-is: %s",
                topic.candidate.item_id,
                exc,
            )
            cleaned_results.append((topic, result))
            continue
        for surface, reading in pairs.items():
            mapping.setdefault(surface, reading)
        cleaned_results.append((topic, result.model_copy(update={"body": cleaned_body})))
    return cleaned_results, mapping


def _drop_overflow_templates(
    results: list[tuple[JudgedTopic, TopicScriptResult]],
) -> tuple[list[tuple[JudgedTopic, TopicScriptResult]], list[tuple[JudgedTopic, TopicScriptResult]]]:
    """T18 テンプレ (無内容な最終防衛) のトピックを、床値を割らない範囲で除外する.

    (T60, Issue #60; 部分ドロップ化は Issue #95) writer が全リトライ失敗すると
    generate_with_fallback はテンプレへ fail-open するが、テンプレ文言
    (「今日は○○のニュースを一つ取り上げます」等) は聴取価値が無い。番組を出す
    こと自体は最優先するため、非テンプレ本数だけで MIN_TOPICS に届く場合でも、
    テンプレを 1 本も落とせない all-or-nothing にはしない — 元の並び順 (arc 配置順)
    の後ろから、合計本数が MIN_TOPICS を割らない範囲でテンプレを 1 本ずつ除外する
    (例: 実1+テンプレ4 → 実1+テンプレ2 の計3本を残し2本落とす)。全除外しても
    MIN_TOPICS に届かない分のテンプレは残す (fail-open: 番組を出すこと優先)。
    元の並び順 (arc 配置順) は保持する。

    戻り値: (episode に残すトピック, 除外したトピック)。
    """
    templates_by_position = [
        (i, r) for i, r in enumerate(results) if r[1].method == METHOD_TEMPLATE
    ]
    if not templates_by_position:
        return results, []

    # 落とせる本数 = 全体本数 - MIN_TOPICS (テンプレ以外がいくつあっても、床値を
    # 割らない範囲でしか落とさない)。後方 (position 順の後ろ) から優先して落とす。
    max_droppable = max(0, len(results) - MIN_TOPICS)
    drop_indices = {i for i, _ in templates_by_position[-max_droppable:]} if max_droppable else set()

    kept = [r for i, r in enumerate(results) if i not in drop_indices]
    dropped = [r for i, r in enumerate(results) if i in drop_indices]
    for topic, _ in dropped:
        logger.info(
            "template fallback dropped from episode (item_id=%d, title=%.30s)",
            topic.candidate.item_id,
            topic.candidate.title,
        )
    return kept, dropped


def run_draft(
    session: Session,
    *,
    editor: ChatClient,
    writer: ChatClient,
    roles: ResolvedRoles,
    variant: str,
    now: datetime,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    auto_reading_dict_path: Path = DEFAULT_AUTO_READING_DICT_PATH,
) -> DraftRunResult | None:
    """draft を 1 回実行し、結果を SQLite に保存して返す.

    候補ゼロ / 編集ゲート全滅の日は None (draft 行を作らない)。
    `auto_reading_dict_path` は writer が本文に埋め込んだ読み注釈の蓄積先
    (T56, Issue #52。既定は `data/reading_dict.auto.yaml`)。
    """
    candidates = extract_candidates(session, now=now, lookback_hours=lookback_hours)
    if not candidates:
        logger.info("no candidates in last %dh, draft skipped", lookback_hours)
        return None

    # T61, Issue #61: 薄い summary の上位候補だけ記事本文フェッチで補強する。
    # editor 判定 (直後の corroboration_counts/judge) と writer 生成の両方が
    # 補強後の summary の恩恵を受けられるよう、editor 判定より前に置く。
    candidates = enrich_thin_candidates(candidates)

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
    results, ruby_mapping = _extract_ruby_from_results(results)
    if ruby_mapping:
        append_auto_readings(auto_reading_dict_path, ruby_mapping)

    # T60, Issue #60: 無内容テンプレ枠は床値を割らない範囲で放送 (markdown/ソース
    # 一覧/番号付け) から除外する。script_versions には除外分も全件残す (下記)。
    aired_results, dropped_results = _drop_overflow_templates(results)
    episode = assemble_episode(
        [(topic, result.body) for topic, result in aired_results], variant, now
    )

    draft = create_episode_draft(
        session,
        EpisodeDraftInput(
            generated_at=episode.generated_at,
            variant=episode.variant,
            title=episode.title,
            estimated_minutes=episode.estimated_minutes,
            notices=episode.notices,
            markdown=episode.markdown,
        ),
    )
    draft_id = int(draft.id)
    # position は episode.markdown の番号付けと一致させる (T60: 除外分は position
    # を持たない = selected=False。テンプレ除外後の aired_results を基準にする)。
    positions = {
        topic.candidate.item_id: i
        for i, (topic, _) in enumerate(aired_results, start=1)
    }
    insert_topic_candidates(
        session,
        draft_id,
        [
            TopicCandidateInput(
                item_id=topic.candidate.item_id,
                prescore=topic.candidate.prescore,
                llm_score=topic.llm_score,
                tone=topic.tone.value,
                source_tier=topic.candidate.tier,
                corroboration_count=topic.corroboration_count,
            )
            for topic in judged
        ],
        positions,
    )
    insert_script_versions(
        session,
        draft_id,
        [
            (
                topic.candidate.item_id,
                ScriptVersionInput(
                    method=result.method, attempts=result.attempts, body=result.body
                ),
            )
            for topic, result in results
        ],
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

    # 生成試行全件 (除外分含む) の内訳。除外有無に関わらず「何本 LLM で書けたか」の
    # 監査値として保つ (script_versions と同じ母集団)。
    method_counts: dict[str, int] = {}
    for _, result in results:
        method_counts[result.method] = method_counts.get(result.method, 0) + 1

    return DraftRunResult(
        draft_id=draft_id,
        episode=episode,
        candidate_count=len(candidates),
        judged_count=len(judged),
        selected_count=len(aired_results),
        dropped_count=len(dropped_results),
        method_counts=method_counts,
        editor_json_stable=json_stable,
    )
