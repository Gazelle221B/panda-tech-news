"""SFX/トランジション候補生成 (T62, Issue #65 スコープA).

Stable Audio 3 Small-SFX (`stabilityai/stable-audio-3-small-sfx`, Stability Community
License, 567.6M パラメータ, CPU 可, 最大120秒, inpainting 対応, 用途に UI・トランジション
明記) で transition/opening/ending の候補 SFX を生成し `assets/sfx/` へ書き出す。
音源採用 (人間試聴, Issue #65 スコープB) の前段の候補生成用スクリプト。

依存: `stable_audio_3` は optional extra `sfx` (`uv sync --extra sfx`)。PyPI に公開が
無いため git 依存 (`pyproject.toml` [tool.uv.sources] 参照)。torch を含む重量級のため
未導入でも本体パイプライン (produce 等) には一切影響しない (遅延 import)。

HF 側の `stabilityai/stable-audio-3-small-sfx` は Gated リポジトリ。初回は
https://huggingface.co/stabilityai/stable-audio-3-small-sfx でライセンス同意の上
`hf auth login` が必要 (未認証時は 401 系エラーになるため分かりやすいメッセージへ変換する)。

本スクリプトはネットワークと実モデルを要するためユニットテスト対象外 (mypy/ruff のみ)。

使い方:
    uv run python scripts/gen_sfx.py --out assets/sfx/ --kind transition --count 3 \\
        --duration 2.5 --seed 0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch

DEFAULT_OUT_DIR = Path("assets/sfx")
DEFAULT_COUNT = 3
DEFAULT_DURATION_SEC = 2.5
DEFAULT_SEED = 0
MODEL_ID = "small-sfx"  # docs/workflows/inference.md の post-trained SFX モデル ID

# kind ごとの既定プロンプト (英語, 放送向け短尺 SFX を狙う。README の Use case
# 「UI・トランジション」を踏まえた文言)。`--prompt` で個別に上書き可能。
_DEFAULT_PROMPTS: dict[str, str] = {
    "transition": (
        "clean modern news broadcast transition, short swoosh with soft synth accent, "
        "tight, no music bed"
    ),
    "opening": (
        "short upbeat tech news opening stinger, bright synth chime, "
        "professional broadcast intro, no vocals"
    ),
    "ending": (
        "short calm tech news closing stinger, gentle synth resolve, "
        "professional broadcast outro, no vocals"
    ),
}
KINDS = tuple(_DEFAULT_PROMPTS)


class GenSfxError(Exception):
    """SFX 生成の失敗 (依存未導入・HF 認証未済等)。CLI 側で分かりやすいメッセージ + exit 1 にする."""


def _load_model() -> object:
    """`stable_audio_3.StableAudioModel` を遅延 import・ロードする.

    - 未導入 (`uv sync --extra sfx` 未実行) は ImportError → GenSfxError に変換。
    - HF 側の認証/ライセンス未同意 (401 系・gated エラー) も分かりやすいメッセージに変換。
    それ以外の例外は生のメッセージを添えて GenSfxError に包む (原因追跡のため握り潰さない)。
    """
    try:
        from stable_audio_3 import StableAudioModel
    except ImportError as exc:
        raise GenSfxError(
            "stable_audio_3 が未導入です。`uv sync --extra sfx` を実行してください。"
        ) from exc
    try:
        return StableAudioModel.from_pretrained(MODEL_ID)
    except Exception as exc:  # noqa: BLE001 (HF/torch 側の例外型を広く捕捉し変換するため)
        message = str(exc)
        if "401" in message or "gated" in message.lower() or "access" in message.lower():
            raise GenSfxError(
                "Hugging Face の認証/ライセンス同意が必要です。"
                "https://huggingface.co/stabilityai/stable-audio-3-small-sfx で"
                "ライセンス同意の上 `hf auth login` を実行してください。"
            ) from exc
        raise GenSfxError(f"モデルのロードに失敗しました ({type(exc).__name__}): {message}") from exc


def generate_candidates(
    *,
    kind: str,
    out_dir: Path,
    count: int,
    duration: float,
    seed: int,
    prompt: str,
) -> list[Path]:
    """`count` 件の候補 wav を `out_dir` へ書き出し、生成したパスのリストを返す.

    候補ごとに `seed` を +1 しながら生成する (同一プロンプトでもバリエーションを得るため)。
    ファイル名は `{kind}_{seed}.wav` (仕様どおり、候補ごとに実際に使った seed を含む)。
    """
    import torchaudio

    model = _load_model()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i in range(count):
        candidate_seed = seed + i
        audio: torch.Tensor = model.generate(  # type: ignore[attr-defined]
            prompt=prompt, duration=duration, seed=candidate_seed, batch_size=1
        )
        out_path = out_dir / f"{kind}_{candidate_seed}.wav"
        sample_rate = model.model.sample_rate  # type: ignore[attr-defined]
        torchaudio.save(str(out_path), audio[0].cpu(), sample_rate)
        written.append(out_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stable Audio 3 Small-SFX で候補 SFX を生成する (Issue #65)"
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT_DIR, help=f"出力ディレクトリ (既定: {DEFAULT_OUT_DIR})"
    )
    parser.add_argument("--kind", choices=KINDS, default="transition", help="生成する SFX 種別")
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT, help=f"生成数 (既定: {DEFAULT_COUNT})"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_SEC,
        help=f"尺 (秒, 既定: {DEFAULT_DURATION_SEC})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"乱数シード起点 (既定: {DEFAULT_SEED}, 候補ごとに +1 して使う)",
    )
    parser.add_argument(
        "--prompt", type=str, default=None, help="既定プロンプトを上書きする英語プロンプト"
    )
    args = parser.parse_args(argv)

    if args.count <= 0:
        print(f"ERROR: --count は正である必要があります: {args.count}", file=sys.stderr)
        return 1
    if args.duration <= 0:
        print(f"ERROR: --duration は正である必要があります: {args.duration}", file=sys.stderr)
        return 1

    prompt = args.prompt or _DEFAULT_PROMPTS[args.kind]
    try:
        written = generate_candidates(
            kind=args.kind,
            out_dir=args.out,
            count=args.count,
            duration=args.duration,
            seed=args.seed,
            prompt=prompt,
        )
    except GenSfxError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(f"生成完了: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
