"""Source Selection Spike v0.1 - feedparser検証

使い方: uv run python scripts/spike_feedparser_check.py
"""
# /// script
# dependencies = [
#     "feedparser",
# ]
# ///
import feedparser  # type: ignore[import-untyped]

URLS = [
    ("deepseek-github-releases",         "https://github.com/deepseek-ai/DeepSeek-V3/releases.atom"),
    ("qwen-github-releases",             "https://github.com/QwenLM/Qwen3/releases.atom"),
    ("moonshot-kimi-github",             "https://github.com/MoonshotAI/Kimi-K2/releases.atom"),
    ("zhipu-glm-github",                 "https://github.com/THUDM/GLM-4/releases.atom"),
    ("xiaomi-mimo-github",               "https://github.com/XiaomiMiMo/MiMo/releases.atom"),
    ("qbitai-feed",                      "https://www.qbitai.com/feed"),
    ("jiqizhixin-rss",                   "https://www.jiqizhixin.com/rss"),
    ("36kr-newsflash",                   "https://36kr.com/feed-newsflash"),
    ("huxiu-rss",                        "https://www.huxiu.com/rss/0.xml"),
    ("juejin-ai-category",               "http://localhost:1200/juejin/category/ai"),
    ("juejin-trending-ai-weekly",        "http://localhost:1200/juejin/trending/ai/weekly"),
]

print(f"{'id':<32} {'entries':>8} {'bozo':>5} {'latest':<32} {'verdict':<10}")
print("-" * 100)

for source_id, url in URLS:
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "karyu-tech-news-spike/0.1"})
        entries = len(feed.entries)
        bozo = 1 if feed.bozo else 0
        latest = ""
        if entries > 0:
            latest = feed.entries[0].get("published", feed.entries[0].get("updated", ""))

        if entries >= 1:
            verdict = "ADOPT"
        elif entries == 0 and bozo == 0:
            verdict = "EMPTY"
        else:
            verdict = "DEFER"

        print(f"{source_id:<32} {entries:>8} {bozo:>5} {str(latest)[:30]:<32} {verdict:<10}")
    except Exception as e:
        print(f"{source_id:<32} {'ERROR':>8} {'-':>5} {str(e)[:30]:<32} {'DEFER':<10}")
