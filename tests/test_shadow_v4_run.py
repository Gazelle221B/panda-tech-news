"""scripts/shadow_v4_run.py のユニットテスト (T68, Issue #91).

文セット構築 (辞書適用・分割・マージ・回帰セット読込) とメトリクス計算 (Kana-CER 分離
集計・幻話疑い判定) を中心に検証する (Issue #91 のテスト方針)。加えて、実サーバを使わず
fake client/backend で完結できる範囲 (health チェック・レポート/history I/O・
Issue コメント整形・process_sentence の fail-open 分岐) も unit test で固定する。
ランナー全体のオーケストレーション (`run_shadow`/`main`, サーバ起動・停止の実プロセス
管理) は実サーバ依存のため対象外 (Issue #91 に明記)。

`scripts/` はパッケージ化されていないため、importlib でファイルパスから動的 import する
(generate_bgm.py のテストと同じ流儀)。Python 3.12 の `dataclasses(slots=True)` は
`sys.modules[cls.__module__]` の存在を要求するため、`exec_module` 前に `sys.modules` へ
登録する (generate_bgm.py には slots dataclass が無いため不要だったが、本モジュールの
`SentenceItem` 等は `slots=True` を使うため必須)。
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import wave
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

import httpx
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _ROOT / "scripts" / "shadow_v4_run.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("shadow_v4_run", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # slots dataclass の KW_ONLY 解決に必須 (Python 3.12)
    spec.loader.exec_module(module)
    return module


shadow = _load_module()


def _wav_bytes(n_frames: int = 10, sample_rate: int = 48000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ---------- build_daily_draft_sentences ----------


def test_build_daily_draft_sentences_splits_by_topic_heading() -> None:
    markdown = "## 1. トピックA\n本文Aです。\n\n## 2. トピックB\n本文Bです。"
    items = shadow.build_daily_draft_sentences(markdown, {}, max_chars=2000, min_sentence_chars=0)
    assert {item.bucket for item in items} == {"topic-1", "topic-2"}
    assert all(item.layer == "daily_draft" for item in items)
    texts = [item.text for item in items]
    assert "本文Aです。" in texts
    assert "本文Bです。" in texts


def test_build_daily_draft_sentences_merge_respects_topic_boundary() -> None:
    markdown = "## 1. A\nどうも。\n\n## 2. B\nこんにちは。"
    items = shadow.build_daily_draft_sentences(
        markdown, {}, max_chars=2000, min_sentence_chars=20
    )
    assert {item.bucket for item in items} == {"topic-1", "topic-2"}
    for item in items:
        if item.bucket == "topic-1":
            assert "こんにちは" not in item.text
        if item.bucket == "topic-2":
            assert "どうも" not in item.text


def test_build_daily_draft_sentences_merges_short_sentences_within_topic() -> None:
    markdown = "## 1. A\nどうも。こんにちは。今日は天気がとても良いですね。"
    unmerged = shadow.build_daily_draft_sentences(
        markdown, {}, max_chars=2000, min_sentence_chars=0
    )
    merged = shadow.build_daily_draft_sentences(
        markdown, {}, max_chars=2000, min_sentence_chars=5
    )
    assert len(merged) < len(unmerged)


def test_build_daily_draft_sentences_applies_reading_dict() -> None:
    markdown = "## 1. A\n百度が発表しました。"
    items = shadow.build_daily_draft_sentences(
        markdown, {"百度": "バイドゥ"}, max_chars=2000, min_sentence_chars=0
    )
    assert any("バイドゥ" in item.text for item in items)
    assert not any("百度" in item.text for item in items)


def test_build_daily_draft_sentences_source_id_is_traceable() -> None:
    markdown = "## 1. A\nどうも。こんにちは。"
    items = shadow.build_daily_draft_sentences(markdown, {}, max_chars=2000, min_sentence_chars=0)
    assert items[0].source_id == "daily_draft:topic-1:s1"
    assert items[1].source_id == "daily_draft:topic-1:s2"


# ---------- load_regression_sentence_set ----------


def test_load_regression_sentence_set_loads_fixture_counts() -> None:
    items = shadow.load_regression_sentence_set(
        shadow.DEFAULT_REGRESSION_SENTENCES_PATH, {}, max_chars=2000
    )
    known = [i for i in items if i.layer == "known_failure"]
    stratified = [i for i in items if i.layer == "stratified"]
    assert len(known) == 10
    assert len(stratified) == 24
    assert {i.bucket for i in stratified} == {"4-8", "9-12", "13-16", "17-24"}
    assert {i.category for i in stratified} == {
        "baseline",
        "digits",
        "ascii_abbrev",
        "chinese_name",
        "parens",
        "quote",
    }


def test_load_regression_sentence_set_source_ids_are_unique() -> None:
    items = shadow.load_regression_sentence_set(
        shadow.DEFAULT_REGRESSION_SENTENCES_PATH, {}, max_chars=2000
    )
    ids = [i.source_id for i in items]
    assert len(ids) == len(set(ids))


def test_load_regression_sentence_set_does_not_merge_short_sentences(tmp_path: Path) -> None:
    path = tmp_path / "regression.yaml"
    path.write_text('known_failures:\n  - "あ。い。"\nstratified: {}\n', encoding="utf-8")
    # 「あ。」「い。」は共に1文字 (min_sentence_chars=20相当が効けばマージされるはずだが、
    # ②③レイヤーはマージ非対象のため 2 文のまま分割される (Issue #91 の層別方針)。
    items = shadow.load_regression_sentence_set(path, {}, max_chars=2000)
    assert len(items) == 2
    assert [i.text for i in items] == ["あ。", "い。"]


def test_load_regression_sentence_set_applies_reading_dict(tmp_path: Path) -> None:
    path = tmp_path / "regression.yaml"
    path.write_text('known_failures:\n  - "百度です。"\nstratified: {}\n', encoding="utf-8")
    items = shadow.load_regression_sentence_set(path, {"百度": "バイドゥ"}, max_chars=2000)
    assert items[0].text == "バイドゥです。"


def test_load_regression_sentence_set_rejects_non_list_known_failures(tmp_path: Path) -> None:
    path = tmp_path / "regression.yaml"
    path.write_text("known_failures: not-a-list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        shadow.load_regression_sentence_set(path, {}, max_chars=2000)


def test_load_regression_sentence_set_rejects_non_dict_stratified(tmp_path: Path) -> None:
    path = tmp_path / "regression.yaml"
    path.write_text("stratified: not-a-dict\n", encoding="utf-8")
    with pytest.raises(ValueError):
        shadow.load_regression_sentence_set(path, {}, max_chars=2000)


def test_load_regression_sentence_set_rejects_non_dict_bucket(tmp_path: Path) -> None:
    path = tmp_path / "regression.yaml"
    path.write_text('stratified:\n  "4-8": not-a-dict\n', encoding="utf-8")
    with pytest.raises(ValueError):
        shadow.load_regression_sentence_set(path, {}, max_chars=2000)


# ---------- build_sentence_set (三層結合) ----------


def test_build_sentence_set_combines_all_three_layers() -> None:
    markdown = "## 1. A\n本文です。"
    items = shadow.build_sentence_set(
        markdown,
        {},
        shadow.DEFAULT_REGRESSION_SENTENCES_PATH,
        max_chars=2000,
        min_sentence_chars=20,
    )
    assert {i.layer for i in items} == {"daily_draft", "known_failure", "stratified"}


# ---------- compute_kana_cer ----------


def test_compute_kana_cer_exact_match_is_zero() -> None:
    result = shadow.compute_kana_cer("今日は良い天気です。", "今日は良い天気です")
    assert result.cer == pytest.approx(0.0)
    assert result.insertions == 0
    assert result.deletions == 0
    assert result.substitutions == 0


def test_compute_kana_cer_trailing_insertion() -> None:
    result = shadow.compute_kana_cer("今日は良い天気です。", "今日は良い天気ですサイノス")
    assert result.insertions == 4
    assert result.deletions == 0
    assert result.substitutions == 0
    assert result.cer > 0


def test_compute_kana_cer_deletion() -> None:
    result = shadow.compute_kana_cer("今日は良い天気です。", "今日は天気です")
    assert result.deletions > 0
    assert result.insertions == 0
    assert result.cer > 0


def test_compute_kana_cer_substitution_detects_digit_misreading() -> None:
    # asr_gate.py docstring と同じ数字誤読の実測パターン (2027年→2017年)
    result = shadow.compute_kana_cer(
        "来年の2027年に発表される見込みです。", "来年の2017年に発表される見込みです"
    )
    assert result.substitutions >= 1
    assert result.cer > 0


# ---------- detect_hallucination_suspicion ----------


def test_detect_hallucination_suspicion_trailing_insertion() -> None:
    verdict = shadow.detect_hallucination_suspicion(
        "今日は良い天気です。", "今日は良い天気ですサイノス"
    )
    assert verdict.suspected is True
    assert verdict.trailing_insertion_chars >= shadow.TRAILING_INSERTION_MIN_CHARS


def test_detect_hallucination_suspicion_length_ratio() -> None:
    verdict = shadow.detect_hallucination_suspicion(
        "対応を進めます。", "本当にすみませんが対応を進めます"
    )
    assert verdict.suspected is True
    assert verdict.length_ratio > shadow.LENGTH_RATIO_SUSPICION_THRESHOLD
    # プレフィックス挿入なので末尾 diff は insert ではない
    assert verdict.trailing_insertion_chars == 0


def test_detect_hallucination_suspicion_exact_match_not_suspected() -> None:
    verdict = shadow.detect_hallucination_suspicion("今日は良い天気です。", "今日は良い天気です")
    assert verdict.suspected is False
    assert verdict.trailing_insertion_chars == 0


def test_detect_hallucination_suspicion_short_trailing_addition_not_suspected() -> None:
    # 末尾挿入が閾値未満 (1文字) かつ長さ比も閾値未満なら疑いとしない
    verdict = shadow.detect_hallucination_suspicion("今日は良い天気です。", "今日は良い天気ですね")
    assert verdict.trailing_insertion_chars < shadow.TRAILING_INSERTION_MIN_CHARS
    assert verdict.suspected is False


# ---------- transcript_agreement ----------


def test_transcript_agreement_identical_is_one() -> None:
    assert shadow.transcript_agreement("こんにちは", "こんにちは") == pytest.approx(1.0)


def test_transcript_agreement_completely_different_is_low() -> None:
    assert shadow.transcript_agreement("こんにちは", "さようなら") < 0.5


# ---------- ShadowConfig.config_hash ----------


def _make_config(**overrides: Any) -> Any:
    base: dict[str, Any] = {
        "whisper_model": "turbo",
        "seed": 42,
        "min_sentence_chars": 20,
        "v3_voice": "hal",
        "v4_voice": "hal",
        "model": "irodori-tts",
        "v4_server_rev": "abc123",
        "v4_ref_audio_sha256": None,
    }
    base.update(overrides)
    return shadow.ShadowConfig(**base)


def test_config_hash_stable_for_same_inputs() -> None:
    assert _make_config().config_hash() == _make_config().config_hash()


def test_config_hash_changes_with_seed() -> None:
    assert _make_config().config_hash() != _make_config(seed=43).config_hash()


def test_config_hash_changes_with_server_rev() -> None:
    assert _make_config().config_hash() != _make_config(v4_server_rev="def456").config_hash()


def test_config_hash_changes_with_ref_audio_hash() -> None:
    assert (
        _make_config().config_hash()
        != _make_config(v4_ref_audio_sha256="deadbeef").config_hash()
    )


# ---------- sha256 helpers ----------


def test_sha256_file_returns_hash_for_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_bytes(b"hello")
    assert shadow.sha256_file(path) == shadow.sha256_hex(b"hello")


def test_sha256_file_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert shadow.sha256_file(tmp_path / "missing.bin") is None


# ---------- git_rev (subprocess はモック, 実 git は呼ばない) ----------


def test_git_rev_returns_stripped_stdout_on_success(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")
    with patch("subprocess.run", return_value=completed):
        assert shadow.git_rev(tmp_path) == "abc123"


def test_git_rev_returns_none_on_nonzero_exit(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="fatal")
    with patch("subprocess.run", return_value=completed):
        assert shadow.git_rev(tmp_path) is None


def test_git_rev_returns_none_on_oserror(tmp_path: Path) -> None:
    with patch("subprocess.run", side_effect=OSError("git not found")):
        assert shadow.git_rev(tmp_path) is None


# ---------- is_server_healthy / wait_for_health (httpx.MockTransport, 実サーバ不使用) ----------


def _client_with_handler(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_is_server_healthy_true_when_200_and_loaded_not_required() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    with _client_with_handler(handler) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8088", require_loaded=False)
            is True
        )


def test_is_server_healthy_false_on_non_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client_with_handler(handler) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8088", require_loaded=False)
            is False
        )


def test_is_server_healthy_requires_loaded_true() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"loaded": False})

    with _client_with_handler(handler) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8089", require_loaded=True)
            is False
        )


def test_is_server_healthy_reads_nested_runtime_loaded() -> None:
    """実サーバの health は {"runtime": {"loaded": ...}} とネストしている (初回実走で発覚した回帰)."""

    def handler_true(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"runtime": {"loaded": True}, "voices": {"files": 11}})

    def handler_false(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"runtime": {"loaded": False}})

    with _client_with_handler(handler_true) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8089", require_loaded=True)
            is True
        )
    with _client_with_handler(handler_false) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8089", require_loaded=True)
            is False
        )


def test_is_server_healthy_loaded_true_passes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"loaded": True})

    with _client_with_handler(handler) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8089", require_loaded=True)
            is True
        )


def test_is_server_healthy_false_on_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with _client_with_handler(handler) as client:
        assert (
            shadow.is_server_healthy(client, "http://127.0.0.1:8089", require_loaded=False)
            is False
        )


def test_wait_for_health_succeeds_immediately() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"loaded": True})

    with _client_with_handler(handler) as client:
        assert (
            shadow.wait_for_health(
                client,
                "http://127.0.0.1:8089",
                timeout_sec=1.0,
                poll_interval_sec=0.01,
                require_loaded=True,
            )
            is True
        )


def test_wait_for_health_times_out() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client_with_handler(handler) as client:
        assert (
            shadow.wait_for_health(
                client,
                "http://127.0.0.1:8089",
                timeout_sec=0.05,
                poll_interval_sec=0.01,
                require_loaded=True,
            )
            is False
        )


# ---------- process_sentence (fake client/ASR backend, 実サーバ不使用) ----------


class _FakeAsrBackend:
    """呼び出し順で v3/v4 の書き起こしを切り替える fake (1回目=v3, 2回目=v4)."""

    def __init__(self, transcripts: dict[str, str]) -> None:
        self._transcripts = transcripts
        self.calls: list[bytes] = []

    def transcribe(self, wav_bytes: bytes) -> str:
        self.calls.append(wav_bytes)
        key = "v3" if len(self.calls) == 1 else "v4"
        return self._transcripts[key]


class _UnavailableAsrBackend:
    def transcribe(self, wav_bytes: bytes) -> str:
        raise shadow.AsrUnavailableError("openai-whisper 未導入")


def _sentence_item(text: str = "今日は良い天気です。") -> Any:
    return shadow.SentenceItem(
        text=text,
        layer="known_failure",
        bucket="known_failure",
        category="",
        source_id="known_failure:1:s1",
    )


def test_process_sentence_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_wav_bytes())

    backend = _FakeAsrBackend({"v3": "今日は良い天気です", "v4": "今日は良い天気です"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = shadow.process_sentence(
            _sentence_item(),
            client=client,
            v3_base_url="http://v3.test",
            v4_base_url="http://v4.test",
            v3_voice="hal",
            v4_voice="hal",
            model="irodori-tts",
            seed=42,
            whisper_backend=backend,
            synth_timeout=5.0,
            seconds_margin=0.25,
        )
    assert result.error is None
    assert result.v3_duration_sec is not None
    assert result.v4_seconds_requested == pytest.approx(
        result.v3_duration_sec + 0.25, abs=5e-3
    )
    assert result.kana_cer is not None
    assert result.hallucination is not None
    assert result.hallucination.suspected is False
    assert result.v3_v4_transcript_agreement == pytest.approx(1.0)


def test_process_sentence_v3_failure_is_fail_open() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    backend = _FakeAsrBackend({"v3": "x", "v4": "x"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = shadow.process_sentence(
            _sentence_item("テスト文。"),
            client=client,
            v3_base_url="http://v3.test",
            v4_base_url="http://v4.test",
            v3_voice="hal",
            v4_voice="hal",
            model="irodori-tts",
            seed=42,
            whisper_backend=backend,
            synth_timeout=5.0,
            seconds_margin=0.25,
        )
    assert result.error is not None
    assert "v3合成失敗" in result.error
    assert result.kana_cer is None


def test_process_sentence_v4_failure_keeps_v3_measurement() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "v3.test" in str(request.url):
            return httpx.Response(200, content=_wav_bytes())
        return httpx.Response(500)

    backend = _FakeAsrBackend({"v3": "テスト文", "v4": "x"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = shadow.process_sentence(
            _sentence_item("テスト文。"),
            client=client,
            v3_base_url="http://v3.test",
            v4_base_url="http://v4.test",
            v3_voice="hal",
            v4_voice="hal",
            model="irodori-tts",
            seed=42,
            whisper_backend=backend,
            synth_timeout=5.0,
            seconds_margin=0.25,
        )
    assert result.error is not None
    assert "v4合成失敗" in result.error
    assert result.v3_duration_sec is not None
    assert result.v3_transcript == "テスト文"
    assert result.kana_cer is None


def test_process_sentence_propagates_asr_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_wav_bytes())

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(shadow.AsrUnavailableError),
    ):
        shadow.process_sentence(
            _sentence_item("テスト文。"),
            client=client,
            v3_base_url="http://v3.test",
            v4_base_url="http://v4.test",
            v3_voice="hal",
            v4_voice="hal",
            model="irodori-tts",
            seed=42,
            whisper_backend=_UnavailableAsrBackend(),
            synth_timeout=5.0,
            seconds_margin=0.25,
        )


# ---------- write_report / history ----------


def _dummy_report(*, config_hash: str = "hash1", cer_values: list[float] | None = None) -> Any:
    started_at = datetime(2026, 8, 3, 7, 0, tzinfo=UTC)
    finished_at = datetime(2026, 8, 3, 7, 10, tzinfo=UTC)
    config = _make_config()
    sentences = []
    resolved_cer_values = [0.0, 0.5] if cer_values is None else cer_values
    for idx, cer in enumerate(resolved_cer_values):
        sentences.append(
            shadow.SentenceResult(
                source_id=f"s{idx}",
                layer="known_failure",
                bucket="known_failure",
                category="",
                expected_text="テスト文",
                kana_cer=shadow.KanaCerResult(
                    insertions=0, deletions=0, substitutions=0, cer=cer
                ),
                hallucination=shadow.HallucinationVerdict(
                    suspected=cer > 0.3, length_ratio=1.0, trailing_insertion_chars=0
                ),
            )
        )
    return shadow.ShadowRunReport(
        run_id="20260803_070000",
        started_at=started_at,
        finished_at=finished_at,
        config=config,
        config_hash=config_hash,
        sentence_results=sentences,
        v4_available=True,
        v4_startup_note=None,
    )


def test_shadow_run_report_summary_counts() -> None:
    report = _dummy_report(cer_values=[0.0, 0.5, 1.0])
    assert report.sentence_count() == 3
    assert report.hallucination_suspect_count() == 2
    assert report.cer_median() == pytest.approx(0.5)


def test_shadow_run_report_cer_median_none_when_no_measurements() -> None:
    report = _dummy_report(cer_values=[])
    assert report.cer_median() is None


def test_write_report_creates_json_file(tmp_path: Path) -> None:
    report = _dummy_report()
    path = shadow.write_report(report, tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "20260803_070000"
    assert data["summary"]["sentence_count"] == 2
    assert len(data["sentences"]) == 2


def test_history_round_trip(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    report = _dummy_report()
    line = shadow.build_history_line(report, config_changed=False)
    shadow.append_history(history_path, line)
    last = shadow.read_last_history_line(history_path)
    assert last is not None
    assert last["run_id"] == "20260803_070000"
    assert last["config_changed"] is False


def test_read_last_history_line_returns_none_when_missing(tmp_path: Path) -> None:
    assert shadow.read_last_history_line(tmp_path / "missing.jsonl") is None


def test_read_last_history_line_returns_last_of_multiple(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    shadow.append_history(history_path, {"run_id": "first"})
    shadow.append_history(history_path, {"run_id": "second"})
    last = shadow.read_last_history_line(history_path)
    assert last is not None
    assert last["run_id"] == "second"


def test_read_last_history_line_fail_open_on_corrupt_json(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    history_path.write_text("not json\n", encoding="utf-8")
    assert shadow.read_last_history_line(history_path) is None


# ---------- build_issue_comment ----------


def test_build_issue_comment_within_ten_lines() -> None:
    report = _dummy_report()
    comment = shadow.build_issue_comment(report, config_changed=False)
    assert len(comment.splitlines()) <= 10


def test_build_issue_comment_includes_config_change_warning() -> None:
    report = _dummy_report()
    comment = shadow.build_issue_comment(report, config_changed=True)
    assert "構成変更" in comment
    assert "リセット" in comment


def test_build_issue_comment_omits_config_change_warning_when_unchanged() -> None:
    report = _dummy_report()
    comment = shadow.build_issue_comment(report, config_changed=False)
    assert "構成変更" not in comment


def test_build_issue_comment_reports_v4_unavailable() -> None:
    started_at = datetime(2026, 8, 3, 7, 0, tzinfo=UTC)
    config = _make_config()
    report = shadow.ShadowRunReport(
        run_id="run1",
        started_at=started_at,
        finished_at=started_at,
        config=config,
        config_hash="hash1",
        sentence_results=[],
        v4_available=False,
        v4_startup_note="health タイムアウト",
    )
    comment = shadow.build_issue_comment(report, config_changed=False)
    assert "NG" in comment
    assert "health タイムアウト" in comment


# ---------- post_issue_comment (subprocess はモック, 実 gh は呼ばない) ----------


def test_post_issue_comment_success() -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=completed) as mock_run:
        assert shadow.post_issue_comment("body", issue_number=88) is True
    called_args = mock_run.call_args.args[0]
    assert called_args[:3] == ["gh", "issue", "comment"]
    assert "88" in called_args


def test_post_issue_comment_fail_open_on_nonzero_exit() -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=completed):
        assert shadow.post_issue_comment("body", issue_number=88) is False


def test_post_issue_comment_fail_open_on_timeout() -> None:
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=1)
    ):
        assert shadow.post_issue_comment("body", issue_number=88) is False


def test_post_issue_comment_fail_open_on_oserror() -> None:
    with patch("subprocess.run", side_effect=OSError("gh not found")):
        assert shadow.post_issue_comment("body", issue_number=88) is False


# ---------- build_discord_summary / post_shadow_summary_to_discord (Issue #95 PR-B) ----------


def test_build_discord_summary_includes_counts_and_issue_reference() -> None:
    report = _dummy_report(cer_values=[0.0, 0.5, 1.0])
    summary = shadow.build_discord_summary(report)
    assert report.run_id in summary
    assert "文数 3" in summary
    assert "幻話疑い 2" in summary
    assert "Issue #88" in summary


def test_post_shadow_summary_to_discord_skips_when_webhook_unset(caplog: Any) -> None:
    report = _dummy_report()
    fake_settings = type("_S", (), {"discord_webhook_url": ""})()
    with (
        patch.object(shadow, "load_settings", return_value=fake_settings),
        patch.object(shadow, "post_summary") as mock_post,
        caplog.at_level("INFO"),
    ):
        assert shadow.post_shadow_summary_to_discord(report) is False
    mock_post.assert_not_called()
    assert "未設定" in caplog.text


def test_post_shadow_summary_to_discord_posts_when_webhook_set() -> None:
    report = _dummy_report()
    fake_settings = type("_S", (), {"discord_webhook_url": "https://discord.example/webhook"})()
    with (
        patch.object(shadow, "load_settings", return_value=fake_settings),
        patch.object(shadow, "post_summary", return_value=True) as mock_post,
    ):
        assert shadow.post_shadow_summary_to_discord(report) is True
    mock_post.assert_called_once()
    called_url, called_content = mock_post.call_args.args
    assert called_url == "https://discord.example/webhook"
    assert report.run_id in called_content


def test_post_shadow_summary_to_discord_fail_open_when_post_fails(caplog: Any) -> None:
    report = _dummy_report()
    fake_settings = type("_S", (), {"discord_webhook_url": "https://discord.example/webhook"})()
    with (
        patch.object(shadow, "load_settings", return_value=fake_settings),
        patch.object(shadow, "post_summary", return_value=False),
        caplog.at_level("WARNING"),
    ):
        assert shadow.post_shadow_summary_to_discord(report) is False
    assert "失敗" in caplog.text
