"""llm.profile のユニットテスト (Sprint 1B Ticket T12)."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from karyu_tech_news.llm.profile import (
    DEFAULT_LLM_PROFILES_PATH,
    LLMProfile,
    LLMProfilesFile,
    LLMProvider,
    load_llm_profiles,
)


def _profile_dict(label: str = "deepseek", **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "label": label,
        "provider": "openai_compatible",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "max_tokens": 1800,
        "temperature": 0.3,
    }
    base.update(overrides)
    return base


def _profiles_file_dict() -> dict[str, object]:
    return {
        "profiles": [
            _profile_dict("deepseek"),
            _profile_dict("mimo", api_key_env="MIMO_API_KEY"),
        ],
        "ab_test": {
            "A": {"editor": "mimo", "writer": "deepseek"},
            "B": {"editor": "mimo", "writer": "mimo"},
        },
    }


# ---------- LLMProfile ----------

def test_llm_profile_minimal_valid() -> None:
    p = LLMProfile.model_validate(_profile_dict())
    assert p.label == "deepseek"
    assert p.provider is LLMProvider.OPENAI_COMPATIBLE
    assert p.notes == ""


def test_llm_profile_base_url_strips_trailing_slash() -> None:
    p = LLMProfile.model_validate(_profile_dict(base_url="https://api.deepseek.com/v1/"))
    assert p.base_url == "https://api.deepseek.com/v1"


def test_llm_profile_rejects_non_http_base_url() -> None:
    with pytest.raises(ValidationError):
        LLMProfile.model_validate(_profile_dict(base_url="ftp://api.example.com/v1"))


def test_llm_profile_rejects_bad_label_pattern() -> None:
    with pytest.raises(ValidationError):
        LLMProfile.model_validate(_profile_dict(label="Has_Underscore"))


def test_llm_profile_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        LLMProfile.model_validate(_profile_dict(provider="anthropic"))


def test_llm_profile_rejects_zero_max_tokens() -> None:
    with pytest.raises(ValidationError):
        LLMProfile.model_validate(_profile_dict(max_tokens=0))


def test_llm_profile_rejects_out_of_range_temperature() -> None:
    with pytest.raises(ValidationError):
        LLMProfile.model_validate(_profile_dict(temperature=2.5))


def test_llm_profile_allows_empty_api_key_env() -> None:
    p = LLMProfile.model_validate(
        _profile_dict("local-ollama", provider="ollama", api_key_env="")
    )
    assert p.provider is LLMProvider.OLLAMA
    assert p.api_key_env == ""


def test_llm_profile_new_fields_default_for_backward_compat() -> None:
    """token_param/send_temperature/seed 無指定時は既存プロファイルの挙動を保つ既定値 (T64)."""
    p = LLMProfile.model_validate(_profile_dict())
    assert p.token_param == "max_tokens"
    assert p.send_temperature is True
    assert p.seed is None


def test_llm_profile_accepts_max_completion_tokens_send_temperature_false_and_seed() -> None:
    p = LLMProfile.model_validate(
        _profile_dict(
            "openai-luna",
            api_key_env="OPENAI_API_KEY",
            token_param="max_completion_tokens",
            send_temperature=False,
            seed=42,
        )
    )
    assert p.token_param == "max_completion_tokens"
    assert p.send_temperature is False
    assert p.seed == 42


def test_llm_profile_rejects_unknown_token_param() -> None:
    with pytest.raises(ValidationError):
        LLMProfile.model_validate(_profile_dict(token_param="max_new_tokens"))


def test_llm_profile_extra_body_defaults_to_none_for_backward_compat() -> None:
    """extra_body 無指定時は既存プロファイルの挙動を保つ既定値 None (T65)."""
    p = LLMProfile.model_validate(_profile_dict())
    assert p.extra_body is None


def test_llm_profile_accepts_extra_body_dict() -> None:
    p = LLMProfile.model_validate(
        _profile_dict(extra_body={"reasoning_effort": "none"})
    )
    assert p.extra_body == {"reasoning_effort": "none"}


# ---------- LLMProfilesFile ----------

def test_profiles_file_valid() -> None:
    f = LLMProfilesFile.model_validate(_profiles_file_dict())
    assert [p.label for p in f.profiles] == ["deepseek", "mimo"]
    assert set(f.ab_test) == {"A", "B"}


def test_profiles_file_rejects_duplicate_labels() -> None:
    raw = _profiles_file_dict()
    raw["profiles"] = [_profile_dict("deepseek"), _profile_dict("deepseek")]
    with pytest.raises(ValidationError):
        LLMProfilesFile.model_validate(raw)


def test_profiles_file_rejects_unknown_ab_test_reference() -> None:
    raw = _profiles_file_dict()
    raw["ab_test"] = {"A": {"editor": "mimo", "writer": "no-such-profile"}}
    with pytest.raises(ValidationError):
        LLMProfilesFile.model_validate(raw)


def test_profile_by_label_returns_profile() -> None:
    f = LLMProfilesFile.model_validate(_profiles_file_dict())
    assert f.profile_by_label("mimo").api_key_env == "MIMO_API_KEY"


def test_profile_by_label_unknown_raises_value_error() -> None:
    f = LLMProfilesFile.model_validate(_profiles_file_dict())
    with pytest.raises(ValueError, match="no-such"):
        f.profile_by_label("no-such")


def test_resolve_roles_returns_editor_and_writer() -> None:
    f = LLMProfilesFile.model_validate(_profiles_file_dict())
    roles = f.resolve_roles("A")
    assert roles.editor.label == "mimo"
    assert roles.writer.label == "deepseek"


def test_resolve_roles_unknown_variant_raises_value_error() -> None:
    f = LLMProfilesFile.model_validate(_profiles_file_dict())
    with pytest.raises(ValueError, match="Z"):
        f.resolve_roles("Z")


# ---------- load_llm_profiles ----------

def test_load_llm_profiles_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_llm_profiles(Path("/nonexistent/llm_profiles.yaml"))


def test_load_real_llm_profiles_yaml() -> None:
    """実 config/llm_profiles.yaml の確定構成を固定する結合テスト."""
    f = load_llm_profiles(DEFAULT_LLM_PROFILES_PATH)
    labels = [p.label for p in f.profiles]
    assert labels == ["deepseek", "mimo", "openai-luna", "mimo-openrouter", "local-ollama"]
    assert set(f.ab_test) == {"A", "B", "C"}

    # T64 (Issue #70): A 案の editor を mimo → openai-luna へ切替 (OpenAI キャンペーン枠)
    roles = f.resolve_roles("A")
    assert roles.editor.label == "openai-luna"
    assert roles.writer.label == "deepseek"

    # openai-luna は 2026-08-02 実機スモークの互換制約を反映 (max_completion_tokens 必須 / temperature 送信不可)
    luna = f.profile_by_label("openai-luna")
    assert luna.token_param == "max_completion_tokens"
    assert luna.send_temperature is False
    assert luna.seed == 42

    # T65 (Issue #73): deepseek は reasoning 垂れ流し対策で extra_body を持つ
    deepseek = f.profile_by_label("deepseek")
    assert deepseek.extra_body == {"reasoning_effort": "none"}

    # 秘密値は環境変数名のみ保持 (実キーを YAML に書かない)
    for p in f.profiles:
        assert "sk-" not in p.api_key_env

    ollama = f.profile_by_label("local-ollama")
    assert ollama.provider is LLMProvider.OLLAMA
    assert ollama.api_key_env == ""
