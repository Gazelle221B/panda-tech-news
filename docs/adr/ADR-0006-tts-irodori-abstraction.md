# ADR-0006: TTS は Irodori-TTS v3 を主軸とし、エンジン抽象化レイヤーを噛ませる

- 日付: 2026-05-26 / 確定 2026-05-28
- ステータス: Accepted (実装は Sprint 2、声リファレンスは検証項目)
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §8.10 FR-090〜092, [meeting.md](../meeting.md) §8, [hal-persona.md](../hal-persona.md)

## 背景

ポッドフィキャストである以上、最終出力は音声。TTS の進化は半年〜1年スパンで連続して起きており (Irodori v3, CosyVoice3, Fish S2 Pro, Kokoro 等)、**今日のベストが3ヶ月後も最適とは限らない**。一方、毎日同じ声で配信するには声の固定が要る。配信言語は日本語 (中国情報を日本語で語る) なので、日本語品質が最優先。

## 決定

1. **主軸を Irodori-TTS v3** (Aratako/Irodori-TTS-500M-v3) とする。
2. **`TTSEngine` インターフェース層**を1枚噛ませ、エンジンを差し替え可能にする (FR-090)。
3. **HAL の人格定義は TTS 非依存**で保持 (FR-091, [hal-persona.md](../hal-persona.md))。エンジンが変わっても声を維持。
4. **VoiceDesign → Speaker Inversion で声を固定**する方針は**実装フェーズの検証項目**であり確定仕様ではない (要件 §2.3)。

## Irodori-TTS v3 を主軸とする根拠

- **日本語専用設計** (llm-jp トークナイザ最適化)。多言語 TTS の「日本語もできる」ではない。
- **OpenAI API 互換サーバー** (Aratako/Irodori-TTS-Server, `POST /v1/audio/speech`) — 既存の OpenAI 互換クライアント構造を薄いラッパーで流用でき、新クライアント不要。
- **絵文字によるスタイル制御** — tc-newsflow の tone 判定 (hard_negative/constructive/bright) を絵文字注釈に変換して感情を載せられる ([architecture §4](../architecture-podcast-station.md))。
- **500M という絶妙なサイズ** — RTX 4070 Ti Super でリアルタイムの1.6倍合成。日次運用に十分。
- **ゼロショット音声クローン** で番組専用の声を固定可能。
- **MIT ライセンス** (商用可)。

## Irodori-TTS v3 の弱点と対策

| 弱点 | 対策 |
|---|---|
| 漢字読み精度が同サイズ他モデル比で弱い (公式明記) | **読み仮名辞書** (FR-092, `config/reading_dict.yaml`) を Sprint 2 で整備。中国企業名/モデル名/人名/ゲーム名/アニメ名/地名のカナを制御 |
| 絵文字制御の効きがコンテキスト依存 | 本番運用で聴いてフィードバック調整 (半年スパン想定) |
| 男性アンカー声がやや弱い | HAL は中性的女性なので当面問題なし。男女ペアが必要になったら別エンジン併用 |
| 個人開発・コミュニティが小さい | 抽象化レイヤーで代替エンジンへ退避可能にしておく |

## エンジン抽象化

```python
class TTSEngine(Protocol):
    def synthesize(self, req: SynthesisRequest) -> SynthesisResult: ...
    def voices(self) -> list[Voice]: ...
    def name(self) -> str: ...
    def capabilities(self) -> Capabilities: ...
```
設定でエンジン選択、更新時はアダプタ書き換えのみ。台本生成・ffmpeg 合成レイヤーは無傷。エンジン横断の周辺処理 (テキスト正規化、SSML 風タグ解釈、長文分割、ピッチ/速度の事後調整) も抽象化レイヤーに置く。

### ジャンル別 / 用途別エンジン戦略
| エンジン | ライセンス | 用途 |
|---|---|---|
| **Irodori-TTS v3** | MIT | メイン (ニュース) |
| Kokoro 82M | Apache 2.0 | fallback・英語固有名詞用 |
| Fish S2 Pro | — | ボイスドラマ特別回 (将来投資) |
| CosyVoice 3 | Apache 2.0 | 声クローン用 (将来) |
| Style-Bert-VITS2 / AivisSpeech | — | 差し替え候補 |

## 影響

- Sprint 2 で `tts/` に `engine.py` (Protocol) + `irodori.py` (実装) を作る。
- HAL の声リファレンス確定は Sprint 2 開始時。当面 VoiceDesign キャプション ([hal-persona.md](../hal-persona.md) の声質仕様) から合成して試聴 → Speaker Inversion 化を検証。
- Sprint 1A/1B では TTS を一切実装しない (ADR-0002 スコープ分離)。

## 不採用案

- **中国語 TTS で中国語配信**: 配信言語は日本語と確定 (要件)。中国語ネイティブ TTS (CosyVoice/IndexTTS) は不要。
- **多言語 TTS 単独 (Fish/CosyVoice を主軸)**: 日本語特化の Irodori の方がニュース読みの自然さで有利。Fish は重く日次運用にオーバー。
- **エンジン直結 (抽象化なし)**: TTS 進化が速く、直結すると乗り換えのたびに合成・配信層まで影響する。
