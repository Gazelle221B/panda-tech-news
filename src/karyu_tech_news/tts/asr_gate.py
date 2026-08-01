"""文単位 ASR 品質ゲート (Sprint 2 Ticket T58, Issue #54).

参照音声条件付け TTS (Irodori 等) は確率的に台本外の発話 (幻話/babble) を挿入する
ことが実測されている。文単位合成の直後にローカル ASR (Whisper) で書き起こし、期待文
と突き合わせて不一致ならその文だけ再合成してリトライし、解消しなければ従来の
fail-open と同様に skip する (`tts/synthesize.py` 側の統合を参照)。

設計原則:
- **ASR バックエンドは Protocol で抽象化** し、テストは fake backend を注入する
  (whisper 実体は使わない)。
- **openai-whisper は optional 依存** (extra `qa-asr`)。未導入環境でも ASR ゲート
  無効時の `produce` 自体を壊さないよう、import はメソッド内で遅延する
  (`tts/kokoro.py` の遅延ロードと同じ流儀)。

閾値の実測根拠 (2026-07-31 dry-run 観測): 幻話は「文頭・文末への一言追加」として
現れ、文の中身自体は台本どおりだった。このため検出の主眼は「文が丸ごと別物」または
「大幅な追加発話」に絞り、軽微な表記ゆれ (例: 「AI」と「エーアイ」のような直交する
読み違い) を誤検出しないよう類似度の閾値は緩めに設定している。

2 段構え判定 (T66, Issue #76): 上記の機械比較だけでは表記ゆれの吸収が粗く、
数字の誤読 (例: 「2027年」→「2017年」) を原理的に検出できない。このため
類似度が高く長さ比も正常な大多数の文は従来どおり機械比較のみ (fast path, LLM
不呼出) で即決するが、曖昧域 (類似度 0.5〜0.85 未満 / 長さ比異常) のみ
`AsrJudge` (LLM 等) に判定を委譲できるようにした。`judge` 未指定、または judge
が None を返した (判定不能) 場合は従来の機械判定にフォールバックする (fail-open)。

fast path の数字整合ガード (2026-08-02 レビュー差し戻し対応): 周辺文が長いと
1 桁の数字誤読でも類似度が容易に 0.85 を超えてしまい、fast path が本チケットの
主目的 (数字誤読検出) を素通りさせる実測が判明した (例:
「来年の2027年に発表される見込みです。」→「来年の2017年に発表される見込みです」
で類似度 0.947)。このため fast path は類似度・長さ比に加えて、期待文と書き起こし
それぞれから抽出した数字列 (`\\d+` の並び) が完全一致する場合のみ許可する。数字列が
不一致 (誤読・脱落・片側のみ漢数字表記など) なら類似度・長さ比が正常でも曖昧域へ
落とし、judge (または judge 不在時は従来の機械判定) に委ねる。
"""
from __future__ import annotations

import difflib
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

# 類似度がこれ未満なら「文が丸ごと別物」とみなし mismatch (閾値の実測根拠はモジュール
# docstring 参照)。judge があっても呼ばない (明白な不一致に LLM は不要)。
SIMILARITY_MISMATCH_THRESHOLD = 0.5
# 類似度が閾値以上でも、書き起こしが期待文よりこの倍率を超えて長ければ「文頭・
# 文末への一言追加」型の幻話 (insertion) とみなす。judge 不在時の機械判定にも使う。
LENGTH_RATIO_INSERTION_THRESHOLD = 1.6
# 類似度がこれ以上かつ長さ比正常なら fast path で即 ok (LLM 不呼出, T66, Issue #76)。
# 大多数の文がここで即決するため、LLM 呼び出しは曖昧域のみに絞られる。
FAST_PATH_SIMILARITY = 0.85

AsrVerdictStatus = Literal["ok", "mismatch", "insertion"]

# 正規化: 小文字化 + 空白 (全角含む) + 主要な日本語句読点・かぎ括弧・中黒・三点リーダを
# 除去する。かな/漢字/ローマ字表記ゆれや数字の読み違いはここでは吸収しない (将来課題)。
_NORMALIZE_STRIP_RE = re.compile(r"[\s　。、,.!?！？「」『』・…]+")
# fast path の数字整合ガード用: 正規化後テキストから半角数字の連続を抽出する
# (2026-08-02 レビュー差し戻し対応, モジュール docstring 参照)。
_DIGITS_RE = re.compile(r"\d+")


class AsrUnavailableError(Exception):
    """ASR バックエンドが利用できない (未導入による import 失敗など)."""


@dataclass(frozen=True)
class AsrVerdict:
    """1 文の ASR 突き合わせ結果."""

    status: AsrVerdictStatus
    similarity: float
    length_ratio: float


@runtime_checkable
class AsrBackend(Protocol):
    """ASR バックエンド抽象. 実装は合成済み wav bytes を書き起こしテキストへ変換する."""

    def transcribe(self, wav_bytes: bytes) -> str: ...


@runtime_checkable
class AsrJudge(Protocol):
    """曖昧域 (類似度 0.5〜0.85 未満 / 長さ比異常) の判定を委譲する抽象 (T66, Issue #76).

    tts 層はこの Protocol のみを知り、具象実装 (LLM 呼び出し) は main.py / llm 層に
    置いて注入する (tts 層が llm 層を import しないため)。None を返すと判定不能とみなし、
    `verify_sentence` は fail-open で従来の機械判定にフォールバックする。
    """

    def judge(self, expected: str, transcript: str) -> AsrVerdictStatus | None: ...


def _normalize(text: str) -> str:
    return _NORMALIZE_STRIP_RE.sub("", text.lower())


def _digit_sequences(normalized_text: str) -> list[str]:
    """正規化済みテキストから数字列 (`\\d+` の並び) を出現順に抽出する.

    fast path の数字整合ガード専用 (2026-08-02 レビュー差し戻し対応)。漢数字・
    全角数字は `\\d` にマッチしないため、片側だけ漢数字表記 (例: 「二千二十七年」) の
    ケースも「数字列が空 (片側は非空)」= 不一致として扱われ、fast path から曖昧域へ
    落ちる (judge が表記ゆれとして ok 判定できる余地を残す設計)。
    """
    return _DIGITS_RE.findall(normalized_text)


def verify_sentence(
    expected: str, transcript: str, *, judge: AsrJudge | None = None
) -> AsrVerdict:
    """期待文と ASR 書き起こしを突き合わせ、不一致/幻話疑いを判定する.

    正規化 (小文字化・空白/句読点除去) した上で、(a) `difflib.SequenceMatcher.ratio()`
    による類似度と (b) 長さ比 (書き起こし / 期待文) を計算する。

    2 段構え判定 (T66, Issue #76):
    - 類似度 < `SIMILARITY_MISMATCH_THRESHOLD` → "mismatch" (文が丸ごと別物、judge 不呼出)。
    - 類似度 >= `FAST_PATH_SIMILARITY` かつ長さ比が `LENGTH_RATIO_INSERTION_THRESHOLD`
      以下 **かつ数字列 (`\\d+`) が期待文・書き起こしで完全一致** → "ok" (fast path、
      judge 不呼出)。数字列の不一致 (誤読・脱落・片側のみ漢数字表記など) は、類似度・
      長さ比が正常でも fast path を通さず曖昧域へ落とす (2026-08-02 レビュー差し戻し
      対応、モジュール docstring 参照)。
    - それ以外 (曖昧域) は `judge` が指定されていれば判定を委譲する。judge が None を
      返す (判定不能) か、judge 自体が未指定なら、従来の機械判定 (長さ比のみで
      ok/insertion を分岐) にフォールバックする。
    """
    norm_expected = _normalize(expected)
    norm_transcript = _normalize(transcript)
    similarity = difflib.SequenceMatcher(None, norm_expected, norm_transcript).ratio()
    length_ratio = len(norm_transcript) / max(len(norm_expected), 1)
    digits_match = _digit_sequences(norm_expected) == _digit_sequences(norm_transcript)

    def _mechanical_status() -> AsrVerdictStatus:
        return "insertion" if length_ratio > LENGTH_RATIO_INSERTION_THRESHOLD else "ok"

    status: AsrVerdictStatus
    if similarity < SIMILARITY_MISMATCH_THRESHOLD:
        status = "mismatch"
    elif (
        similarity >= FAST_PATH_SIMILARITY
        and length_ratio <= LENGTH_RATIO_INSERTION_THRESHOLD
        and digits_match
    ):
        status = "ok"
    elif judge is not None:
        judged = judge.judge(expected, transcript)
        status = judged if judged is not None else _mechanical_status()
    else:
        status = _mechanical_status()
    return AsrVerdict(status=status, similarity=similarity, length_ratio=length_ratio)


class WhisperAsrBackend:
    """openai-whisper (ローカル) を `AsrBackend` に適合させるアダプタ.

    実バックエンドは初回 `transcribe` 呼び出し時に遅延ロードし、インスタンスへ
    キャッシュする (2 回目以降はロード済みモデルを再利用)。import はメソッド内で
    行うため、未導入環境でもこのクラスを構築するだけなら失敗しない
    (`tts/kokoro.py` の `KokoroTTSEngine._backend()` と同じ流儀)。
    """

    def __init__(self, model_name: str = "turbo") -> None:
        self._model_name = model_name
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            import whisper
        except ImportError as exc:
            raise AsrUnavailableError(
                "openai-whisper 未導入。`uv sync --extra qa-asr` で導入してください"
            ) from exc
        self._model = whisper.load_model(self._model_name)
        return self._model

    def transcribe(self, wav_bytes: bytes) -> str:
        model = self._load_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = Path(tmp.name)
        try:
            result = model.transcribe(tmp_path.as_posix(), language="ja", temperature=0.0)
        finally:
            tmp_path.unlink(missing_ok=True)
        text = result.get("text", "") if isinstance(result, dict) else result
        return str(text).strip()
