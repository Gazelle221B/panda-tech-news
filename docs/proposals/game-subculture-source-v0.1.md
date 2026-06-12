# 提案: Game/Subculture 系予備ソースの追加候補 v0.1

> ステータス: **人間判断待ち** ([PROJECT_STATE.md](../PROJECT_STATE.md) 人間判断待ち項目「初期9本に Game/Subculture 系を1本予備で入れるか」= [Spike §3 B案](../source-selection-spike-v0.1.md))。
> 採用判断・enabled 化は人間。採用時の sources.yaml 追加 + `validate-sources` + 数日の collect 観察は別チケット。

## 背景 (なぜ今この判断材料か)

- 番組アークは締めに **bright (ゲーム/サブカルの明るい話題)** を要求する ([config/show_format.yaml](../../config/show_format.yaml) `arc.close`)。
- 現行 9 ソースは AI/Tech 系のみで **Game 専門ソースが 0 本** — bright 候補は総合系の偶発記事に依存しており、T22 観察でも bright 枠の品質はこの構成に律速される。
- スキーマは `SourceCategory.GAME` / `SUBCULTURE` を既に定義済み ([config.py](../../src/karyu_tech_news/config.py)) — 設計上は受け入れ準備完了。

## 調査と検証 (2026-06-12)

調査: Gemini CLI (検索グラウンディング) に候補抽出を委任 → セルフホスト RSSHub (`localhost:1200`) で**実取得検証** (Claude Code)。

| 候補 | RSSHub ルート | 実検証結果 | 評価 |
|---|---|---|---|
| **IndieNova (indienova.com)** | `/indienova/article`・`/indienova/news` | **HTTP 200・各 12 件取得成功** | ✅ **第一候補**。インディーゲーム/サブカル、ポジティブ話題中心、「AI×ゲーム制作」の交差点記事が bright 枠に合致。更新頻度 低〜中だが bright 枠は 1 日 1 本で足りる |
| 游研社 (yystv.cn) | `/yystv/docs` | **HTTP 503** | ❌ 現セルフホスト構成で取得不可。調査評価は最有力だったが、503 解消には RSSHub 側の追加構成 (puppeteer 等) が必要な可能性 — Sprint 1B の §3.4 (Playwright/Cookie 必須ルート禁止の精神) に照らし深追いしない |
| 机核 GCORES (gcores.com) | `/gcores/category/1` | **HTTP 503** | ❌ 同上。長文記事が多く要約コスト高の懸念も |
| 触乐 (chuapp.com) | — | 未検証 | 社会派 (規制・労働環境) 寄りで bright 目的に不適 (調査評)。除外 |

## 推薦

**IndieNova を `enabled: false` で追加し、人間が有効化を判断する** (Spike 時の「監視」運用と同じ入り方)。採用時のスニペット:

```yaml
  # ===== Tier3 RSSHub (Game/Subculture 予備, Spike §3 B案) =====
  - id: indienova-article
    name: IndieNova 文章
    url: "http://localhost:1200/indienova/article"
    tier: 3
    category: Game
    enabled: false
    requires_cookie: false
    notes: "インディーゲーム/サブカル。arc close=bright 用。2026-06-12 セルフホスト RSSHub 検証 HTTP 200 (12件)。有効化は人間判断。"
```

- tier 3 の根拠: RSSHub 経由の準一次メディア (掘金と同じ扱い)。Tier3 は編集ゲートで独立 2 ソース確認の対象 ([edit/select.py](../../src/karyu_tech_news/edit/select.py)) のため、誤報リスクは既存の防御で吸収される。
- 判断不要なケース: T22 観察で bright 枠が現行 9 本で十分賄えていれば、追加自体を見送ってよい (その判定材料は `evaluate` と TEST_LOG の T22 記録にある)。

## リスク
- 更新が少ない日は bright 候補ゼロ → 既存どおり総合系から bright を拾う (現状と同じ。悪化はしない)。
- RSSHub ルートの将来的な仕様変更 → fail-open (FR-060) と `source_health` 監視で検知できる。
