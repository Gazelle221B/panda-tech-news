# Source Selection Spike v0.1

> Status: Completed (検証済、2026-05-29)
> Owner: HAL
> Date: 2026-05-29
> Sprint: 1A 前段

## 1. 目的

Sprint 1A の前に、初期収集ソース10本を確定する。

このSpikeの目的は「最良のニュースソースを網羅すること」ではない。目的は、Cookie不要・海外IPから取得可能・RSS/RSSHubで安定取得できる初期ソースを10本選び、収集基盤の検証に使える状態にすることである。

## 2. 判断方針

初期10本は、以下の基準で選ぶ。

- Tier1公式を5本
- Tier2ニュースを3本
- Tier3コミュニティを2本
- Cookie必須ルートは含めない
- Playwright、中国IPプロキシ、ログインCookie依存は含めない
- RSSHubルートは使ってよいが、壊れてもfail-openできる前提にする
- AI比率は高めでよい。Game/Subculture/Anime はSprint 1B以降で拡張する

RSSHubの掘金ルートについては、公式ドキュメント上で `/juejin/category/:category` があり、`ai` がカテゴリ値として示されている。したがって `http://localhost:1200/juejin/category/ai` は候補として妥当である。

## 3. 事前確認で得られた知見

- `https://www.pingwest.com/feed` は 404 を返すため、初期候補から除外する
- `https://www.jiqizhixin.com/rss` は RSS ではなくデータサービスページへリダイレクトされる挙動を示すため、保留扱いとする
- GitHub Atom フィード(`/releases.atom`)は安定しているが、ローカルの curl/feedparser で再確認が必要

## 4. 初期10本(改訂候補)

| # | id | tier | category | enabled | 備考 |
| --- | --- | --- | --- | --- | --- |
| 1 | deepseek-github-releases | 1 | AI | true | DeepSeek公式リリース |
| 2 | qwen-github-releases | 1 | AI | true | Alibaba Qwen公式 (リリース未発行、監視維持) |
| 3 | moonshot-kimi-github | 1 | AI | true | Moonshot/Kimi公式 (リリース未発行、監視維持) |
| 4 | zhipu-glm-github | 1 | AI | true | 智谱AI/清華 GLM (リリース未発行、監視維持) |
| 5 | xiaomi-mimo-github | 1 | AI | true | Xiaomi MiMo公式 (リリース未発行、監視維持) |
| 6 | qbitai-feed | 2 | AI | true | 量子位、机器之心代替 |
| 7 | jiqizhixin-rss | 2 | AI | **false** | 保留、RSS復活時に有効化 |
| 8 | 36kr-newsflash | 2 | Tech | true | 36Kr速報 |
| 9 | huxiu-rss | 2 | Tech | **false** | feedparser bozoエラー、保留 |
| 10 | juejin-ai-category | 3 | AI | true | 掘金AIカテゴリ |
| 11 | juejin-trending-ai-weekly | 3 | AI | true | 掘金週次人気 |

合計11本(うち `enabled: true` が9本、`enabled: false` が2本)。

詳細YAMLは [`config/sources.yaml`](../config/sources.yaml) を参照。

## 5. 除外したソースと理由

| ソース | 理由 | 将来の扱い |
| --- | --- | --- |
| pingwest-rss | `/feed` が 404 | Sprint 1B 以降、別ルートを探す |
| jiqizhixin-rss | `/rss` がデータサービスページへリダイレクト | YAML に `enabled: false` で残置、復活時に有効化 |
| huxiu-rss | feedparser bozo=1 (フィード構造エラー) | YAML に `enabled: false` で残置、RSSHubルート復活時に再検証 |
| huggingface-papers-daily | 中華圏限定ソースではない、公式RSSなし | Sprint 1B 以降、`research_context` グループとして別枠で扱う |
| bilibili UP 主 | UP 主選定に時間がかかる | Sprint 1A 完了後、Game/Subculture 拡張時に追加 |
| 微博 | Cookie 必須ルートが多い | スコープ外、当面追加予定なし |
| 小红书 | RSSHub 仕様変更が頻発 | スコープ外、当面追加予定なし |

## 6. Spike 実行手順

検証は1日で終える。以下の3段階で実施する。

### 6.1 HTTP レスポンス確認

`scripts/spike_curl_check.sh`:

```bash
#!/usr/bin/env bash
# Source Selection Spike v0.1 - HTTP応答確認
# 使い方: bash scripts/spike_curl_check.sh

set -u

URLS=(
  "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"
  "https://github.com/QwenLM/Qwen3/releases.atom"
  "https://github.com/MoonshotAI/Kimi-K2/releases.atom"
  "https://github.com/THUDM/GLM-4/releases.atom"
  "https://github.com/XiaomiMiMo/MiMo/releases.atom"
  "https://www.qbitai.com/feed"
  "https://www.jiqizhixin.com/rss"
  "https://36kr.com/feed-newsflash"
  "https://www.huxiu.com/rss/0.xml"
  "http://localhost:1200/juejin/category/ai"
  "http://localhost:1200/juejin/trending/ai/weekly"
)

for url in "${URLS[@]}"; do
  echo "=== $url ==="
  curl -L -sI -m 15 "$url" | head -10
  echo
done

## 7. 実行結果と採否判断

検証日: 2026-05-29
実行環境: macOS / Colima Docker / RSSHub localhost:1200

### 7.1 curl check (HTTP応答確認)

| ソース | HTTP Status | Content-Type | 判断 |
| --- | --- | --- | --- |
| deepseek-github-releases | 200 | application/atom+xml | OK |
| qwen-github-releases | 200 | application/atom+xml | OK (0エントリ) |
| moonshot-kimi-github | 200 | application/atom+xml | OK (0エントリ) |
| zhipu-glm-github | 301 → 200 | application/atom+xml | OK (0エントリ、リダイレクト先へ自動追従) |
| xiaomi-mimo-github | 200 | application/atom+xml | OK (0エントリ) |
| qbitai-feed | 200 | application/rss+xml | OK |
| jiqizhixin-rss | 302 → 非RSS | text/html | DEFER |
| 36kr-newsflash | 200 | application/rss+xml | OK |
| huxiu-rss | 確認済 | — | feedparserでboゾ判定 |
| juejin-ai-category | 200 | application/xml | OK (RSSHub経由) |
| juejin-trending-ai-weekly | 200 | application/xml | OK (RSSHub経由) |

### 7.2 feedparser check (フィード構造検証)

| id | entries | bozo | verdict | 判断 |
| --- | --- | --- | --- | --- |
| deepseek-github-releases | 1 | 0 | ADOPT | 有効、リリース取得可 |
| qwen-github-releases | 0 | 0 | EMPTY | リリース未発行、監視維持 |
| moonshot-kimi-github | 0 | 0 | EMPTY | リリース未発行、監視維持 |
| zhipu-glm-github | 0 | 0 | EMPTY | リリース未発行、監視維持 |
| xiaomi-mimo-github | 0 | 0 | EMPTY | リリース未発行、監視維持 |
| qbitai-feed | 10 | 0 | ADOPT | 有効、最新10件取得可 |
| jiqizhixin-rss | 0 | 1 | DEFER | RSS廃止、データサービスへリダイレクト |
| 36kr-newsflash | 20 | 0 | ADOPT | 有効、最新20件取得可 |
| huxiu-rss | 0 | 1 | DEFER | フィード構造エラー(bozo=1) |
| juejin-ai-category | 20 | 0 | ADOPT | 有効、RSSHub経由で正常 |
| juejin-trending-ai-weekly | 20 | 0 | ADOPT | 有効、RSSHub経由で正常 |

### 7.3 最終採否と enabled 確定

| id | tier | enabled | 理由 |
| --- | --- | --- | --- |
| deepseek-github-releases | 1 | **true** | 唯一リリースがあるTier1 |
| qwen-github-releases | 1 | **true** | EMPTYだがリリース発行時に自動取得、監視維持 |
| moonshot-kimi-github | 1 | **true** | EMPTYだがリリース発行時に自動取得、監視維持 |
| zhipu-glm-github | 1 | **true** | EMPTYだがリリース発行時に自動取得、監視維持 |
| xiaomi-mimo-github | 1 | **true** | EMPTYだがリリース発行時に自動取得、監視維持 |
| qbitai-feed | 2 | **true** | ADOPT、机器之心代替 |
| jiqizhixin-rss | 2 | **false** | DEFER、RSS復活時に有効化 |
| 36kr-newsflash | 2 | **true** | ADOPT、速報ソース |
| huxiu-rss | 2 | **false** | DEFER、feedparser bozoエラー |
| juejin-ai-category | 3 | **true** | ADOPT、RSSHub経由正常 |
| juejin-trending-ai-weekly | 3 | **true** | ADOPT、RSSHub経由正常 |

有効ソース: 9本 (Tier1×5 + Tier2×2 + Tier3×2)
保留ソース: 2本 (jiqizhixin-rss, huxiu-rss)

`config/sources.yaml` は本結果に基づき更新済。
