"""OpenAI 互換 LLM クライアント (provider 抽象).

Sprint 1B Ticket T12。LLMProfile を受け取り chat completion を 1 回実行する。
実 model ID / endpoint の確定は T13 接続確認 (人間判断後)。本モジュールの
ユニットテストは httpx をモックし、実 API は呼ばない (IMPLEMENTATION_PLAN-1B §5)。

秘密管理: API キーは profile.api_key_env が指す環境変数から実行時に解決し、
ログ・例外メッセージにキー値を出さない (要件 §9.5)。
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel

from karyu_tech_news.llm.profile import LLMProfile, LLMProvider

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60
MAX_RETRIES = 2


class LLMError(Exception):
    """LLM 呼び出しの失敗 (キー未設定・HTTP 失敗・応答不正)."""


class LLMResponse(BaseModel):
    """chat completion 1 回分の応答. usage はコストログ (T20 llm_runs) に使う."""

    content: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


def resolve_api_key(profile: LLMProfile) -> str:
    """profile の api_key_env から実キーを解決する.

    api_key_env が空 (ollama 等、キー不要) なら空文字を返す。
    指定があるのに環境変数が未設定/空なら LLMError (環境変数名のみ出し、値は扱わない)。
    """
    if not profile.api_key_env:
        return ""
    key = os.getenv(profile.api_key_env, "")
    if not key:
        raise LLMError(
            f"API key env var not set: {profile.api_key_env} (profile={profile.label})"
        )
    return key


class LLMClient:
    """OpenAI 互換 chat completions クライアント (非ストリーミング)."""

    def __init__(self, profile: LLMProfile) -> None:
        self.profile = profile
        self._api_key = resolve_api_key(profile)

    def chat(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> LLMResponse:
        """system + user の 2 メッセージで chat completion を実行する.

        json_mode=True で response_format=json_object を要求する
        (編集判定 T15 用。台本生成はプレーンテキスト, IMPLEMENTATION_PLAN-1B §8)。
        temperature は通常 profile 値を使い、編集判定 (temp=0 固定,
        design-inheritance §4.2) のみ呼び出し側で上書きする。ただし
        profile.send_temperature=False のモデル (T64: temperature 指定不可の
        OpenAI Luna 系) では、この引数の指定有無に関わらず body から
        temperature を完全に省略する。
        """
        body: dict[str, Any] = {
            "model": self.profile.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            self.profile.token_param: self.profile.max_tokens,
            "stream": False,
        }
        if self.profile.send_temperature:
            body["temperature"] = (
                self.profile.temperature if temperature is None else temperature
            )
        if self.profile.seed is not None:
            body["seed"] = self.profile.seed
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if self.profile.provider is LLMProvider.OLLAMA:
            # reasoning モデルの思考出力を抑止 (design-inheritance §9)
            body["think"] = False

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{self.profile.base_url}/chat/completions"
        data = self._post_with_retry(url, body, headers)
        return self._parse_response(data)

    def _post_with_retry(
        self, url: str, body: dict[str, Any], headers: dict[str, str]
    ) -> Any:
        """一過性の失敗 (接続断・5xx/429) を想定し最大 MAX_RETRIES 回リトライ (要件 §9.3)."""
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = httpx.post(url, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    logger.info(
                        "LLM retry %d/%d for profile=%s: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        self.profile.label,
                        exc,
                    )
                continue
        raise LLMError(
            f"LLM request failed after {MAX_RETRIES + 1} attempts "
            f"(profile={self.profile.label}): {last_exc}"
        ) from last_exc

    def _parse_response(self, data: Any) -> LLMResponse:
        """choices[0].message.content を取り出す. 外部応答なので形を信用しない."""
        if not isinstance(data, dict):
            raise LLMError(f"LLM response is not a JSON object (profile={self.profile.label})")
        choices = data.get("choices") or []
        if not choices:
            raise LLMError(f"LLM response has no choices (profile={self.profile.label})")
        message = choices[0].get("message") or {}
        # reasoning モデルは content 空で reasoning_content / reasoning に本文を吐くことがある
        # (多数フィールドを順に試す頑健設計, design-inheritance §9。reasoning は Ollama 実測)
        content = ""
        for field in ("content", "reasoning_content", "reasoning"):
            content = str(message.get(field) or "")
            if content:
                break
        if not content:
            raise LLMError(f"LLM response has empty content (profile={self.profile.label})")
        usage = data.get("usage") or {}
        return LLMResponse(
            content=content,
            model=str(data.get("model") or self.profile.model),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
