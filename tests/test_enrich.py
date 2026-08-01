"""edit.enrich のユニットテスト (T61, Issue #61 薄記事の本文フェッチ補強)."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from karyu_tech_news.edit.enrich import ENRICHED_SUMMARY_CHARS, enrich_thin_candidates
from karyu_tech_news.edit.prescore import THIN_SUMMARY_CHARS, THIN_SUMMARY_PENALTY, ScoredCandidate

NOW = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)

THICK_SUMMARY = "十分な長さのダミー概要文をここに用意しておく必要がある四十字以上のテキストです。"
assert len(THICK_SUMMARY) >= THIN_SUMMARY_CHARS


def _candidate(
    item_id: int,
    *,
    summary: str = "",
    prescore: int = 50,
    link: str = "https://example.com/a",
) -> ScoredCandidate:
    return ScoredCandidate(
        item_id=item_id,
        source_id="src-a",
        title=f"话题{item_id}",
        summary=summary,
        link=link,
        published_at=None,
        fetched_at=NOW,
        tier=1,
        category="AI",
        canonical_url_hash="",
        prescore=prescore,
    )


def test_enrich_replaces_thin_candidate_and_restores_penalty() -> None:
    candidate = _candidate(1, summary="薄い", prescore=15)  # THIN_SUMMARY_PENALTY 込みの想定
    article_text = "本文" * 200  # 400字、600字未満なのでそのまま全部使われる

    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value=article_text) as mock_fetch:
        result = enrich_thin_candidates([candidate])

    mock_fetch.assert_called_once_with(candidate.link)
    assert len(result) == 1
    assert result[0].summary == article_text
    assert result[0].prescore == candidate.prescore - THIN_SUMMARY_PENALTY
    assert result[0].item_id == candidate.item_id


def test_enrich_truncates_to_600_chars_by_codepoint() -> None:
    candidate = _candidate(1, summary="")
    # 中華圏記事を想定した多バイト文字 (UTF-8 では 1 字 3 バイト) を 700 字用意し、
    # バイト単位切り詰めではなく Python str (コードポイント) 単位で 600 字になることを確認。
    article_text = "中" * 700

    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value=article_text):
        result = enrich_thin_candidates([candidate])

    assert len(result[0].summary) == ENRICHED_SUMMARY_CHARS
    assert result[0].summary == "中" * ENRICHED_SUMMARY_CHARS


def test_enrich_thick_candidate_not_fetched() -> None:
    candidate = _candidate(1, summary=THICK_SUMMARY, prescore=40)

    with patch("karyu_tech_news.edit.enrich.fetch_article_text") as mock_fetch:
        result = enrich_thin_candidates([candidate])

    mock_fetch.assert_not_called()
    assert result == [candidate]


def test_enrich_outside_top_k_not_fetched() -> None:
    candidates = [
        _candidate(1, summary=""),
        _candidate(2, summary=""),
        _candidate(3, summary=""),  # top_k=2 の範囲外
    ]

    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value=None) as mock_fetch:
        result = enrich_thin_candidates(candidates, top_k=2, max_fetch=5)

    assert mock_fetch.call_count == 2
    fetched_links = {call.args[0] for call in mock_fetch.call_args_list}
    assert fetched_links == {candidates[0].link, candidates[1].link}
    assert result[2] == candidates[2]  # 範囲外はフェッチされず元のまま


def test_enrich_respects_max_fetch_limit() -> None:
    candidates = [_candidate(i, summary="", link=f"https://example.com/{i}") for i in range(1, 5)]

    with patch(
        "karyu_tech_news.edit.enrich.fetch_article_text", return_value="本文" * 100
    ) as mock_fetch:
        result = enrich_thin_candidates(candidates, top_k=10, max_fetch=2)

    assert mock_fetch.call_count == 2
    # 先頭2件だけ置換され、残り2件は元のまま (fetch すら試みない)
    assert result[0].summary == "本文" * 100
    assert result[1].summary == "本文" * 100
    assert result[2] == candidates[2]
    assert result[3] == candidates[3]


def test_enrich_fetch_failure_keeps_original_candidate() -> None:
    candidate = _candidate(1, summary="", prescore=10)

    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value=None) as mock_fetch:
        result = enrich_thin_candidates([candidate])

    mock_fetch.assert_called_once()
    assert result == [candidate]


def test_enrich_fetch_too_short_keeps_original_candidate() -> None:
    candidate = _candidate(1, summary="", prescore=10)

    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value="短い本文"):
        result = enrich_thin_candidates([candidate])

    assert result == [candidate]


def test_enrich_does_not_mutate_original_list() -> None:
    candidate = _candidate(1, summary="", prescore=10)
    original_summary = candidate.summary
    original_prescore = candidate.prescore
    candidates = [candidate]

    with patch("karyu_tech_news.edit.enrich.fetch_article_text", return_value="本文" * 100):
        result = enrich_thin_candidates(candidates)

    # 元のリスト・元の candidate インスタンスは変更されていない
    assert candidates[0] is candidate
    assert candidate.summary == original_summary
    assert candidate.prescore == original_prescore
    # 返り値は新しいオブジェクト
    assert result[0] is not candidate
    assert result[0].summary != original_summary


def test_enrich_empty_candidates_returns_empty() -> None:
    with patch("karyu_tech_news.edit.enrich.fetch_article_text") as mock_fetch:
        result = enrich_thin_candidates([])

    mock_fetch.assert_not_called()
    assert result == []
