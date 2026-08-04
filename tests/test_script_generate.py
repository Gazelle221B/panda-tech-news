"""script.generate のユニットテスト (Sprint 1B Ticket T17). LLM はモック."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from karyu_tech_news.edit.judge import JudgedTopic, Tone
from karyu_tech_news.edit.prescore import ScoredCandidate
from karyu_tech_news.llm.client import LLMResponse
from karyu_tech_news.script.generate import (
    TOPIC_CHAR_LIMIT,
    WRITER_CHAR_BUDGET,
    EpisodeScript,
    ShowPhrases,
    apply_date_placeholder,
    assemble_episode,
    build_writer_prompts,
    format_broadcast_date,
    generate_topic_script,
    load_show_phrases,
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


# ---------- writer char budget (T22 defect①: DeepSeek 300字超過対策) ----------

def test_writer_prompt_uses_char_budget() -> None:
    # writer プロンプトはハード上限(300)より厳しい予算を提示してマージンを取る
    assert WRITER_CHAR_BUDGET < TOPIC_CHAR_LIMIT
    system, _ = build_writer_prompts(_topic())
    assert str(WRITER_CHAR_BUDGET) in system


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
    assert str(TOPIC_CHAR_LIMIT) in system
    assert "カナ" in system
    assert "転載" in system
    assert "DeepSeek 发布新模型" in user
    assert "tone=neutral" in user


def test_writer_prompts_rumor_instruction_for_tier4() -> None:
    _, user = build_writer_prompts(_topic(tier=4))
    assert "噂" in user


def test_writer_prompts_include_ruby_instruction() -> None:
    """新出固有名詞にインライン読み注釈を付けさせる指示 (T56, Issue #52)."""
    system, _ = build_writer_prompts(_topic())
    assert "[[表記|カタカナ読み]]" in system
    assert "簡体字" in system
    assert "AI・IT" in system  # 定着済み略語には不要、の除外例


def test_writer_prompts_ruby_instruction_has_few_shot_examples() -> None:
    """deepseek-chat 不追従対策: 具体例2つとカナ表記指示との使い分けを明示 (T59, Issue #59)."""
    system, _ = build_writer_prompts(_topic())
    assert "[[零一万物|リンイーワンウー]]" in system
    assert "[[MoWorld|モワールド]]" in system
    assert "使い分け" in system


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
    assert any(str(TOPIC_CHAR_LIMIT) in v for v in violations)


def test_validate_char_limit_is_strict_at_360() -> None:
    """ラベル込みの全体で 360 文字 (空白除く) を厳密適用する境界テスト.

    元は 300 字上限だったが、2026-08-04 障害・Issue #95 (deepseek-v4-flash +
    T61 記事本文補強後は 301〜357 字の僅少超過が頻発し template 落ちしていた)
    を受けて 360 に緩和された (PR #10 Copilot 指摘の境界厳密性テスト自体は維持)。
    pad 長はラベル文字数から動的に算出し、TOPIC_CHAR_LIMIT 変更に追従させる。
    """
    base = "**Hook:** {pad}\n**Insight:** い\n**Action:** う"
    label_chars = script_char_count(base.format(pad=""))
    pad_len = TOPIC_CHAR_LIMIT - label_chars
    exactly_at_limit = base.format(pad="あ" * pad_len)
    over_by_one = base.format(pad="あ" * (pad_len + 1))
    assert script_char_count(exactly_at_limit) == TOPIC_CHAR_LIMIT
    assert validate_topic_script(exactly_at_limit) == []
    assert any(str(TOPIC_CHAR_LIMIT) in v for v in validate_topic_script(over_by_one))


def test_validate_flags_url_in_body() -> None:
    body = VALID_BODY + "\n出典: https://example.com/article"
    violations = validate_topic_script(body)
    assert any("URL" in v for v in violations)


def test_validate_flags_replacement_character() -> None:
    body = VALID_BODY.replace("発表しました", "返り�きました")
    violations = validate_topic_script(body)
    assert any("置換文字" in v for v in violations)


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
    # 確定タイトルコール/オープニング/クロージング (hal-persona §4, Issue #39, T54)
    assert "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。" in episode.markdown
    assert "キャスターのHALです。支度の手を止めずに" in episode.markdown
    assert "今日の華流テック通信は以上です。それでは皆さん、良い一日を。HALでした。" in episode.markdown


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


# ---------- load_show_phrases (T54, Issue #39 固定句の YAML 配線) ----------


def test_load_show_phrases_reads_real_show_format_yaml() -> None:
    """実 config/show_format.yaml から確定フレーズ 3 種を読み込む.

    opening は `{date}` プレースホルダを含んだ生の状態で返る (T63, Issue #69: 日付置換は
    `load_show_phrases` ではなく `apply_date_placeholder` の責務)。
    """
    phrases = load_show_phrases()
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"
    assert phrases.opening.startswith("{date}。キャスターのHALです。")
    assert phrases.closing.startswith("今日の華流テック通信は以上です。")


def test_load_show_phrases_reads_custom_path(tmp_path: Path) -> None:
    """任意の show_format_path (`phrases` セクション) を正しく読む."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text(
        "phrases:\n"
        '  title_call: "カスタムタイトルコール"\n'
        '  opening: "カスタムオープニング"\n'
        '  closing: "カスタムクロージング"\n',
        encoding="utf-8",
    )
    phrases = load_show_phrases(custom)
    assert phrases == ("カスタムタイトルコール", "カスタムオープニング", "カスタムクロージング")


def test_load_show_phrases_missing_file_fails_open_to_defaults(tmp_path: Path) -> None:
    """ファイルが存在しない場合、確定フレーズの既定値へ fail-open する (番組を止めない)."""
    phrases = load_show_phrases(tmp_path / "nope.yaml")
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"
    assert phrases.opening.startswith("キャスターのHALです。")
    assert phrases.closing.startswith("今日の華流テック通信は以上です。")


def test_load_show_phrases_missing_phrases_section_fails_open(tmp_path: Path) -> None:
    """`phrases` セクション自体が無い YAML でも fail-open で既定値になる."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text("delivery:\n  cadence: weekdays\n", encoding="utf-8")
    phrases = load_show_phrases(custom)
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"


def test_load_show_phrases_partial_fields_fall_back_individually(tmp_path: Path) -> None:
    """個別フィールドが欠落していても、そのフィールドだけ既定値にフォールバックする."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text(
        'phrases:\n  opening: "カスタムオープニングのみ"\n',
        encoding="utf-8",
    )
    phrases = load_show_phrases(custom)
    assert phrases.opening == "カスタムオープニングのみ"
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"
    assert phrases.closing.startswith("今日の華流テック通信は以上です。")


def test_load_show_phrases_broken_yaml_fails_open(tmp_path: Path) -> None:
    """YAML パース不能でも例外を投げず既定値へ fail-open する."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text("phrases: [unterminated", encoding="utf-8")
    phrases = load_show_phrases(custom)
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"


def test_load_show_phrases_non_utf8_file_fails_open(tmp_path: Path) -> None:
    """非 UTF-8 破損ファイル (UnicodeDecodeError) でも例外を投げず既定値へ fail-open する
    (GrokBuild レビュー Low: OSError の派生ではないため個別捕捉が必要だった)."""
    custom = tmp_path / "show_format.yaml"
    custom.write_bytes(b"phrases:\n  opening: \xff\xfe\x00broken")
    phrases = load_show_phrases(custom)
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"
    assert phrases.opening.startswith("キャスターのHALです。")
    assert phrases.closing.startswith("今日の華流テック通信は以上です。")


def test_load_show_phrases_non_string_field_falls_back_to_default(tmp_path: Path) -> None:
    """フィールドの型が str でない (例: opening: 123) 場合も既定値へフォールバックする
    (GrokBuild レビュー Low: fail-open 契約の型不正ケースを固定するテスト)."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text(
        "phrases:\n"
        "  title_call: 42\n"
        "  opening: 123\n"
        '  closing: "テスト用クロージングのみ str"\n',
        encoding="utf-8",
    )
    phrases = load_show_phrases(custom)
    assert phrases.title_call == "華流テック通信、HAL Daily Briefing — 中華圏テックの今を、5分で。"
    assert phrases.opening.startswith("キャスターのHALです。")
    assert phrases.closing == "テスト用クロージングのみ str"  # str 型のフィールドは正常に反映される


def test_assemble_episode_respects_custom_show_format_path(tmp_path: Path) -> None:
    """assemble_episode の show_format_path 経由で固定句が差し替わる (ハードコードではない証明)."""
    custom = tmp_path / "show_format.yaml"
    custom.write_text(
        "phrases:\n"
        '  title_call: "テスト用タイトルコール"\n'
        '  opening: "テスト用オープニング"\n'
        '  closing: "テスト用クロージング"\n',
        encoding="utf-8",
    )
    topics = [(_topic(1, title="話題A"), VALID_BODY)]
    episode = assemble_episode(topics, variant="A", generated_at=NOW, show_format_path=custom)
    assert "テスト用タイトルコール" in episode.markdown
    assert "テスト用オープニング" in episode.markdown
    assert "テスト用クロージング" in episode.markdown


# ---------- format_broadcast_date (T63, Issue #69: イントロへの当日日付組み込み) ----------


def test_format_broadcast_date_no_zero_pad_two_digit_month_day() -> None:
    """月日はゼロ埋めしない (Irodori が自然に読める表記)."""
    dt = datetime(2026, 12, 25, 7, 0, tzinfo=UTC)  # JST 2026-12-25 16:00, 金曜日
    assert format_broadcast_date(dt) == "12月25日、金曜日"


def test_format_broadcast_date_single_digit_month_and_day() -> None:
    dt = datetime(2026, 3, 5, 7, 0, tzinfo=UTC)  # JST 2026-03-05 16:00, 木曜日
    assert format_broadcast_date(dt) == "3月5日、木曜日"


def test_format_broadcast_date_omits_year() -> None:
    """年は要件外 (Issue #69 仕様: 月日+曜日のみ)."""
    assert "2026" not in format_broadcast_date(NOW)


def test_format_broadcast_date_naive_datetime_treated_as_utc() -> None:
    """tzinfo 無しの naive datetime は UTC とみなして JST へ変換する
    (deliver/discord.py::format_summary と同じ防御的方針)."""
    naive = datetime(2026, 6, 10, 7, 0)
    aware = datetime(2026, 6, 10, 7, 0, tzinfo=UTC)
    assert format_broadcast_date(naive) == format_broadcast_date(aware) == "6月10日、水曜日"


def test_format_broadcast_date_utc_to_jst_day_boundary() -> None:
    """UTC 15:00 (= JST 0:00) を跨ぐと日付が繰り上がる境界を確認する."""
    before = datetime(2026, 8, 1, 14, 59, tzinfo=UTC)
    after = datetime(2026, 8, 1, 15, 0, tzinfo=UTC)
    assert format_broadcast_date(before) == "8月1日、土曜日"
    assert format_broadcast_date(after) == "8月2日、日曜日"


def test_format_broadcast_date_all_weekdays_in_japanese() -> None:
    """月〜日、全曜日が正しい日本語表記 (「○曜日」) になることを確認する."""
    base = datetime(2026, 6, 7, 20, 0, tzinfo=UTC)  # JST 2026-06-08 05:00, 月曜日始まり
    expected_weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    for i, weekday_ja in enumerate(expected_weekdays):
        dt = base + timedelta(days=i)
        assert format_broadcast_date(dt).endswith(f"、{weekday_ja}曜日")


# ---------- apply_date_placeholder (T63, Issue #69: {date} 置換の fail-open 契約) ----------


def test_apply_date_placeholder_substitutes_in_all_phrase_fields() -> None:
    phrases = ShowPhrases(
        title_call="タイトル{date}コール",
        opening="{date}。オープニング",
        closing="クロージング{date}",
    )
    result = apply_date_placeholder(phrases, "8月2日、日曜日")
    assert result == ShowPhrases(
        title_call="タイトル8月2日、日曜日コール",
        opening="8月2日、日曜日。オープニング",
        closing="クロージング8月2日、日曜日",
    )


def test_apply_date_placeholder_passes_through_when_no_placeholder() -> None:
    """プレースホルダを含まない旧フレーズは無変化でそのまま通す (fail-open, str.replace は
    対象が無ければ何もしない)."""
    phrases = ShowPhrases(
        title_call="旧タイトルコール",
        opening="旧オープニング",
        closing="旧クロージング",
    )
    assert apply_date_placeholder(phrases, "8月2日、日曜日") == phrases


# ---------- assemble_episode への日付統合 (T63, Issue #69) ----------


def test_assemble_episode_injects_broadcast_date_into_markdown() -> None:
    """draft 実行時刻 (generated_at, JST 変換) の当日日付がイントロに組み込まれる."""
    topics = [(_topic(1, title="話題A"), VALID_BODY)]
    episode = assemble_episode(topics, variant="A", generated_at=NOW)
    assert format_broadcast_date(NOW) in episode.markdown
    assert "6月10日、水曜日。キャスターのHALです。" in episode.markdown


def test_assemble_episode_date_tracks_generated_at_not_hardcoded() -> None:
    """日付は generated_at 由来 (固定文言のハードコードではない)."""
    topics = [(_topic(1, title="話題A"), VALID_BODY)]
    other_now = datetime(2026, 12, 25, 7, 0, tzinfo=UTC)
    episode = assemble_episode(topics, variant="A", generated_at=other_now)
    assert "12月25日、金曜日" in episode.markdown
    assert "6月10日、水曜日" not in episode.markdown
