# assets/sfx/ — オープニング/トランジション/エンディング SFX (T62, Issue #65)

`transition.wav` (2.0s) / `opening.wav` (4.0s) / `ending.wav` (3.0s) は Stable Audio 3
Small-SFX (`stabilityai/stable-audio-3-small-sfx`, `scripts/gen_sfx.py` で生成, Stability
Community License) による候補からプロダクトオーナーが 2026-08-01 に選定した確定音源で、
ピーク -3dBFS に正規化済み。内容: `transition` = マリンバ2音のドライなスティンガー、
`opening` = エレピ+パルスの立ち上がり、`ending` = 解決コードで締める短いフレーズ。
`config/show_format.yaml` の `sfx.{transition,opening,ending}` が参照し、`sfx.enabled: true`
(既定) で `mix/transitions.py::concat_with_transitions` が produce の完パケに挿入する。

ライセンスは Stability AI Community License (HuggingFace 上は Gated リポジトリのため生成には
ライセンス同意 + `hf auth login` が必要)。同ライセンスは非商用・研究利用は無償、商用利用も
年間売上 $1M 未満の組織は無償だが、それ以上は Stability AI とのエンタープライズ契約が必要と
いう条件。配信規模が変わった場合は本条件を満たすか都度確認すること。

新規候補が必要な場合は `uv run python scripts/gen_sfx.py --kind transition|opening|ending
--count 3` などで生成 → プロダクトオーナーが試聴 → 採用した1本でこのディレクトリの該当
ファイルを置き換える。
