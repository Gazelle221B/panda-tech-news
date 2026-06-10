"""script.generate のユニットテスト (Sprint 1B Ticket T17). LLM はモック."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from karyu_tech_news.edit.judge import JudgedTopic, Tone
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.llm.client import LLMResponse
from karyu_tech_news.script.generate import (
    TOPIC_CHAR_LIMIT,
    EpisodeScript,
    assemble_episode,
    build_writer_prompts,
    generate_topic_script,
    script_char_count,
    validate_topic_script,
)

NOW = datetime(2026, 6, 10, 7, 0, tzinfo=UTC)

VALID_BODY = (
    "**Hook:** ディープシーク (DeepSeek) が新モデルを発表しました。\n"
    "**Insight:** 日本の開発者にも API 経由で利用でき、コスト面の選択肢が広がります。\n"
    "**Action:** 公式リリースノートの性能比較に注目です。"
)


def _topic(
    item_id: int = 1,
    *,
    title: str = "DeepSeek 发布新模型",
    tone: Tone = Tone.NEUTRAL,
    tier: int = 1,
    corroboration: int = 1,
    category: str = "AI",
) -> JudgedTopic:
    return JudgedTopic(
        candidate=ScoredCandidate(
            item_id=item_id,
            source_id="src-a",
            title=title,
            summary="模型性能提升",
            link=f"https://example.com/{item_id}",
            published_at=None,
            fetched_at=NOW,
            tier=tier,
            category=category,
            canonical_url_hash="",
            prescore=10,
        ),
        llm_score=80,
        tone=tone,
        corroboration_count=corroboration,
    )


# ---------- script_char_count ----------

def test_script_char_count_excludes_whitespace() -> None:
    assert script_char_count("こん にちは\n世界") == 7


def test_script_char_count_counts_codepoints() -> None:
    # CJK もコードポイント単位 (バイト数ではない)
    assert script_char_count("中文字符") == 4


# ---------- build_writer_prompts ----------

def test_writer_prompts_enforce_contract() -> None:
    system, user = build_writer_prompts(_topic())
    assert "Hook" in system
    assert "Insight" in system
    assert "Action" in system
    assert "300" in system
    assert "カナ" in system
    assert "転載" in system
    assert "DeepSeek 发布新模型" in user
    assert "tone=neutral" in user


def test_writer_prompts_rumor_instruction_for_tier4() -> None:
    _, user = build_writer_prompts(_topic(tier=4))
    assert "噂" in user


# ---------- generate_topic_script ----------

def test_generate_topic_script_plain_text_mode() -> None:
    client = MagicMock()
    client.chat.return_value = LLMResponse(content=VALID_BODY)

    body = generate_topic_script(client, _topic())

    assert body == VALID_BODY
    kwargs = client.chat.call_args.kwargs
    # 台本はプレーンテキスト — JSON モードにしない (IMPLEMENTATION_PLAN-1B §8)
    assert kwargs.get("json_mode", False) is False


# ---------- validate_topic_script ----------

def test_validate_accepts_valid_body() -> None:
    assert validate_topic_script(VALID_BODY) == []


def test_validate_flags_missing_sections() -> None:
    violations = validate_topic_script("**Hook:** 出来事のみ。")
    assert any("Insight" in v for v in violations)
    assert any("Action" in v for v in violations)


def test_validate_flags_over_char_limit() -> None:
    body = (
        "**Hook:** " + "あ" * TOPIC_CHAR_LIMIT
        + "\n**Insight:** い\n**Action:** う"
    )
    violations = validate_topic_script(body)
    assert any("300" in v for v in violations)


def test_validate_flags_url_in_body() -> None:
    body = VALID_BODY + "\n出典: https://example.com/article"
    violations = validate_topic_script(body)
    assert any("URL" in v for v in violations)


def test_validate_flags_forbidden_phrases() -> None:
    body = (
        "**Hook:** 中国すごいという話題です。\n**Insight:** い\n**Action:** う"
    )
    violations = validate_topic_script(body)
    assert any("禁止表現" in v for v in violations)


def test_validate_flags_empty_body() -> None:
    assert validate_topic_script("") != []


def test_validate_requires_rumor_marker_when_asked() -> None:
    violations = validate_topic_script(VALID_BODY, require_rumor_marker=True)
    assert any("噂" in v for v in violations)

    marked = VALID_BODY.replace("**Hook:** ", "**Hook:** これは噂レベルですが — ")
    assert validate_topic_script(marked, require_rumor_marker=True) == []


# ---------- assemble_episode ----------

def test_assemble_episode_builds_markdown() -> None:
    topics = [
        (_topic(1, title="話題A", tone=Tone.HARD_NEGATIVE), VALID_BODY),
        (_topic(2, title="話題B", tone=Tone.BRIGHT), VALID_BODY),
    ]
    episode = assemble_episode(topics, variant="A", generated_at=NOW)

    assert isinstance(episode, EpisodeScript)
    assert episode.variant == "A"
    assert "華流テック通信" in episode.markdown
    assert "## 1. 話題A" in episode.markdown
    assert "## 2. 話題B" in episode.markdown
    assert VALID_BODY.splitlines()[0] in episode.markdown
    # 台本本文の後にソース一覧 (URL は本文ではなくここに)
    assert "https://example.com/1" in episode.markdown
    assert episode.sources == [
        ("話題A", "https://example.com/1"),
        ("話題B", "https://example.com/2"),
    ]
    assert episode.estimated_minutes >= 1
    # 暫定オープニング/クロージング (hal-persona §4)
    assert "華流テック通信、本日のHAL Daily Briefingです。" in episode.markdown
    assert "以上、本日の華流テックでした。" in episode.markdown


def test_assemble_episode_tier4_notice() -> None:
    topics = [(_topic(1, title="噂話題", tier=4, corroboration=2), VALID_BODY)]
    episode = assemble_episode(topics, variant="B", generated_at=NOW)
    assert any("噂" in n for n in episode.notices)
    assert "噂" in episode.markdown


def test_assemble_episode_no_notices_for_official() -> None:
    topics = [(_topic(1, tier=1), VALID_BODY)]
    episode = assemble_episode(topics, variant="A", generated_at=NOW)
    assert episode.notices == []


def test_assemble_episode_headlines() -> None:
    topics = [
        (_topic(1, title="話題A"), VALID_BODY),
        (_topic(2, title="話題B"), VALID_BODY),
    ]
    episode = assemble_episode(topics, variant="C", generated_at=NOW)
    assert episode.headlines == ["話題A", "話題B"]
