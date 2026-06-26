"""台本生成の二重防御 fallback.

Sprint 1B Ticket T18 (design-inheritance §7 の継承)。
LLM 出力が契約違反 (validate_topic_script) のとき:

1. 違反フィードバックを添えて 1 回だけ再生成
2. それも違反ならテンプレートで生成 (LLM 不使用・常に契約適合)

テンプレートは複数パターンを乱択し、毎日同じ枕詞になるのを避ける
(meeting 改善提案)。fallback が無いと LLM が出力を崩した日に番組が
出ない — 「番組を出すこと」を最優先する最後の砦。
"""
from __future__ import annotations

import logging
import random

from pydantic import BaseModel

from karyu_tech_news.edit.judge import ChatClient, JudgedTopic
from karyu_tech_news.llm.client import LLMError
from karyu_tech_news.script.generate import (
    WRITER_CHAR_BUDGET,
    build_writer_prompts,
    validate_topic_script,
)

logger = logging.getLogger(__name__)

# {rumor} は Tier4 のとき「これは噂レベルですが — 」が入る。
# T36: テンプレ fallback は原題を読ませない。中国語原題をそのまま Hook に入れると、
# TTS 前処理で pinyin 化できても音声として不自然になるため、category ベースの日本語
# 定型文に落とす。原題は Markdown 見出し/ソース一覧に視覚情報として残る。
_TEMPLATES = (
    (
        "**Hook:** {rumor}本日注目の {category} トピックです。\n"
        "**Insight:** 詳細は引き続き確認中ですが、{category} 領域の動きとして"
        "押さえておきたいニュースです。\n"
        "**Action:** 続報と一次情報の更新に注目してください。"
    ),
    (
        "**Hook:** {rumor}{category} 領域で、新しい動きが入ってきました。\n"
        "**Insight:** 中華圏の {category} 動向を追う上で参考になる話題です。\n"
        "**Action:** 関連する公式発表が出ないか、今後の発信をチェックしましょう。"
    ),
    (
        "**Hook:** {rumor}今日は中華圏の {category} ニュースを一つ取り上げます。\n"
        "**Insight:** 一次情報の確認はこれからですが、日本のリスナーにも関わり得る動きです。\n"
        "**Action:** 明日以降の続報で深掘りします。気になる方はソース一覧をどうぞ。"
    ),
    (
        "**Hook:** {rumor}{category} 分野で、続報を追いたい話題が出ています。\n"
        "**Insight:** {category} 分野の変化として、影響範囲を見極めたいところです。\n"
        "**Action:** 公式リリースやコミュニティの反応を合わせて確認してみてください。"
    ),
)
FALLBACK_TEMPLATE_COUNT = len(_TEMPLATES)

RUMOR_PREFIX = "これは噂レベルですが — "


class TopicScriptResult(BaseModel):
    """1 トピック分の生成結果. method と違反は A/B/C ログ (T20 修正回数) に使う."""

    body: str
    method: str  # "llm" | "llm_retry" | "template"
    attempts: int
    violations_first: list[str]


def fallback_topic_script(topic: JudgedTopic, pattern_index: int | None = None) -> str:
    """テンプレートで 1 トピック分の台本を生成する (LLM 不使用・常に契約適合).

    pattern_index 省略時は乱択 (毎日同じ枕詞を避ける)。
    """
    if pattern_index is None:
        pattern_index = random.randrange(FALLBACK_TEMPLATE_COUNT)
    template = _TEMPLATES[pattern_index % FALLBACK_TEMPLATE_COUNT]

    rumor = RUMOR_PREFIX if topic.candidate.tier >= 4 else ""
    return template.format(rumor=rumor, category=topic.candidate.category)


def generate_with_fallback(client: ChatClient, topic: JudgedTopic) -> TopicScriptResult:
    """LLM 生成 → 違反なら再生成 → それも違反ならテンプレ fallback.

    LLMError も違反と同様に扱い、パイプラインを止めない (要件 §9.3)。
    """
    require_rumor = topic.candidate.tier >= 4
    system, user = build_writer_prompts(topic)

    violations_first: list[str] = []
    for attempt in (1, 2):
        prompt_user = user
        if attempt == 2:
            prompt_user = (
                f"{user}\n\n前回の出力には次の契約違反がありました。"
                f"修正して書き直してください: {'; '.join(violations_first)}\n"
                f"特に文字数は空白除き {WRITER_CHAR_BUDGET} 文字以内に必ず短縮すること。"
            )
        try:
            body = client.chat(system=system, user=prompt_user).content
        except LLMError as exc:
            logger.warning(
                "writer LLM failed (attempt %d, item_id=%d): %s",
                attempt,
                topic.candidate.item_id,
                exc,
            )
            if attempt == 1:
                violations_first = [f"LLM 呼び出し失敗: {exc}"]
            continue

        violations = validate_topic_script(body, require_rumor_marker=require_rumor)
        if not violations:
            return TopicScriptResult(
                body=body,
                method="llm" if attempt == 1 else "llm_retry",
                attempts=attempt,
                violations_first=violations_first,
            )
        logger.info(
            "script violations (attempt %d, item_id=%d): %s",
            attempt,
            topic.candidate.item_id,
            violations,
        )
        if attempt == 1:
            violations_first = violations

    return TopicScriptResult(
        body=fallback_topic_script(topic),
        method="template",
        attempts=3,
        violations_first=violations_first,
    )
