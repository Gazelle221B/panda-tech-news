"""deliver.discord の台本投稿 (post_markdown) のユニットテスト (Ticket T21)."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest

from karyu_tech_news.deliver.discord import (
    DISCORD_CONTENT_LIMIT,
    _split_for_discord,
    post_markdown,
    post_summary,
)

# ---------- _split_for_discord ----------

def test_split_short_content_single_chunk() -> None:
    assert _split_for_discord("こんにちは\n世界") == ["こんにちは\n世界"]

def test_split_long_content_multiple_chunks() -> None:
    lines = "\n".join(f"行{i} " + "あ" * 100 for i in range(40))
    chunks = _split_for_discord(lines)
    assert len(chunks) > 1
    assert all(len(c) <= DISCORD_CONTENT_LIMIT for c in chunks)
    # 改行以外の内容が失われない
    assert "".join(c.replace("\n", "") for c in chunks) == lines.replace("\n", "")


def test_split_single_overlong_line_is_hard_split() -> None:
    content = "あ" * (DISCORD_CONTENT_LIMIT * 2 + 10)
    chunks = _split_for_discord(content)
    assert all(len(c) <= DISCORD_CONTENT_LIMIT for c in chunks)
    assert "".join(chunks) == content


# ---------- post_markdown ----------

def _ok_resp() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    return resp


def test_post_markdown_single_post() -> None:
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post", return_value=_ok_resp()
    ) as mock_post:
        assert post_markdown("https://discord.test/webhook", "# 台本") is True
    assert mock_post.call_count == 1


def test_post_markdown_chunks_long_content() -> None:
    content = "\n".join("あ" * 100 for _ in range(40))
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post", return_value=_ok_resp()
    ) as mock_post:
        assert post_markdown("https://discord.test/webhook", content) is True
    assert mock_post.call_count >= 2


def test_post_markdown_returns_false_on_failure() -> None:
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post",
        side_effect=Exception("boom"),
    ):
        assert post_markdown("https://discord.test/webhook", "# 台本") is False


def test_post_markdown_empty_url_returns_false() -> None:
    assert post_markdown("", "# 台本") is False


def test_post_markdown_empty_content_returns_false() -> None:
    assert post_markdown("https://discord.test/webhook", "   ") is False


# ---------- 秘密非漏洩 (要件 §9.5, Codex レビュー 2026-06-12 Critical 対応) ----------

WEBHOOK_WITH_TOKEN = "https://discord.com/api/webhooks/123456/secret-token-abc"


def _http_status_error_resp(status_code: int) -> MagicMock:
    """raise_for_status が URL 込みメッセージの HTTPStatusError を投げる応答."""
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"Server error '{status_code}' for url '{WEBHOOK_WITH_TOKEN}'",
        request=MagicMock(),
        response=MagicMock(status_code=status_code),
    )
    return resp


def test_post_summary_http_error_log_has_no_webhook_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post",
        return_value=_http_status_error_resp(500),
    ), caplog.at_level(logging.ERROR):
        assert post_summary(WEBHOOK_WITH_TOKEN, "x") is False

    assert "secret-token-abc" not in caplog.text
    assert "discord.com/api/webhooks" not in caplog.text
    assert "500" in caplog.text  # status code は記録される


def test_post_summary_connect_error_log_has_no_webhook_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post",
        side_effect=httpx.ConnectError(f"failed for {WEBHOOK_WITH_TOKEN}"),
    ), caplog.at_level(logging.ERROR):
        assert post_summary(WEBHOOK_WITH_TOKEN, "x") is False

    assert "secret-token-abc" not in caplog.text
    assert "ConnectError" in caplog.text  # 例外型名は記録される


def test_post_markdown_http_error_log_has_no_webhook_token(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch(
        "karyu_tech_news.deliver.discord.httpx.post",
        return_value=_http_status_error_resp(429),
    ), caplog.at_level(logging.ERROR):
        assert post_markdown(WEBHOOK_WITH_TOKEN, "# 台本") is False

    assert "secret-token-abc" not in caplog.text
    assert "discord.com/api/webhooks" not in caplog.text
