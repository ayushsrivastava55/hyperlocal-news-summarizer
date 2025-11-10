"""
API Smoke Test for Hyperlocal News Summarizer
"""

import sys
import time
import json
import argparse
import requests

DEFAULT_BASE = "http://localhost:5001"

DEFAULT_FEEDS = [
    {
        "type": "RSS",
        "url": "https://www.lokmat.com/rss/nagpur/",
        "name": "Lokmat Nagpur"
    },
    {
        "type": "RSS",
        "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms",
        "name": "Times of India Nagpur"
    },
    {
        "type": "RSS",
        "url": "https://www.thehitavada.com/rss",
        "name": "Hitavada Nagpur"
    }
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base URL of the running server")
    parser.add_argument("--limit_per_feed", default=3, type=int)
    parser.add_argument("--max_total", default=5, type=int)
    args = parser.parse_args()

    base = args.base.rstrip("/")
    print(f"🔎 Testing API at {base}")

    # 1) Health
    r = requests.get(f"{base}/api/health", timeout=10)
    r.raise_for_status()
    print("✅ /api/health OK:", r.json())

    # 2) Collect only
    r = requests.post(
        f"{base}/api/collect",
        json={"feed_configs": DEFAULT_FEEDS, "limit_per_feed": args.limit_per_feed},
        timeout=20,
    )
    r.raise_for_status()
    collected = r.json()
    print(f"✅ /api/collect OK: collected={collected.get('count')}")
    assert collected.get("count", 0) > 0, "No articles collected from live feeds"

    # 3) Process (full pipeline, limited)
    print("⏳ /api/process (this may take time on first run for model download)...")
    r = requests.post(
        f"{base}/api/process",
        json={
            "feed_configs": DEFAULT_FEEDS,
            "limit_per_feed": args.limit_per_feed,
            "max_total": args.max_total,
        },
        timeout=600,
    )
    r.raise_for_status()
    processed = r.json()
    print(f"✅ /api/process OK: processed={processed.get('articles_processed')}")
    assert processed.get("articles_processed", 0) > 0, "No articles processed"

    # 4) Stats
    r = requests.get(f"{base}/api/stats", timeout=10)
    r.raise_for_status()
    print("✅ /api/stats OK:", r.json())

    # 5) Report
    r = requests.get(f"{base}/api/report", params={"location": "Nagpur"}, timeout=10)
    r.raise_for_status()
    report = r.json()
    print(f"✅ /api/report OK: total_articles={report.get('report_metadata', {}).get('total_articles')}")

    print("\n🎉 Smoke tests passed.")


if __name__ == "__main__":
    main()


