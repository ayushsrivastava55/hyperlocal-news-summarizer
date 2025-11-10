"""
Feed Discovery using SerpAPI
 - Discover RSS-like URLs for a given city via Google search
 - Fetch city news via Google News engine as a fallback
"""

import os
import logging
from typing import List, Dict
import requests

logger = logging.getLogger(__name__)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERPAPI_BASE = "https://serpapi.com/search.json"


def _require_api_key():
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY is not configured in environment.")


def discover_feeds_by_city(city: str, max_results: int = 8) -> List[Dict]:
    """
    Use SerpAPI Google search to discover potential RSS/feed URLs for a city.
    Heuristics: search queries targeting 'rss' and 'feed' keywords on well-known news domains.
    """
    _require_api_key()
    if not city or not city.strip():
        return []

    queries = [
        f"site:indiatimes.com rss {city}",
        f"site:timesofindia.indiatimes.com rssfeeds {city}",
        f"site:thehindu.com rss {city}",
        f"site:zeenews.india.com rss {city}",
        f"site:hindustantimes.com rss {city}",
        f"site:news {city} inurl:rss",
        f"{city} news rss",
    ]

    headers = {"User-Agent": "Mozilla/5.0"}
    discovered: Dict[str, Dict] = {}

    for q in queries:
        try:
            params = {
                "engine": "google",
                "q": q,
                "api_key": SERPAPI_API_KEY,
                "num": 10,
                "hl": "en",
                "gl": "in",
            }
            resp = requests.get(SERPAPI_BASE, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("organic_results", []):
                link = item.get("link", "")
                title = item.get("title", "") or item.get("displayed_link", "")
                if not link:
                    continue
                # Heuristic: consider links that look like RSS or feed endpoints
                if any(tok in link.lower() for tok in ["rss", "rssfeeds", "feed", ".xml", ".rss", ".atom"]):
                    if link not in discovered:
                        discovered[link] = {"name": title or link, "url": link}
                if len(discovered) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"SerpAPI discover error for query '{q}': {e}")
        if len(discovered) >= max_results:
            break

    return list(discovered.values())[:max_results]


def fetch_city_news_via_serpapi(city: str, max_results: int = 10) -> List[Dict]:
    """
    Use SerpAPI Google News engine to fetch recent news for a city.
    Returns a list of article-like dictionaries compatible with our pipeline.
    """
    _require_api_key()
    if not city or not city.strip():
        return []

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        params = {
            "engine": "google_news",
            "q": f"{city} news",
            "api_key": SERPAPI_API_KEY,
            "hl": "en",
            "gl": "in",
            "num": max_results,
        }
        resp = requests.get(SERPAPI_BASE, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        news_results = data.get("news_results", []) or []
        articles: List[Dict] = []
        for item in news_results[:max_results]:
            title = item.get("title", "")
            link = item.get("link", "")
            source = (item.get("source", {}) or {}).get("name") or item.get("source")
            date = item.get("date", "") or item.get("date_utc", "")
            snippet = item.get("snippet", "")
            if not link or not title:
                continue
            articles.append({
                "title": title,
                "description": snippet,
                "link": link,
                "published": date,
                "source": source or "SerpAPI News",
                "feed_type": "SERPAPI_NEWS",
                "raw_content": f"{title} {snippet}",
            })
        return articles
    except Exception as e:
        logger.error(f"SerpAPI city news error: {e}")
        return []


