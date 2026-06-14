"""script.fallback のユニットテスト (Sprint 1B Ticket T18). LLM はモック."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from karyu_tech_news.edit.judge import JudgedTopic, Tone
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.llm.client import LLMError, LLMResponse
from karyu_tech_news.script.fallback import (
    FALLBACK_TEMPLATE_COUNT,
    TopicScriptResult,
    fallback_topic_script,
    generate_with_fallback,
)
from karyu_tech_news.script.generate import WRITER_CHAR_BUDGET, validate_topic_script

NOW = datetime(2026, 6, 10, 7, 0, tzinfo=UTC)

VALID_BODY = (
    "**Hook:** ディープシーク (DeepSeek) が新モデルを発表しました。\n"
    "**Insight:** 日本の開発者にも API 経由で利用でき、選択肢が広がります。\n"
    "**Action:** 公式リリースノートの性能比較に注目です。"
)

INVALID_BODY = "ただの要約テキスト。Hook も Insight も無い。"

# 構造は正しいが空白除き 300 字を超える本文 (DeepSeek の冗長出力を模す)
_FILLER = "詳細な背景説明をここに長々と書き連ねていきます" * 8
OVER_LIMIT_BODY = (
    f"**Hook:** {_FILLER}\n**Insight:** {_FILLER}\n**Action:** {_FILLER}"
)


def _topic(
    item_id: int = 1,
    *,
    title: str = "DeepSeek 发布新模型",
    tier: int = 1,
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
            category="AI",
            canonical_url_hash="",
            prescore=10,
        ),
        llm_score=80,
        tone=Tone.NEUTRAL,
        corroboration_count=2,
    )


# ---------- fallback_topic_script ----------

def test_fallback_all_patterns_pass_validation() -> None:
    for i in range(FALLBACK_TEMPLATE_COUNT):
        body = fallback_topic_script(_topic(), pattern_index=i)
        assert validate_topic_script(body) == [], f"pattern {i} が契約違反"


def test_fallback_patterns_differ() -> None:
    bodies = {
        fallback_topic_script(_topic(), pattern_index=i)
        for i in range(FALLBACK_TEMPLATE_COUNT)
    }
    assert len(bodies) == FALLBACK_TEMPLATE_COUNT  # 枕詞の乱択用に全パターン別文面


def test_fallback_tier4_includes_rumor_marker() -> None:
    for i in range(FALLBACK_TEMPLATE_COUNT):
        body = fallback_topic_script(_topic(tier=4), pattern_index=i)
        assert validate_topic_script(body, require_rumor_marker=True) == []


def test_fallback_random_selection_is_valid() -> None:
    body = fallback_topic_script(_topic())  # pattern_index=None → 乱択
    assert validate_topic_script(body) == []


def test_fallback_truncates_long_title() -> None:
    body = fallback_topic_script(_topic(title="超" * 500), pattern_index=0)
    assert validate_topic_script(body) == []


# ---------- generate_with_fallback ----------

def _client_returning(*contents: object) -> MagicMock:
    client = MagicMock()
    effects = [
        c if isinstance(c, Exception) else LLMResponse(content=str(c)) for c in contents
    ]
    client.chat.side_effect = effects
    return client


def test_generate_with_fallback_first_try_ok() -> None:
    client = _client_returning(VALID_BODY)

    result = generate_with_fallback(client, _topic())

    assert isinstance(result, TopicScriptResult)
    assert result.body == VALID_BODY
    assert result.method == "llm"
    assert result.attempts == 1
    assert client.chat.call_count == 1


def test_generate_with_fallback_retry_with_feedback() -> None:
    client = _client_returning(INVALID_BODY, VALID_BODY)

    result = generate_with_fallback(client, _topic())

    assert result.body == VALID_BODY
    assert result.method == "llm_retry"
    assert result.attempts == 2
    assert client.chat.call_count == 2
    # 2回目の user プロンプトに違反フィードバックが含まれる
    second_user = client.chat.call_args_list[1].kwargs["user"]
    assert "違反" in second_user


def test_retry_feedback_includes_char_budget() -> None:
    # T22 defect①: 300字超過時の再生成プロンプトに字数予算(260)を明示し短縮を促す
    client = _client_returning(OVER_LIMIT_BODY, VALID_BODY)

    result = generate_with_fallback(client, _topic())

    assert result.method == "llm_retry"
    assert result.attempts == 2
    second_user = client.chat.call_args_list[1].kwargs["user"]
    assert str(WRITER_CHAR_BUDGET) in second_user


def test_generate_with_fallback_template_when_llm_keeps_failing() -> None:
    client = _client_returning(INVALID_BODY, INVALID_BODY)

    result = generate_with_fallback(client, _topic())

    assert result.method == "template"
    assert validate_topic_script(result.body) == []
    assert result.violations_first != []


def test_generate_with_fallback_template_on_llm_error() -> None:
    client = _client_returning(LLMError("boom"), LLMError("boom"))

    result = generate_with_fallback(client, _topic())

    assert result.method == "template"
    assert validate_topic_script(result.body) == []


def test_generate_with_fallback_tier4_requires_rumor_marker() -> None:
    # Tier4 なのに噂明示が無い LLM 出力 → 違反 → 最終的にテンプレ (噂明示込み)
    client = _client_returning(VALID_BODY, VALID_BODY)

    result = generate_with_fallback(client, _topic(tier=4))

    assert result.method == "template"
    assert "噂" in result.body
