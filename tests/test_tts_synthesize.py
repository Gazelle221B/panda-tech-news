"""tts.synthesize のユニットテスト (Sprint 2 Ticket T28). モック駆動.

文単位合成 + wav 結合を検証する。str 単位 (コードポイント) の長文分割、1 文失敗時の
fail-open (番組を止めない)、読み仮名正規化の適用、wav の正しい結合を固定する。
"""
from __future__ import annotations

import io
import wave
from datetime import UTC, datetime

import pytest

from karyu_tech_news.script.structure import Segment, StructuredScript
from karyu_tech_news.tts.engine import (
    Capabilities,
    MockTTSEngine,
    SynthesisRequest,
    SynthesisResult,
    TTSError,
    Voice,
)
from karyu_tech_news.tts.synthesize import (
    concat_wav,
    split_sentences,
    synthesize_script,
)

NOW = datetime(2026, 6, 14, 7, 0, tzinfo=UTC)


def _script(*texts_tones: tuple[str, str]) -> StructuredScript:
    segs = [Segment(kind="topic", text=t, tone=tn, bgm="neutral") for t, tn in texts_tones]
    return StructuredScript(variant="A", generated_at=NOW, segments=segs)


def _nframes(wav_bytes: bytes) -> int:
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        return r.getnframes()


# ---------- split_sentences ----------

def test_split_on_japanese_punctuation() -> None:
    assert split_sentences("深刻だ。また明日。", 100) == ["深刻だ。", "また明日。"]


def test_split_drops_empty_and_whitespace() -> None:
    assert split_sentences("\n  \n文。\n", 100) == ["文。"]


def test_split_long_sentence_by_codepoints() -> None:
    # 句点なしの長文を str 単位で分割 (バイト切り禁止, design-inheritance §6)
    parts = split_sentences("あ" * 250, 100)
    assert [len(p) for p in parts] == [100, 100, 50]
    assert "".join(parts) == "あ" * 250


# ---------- concat_wav ----------

def test_concat_wav_sums_frames() -> None:
    eng = MockTTSEngine()
    a = eng.synthesize(SynthesisRequest(text="あいう", voice_id="hal")).audio
    b = eng.synthesize(SynthesisRequest(text="えお", voice_id="hal")).audio
    combined = concat_wav([a, b])
    assert _nframes(combined) == _nframes(a) + _nframes(b)


def test_concat_wav_empty_returns_valid_silent_wav() -> None:
    # 空入力でも有効な無音 wav (0フレーム) を返す (下流が wave.open で落ちない)
    assert _nframes(concat_wav([])) == 0


def test_concat_wav_skips_corrupt_chunk() -> None:
    # 壊れた wav chunk は fail-open で skip し、正常 chunk は結合する (Copilot 指摘)
    good = MockTTSEngine().synthesize(SynthesisRequest(text="あ", voice_id="hal")).audio
    combined = concat_wav([good, b"not a valid wav", good])
    assert _nframes(combined) == 2 * _nframes(good)


def test_concat_wav_all_corrupt_returns_silent_wav() -> None:
    assert _nframes(concat_wav([b"garbage", b"also bad"])) == 0


def test_split_sentences_rejects_nonpositive_max_chars() -> None:
    # engine が max_chars=0/負を返したら早期に分かりやすく失敗 (Copilot 指摘)
    with pytest.raises(ValueError):
        split_sentences("文。", 0)


def test_split_keeps_annotated_emoji_with_sentence() -> None:
    # T27 が句点直前に挿入した絵文字は分割で単独文にならない (Codex High 回帰)
    assert split_sentences("深刻です😟。", 100) == ["深刻です😟。"]


# ---------- synthesize_script ----------

def test_synthesize_script_returns_wav() -> None:
    res = synthesize_script(_script(("一文目。二文目。", "neutral")), MockTTSEngine(), {})
    assert isinstance(res, SynthesisResult)
    assert res.audio_format == "wav"
    assert _nframes(res.audio) > 0


def test_synthesize_script_applies_reading_dict() -> None:
    # 正規化が合成前に効く: 「小米」→「シャオミ」で渡る
    received: list[str] = []

    class _RecordingEngine:
        def name(self) -> str:
            return "rec"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            received.append(req.text)
            return MockTTSEngine().synthesize(req)

    synthesize_script(_script(("小米。", "neutral")), _RecordingEngine(), {"小米": "シャオミ"})
    assert any("シャオミ" in t for t in received)
    assert all("小米" not in t for t in received)


def test_synthesize_sanitizes_chinese_title_before_reading_dict() -> None:
    # T35 回帰: 読み辞書を先に当てると `豆包` -> `ドウバオ` のカナ混入で
    # quoted title が日本語扱いされ、中国語原題が TTS に残っていた。
    # T36 ASR 回帰: pinyin 羅列も「変な読み」になるため、日本語参照へ退避する。
    received: list[str] = []
    synthesize_script(
        _script(("今日は「刚刚，豆包2.1发布」を取り上げます。", "neutral")),
        _recording_engine(received, emoji_style=False),
        {"豆包": "ドウバオ"},
    )
    joined = "".join(received)
    assert "この話題" in joined
    assert "gang gang" not in joined
    assert "dou bao" not in joined
    assert "fa bu" not in joined
    assert "刚刚" not in joined
    assert "发布" not in joined
    assert "ドウバオ" not in joined


def _recording_engine(received: list[str], *, emoji_style: bool):  # type: ignore[no-untyped-def]
    class _Rec:
        def name(self) -> str:
            return "rec"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(
                emoji_style=emoji_style, voice_clone=False, streaming=False, max_chars=100
            )

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            received.append(req.text)
            return MockTTSEngine().synthesize(req)

    return _Rec()


_EMOJI_MAP = {"neutral": ["📖"], "bright": ["😊"]}


def test_synthesize_script_applies_emoji_per_sentence_when_supported() -> None:
    # 絵文字対応エンジンでは tone 絵文字を **文単位** で句点直前に挿入する (T33+)
    received: list[str] = []
    synthesize_script(
        _script(("一文目。二文目。", "neutral")),
        _recording_engine(received, emoji_style=True),
        {},
        emoji_mapping=_EMOJI_MAP,
    )
    assert received == ["一文目📖。", "二文目📖。"]


def test_synthesize_script_skips_emoji_when_engine_unsupported() -> None:
    # 絵文字非対応エンジン (kokoro 等) では mapping を渡しても挿入しない (capabilities ゲート)
    received: list[str] = []
    synthesize_script(
        _script(("一文目。", "bright")),
        _recording_engine(received, emoji_style=False),
        {},
        emoji_mapping=_EMOJI_MAP,
    )
    assert received == ["一文目。"]


def test_synthesize_script_no_emoji_without_mapping() -> None:
    # mapping 未指定なら絵文字非適用 (後方互換: 既存呼び出し元は無変更で従来動作)
    received: list[str] = []
    synthesize_script(
        _script(("一文目。", "neutral")),
        _recording_engine(received, emoji_style=True),
        {},
    )
    assert received == ["一文目。"]


def _caption_recording_engine(captions: list[str | None], *, voice_design: bool):  # type: ignore[no-untyped-def]
    class _Rec:
        def name(self) -> str:
            return "rec"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(
                emoji_style=False, voice_clone=False, streaming=False,
                max_chars=100, voice_design=voice_design,
            )

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            captions.append(req.caption)
            return MockTTSEngine().synthesize(req)

    return _Rec()


def test_synthesize_script_passes_caption_when_voice_design() -> None:
    # VoiceDesign 対応エンジンには caption が各文の SynthesisRequest へ渡る (T34)
    captions: list[str | None] = []
    synthesize_script(
        _script(("一文目。", "neutral")),
        _caption_recording_engine(captions, voice_design=True),
        {},
        caption="落ち着いた知的な声",
    )
    assert captions == ["落ち着いた知的な声"]


def test_synthesize_script_drops_caption_when_not_voice_design() -> None:
    # 非対応エンジン (kokoro 等) には caption を渡さない (None 化, capabilities ゲート)
    captions: list[str | None] = []
    synthesize_script(
        _script(("一文目。", "neutral")),
        _caption_recording_engine(captions, voice_design=False),
        {},
        caption="落ち着いた知的な声",
    )
    assert captions == [None]


def test_synthesize_script_fail_open_on_sentence_error() -> None:
    # 1 文の合成失敗で番組を止めない (他文の音声は出る)
    class _FlakyEngine:
        def name(self) -> str:
            return "flaky"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            if "BOOM" in req.text:
                raise TTSError("synth failed")
            return MockTTSEngine().synthesize(req)

    res = synthesize_script(_script(("正常。BOOM。", "neutral")), _FlakyEngine(), {})
    assert _nframes(res.audio) > 0  # 「正常。」の音声は残る
    assert res.attempted_sentences == 2
    assert res.synthesized_sentences == 1
    assert res.skipped_sentences == 1


def test_synthesize_result_sample_rate_matches_wav_header() -> None:
    # chunk skip (異 sample rate) があっても返却 sample_rate は実 wav ヘッダと一致 (Codex Med 回帰)
    def _wav(rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"\xff\x7f" * 10)
        return buf.getvalue()

    class _MixedRateEngine:
        def __init__(self) -> None:
            self.calls = 0

        def name(self) -> str:
            return "mixed"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            self.calls += 1
            rate = 48000 if self.calls == 1 else 24000  # 2文目だけ異 rate
            return SynthesisResult(audio=_wav(rate), sample_rate=rate)

    res = synthesize_script(_script(("一文目。二文目。", "neutral")), _MixedRateEngine(), {})
    with wave.open(io.BytesIO(res.audio), "rb") as r:
        assert res.sample_rate == r.getframerate() == 48000  # 先頭 chunk に揃う
    assert res.attempted_sentences == 2
    assert res.synthesized_sentences == 1
    assert res.skipped_sentences == 1


def test_synthesize_script_counts_zero_frame_chunk_as_skipped() -> None:
    class _ZeroFrameEngine:
        def name(self) -> str:
            return "zero"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            return SynthesisResult(audio=concat_wav([]), sample_rate=48000)

    res = synthesize_script(_script(("文。", "neutral")), _ZeroFrameEngine(), {})
    assert _nframes(res.audio) == 0
    assert res.attempted_sentences == 1
    assert res.synthesized_sentences == 0
    assert res.skipped_sentences == 1


def test_synthesize_script_counts_silent_chunk_as_skipped() -> None:
    def _wav(*, silent: bool) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes((b"\x00\x00" if silent else b"\xff\x7f") * 100)
        return buf.getvalue()

    class _OneSilentEngine:
        def __init__(self) -> None:
            self.calls = 0

        def name(self) -> str:
            return "one-silent"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            self.calls += 1
            return SynthesisResult(audio=_wav(silent=self.calls == 2), sample_rate=48000)

    res = synthesize_script(_script(("読める文。無音になる文。", "neutral")), _OneSilentEngine(), {})
    assert _nframes(res.audio) == 100
    assert res.attempted_sentences == 2
    assert res.synthesized_sentences == 1
    assert res.skipped_sentences == 1


def test_synthesize_script_counts_sparse_click_chunk_as_skipped() -> None:
    def _wav(*, click_only: bool) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(1000)
            if click_only:
                w.writeframes(b"\xff\x7f" + (b"\x00\x00" * 999))
            else:
                w.writeframes(b"\xff\x7f" * 1000)
        return buf.getvalue()

    class _OneClickEngine:
        def __init__(self) -> None:
            self.calls = 0

        def name(self) -> str:
            return "one-click"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            self.calls += 1
            return SynthesisResult(audio=_wav(click_only=self.calls == 2), sample_rate=1000)

    res = synthesize_script(_script(("読める文。クリックだけ。", "neutral")), _OneClickEngine(), {})
    assert _nframes(res.audio) == 1000
    assert res.attempted_sentences == 2
    assert res.synthesized_sentences == 1
    assert res.skipped_sentences == 1


def test_synthesize_script_keeps_short_speech_with_padding() -> None:
    def _wav(*, padded_short_speech: bool) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(1000)
            if padded_short_speech:
                w.writeframes((b"\x00\x00" * 1400) + (b"\xff\x7f" * 200) + (b"\x00\x00" * 1400))
            else:
                w.writeframes(b"\xff\x7f" * 1000)
        return buf.getvalue()

    class _OnePaddedShortSpeechEngine:
        def __init__(self) -> None:
            self.calls = 0

        def name(self) -> str:
            return "one-padded-short-speech"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            self.calls += 1
            return SynthesisResult(audio=_wav(padded_short_speech=self.calls == 2), sample_rate=1000)

    res = synthesize_script(_script(("通常の文。短い実発話。", "neutral")), _OnePaddedShortSpeechEngine(), {})
    assert _nframes(res.audio) == 4000
    assert res.attempted_sentences == 2
    assert res.synthesized_sentences == 2
    assert res.skipped_sentences == 0


def test_synthesize_script_all_fail_returns_empty_audio() -> None:
    class _DeadEngine:
        def name(self) -> str:
            return "dead"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            raise TTSError("always fails")

    res = synthesize_script(_script(("文。", "neutral")), _DeadEngine(), {})
    # 全滅でも例外を投げず、有効な無音 wav (0フレーム) を返す (下流が wave.open 可能)
    assert _nframes(res.audio) == 0
    assert res.attempted_sentences == 1
    assert res.synthesized_sentences == 0
    assert res.skipped_sentences == 1


def test_synthesize_strips_markdown_markers_before_synth() -> None:
    # **Hook:** 等の Markdown マーカーは TTS に渡さない (実音声 smoke で発見)
    received: list[str] = []

    class _RecordingEngine:
        def name(self) -> str:
            return "rec"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=200)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            received.append(req.text)
            return MockTTSEngine().synthesize(req)

    body = "**Hook:** つかみ。\n**Insight:** 意味。\n**Action:** 行動。"
    synthesize_script(_script((body, "neutral")), _RecordingEngine(), {})
    joined = "".join(received)
    assert "**" not in joined and "Hook" not in joined  # マーカー除去済み
    assert "つかみ" in joined and "行動" in joined  # 本文は残る


def test_synthesize_strips_ascii_gloss_before_synth() -> None:
    # 「カナ (原語)」の原語グロスは TTS で読まない & 二重読み回避 (Codex Medium 回帰)
    received: list[str] = []

    class _RecordingEngine:
        def name(self) -> str:
            return "rec"

        def voices(self) -> list[Voice]:
            return [Voice(id="hal", name="HAL")]

        def capabilities(self) -> Capabilities:
            return Capabilities(emoji_style=False, voice_clone=False, streaming=False, max_chars=100)

        def synthesize(self, req: SynthesisRequest) -> SynthesisResult:
            received.append(req.text)
            return MockTTSEngine().synthesize(req)

    synthesize_script(_script(("ディープシーク (DeepSeek)。", "neutral")), _RecordingEngine(), {})
    joined = "".join(received)
    assert "(" not in joined and "DeepSeek" not in joined  # グロス除去
    assert "ディープシーク" in joined


def test_synthesize_strips_links_and_keeps_pronunciation_before_synth() -> None:
    received: list[str] = []
    synthesize_script(
        _script(("詳しくは[公式資料](https://example.com/a)。灵晟（リンション）が首位。", "neutral")),
        _recording_engine(received, emoji_style=False),
        {},
    )
    joined = "".join(received)
    assert "https://" not in joined
    assert "](" not in joined
    assert "灵晟" not in joined
    assert "リンション" in joined
