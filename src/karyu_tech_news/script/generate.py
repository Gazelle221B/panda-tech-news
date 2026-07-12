"""Markdown 台本生成 (Hook / Insight / Action).

Sprint 1B Ticket T17。writer LLM に 1 トピック分のプレーンテキスト台本を
書かせ、コード側で検証・組み立てを行う。

役割分離 (IMPLEMENTATION_PLAN-1B §8):
- LLM はプレーンテキスト台本のみ (JSON と同時に書かせない)
- 検証 (300 字・URL 混入・禁止表現・噂明示) と番組への組み立ては決定的コード
- 出典 URL は本文に入れず、ソース一覧セクションへ (design-inheritance §8)
"""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import yaml
from pydantic import BaseModel

from karyu_tech_news.config import PROJECT_ROOT
from karyu_tech_news.edit.judge import ChatClient, JudgedTopic

TOPIC_CHAR_LIMIT = 300  # show_format.yaml topic_structure.char_limit_jp (空白除く)。ハード検証値
# writer プロンプトに提示する目標予算。ハード上限より厳しめにしてマージンを取る
# (T22 観察: DeepSeek が 300 字ちょうどを狙うと一貫超過し template 落ちした defect 対策)
WRITER_CHAR_BUDGET = 260
PROMPT_TITLE_LIMIT = 180
PROMPT_SUMMARY_LIMIT = 420
CHARS_PER_MINUTE = 300  # 日本語読み上げの目安 (推定尺用)

SHOW_TITLE = "華流テック通信 — HAL Daily Briefing"
RUMOR_MARKER = "噂"  # 「これは噂レベルですが — 」等の明示を要求 (editorial-policy §10)

DEFAULT_SHOW_FORMAT_PATH = PROJECT_ROOT / "config" / "show_format.yaml"

# 確定挨拶フレーズ (Issue #39, 2026-07-12 人間選定, T54) の既定値。
# config/show_format.yaml の `phrases` セクションが読めない/フィールド欠落の場合の
# fail-open フォールバック (ハードコードは避けたいが、ファイル I/O が失敗しても
# 番組を止めないための最終防衛線として確定文言そのものを既定にする)。
_DEFAULT_TITLE_CALL = "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"
_DEFAULT_OPENING_PHRASE = (
    "キャスターのHALです。支度の手を止めずに、今朝の中華圏テック、要点だけボクと一緒に追いかけましょう。"
)
_DEFAULT_CLOSING_PHRASE = "今日の華流テック通信は以上です。それでは皆さん、良い一日を。HALでした。"


class ShowPhrases(NamedTuple):
    """番組固定挨拶フレーズ 3 種 (hal-persona §4)."""

    title_call: str
    opening: str
    closing: str


def load_show_phrases(path: Path = DEFAULT_SHOW_FORMAT_PATH) -> ShowPhrases:
    """show_format.yaml の `phrases` (固定挨拶句) を読む (T54, Issue #39).

    ファイル欠落・YAML 破損・`phrases` セクション欠落・個別フィールド欠落は、
    いずれも fail-open で既定句 (確定文言そのもの) にフォールバックする
    (AGENTS §3.3 の「1 箇所の失敗で全体を止めない」精神を config 読み込みにも適用)。
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        raw = None
    phrases = raw.get("phrases") if isinstance(raw, dict) else None
    phrases = phrases if isinstance(phrases, dict) else {}

    def _pick(key: str, default: str) -> str:
        value = phrases.get(key)
        return value if isinstance(value, str) and value.strip() else default

    return ShowPhrases(
        title_call=_pick("title_call", _DEFAULT_TITLE_CALL),
        opening=_pick("opening", _DEFAULT_OPENING_PHRASE),
        closing=_pick("closing", _DEFAULT_CLOSING_PHRASE),
    )

# editorial-policy §10 / hal-persona §3 の禁止表現 (決定的チェック分)
FORBIDDEN_PHRASES = ("中国すごい", "日本終わった", "中国製は粗悪", "以下は要約です")
REPLACEMENT_CHARACTER = "\ufffd"  # 文字化け混入。TTS が記号名を読むため台本契約違反。

_SECTION_LABELS = ("**Hook:**", "**Insight:**", "**Action:**")


class EpisodeScript(BaseModel):
    """1 エピソード分の組み立て済み台本. Discord 投稿 (T21) と永続化 (T19) の入力."""

    title: str
    generated_at: datetime
    variant: str
    headlines: list[str]
    markdown: str
    sources: list[tuple[str, str]]
    estimated_minutes: int
    notices: list[str]


def script_char_count(text: str) -> int:
    """空白 (改行含む) を除いたコードポイント数 (design-inheritance §6)."""
    return len("".join(text.split()))


def _truncate(text: str, limit: int) -> str:
    """コードポイント単位の切り詰め (バイト切り禁止, styleguide §4)."""
    return text if len(text) <= limit else text[:limit]


def build_writer_prompts(topic: JudgedTopic) -> tuple[str, str]:
    """writer LLM への (system, user) プロンプトを組み立てる.

    system は HAL 人格 + 出力契約 (design-inheritance §8 + editorial-policy §11)。
    """
    system = (
        "あなたは AI キャスター HAL。番組「華流テック通信 — HAL Daily Briefing」の"
        "台本ライター。与えられた 1 トピック分の日本語台本だけを書く。"
        "前置き・後書き・箇条書きダイジェスト・調査メモにしない。\n"
        "出力形式 (この 3 行のみ):\n"
        "**Hook:** つかみ — 何が起きたか\n"
        "**Insight:** なぜ重要か — 日本のリスナー視点での意味\n"
        "**Action:** リスナーが取れる行動 — 注目ポイント、追うべきリポジトリやイベント\n"
        "制約:\n"
        f"- 全体で {WRITER_CHAR_BUDGET} 文字以内 (空白除く) に必ず収める"
        f"。長くなる場合は説明を削って短くする (上限は {TOPIC_CHAR_LIMIT} 文字、これは厳守)\n"
        "- 中国語固有名詞はカナ表記にし、初出のみ括弧で原語併記 (例: ディープシーク (DeepSeek))\n"
        "- 記事本文の転載禁止。要約と HAL 自身の解説のみ\n"
        "- 出典 URL・Source 行を本文に入れない\n"
        "- 絵文字を使わない\n"
        "- 「中国すごい」「日本終わった」等の評価断定・政治的断定・国家や民族への一般化をしない\n"
        "- 未確認・噂レベルの情報は「これは噂レベルですが — 」と明示する\n"
        "- 落ち着いた、聞き取りやすい口調 (過度な煽り・テンション芸をしない)"
    )
    cand = topic.candidate
    rumor_note = ""
    if cand.tier >= 4:
        rumor_note = "\nこのトピックは噂レベル (Tier4)。必ず噂であることを明示する。"
    user = (
        f"トピック [tone={topic.tone.value} tier={cand.tier} category={cand.category} "
        f"corroboration={topic.corroboration_count}]\n"
        f"タイトル: {_truncate(cand.title, PROMPT_TITLE_LIMIT)}\n"
        f"概要: {_truncate(cand.summary, PROMPT_SUMMARY_LIMIT)}"
        f"{rumor_note}"
    )
    return system, user


def generate_topic_script(client: ChatClient, topic: JudgedTopic) -> str:
    """writer LLM に 1 トピック分の台本を書かせる (プレーンテキスト・profile 温度)."""
    system, user = build_writer_prompts(topic)
    response = client.chat(system=system, user=user)
    return response.content


def validate_topic_script(text: str, *, require_rumor_marker: bool = False) -> list[str]:
    """台本 1 トピック分の契約違反を列挙する (空リスト = 合格).

    違反リストは T18 (再生成 → テンプレ fallback) の判定に使う。
    """
    violations = []
    if not text.strip():
        violations.append("台本が空")
        return violations
    for label in _SECTION_LABELS:
        if label not in text:
            violations.append(f"必須セクション欠落: {label.strip('*:')}")
    count = script_char_count(text)
    if count > TOPIC_CHAR_LIMIT:
        violations.append(f"300 文字超過 (空白除く {count} 文字)")
    if "http://" in text or "https://" in text:
        violations.append("本文に URL を含めない (ソース一覧で別掲)")
    if REPLACEMENT_CHARACTER in text:
        violations.append("本文に置換文字 (�) を含めない")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            violations.append(f"禁止表現: {phrase}")
    if require_rumor_marker and RUMOR_MARKER not in text:
        violations.append("噂レベルの明示が無い (Tier4)")
    return violations


def assemble_episode(
    topics: list[tuple[JudgedTopic, str]],
    variant: str,
    generated_at: datetime,
    *,
    show_format_path: Path = DEFAULT_SHOW_FORMAT_PATH,
) -> EpisodeScript:
    """検証済みトピック台本を 1 エピソードの Markdown に組み立てる (決定的コード).

    形式は要件 §14.2 / show-format §8 の投稿項目に対応:
    タイトル・生成日時・タイトルコール・オープニング挨拶・トピック見出し・台本本文・
    ソース一覧・profile・推定尺・注意事項。挨拶フレーズは `show_format_path` の
    `phrases` から読む (T54, 既定は `config/show_format.yaml`。fail-open は
    `load_show_phrases` 参照)。
    """
    phrases = load_show_phrases(show_format_path)
    headlines = [t.candidate.title for t, _ in topics]
    sources = [(t.candidate.title, t.candidate.link) for t, _ in topics]
    notices = [
        f"噂レベルの情報を含みます: {t.candidate.title} (Tier4)"
        for t, _ in topics
        if t.candidate.tier >= 4
    ]

    lines = [
        f"# {SHOW_TITLE}",
        f"生成日時: {generated_at.strftime('%Y-%m-%d %H:%M')} / LLM profile: {variant}",
        "",
        phrases.title_call,
        phrases.opening,
        "",
    ]
    for i, (topic, body) in enumerate(topics, start=1):
        lines.append(f"## {i}. {topic.candidate.title}")
        lines.append(body)
        lines.append("")
    lines.append(phrases.closing)
    lines.append("")
    lines.append("---")
    lines.append("### ソース一覧")
    for i, (title, link) in enumerate(sources, start=1):
        lines.append(f"{i}. [{title}]({link})")
    if notices:
        lines.append("")
        lines.append("### 注意事項")
        for notice in notices:
            lines.append(f"- {notice}")
    markdown = "\n".join(lines)

    script_chars = sum(script_char_count(body) for _, body in topics)
    estimated_minutes = max(1, math.ceil(script_chars / CHARS_PER_MINUTE) + 1)

    return EpisodeScript(
        title=SHOW_TITLE,
        generated_at=generated_at,
        variant=variant,
        headlines=headlines,
        markdown=markdown,
        sources=sources,
        estimated_minutes=estimated_minutes,
        notices=notices,
    )
