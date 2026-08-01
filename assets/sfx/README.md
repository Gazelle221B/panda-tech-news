# assets/sfx/ — トピック間トランジション SFX (T62, Issue #65)

候補音源は `scripts/gen_sfx.py`(Stable Audio 3 Small-SFX, `stabilityai/stable-audio-3-small-sfx`)で生成する。モデルは Stability AI Community License 配布(HuggingFace 上は Gated リポジトリのためライセンス同意 + `hf auth login` が必要)。同ライセンスは非商用・研究利用は無償、商用利用も年間売上 $1M 未満の組織は無償だが、それ以上は Stability AI とのエンタープライズ契約が必要という条件。採用にあたっては本条件を満たすか都度確認すること。

採用手順: `uv run python scripts/gen_sfx.py --kind transition --count 3` などで候補を生成 → プロダクトオーナーが試聴 → 採用した1本を `transition.wav`(`config/show_format.yaml` の `sfx.transition` が参照するパス)としてこのディレクトリへ配置 → `sfx.enabled: true` に切り替える(Issue #65 スコープB)。

このディレクトリ内の `*.wav` は `.gitignore` により追跡対象外(素材本体はコミットしない、配置のみ管理)。
