#!/usr/bin/env bash
# Source Selection Spike v0.1 - HTTP応答確認
# 使い方: bash scripts/spike_curl_check.sh
# 参照:   docs/source-selection-spike-v0.1.md §6.1
#
# 採否の目安:
#   200 が返り Content-Type が xml/atom 系     → ADOPT 候補
#   301/302 でフィード以外へリダイレクト        → DEFER (例: jiqizhixin /rss)
#   403/404/timeout                            → DEFER

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
