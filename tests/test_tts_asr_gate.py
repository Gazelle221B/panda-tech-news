"""tts.asr_gate のユニットテスト (Sprint 2 Ticket T58, Issue #54). whisper 実体は使わない.

verify_sentence の判定ロジックと、WhisperAsrBackend の遅延 import 契約 (未導入時に
AsrUnavailableError) を固定する。実 openai-whisper での書き起こし精度検証は対象外
(人間環境での実 produce smoke で行う)。
"""
from __future__ import annotations

import sys

import pytest

from karyu_tech_news.tts.asr_gate import (
    AsrBackend,
    AsrJudge,
    AsrUnavailableError,
    AsrVerdict,
    AsrVerdictStatus,
    WhisperAsrBackend,
    verify_sentence,
)

# ---------- verify_sentence ----------


def test_verify_sentence_exact_match_is_ok() -> None:
    verdict = verify_sentence("今日は良い天気です。", "今日は良い天気です")
    assert verdict.status == "ok"
    assert verdict.similarity == pytest.approx(1.0)


def test_verify_sentence_completely_different_is_mismatch() -> None:
    # 文が丸ごと別物 (類似度が閾値未満)
    verdict = verify_sentence("今日は良い天気です。", "株価が急落しました")
    assert verdict.status == "mismatch"
    assert verdict.similarity < 0.5


def test_verify_sentence_empty_transcript_is_mismatch() -> None:
    # 無音 ASR 等で空文字が返ったケース (類似度 0)
    verdict = verify_sentence("今日は良い天気です。", "")
    assert verdict.status == "mismatch"
    assert verdict.similarity == 0.0


def test_verify_sentence_trailing_addition_is_insertion() -> None:
    # 2026-07-31 dry-run 実測の典型パターン: 文末への一言追加 (幻話疑い)
    verdict = verify_sentence(
        "対応を進めます。", "本当にすみませんが対応を進めます"
    )
    assert verdict.status == "insertion"
    assert verdict.similarity >= 0.5
    assert verdict.length_ratio > 1.6


def test_verify_sentence_notation_variance_stays_ok() -> None:
    # 表記ゆれ (「AI」↔「エーアイ」等の直交する読み違い) は誤検出しない (閾値を緩めた理由)
    verdict = verify_sentence("これはAIの話です。", "これはエーアイの話です")
    assert verdict.status == "ok"


def test_verify_sentence_ignores_case_and_punctuation() -> None:
    verdict = verify_sentence("Hello、World!", "hello world")
    assert verdict.status == "ok"


# ---------- アルファベット⇔カナ読み正規化 (Issue #107) ----------
#
# 2026-08-12 の実配信ゼロ (朝 3/39 文・夜リトライ 4/39 文) を再現する回帰テスト。
# 曖昧域 (類似度 0.5〜0.85 未満) に落ちて長文で表記ゆれの影響が相対的に大きくなり、
# judge 無しの機械判定・judge 有りの誤判定いずれのケースも fast path で吸収できる
# ようになったことを固定する。


def test_verify_sentence_alphabet_kana_short_sentence_reproduces_incident() -> None:
    # Issue #107 記載のインシデント最小再現例。
    verdict = verify_sentence("エーアイが自作主張する時代", "AIが自作主張する時代")
    assert verdict.status == "ok"
    assert verdict.similarity == pytest.approx(1.0)


def test_verify_sentence_alphabet_kana_long_sentence_reaches_fast_path() -> None:
    # 2026-08-12 20:15 の実失敗文 (similarity=0.83 で曖昧域へ落ち judge が mismatch 判定)。
    # 正規化後は完全一致し、fast path (judge 不呼出) で ok になることを固定する。
    judge = _RecordingJudge("mismatch")  # 呼ばれたら誤判定になる値をわざと設定
    expected = "エーアイ競争の焦点が、チップ性能から電力供給へ移っている証左です。"
    transcript = "AI競争の焦点が、チップ性能から電力供給へ移っている証左です"
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert verdict.status == "ok"
    assert verdict.similarity == pytest.approx(1.0)
    assert judge.calls == []  # fast path のまま judge に到達しない


def test_verify_sentence_alphabet_kana_case_insensitive_and_fullwidth() -> None:
    # 大文字小文字 (Ai) と全角英字 (ＡＩ) の両方を吸収する。
    assert verify_sentence("エーアイの話です。", "Aiの話です").status == "ok"
    assert verify_sentence("エーアイの話です。", "ＡＩの話です").status == "ok"


def test_verify_sentence_alphabet_kana_does_not_match_inside_longer_word() -> None:
    # 語境界チェック: 短い略語 (id) が長い英字連続の内部 (android) にマッチして
    # 誤って正規化されないこと (`_ALPHABET_KANA_RE` の境界規則を固定)。
    verdict = verify_sentence("最新のandroid端末です。", "最新のandroid端末です")
    assert verdict.status == "ok"
    assert verdict.similarity == pytest.approx(1.0)  # 正規化が発火せず元の文字列のまま一致


def test_verify_sentence_alphabet_kana_hallucination_insertion_stays_detected() -> None:
    # 正規化を追加しても幻話 (長い勝手な挿入) の検出力は落ちない。
    verdict = verify_sentence(
        "AIの導入が進みます。", "本当にすみませんがエーアイの導入が進みます"
    )
    assert verdict.status == "insertion"
    assert verdict.length_ratio > 1.6


def test_verify_sentence_alphabet_kana_unrelated_sentence_stays_mismatch() -> None:
    # 正規化を追加しても、AI/エーアイ 以外が全く異なる文なら不一致のまま。
    verdict = verify_sentence("AIの話です。", "株価が急落しました")
    assert verdict.status == "mismatch"


@pytest.mark.parametrize(
    ("alphabet", "kana"),
    [
        ("AI", "エーアイ"),
        ("AGI", "エージーアイ"),
        ("API", "エーピーアイ"),
        ("App", "アプリ"),
        ("AR", "エーアール"),
        ("CEO", "シーイーオー"),
        ("CPU", "シーピーユー"),
        ("DX", "ディーエックス"),
        ("EV", "イーブイ"),
        ("GPT", "ジーピーティー"),
        ("GPU", "ジーピーユー"),
        ("ID", "アイディー"),
        ("IoT", "アイオーティー"),
        ("IT", "アイティー"),
        ("LLM", "エルエルエム"),
        ("ML", "エムエル"),
        ("NFT", "エヌエフティー"),
        ("OS", "オーエス"),
        ("PC", "ピーシー"),
        ("PDF", "ピーディーエフ"),
        ("SNS", "エスエヌエス"),
        ("TV", "ティーブイ"),
        ("UI", "ユーアイ"),
        ("URL", "ユーアールエル"),
        ("UX", "ユーエックス"),
        ("VR", "ブイアール"),
    ],
)
def test_verify_sentence_alphabet_kana_table_entries(alphabet: str, kana: str) -> None:
    # テーブルの各エントリが単体で一致判定になることを固定する。
    verdict = verify_sentence(f"{kana}の話です。", f"{alphabet}の話です")
    assert verdict.status == "ok"
    assert verdict.similarity == pytest.approx(1.0)


def test_asr_verdict_is_frozen_dataclass() -> None:
    verdict = AsrVerdict(status="ok", similarity=1.0, length_ratio=1.0)
    with pytest.raises(AttributeError):
        verdict.status = "mismatch"  # type: ignore[misc]


# ---------- AsrBackend protocol ----------


class _FakeAsrBackend:
    def transcribe(self, wav_bytes: bytes) -> str:
        return "テスト"


def test_fake_backend_satisfies_protocol() -> None:
    assert isinstance(_FakeAsrBackend(), AsrBackend)


# ---------- AsrJudge protocol / verify_sentence 段階分岐 (T66, Issue #76) ----------


class _RecordingJudge:
    """呼出有無と引数を記録する fake judge. 固定 verdict (または None) を返す."""

    def __init__(self, verdict: AsrVerdictStatus | None) -> None:
        self._verdict = verdict
        self.calls: list[tuple[str, str]] = []

    def judge(self, expected: str, transcript: str) -> AsrVerdictStatus | None:
        self.calls.append((expected, transcript))
        return self._verdict


def test_fake_judge_satisfies_protocol() -> None:
    assert isinstance(_RecordingJudge("ok"), AsrJudge)


def test_verify_sentence_fast_path_does_not_call_judge() -> None:
    # 類似度 >= FAST_PATH_SIMILARITY かつ長さ比正常 → judge を一切呼ばない
    judge = _RecordingJudge("mismatch")  # 呼ばれたら誤判定になる値をわざと設定
    verdict = verify_sentence("今日は良い天気です。", "今日は良い天気です", judge=judge)
    assert verdict.status == "ok"
    assert judge.calls == []


def test_verify_sentence_definite_mismatch_does_not_call_judge() -> None:
    # 類似度 < SIMILARITY_MISMATCH_THRESHOLD (壊滅的不一致) → judge を呼ばず即 mismatch
    judge = _RecordingJudge("ok")  # 呼ばれたら誤判定になる値をわざと設定
    verdict = verify_sentence("今日は良い天気です。", "株価が急落しました", judge=judge)
    assert verdict.status == "mismatch"
    assert judge.calls == []


def test_verify_sentence_ambiguous_zone_calls_judge_and_uses_its_verdict() -> None:
    # 曖昧域 (類似度 0.5〜0.85 未満、長さ比正常) は judge に委譲し、その結果を採用する。
    # 機械判定のみなら ok だが、judge が mismatch を返せばそれを優先する (judge の判断を
    # 尊重する契約を固定)。この例は AI/エーアイ 等の既知の表記ゆれとは無関係の文の差分
    # (Issue #107 のアルファベット⇔カナ正規化で fast path に吸収されないよう、意図的に
    # 表記ゆれテーブルの対象外の語を使う)。
    judge = _RecordingJudge("mismatch")
    expected, transcript = "新しい機能を追加しました。", "古い機能を削除しました"
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert 0.5 <= verdict.similarity < 0.85  # 曖昧域に入っていることの前提確認
    assert verdict.status == "mismatch"
    assert judge.calls == [(expected, transcript)]


def test_verify_sentence_judge_none_falls_back_to_mechanical_status() -> None:
    # 曖昧域で judge が None (判定不能) を返したら、従来の機械判定 (長さ比のみ) へ
    # fail-open する。
    judge = _RecordingJudge(None)
    expected, transcript = "新しい機能を追加しました。", "古い機能を削除しました"
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert judge.calls == [(expected, transcript)]
    # 長さ比が正常 (<= LENGTH_RATIO_INSERTION_THRESHOLD) なので機械判定は ok
    assert verdict.status == "ok"


def test_verify_sentence_ambiguous_zone_without_judge_uses_mechanical_status() -> None:
    # judge 未指定なら曖昧域でも従来どおり機械判定のみ (後方互換の固定)。
    expected, transcript = "新しい機能を追加しました。", "古い機能を削除しました"
    verdict = verify_sentence(expected, transcript)
    assert 0.5 <= verdict.similarity < 0.85
    assert verdict.status == "ok"


def test_verify_sentence_ambiguous_zone_number_mismatch_detected_via_judge() -> None:
    # T66 の主目的: 機械判定だけでは拾えない数字誤読を judge が検出する。
    expected, transcript = "2027年。", "2017年"
    mechanical_only = verify_sentence(expected, transcript)
    assert 0.5 <= mechanical_only.similarity < 0.85  # 曖昧域に入る (前提確認)
    assert mechanical_only.status == "ok"  # 機械判定だけでは数字誤読を拾えない

    judge = _RecordingJudge("mismatch")
    with_judge = verify_sentence(expected, transcript, judge=judge)
    assert with_judge.status == "mismatch"
    assert judge.calls == [(expected, transcript)]


# ---------- fast path の数字整合ガード (2026-08-02 レビュー差し戻し対応) ----------
#
# 実測: 「来年の2027年に発表される見込みです。」→「来年の2017年に発表される見込みです」
# は類似度 0.947 (>= FAST_PATH_SIMILARITY) かつ長さ比 1.0 (正常) のため、数字整合
# ガード導入前は fast path を素通りして judge に到達せず、数字誤読 (2027→2017) を
# 検出できなかった。ガード導入後はこのケースも曖昧域に落ち、judge (または judge 不在時
# は機械判定) に委ねられる。


def test_verify_sentence_long_sentence_digit_mismatch_bypasses_fast_path() -> None:
    # 数字整合ガードの主目的: 高類似度・正常長さ比でも数字列が不一致なら fast path を
    # 通さず judge に委譲する (レビュー指摘の実測回帰ケース)。
    expected = "来年の2027年に発表される見込みです。"
    transcript = "来年の2017年に発表される見込みです"
    mechanical_only = verify_sentence(expected, transcript)
    assert mechanical_only.similarity >= 0.85  # fast path の類似度条件は満たす (前提確認)
    assert mechanical_only.length_ratio <= 1.6  # 長さ比も正常 (前提確認)
    # 数字整合ガードが無ければここで fast path (ok) になってしまうはずのケース。
    # judge 未指定なので曖昧域へ落ちた上で機械判定にフォールバックし、結果は ok のまま
    # (後方互換: 挙動そのものは変わらないが、judge があれば介入できる経路を通る)。
    assert mechanical_only.status == "ok"

    judge = _RecordingJudge("mismatch")
    with_judge = verify_sentence(expected, transcript, judge=judge)
    assert with_judge.status == "mismatch"  # judge の判定 (数字誤読) が採用される
    assert judge.calls == [(expected, transcript)]  # fast path を通らず judge に到達した


def test_verify_sentence_long_sentence_matching_digits_still_uses_fast_path() -> None:
    # 数字列が一致する長文は従来どおり fast path (judge 不呼出) のまま。
    expected = "来年の2027年に発表される見込みです。"
    transcript = "来年の2027年に発表される見込みです"
    judge = _RecordingJudge("mismatch")  # 呼ばれたら誤判定になる値をわざと設定
    verdict = verify_sentence(expected, transcript, judge=judge)
    assert verdict.status == "ok"
    assert judge.calls == []  # fast path のまま judge に到達しない


def test_verify_sentence_kanji_numeral_transcript_bypasses_fast_path_and_uses_judge() -> None:
    # 書き起こしが漢数字表記 (Whisper が数字を漢数字として書き起こすケースを想定) の場合、
    # 期待文側の算用数字と数字列が一致しない (片側が空) ため fast path を通さず judge に
    # 委譲する。judge が表記ゆれとして ok を返せば、その判定が採用される。
    expected = (
        "中国の大手テクノロジー企業各社は、来年の2027年に向けて大規模な投資計画を"
        "相次いで発表する見込みだと報じられています。"
    )
    transcript = (
        "中国の大手テクノロジー企業各社は、来年の二千二十七年に向けて大規模な投資計画を"
        "相次いで発表する見込みだと報じられています"
    )
    mechanical_only = verify_sentence(expected, transcript)
    assert mechanical_only.similarity >= 0.85  # fast path の類似度条件は満たす (前提確認)
    assert mechanical_only.length_ratio <= 1.6

    judge = _RecordingJudge("ok")
    with_judge = verify_sentence(expected, transcript, judge=judge)
    assert with_judge.status == "ok"
    assert judge.calls == [(expected, transcript)]  # fast path を通らず judge に到達した


# ---------- WhisperAsrBackend (遅延 import) ----------


def test_whisper_backend_missing_dependency_raises_asr_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # openai-whisper の import を強制失敗させ、未導入時 AsrUnavailableError を hermetic に固定
    monkeypatch.setitem(sys.modules, "whisper", None)
    backend = WhisperAsrBackend()
    with pytest.raises(AsrUnavailableError):
        backend.transcribe(b"not a real wav")


def test_whisper_backend_construction_does_not_require_whisper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # コンストラクタ自体は import しない (未導入環境でも produce の構築を壊さない, T58 設計)
    monkeypatch.setitem(sys.modules, "whisper", None)
    WhisperAsrBackend()  # 例外を送出しないことを確認


def test_whisper_backend_caches_loaded_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class _FakeModel:
        def transcribe(self, path: str, **kwargs: object) -> dict[str, str]:
            calls.append(path)
            return {"text": "こんにちは"}

    class _FakeWhisperModule:
        @staticmethod
        def load_model(name: str) -> _FakeModel:
            calls.append(f"load:{name}")
            return _FakeModel()

    monkeypatch.setitem(sys.modules, "whisper", _FakeWhisperModule())
    backend = WhisperAsrBackend(model_name="turbo")
    assert backend.transcribe(b"RIFF....") == "こんにちは"
    assert backend.transcribe(b"RIFF....") == "こんにちは"
    # load_model は初回のみ (2 回目以降はキャッシュ済みモデルを再利用)
    assert calls.count("load:turbo") == 1
