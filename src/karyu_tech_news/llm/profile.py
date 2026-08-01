"""LLM profile 定義 YAML のスキーマと A/B/C 役割解決.

Sprint 1B Ticket T12。config/llm_profiles.yaml をロードし、
editor (編集判定) / writer (台本生成) の割り当てを設定だけで切替する
(ADR-0005, design-inheritance §2)。実キーは YAML に置かず、
api_key_env が指す環境変数から実行時に解決する (llm/client.py)。
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from karyu_tech_news.config import PROJECT_ROOT


class LLMProvider(StrEnum):
    """LLM プロバイダ種別.

    - openai_compatible: OpenAI 互換 API (DeepSeek / MiMo / OpenRouter)
    - ollama: ローカル Ollama (think=false を強制, design-inheritance §9)
    """

    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"


class LLMProfile(BaseModel):
    """個別 LLM profile の定義."""

    label: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*$")]
    provider: LLMProvider
    api_key_env: str = ""
    base_url: Annotated[str, Field(min_length=1)]
    model: Annotated[str, Field(min_length=1)]
    max_tokens: Annotated[int, Field(gt=0)]
    temperature: Annotated[float, Field(ge=0.0, le=2.0)]
    token_param: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    send_temperature: bool = True
    seed: int | None = None
    notes: str = ""

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """http(s) で始まることを確認し、末尾スラッシュを除去.

        client.py が `{base_url}/chat/completions` を組み立てるため正規化しておく。
        """
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"base_url must start with http:// or https://, got: {v!r}")
        return v


class RolePair(BaseModel):
    """A/B/C 検証 1 案あたりの editor/writer 割り当て (profile label で参照)."""

    editor: str
    writer: str


class ResolvedRoles(NamedTuple):
    """resolve_roles の返り値 (label を実 profile に解決済み)."""

    editor: LLMProfile
    writer: LLMProfile


class LLMProfilesFile(BaseModel):
    """llm_profiles.yaml のトップレベルスキーマ."""

    profiles: list[LLMProfile]
    ab_test: dict[str, RolePair]

    @field_validator("profiles")
    @classmethod
    def validate_unique_labels(cls, v: list[LLMProfile]) -> list[LLMProfile]:
        """label の重複を禁止."""
        seen: set[str] = set()
        for profile in v:
            if profile.label in seen:
                raise ValueError(f"Duplicate profile label: {profile.label!r}")
            seen.add(profile.label)
        return v

    @model_validator(mode="after")
    def validate_ab_test_references(self) -> LLMProfilesFile:
        """ab_test の editor/writer が実在する profile label を指すことを保証."""
        labels = {p.label for p in self.profiles}
        for variant, pair in self.ab_test.items():
            for role, label in (("editor", pair.editor), ("writer", pair.writer)):
                if label not in labels:
                    raise ValueError(
                        f"ab_test[{variant!r}].{role} references unknown profile: {label!r}"
                    )
        return self

    def profile_by_label(self, label: str) -> LLMProfile:
        """label で profile を引く. 未知の label は ValueError."""
        for profile in self.profiles:
            if profile.label == label:
                return profile
        available = [p.label for p in self.profiles]
        raise ValueError(f"Unknown profile label: {label!r} (available: {available})")

    def resolve_roles(self, variant: str) -> ResolvedRoles:
        """A/B/C 案を editor/writer の実 profile に解決する (ADR-0005)."""
        if variant not in self.ab_test:
            raise ValueError(
                f"Unknown ab_test variant: {variant!r} (available: {sorted(self.ab_test)})"
            )
        pair = self.ab_test[variant]
        return ResolvedRoles(
            editor=self.profile_by_label(pair.editor),
            writer=self.profile_by_label(pair.writer),
        )


def load_llm_profiles(path: Path) -> LLMProfilesFile:
    """llm_profiles.yaml をロードして Pydantic でバリデーションする.

    Raises:
        FileNotFoundError: ファイルが存在しない
        yaml.YAMLError: YAML パースエラー
        pydantic.ValidationError: スキーマバリデーションエラー
    """
    if not path.exists():
        raise FileNotFoundError(f"LLM profiles file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return LLMProfilesFile.model_validate(raw)


DEFAULT_LLM_PROFILES_PATH = PROJECT_ROOT / "config" / "llm_profiles.yaml"
