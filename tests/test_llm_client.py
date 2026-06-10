"""llm.client のユニットテスト (Sprint 1B Ticket T12). 実 API は呼ばずすべてモック."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from karyu_tech_news.llm.client import (
    MAX_RETRIES,
    TIMEOUT_SECONDS,
    LLMClient,
    LLMError,
    LLMResponse,
    resolve_api_key,
)
from karyu_tech_news.llm.profile import LLMProfile


def _profile(**overrides: object) -> LLMProfile:
    base: dict[str, object] = {
        "label": "deepseek",
        "provider": "openai_compatible",
        "api_key_env": "TEST_LLM_API_KEY",
        "base_url": "https://api.example.com/v1",
        "model": "deepseek-chat",
        "max_tokens": 1800,
        "temperature": 0.3,
    }
    base.update(overrides)
    return LLMProfile.model_validate(base)


def _ollama_profile() -> LLMProfile:
    return _profile(
        label="local-ollama",
        provider="ollama",
        api_key_env="",
        base_url="http://localhost:11434/v1",
        model="qwen3",
    )


def _chat_response_json(content: str = "こんにちは") -> dict[str, Any]:
    return {
        "model": "deepseek-chat",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _mock_resp(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


# ---------- resolve_api_key ----------

def test_resolve_api_key_empty_env_name_returns_empty() -> None:
    assert resolve_api_key(_ollama_profile()) == ""


def test_resolve_api_key_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    assert resolve_api_key(_profile()) == "sk-test-123"


def test_resolve_api_key_missing_env_raises_without_leaking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "")
    with pytest.raises(LLMError) as exc_info:
        resolve_api_key(_profile())
    # 環境変数名は出すが、キー値は存在しないので漏れようがないことを明示
    assert "TEST_LLM_API_KEY" in str(exc_info.value)


# ---------- LLMClient.chat ----------

def test_chat_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())
    mock_resp = _mock_resp(_chat_response_json())

    with patch(
        "karyu_tech_news.llm.client.httpx.post", return_value=mock_resp
    ) as mock_post:
        res = client.chat(system="あなたは編集者", user="判定して")

    assert isinstance(res, LLMResponse)
    assert res.content == "こんにちは"
    assert res.model == "deepseek-chat"
    assert res.prompt_tokens == 10
    assert res.completion_tokens == 5

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.example.com/v1/chat/completions"
    assert kwargs["timeout"] == TIMEOUT_SECONDS
    body = kwargs["json"]
    assert body["model"] == "deepseek-chat"
    assert body["max_tokens"] == 1800
    assert body["temperature"] == 0.3
    assert body["messages"][0] == {"role": "system", "content": "あなたは編集者"}
    assert body["messages"][1] == {"role": "user", "content": "判定して"}
    assert "response_format" not in body
    assert "think" not in body
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test-123"


def test_chat_json_mode_sets_response_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())
    mock_resp = _mock_resp(_chat_response_json('{"topics": []}'))

    with patch(
        "karyu_tech_news.llm.client.httpx.post", return_value=mock_resp
    ) as mock_post:
        client.chat(system="s", user="u", json_mode=True)

    body = mock_post.call_args.kwargs["json"]
    assert body["response_format"] == {"type": "json_object"}


def test_chat_ollama_forces_think_false_and_no_auth_header() -> None:
    client = LLMClient(_ollama_profile())
    mock_resp = _mock_resp(_chat_response_json())

    with patch(
        "karyu_tech_news.llm.client.httpx.post", return_value=mock_resp
    ) as mock_post:
        client.chat(system="s", user="u")

    body = mock_post.call_args.kwargs["json"]
    assert body["think"] is False
    assert "Authorization" not in mock_post.call_args.kwargs["headers"]


def test_chat_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())
    mock_resp = _mock_resp(_chat_response_json())

    with patch(
        "karyu_tech_news.llm.client.httpx.post",
        side_effect=[httpx.ConnectError("boom"), mock_resp],
    ) as mock_post:
        res = client.chat(system="s", user="u")

    assert res.content == "こんにちは"
    assert mock_post.call_count == 2


def test_chat_fails_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())

    with patch(
        "karyu_tech_news.llm.client.httpx.post",
        side_effect=httpx.ConnectError("boom"),
    ) as mock_post, pytest.raises(LLMError):
        client.chat(system="s", user="u")

    assert mock_post.call_count == MAX_RETRIES + 1


def test_chat_error_message_does_not_leak_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-secret-value")
    client = LLMClient(_profile())

    with patch(
        "karyu_tech_news.llm.client.httpx.post",
        side_effect=httpx.ConnectError("boom"),
    ), pytest.raises(LLMError) as exc_info:
        client.chat(system="s", user="u")

    assert "sk-secret-value" not in str(exc_info.value)


def test_chat_empty_content_falls_back_to_reasoning_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reasoning モデルは content 空で reasoning_content に本文を吐くことがある."""
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())
    payload: dict[str, Any] = {
        "choices": [
            {"message": {"role": "assistant", "content": "", "reasoning_content": "本文"}}
        ],
    }

    with patch(
        "karyu_tech_news.llm.client.httpx.post", return_value=_mock_resp(payload)
    ):
        res = client.chat(system="s", user="u")

    assert res.content == "本文"
    # usage 欠落時は 0 で埋める
    assert res.prompt_tokens == 0


def test_chat_no_choices_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())

    with patch(
        "karyu_tech_news.llm.client.httpx.post",
        return_value=_mock_resp({"choices": []}),
    ), pytest.raises(LLMError):
        client.chat(system="s", user="u")


def test_chat_empty_content_everywhere_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())
    payload: dict[str, Any] = {"choices": [{"message": {"content": ""}}]}

    with patch(
        "karyu_tech_news.llm.client.httpx.post", return_value=_mock_resp(payload)
    ), pytest.raises(LLMError):
        client.chat(system="s", user="u")


def test_chat_http_status_error_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "sk-test-123")
    client = LLMClient(_profile())
    err_resp = MagicMock()
    err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=MagicMock(), response=MagicMock()
    )

    with patch(
        "karyu_tech_news.llm.client.httpx.post", return_value=err_resp
    ) as mock_post, pytest.raises(LLMError):
        client.chat(system="s", user="u")

    # HTTP エラーもリトライ対象 (一過性の 5xx/429 を想定)
    assert mock_post.call_count == MAX_RETRIES + 1
