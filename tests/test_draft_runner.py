"""script.runner (draft パイプライン統合) のユニットテスト (Ticket T21). LLM はモック."""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

import karyu_tech_news.script.runner as runner_module
from karyu_tech_news.config import SourceCategory, SourceConfig, SourceTier
from karyu_tech_news.edit.judge import JudgedTopic, Tone
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.llm.client import LLMResponse
from karyu_tech_news.llm.profile import LLMProfile, ResolvedRoles
from karyu_tech_news.script.fallback import METHOD_TEMPLATE, TopicScriptResult
from karyu_tech_news.script.ruby import load_auto_readings
from karyu_tech_news.script.runner import (
    DraftRunResult,
    _drop_overflow_templates,
    run_draft,
)
from karyu_tech_news.store.repo import create_db_engine, init_db, upsert_source
from karyu_tech_news.store.schema import (
    EpisodeDraft,
    Item,
    LLMRun,
    ScriptVersion,
    TopicCandidate,
)

NOW = datetime(2026, 6, 11, 7, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_real_article_fetch() -> Generator[None, None, None]:
    """T61: run_draft は enrich_thin_candidates 経由で記事本文を HTTP フェッチしうる。
    本ファイルの既存テストは薄い summary ("") をシードしており HTTP をモックして
    いないため、既定でフェッチ失敗 (None) にして実ネットワークアクセスを防ぐ
    (fail-open のため候補は元のまま = 既存テストの前提を変えない)。
    """
    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value=None):
        yield

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


def _editor_json(n: int) -> str:
    """n 件全候補を neutral tone・score 80 で判定する editor JSON (T60 テスト用)."""
    topics = ",".join(
        f'{{"index": {i}, "score": 80, "tone": "neutral"}}' for i in range(1, n + 1)
    )
    return '{"topics": [' + topics + "]}"


def _writer_forcing_template(target_title: str) -> MagicMock:
    """target_title の topic だけ契約違反本文を返し、generate_with_fallback を
    template へ fail-open させる (他の topic は VALID_BODY で正常, T60 テスト用).

    呼び出し順ではなく user プロンプト中のタイトル文字列で判定するため、
    select_topics/arrange_arc の並び替えに依存しない。
    """
    client = MagicMock()

    def _chat(system: str, user: str, **_: object) -> LLMResponse:
        if f"タイトル: {target_title}" in user:
            return LLMResponse(content="違反本文", prompt_tokens=10, completion_tokens=5)
        return LLMResponse(content=VALID_BODY, prompt_tokens=10, completion_tokens=5)

    client.chat.side_effect = _chat
    return client


def _writer_forcing_templates(target_titles: set[str]) -> MagicMock:
    """target_titles に含まれる topic だけ契約違反本文を返し、複数 topic を
    まとめて template へ fail-open させる (Issue #95 部分ドロップ統合テスト用。
    単一タイトル版の _writer_forcing_template の複数版)."""
    client = MagicMock()

    def _chat(system: str, user: str, **_: object) -> LLMResponse:
        if any(f"タイトル: {title}" in user for title in target_titles):
            return LLMResponse(content="違反本文", prompt_tokens=10, completion_tokens=5)
        return LLMResponse(content=VALID_BODY, prompt_tokens=10, completion_tokens=5)

    client.chat.side_effect = _chat
    return client


_CATEGORIES = (
    SourceCategory.AI,
    SourceCategory.TECH,
    SourceCategory.GAME,
    SourceCategory.SUBCULTURE,
    SourceCategory.OSS,
    SourceCategory.ANIME,
)


def _seed_n_items(session: Session, n: int) -> None:
    """distinct な source/category を持つ item を n 件シードする (キャップ回避, T60 テスト用).

    summary は 40 字以上 (THIN_SUMMARY_PENALTY の影響を受けない) にしておく。
    """
    summary = "十分な長さのダミー概要文をここに用意しておく必要がある四十字以上のテキストです。"
    for i in range(1, n + 1):
        sid = f"src-{i}"
        upsert_source(
            session,
            SourceConfig(
                id=sid,
                name=sid,
                url="https://example.com/feed",
                tier=SourceTier.OFFICIAL,
                category=_CATEGORIES[(i - 1) % len(_CATEGORIES)],
            ),
        )
    for i in range(1, n + 1):
        session.add(
            Item(
                source_id=f"src-{i}",
                item_key=f"k{i}",
                external_id=None,
                title=f"话题{i}",
                link=f"https://example.com/{i}",
                summary=summary,
                published_at=None,
                fetched_at=NOW,
                raw_json="{}",
                canonical_url_hash="",
            )
        )
    session.commit()


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


def test_run_draft_calls_enrich_before_editor_judge(session: Session) -> None:
    """T61, Issue #61: enrich_thin_candidates は editor 判定 (corroboration_counts/
    judge) より前に candidates へ適用される."""
    _seed_items(session)
    call_order: list[str] = []

    def _fake_enrich(candidates: list[object], **_: object) -> list[object]:
        call_order.append("enrich")
        return candidates

    def _fake_corroboration(_session: Session, candidates: list[object]) -> dict[int, int]:
        call_order.append("corroboration_counts")
        return {c.item_id: 1 for c in candidates}  # type: ignore[attr-defined]

    with patch.object(runner_module, "enrich_thin_candidates", side_effect=_fake_enrich) as mock_enrich, \
         patch.object(runner_module, "corroboration_counts", side_effect=_fake_corroboration):
        result = run_draft(
            session,
            editor=_client(EDITOR_JSON),
            writer=_client(VALID_BODY, VALID_BODY),
            roles=_roles(),
            variant="A",
            now=NOW,
        )

    assert result is not None
    assert call_order == ["enrich", "corroboration_counts"]
    mock_enrich.assert_called_once()


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
    # T63, Issue #69: イントロに draft 実行時刻 (now=NOW, JST 変換) の当日日付が入る。
    # NOW = 2026-06-11 07:00 UTC -> JST 2026-06-11 16:00 (木曜日)
    assert "6月11日、木曜日" in result.episode.markdown

    draft = session.execute(select(EpisodeDraft)).scalar_one()
    assert draft.variant == "A"
    assert "6月11日、木曜日" in str(draft.markdown)  # DB 保存済み markdown にも反映

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


def test_run_draft_extracts_ruby_and_updates_auto_dict(
    session: Session, tmp_path: Path
) -> None:
    """writer が本文に埋め込んだ [[表記|カナ読み]] を抽出し、保存 markdown はクリーン化・
    自動読み辞書 (data/reading_dict.auto.yaml 相当) へ蓄積する (T56, Issue #52)."""
    _seed_items(session)
    editor = _client(EDITOR_JSON)
    body_with_ruby = (
        "**Hook:** [[零一万物|レイイチバンブツ]] が新モデルを発表しました。\n"
        "**Insight:** 日本の開発者にも API 経由で利用でき、選択肢が広がります。\n"
        "**Action:** 公式リリースノートの性能比較に注目です。"
    )
    writer = _client(body_with_ruby, VALID_BODY)
    auto_path = tmp_path / "reading_dict.auto.yaml"

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
        auto_reading_dict_path=auto_path,
    )

    assert result is not None
    assert "[[" not in result.episode.markdown  # ルビ記法は本文から除去される
    assert "零一万物" in result.episode.markdown  # 表記自体は残る

    assert auto_path.exists()
    assert load_auto_readings(auto_path) == {"零一万物": "レイイチバンブツ"}

    draft = session.execute(select(EpisodeDraft)).scalar_one()
    assert "[[" not in str(draft.markdown)  # DB 保存済み markdown もクリーン

    scripts = session.execute(select(ScriptVersion)).scalars().all()
    assert all("[[" not in str(s.body) for s in scripts)  # 個別トピック本文もクリーン


# ---------- T60 (Issue #60): テンプレ枠ドロップ ----------

def test_run_draft_drops_template_above_floor(session: Session) -> None:
    """5 本中 1 本が無内容テンプレのとき、床値 (MIN_TOPICS=3) を割らないため
    4 本に除外される。markdown・ソース一覧には出ないが script_versions には残る。"""
    _seed_n_items(session, 5)
    editor = _client(_editor_json(5))
    writer = _writer_forcing_template("话题3")

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    assert result is not None
    assert result.selected_count == 4
    assert result.dropped_count == 1
    assert result.method_counts == {"llm": 4, "template": 1}
    assert "话题3" not in result.episode.markdown
    assert result.episode.markdown.count("**Hook:**") == 4
    assert len(result.episode.sources) == 4

    # script_versions は除外分も含め全 5 件が監査証跡として残る
    scripts = session.execute(select(ScriptVersion)).scalars().all()
    assert len(scripts) == 5
    assert {str(s.method) for s in scripts} == {"llm", "template"}

    # topic_candidates: 除外分は selected=False / position=None
    candidates = session.execute(select(TopicCandidate)).scalars().all()
    assert len(candidates) == 5
    selected = [c for c in candidates if bool(c.selected)]
    assert len(selected) == 4
    assert sorted(int(c.position) for c in selected) == [1, 2, 3, 4]

    dropped = [c for c in candidates if not bool(c.selected)]
    assert len(dropped) == 1
    assert dropped[0].position is None


def test_run_draft_keeps_template_at_floor(session: Session) -> None:
    """3 本中 1 本が無内容テンプレのとき、除外すると MIN_TOPICS を割るため
    従来どおりテンプレのまま残る (fail-open: 番組を出すこと優先)."""
    _seed_n_items(session, 3)
    editor = _client(_editor_json(3))
    writer = _writer_forcing_template("话题2")

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    assert result is not None
    assert result.selected_count == 3
    assert result.dropped_count == 0
    assert result.method_counts == {"llm": 2, "template": 1}
    assert result.episode.markdown.count("**Hook:**") == 3  # テンプレも契約適合、3 本とも残る

    scripts = session.execute(select(ScriptVersion)).scalars().all()
    assert len(scripts) == 3

    candidates = session.execute(select(TopicCandidate)).scalars().all()
    assert all(bool(c.selected) for c in candidates)
    assert sorted(int(c.position) for c in candidates) == [1, 2, 3]


def test_run_draft_partial_drop_real1_template4_end_to_end(session: Session) -> None:
    """実1+テンプレ4 (計5本) の部分ドロップを run_draft 経由で確認する統合テスト
    (codex terra レビュー non-blocking, PR #96)。実1+テンプレ2 の計3本が放送され、
    markdown/ソース一覧は3本のみになる一方、topic_candidates の selected/position と
    script_versions の監査証跡 (除外分2本も残る) は整合していることを確認する。"""
    _seed_n_items(session, 5)
    editor = _client(_editor_json(5))
    # 話题1 のみ正常な LLM 出力、話题2〜5 はすべてテンプレへ fail-open させる
    writer = _writer_forcing_templates({"话题2", "话题3", "话题4", "话题5"})

    result = run_draft(
        session,
        editor=editor,
        writer=writer,
        roles=_roles(),
        variant="A",
        now=NOW,
    )

    assert result is not None
    assert result.selected_count == 3
    assert result.dropped_count == 2
    assert result.method_counts == {"llm": 1, "template": 4}

    # markdown / ソース一覧は放送された3本のみ (話题4, 話题5 はドロップされ現れない)
    assert result.episode.markdown.count("**Hook:**") == 3
    assert len(result.episode.sources) == 3
    assert "话题4" not in result.episode.markdown
    assert "话题5" not in result.episode.markdown

    # topic_candidates: 放送された3本のみ selected=True / position=1..3、
    # ドロップされた2本は selected=False / position=None
    candidates = session.execute(select(TopicCandidate)).scalars().all()
    assert len(candidates) == 5
    selected = [c for c in candidates if bool(c.selected)]
    assert len(selected) == 3
    assert sorted(int(c.position) for c in selected) == [1, 2, 3]
    dropped = [c for c in candidates if not bool(c.selected)]
    assert len(dropped) == 2
    assert all(c.position is None for c in dropped)

    # script_versions: 除外分含め全5件が監査証跡として残る (llm 1件 + template 4件)
    scripts = session.execute(select(ScriptVersion)).scalars().all()
    assert len(scripts) == 5
    method_by_item = {int(s.item_id): str(s.method) for s in scripts}
    assert sum(1 for m in method_by_item.values() if m == "llm") == 1
    assert sum(1 for m in method_by_item.values() if m == METHOD_TEMPLATE) == 4


# ---------- _drop_overflow_templates 部分ドロップ (Issue #95) ----------
#
# T60 導入時は「1 本でも除外すると MIN_TOPICS を割るなら全部残す」all-or-nothing
# だった。Issue #95 で、床値を割らない範囲でテンプレを 1 本ずつ (position 順の
# 後ろから) 落とす部分ドロップへ変更した。


def _judged(item_id: int) -> JudgedTopic:
    return JudgedTopic(
        candidate=ScoredCandidate(
            item_id=item_id,
            source_id="src-a",
            title=f"话题{item_id}",
            summary="十分な長さのダミー概要文をここに用意しておく必要がある四十字以上のテキストです。",
            link=f"https://example.com/{item_id}",
            published_at=None,
            fetched_at=NOW,
            tier=1,
            category="AI",
            canonical_url_hash="",
            prescore=10,
        ),
        llm_score=80,
        tone=Tone.NEUTRAL,
        corroboration_count=1,
    )


def _result(method: str) -> TopicScriptResult:
    return TopicScriptResult(body=VALID_BODY, method=method, attempts=1, violations_first=[])


def test_drop_overflow_templates_partial_drop_real1_template4() -> None:
    """実1+テンプレ4 (計5本, MIN_TOPICS=3) → 実1+テンプレ2 の計3本を残し、
    position 順の後ろから2本落とす."""
    results = [
        (_judged(1), _result("llm")),
        (_judged(2), _result(METHOD_TEMPLATE)),
        (_judged(3), _result(METHOD_TEMPLATE)),
        (_judged(4), _result(METHOD_TEMPLATE)),
        (_judged(5), _result(METHOD_TEMPLATE)),
    ]

    kept, dropped = _drop_overflow_templates(results)

    assert [t.candidate.item_id for t, _ in kept] == [1, 2, 3]
    assert [t.candidate.item_id for t, _ in dropped] == [4, 5]


def test_drop_overflow_templates_partial_drop_real3_template2() -> None:
    """実3+テンプレ2 (計5本) → 実3本を残し、テンプレ2本を落とす."""
    results = [
        (_judged(1), _result("llm")),
        (_judged(2), _result("llm")),
        (_judged(3), _result("llm")),
        (_judged(4), _result(METHOD_TEMPLATE)),
        (_judged(5), _result(METHOD_TEMPLATE)),
    ]

    kept, dropped = _drop_overflow_templates(results)

    assert [t.candidate.item_id for t, _ in kept] == [1, 2, 3]
    assert [t.candidate.item_id for t, _ in dropped] == [4, 5]


def test_drop_overflow_templates_keeps_all_at_floor() -> None:
    """実1+テンプレ1 (計2本 < MIN_TOPICS) は、実+テンプレ計が MIN_TOPICS を
    割っているため1本も落とさず全部残す (fail-open: 番組を出すこと優先)."""
    results = [
        (_judged(1), _result("llm")),
        (_judged(2), _result(METHOD_TEMPLATE)),
    ]

    kept, dropped = _drop_overflow_templates(results)

    assert [t.candidate.item_id for t, _ in kept] == [1, 2]
    assert dropped == []


def test_drop_overflow_templates_no_templates_returns_all_kept() -> None:
    results = [(_judged(1), _result("llm")), (_judged(2), _result("llm"))]

    kept, dropped = _drop_overflow_templates(results)

    assert kept == results
    assert dropped == []
