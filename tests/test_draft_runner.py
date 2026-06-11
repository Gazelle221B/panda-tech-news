"""script.runner (draft パイプライン統合) のユニットテスト (Ticket T21). LLM はモック."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.llm.client import LLMResponse
from karyu_tech_news.llm.profile import LLMProfile, ResolvedRoles
from karyu_tech_news.script.runner import DraftRunResult, run_draft
from karyu_tech_news.store.repo import create_db_engine, init_db, upsert_source
from karyu_tech_news.store.schema import (
    EpisodeDraft,
    Item,
    LLMRun,
    ScriptVersion,
    TopicCandidate,
)

NOW = datetime(2026, 6, 11, 7, 0, tzinfo=UTC)

VALID_BODY = (
    "**Hook:** ディープシーク (DeepSeek) が新モデルを発表しました。\n"
    "**Insight:** 日本の開発者にも API 経由で利用でき、選択肢が広がります。\n"
    "**Action:** 公式リリースノートの性能比較に注目です。"
)

EDITOR_JSON = (
    '{"topics": ['
    '{"index": 1, "score": 90, "tone": "hard_negative"},'
    '{"index": 2, "score": 70, "tone": "bright"}]}'
)


def _roles() -> ResolvedRoles:
    def profile(label: str) -> LLMProfile:
        return LLMProfile.model_validate(
            {
                "label": label,
                "provider": "openai_compatible",
                "api_key_env": "",
                "base_url": "https://api.example.com/v1",
                "model": f"{label}-model",
                "max_tokens": 1800,
                "temperature": 0.3,
            }
        )

    return ResolvedRoles(editor=profile("mimo"), writer=profile("deepseek"))


def _client(*contents: str) -> MagicMock:
    client = MagicMock()
    client.chat.side_effect = [
        LLMResponse(content=c, prompt_tokens=10, completion_tokens=5) for c in contents
    ]
    return client


@pytest.fixture
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine: Engine = create_db_engine(tmp_path / "test.db")
    init_db(engine)
    with Session(engine) as s:
        yield s


def _seed_items(session: Session) -> None:
    for sid, tier in (("src-a", SourceTier.OFFICIAL), ("src-b", SourceTier.SEMI_OFFICIAL)):
        upsert_source(
            session,
            SourceConfig(
                id=sid,
                name=sid,
                url="https://example.com/feed",
                tier=tier,
                category=SourceCategory.AI,
            ),
        )
    for i, sid in enumerate(["src-a", "src-b"], start=1):
        session.add(
            Item(
                source_id=sid,
                item_key=f"k{i}",
                external_id=None,
                title=f"话题{i}",
                link=f"https://example.com/{i}",
                summary="",
                published_at=None,
                fetched_at=NOW,
                raw_json="{}",
                canonical_url_hash="",
            )
        )
    session.commit()


def test_run_draft_returns_none_when_no_candidates(session: Session) -> None:
    result = run_draft(
        session,
        editor=_client(EDITOR_JSON),
        writer=_client(VALID_BODY),
        roles=_roles(),
        variant="A",
        now=NOW,
    )
    assert result is None


def test_run_draft_full_pipeline(session: Session) -> None:
    _seed_items(session)
    editor = _client(EDITOR_JSON)
    writer = _client(VALID_BODY, VALID_BODY)

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    assert isinstance(result, DraftRunResult)
    assert result.candidate_count == 2
    assert result.selected_count == 2
    assert result.editor_json_stable is True
    assert result.method_counts == {"llm": 2}
    assert "華流テック通信" in result.episode.markdown

    draft = session.execute(select(EpisodeDraft)).scalar_one()
    assert draft.variant == "A"

    candidates = session.execute(select(TopicCandidate)).scalars().all()
    assert len(candidates) == 2
    assert all(bool(c.selected) for c in candidates)
    assert sorted(int(c.position) for c in candidates) == [1, 2]

    scripts = session.execute(select(ScriptVersion)).scalars().all()
    assert len(scripts) == 2
    assert {str(s.method) for s in scripts} == {"llm"}

    runs = session.execute(select(LLMRun)).scalars().all()
    by_role = {str(r.role): r for r in runs}
    assert set(by_role) == {"editor", "writer"}
    assert bool(by_role["editor"].json_stable) is True
    assert by_role["editor"].profile_label == "mimo"
    assert by_role["writer"].profile_label == "deepseek"
    assert int(by_role["editor"].prompt_tokens) == 10
    assert int(by_role["writer"].prompt_tokens) == 20  # 2 トピック分


def test_run_draft_partial_judgment_neutral_fills_missing(session: Session) -> None:
    """editor が一部しか判定を返さない日も、未判定分を neutral 充填して番組を出す."""
    _seed_items(session)
    # index=1 のみ判定、index=2 は欠落
    editor = _client('{"topics": [{"index": 1, "score": 90, "tone": "hard_negative"}]}')
    writer = _client(VALID_BODY, VALID_BODY)

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    assert result is not None
    assert result.judged_count == 2  # 1 (LLM) + 1 (neutral 充填)
    assert result.selected_count == 2
    assert result.editor_json_stable is False  # 全候補をカバーできていない


def test_run_draft_editor_garbage_falls_back_to_neutral(session: Session) -> None:
    _seed_items(session)
    editor = _client("JSONではない出力")
    writer = _client(VALID_BODY, VALID_BODY)

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    # editor が崩れても番組は出る (fail-open)。json_stable=False が記録される
    assert result is not None
    assert result.editor_json_stable is False
    runs = session.execute(select(LLMRun)).scalars().all()
    editor_run = next(r for r in runs if str(r.role) == "editor")
    assert bool(editor_run.json_stable) is False


def test_run_draft_writer_violations_use_template(session: Session) -> None:
    _seed_items(session)
    editor = _client(EDITOR_JSON)
    # 2 トピック × (初回 + 再生成) すべて違反 → 全部テンプレ
    writer = _client("違反本文", "違反本文", "違反本文", "違反本文")

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    assert result is not None
    assert result.method_counts == {"template": 2}
    assert "**Hook:**" in result.episode.markdown  # テンプレでも契約適合
