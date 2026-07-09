"""tts.coverage のユニットテスト (T46, 読み辞書カバレッジ観測).

`prepare_tts_text()` 適用前後の diff から残存トークンを検出する観測専用モジュール。
辞書自動追記・自動翻字は行わない (観測結果を検証するのみ)。
"""
from __future__ import annotations

from karyu_tech_news.tts.coverage import analyze_coverage, format_coverage_summary


def test_detects_residual_ascii_tokens() -> None:
    # 辞書に無い ASCII 語 (UnknownVendor) は変換されず残存する。
    text = "UnknownVendor が新製品を発表した。"
    report = analyze_coverage(text, {})
    assert report.ascii_residual_count >= 1
    assert any(t.token == "UnknownVendor" for t in report.ascii_top_tokens)


def test_clean_text_has_zero_residual() -> None:
    # 辞書ヒットする既知語のみのテキストは残存 0 件になる。
    text = "OpenAI が新製品を発表した。"
    report = analyze_coverage(text, {"OpenAI": "オープンエーアイ"})
    assert report.ascii_residual_count == 0
    assert report.ascii_top_tokens == ()


def test_clean_japanese_text_has_zero_candidates() -> None:
    # ASCII も簡体字シグナルも含まない日本語文は候補語 0 件、ヒット率 None。
    text = "本日は晴天なり、話題をお届けします。"
    report = analyze_coverage(text, {})
    assert report.ascii_residual_count == 0
    assert report.cjk_residual_count == 0
    assert report.candidate_count == 0
    assert report.dict_hit_rate is None


def test_dict_hit_rate_reflects_conversion_ratio() -> None:
    # 候補2語のうち1語だけ辞書ヒットする場合、ヒット率は0.5になる。
    text = "OpenAI と UnknownVendor が提携した。"
    report = analyze_coverage(text, {"OpenAI": "オープンエーアイ"})
    assert report.candidate_count == 2
    assert report.converted_count == 1
    assert report.dict_hit_rate == 0.5


def test_dict_hit_rate_full_coverage_is_one() -> None:
    text = "OpenAI と Google が提携した。"
    report = analyze_coverage(
        text, {"OpenAI": "オープンエーアイ", "Google": "グーグル"}
    )
    assert report.candidate_count == 2
    assert report.converted_count == 2
    assert report.dict_hit_rate == 1.0


def test_detects_residual_simplified_chinese_token() -> None:
    # 「」に囲まれていない簡体字トークンは sanitize_chinese_title_quotes の対象外
    # (quote 検出のみ) のため素通りし、observability 側で検出できる必要がある。
    text = "开发进度は这个软件の竞争力を左右する。"
    report = analyze_coverage(text, {})
    assert report.cjk_residual_count >= 1


def test_top_n_limits_returned_tokens() -> None:
    text = " ".join(f"VendorAlpha{i} VendorBeta{i}" for i in range(5))
    report = analyze_coverage(text, {}, top_n=2)
    assert len(report.ascii_top_tokens) <= 2


def test_format_coverage_summary_includes_hit_rate_and_counts() -> None:
    text = "UnknownVendor が発表した。"
    report = analyze_coverage(text, {})
    summary = format_coverage_summary(report)
    assert "読み辞書カバレッジ" in summary
    assert "残存ASCII" in summary
    assert "残存CJK" in summary


def test_format_coverage_summary_handles_no_candidates() -> None:
    report = analyze_coverage("こんにちは。", {})
    summary = format_coverage_summary(report)
    assert "N/A" in summary
