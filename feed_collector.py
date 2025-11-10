"""
Feed Collector Module
Collects news from RSS feeds and APIs
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedCollector:
    """Collects news articles from RSS feeds and APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect_rss_feed(self, feed_url: str, source_name: str, limit: int = 10) -> List[Dict]:
        """
        Collect articles from RSS feed
        
        Args:
            feed_url: URL of the RSS feed
            source_name: Name of the news source
            
        Returns:
            List of article dictionaries
        """
        articles = []
        try:
            # Fetch with browser-like headers to avoid being blocked
            resp = self.session.get(feed_url, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            
            for entry in feed.entries[:limit]:  # Limit articles per feed
                raw_desc = entry.get('description', '')
                # Clean HTML from descriptions to avoid broken UI markup
                desc_text = BeautifulSoup(raw_desc, 'html.parser').get_text(separator=' ', strip=True)
                article = {
                    'title': entry.get('title', ''),
                    'description': desc_text,
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': source_name,
                    'feed_type': 'RSS',
                    'raw_content': f"{entry.get('title', '')} {desc_text}"
                }
                articles.append(article)
            
            logger.info(f"Collected {len(articles)} articles from {source_name}")
            
        except Exception as e:
            logger.error(f"Error collecting RSS feed {feed_url}: {str(e)}")
        
        return articles
    
    def collect_api_news(self, api_url: str, api_key: Optional[str] = None, 
                        source_name: str = "API Source", limit: int = 10) -> List[Dict]:
        """
        Collect articles from news API
        
        Args:
            api_url: API endpoint URL
            api_key: Optional API key
            source_name: Name of the news source
            
        Returns:
            List of article dictionaries
        """
        articles = []
        try:
            headers = {}
            if api_key:
                headers['X-API-Key'] = api_key
            
            response = self.session.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different API response formats
            if 'articles' in data:
                items = data['articles']
            elif 'results' in data:
                items = data['results']
            else:
                items = data if isinstance(data, list) else []
            
            for item in items[:limit]:  # Limit to N articles
                raw_desc = item.get('description', '') or item.get('summary', '')
                desc_text = BeautifulSoup(raw_desc, 'html.parser').get_text(separator=' ', strip=True)
                article = {
                    'title': item.get('title', ''),
                    'description': desc_text,
                    'link': item.get('url', '') or item.get('link', ''),
                    'published': item.get('publishedAt', '') or item.get('published', ''),
                    'source': source_name,
                    'feed_type': 'API',
                    'raw_content': f"{item.get('title', '')} {desc_text}"
                }
                articles.append(article)
            
            logger.info(f"Collected {len(articles)} articles from {source_name} API")
            
        except Exception as e:
            logger.error(f"Error collecting API news {api_url}: {str(e)}")
        
        return articles
    
    def scrape_article_content(self, url: str) -> str:
        """
        Scrape full article content from URL
        
        Args:
            url: Article URL
            
        Returns:
            Full article text
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find article content
            article = soup.find('article')
            if article:
                return article.get_text(separator=' ', strip=True)
            
            # Fallback to body text
            return soup.get_text(separator=' ', strip=True)
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {str(e)}")
            return ""
    
    def collect_multiple_feeds(self, feed_configs: List[Dict], per_feed_limit: Optional[int] = None) -> List[Dict]:
        """
        Collect from multiple RSS feeds and APIs
        
        Args:
            feed_configs: List of feed configurations
                [{'type': 'RSS', 'url': '...', 'name': '...'}, ...]
                
        Returns:
            Combined list of all articles
        """
        all_articles = []
        
        for config in feed_configs:
            feed_type = config.get('type', 'RSS').upper()
            
            if feed_type == 'RSS':
                articles = self.collect_rss_feed(
                    config['url'],
                    config.get('name', 'Unknown Source'),
                    limit=per_feed_limit or 10
                )
            elif feed_type == 'API':
                articles = self.collect_api_news(
                    config['url'],
                    config.get('api_key'),
                    config.get('name', 'Unknown Source'),
                    limit=per_feed_limit or 10
                )
            else:
                logger.warning(f"Unknown feed type: {feed_type}")
                continue
            
            all_articles.extend(articles)
        
        logger.info(f"Total articles collected: {len(all_articles)}")
        return all_articles


# Default feed configurations (All URLs Verified ✅)
NAGPUR_FEED_CONFIGS = [
    {
        'type': 'RSS',
        'url': 'https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms',
        'name': 'Times of India - Bengaluru'
    },
    {
        'type': 'RSS',
        'url': 'https://www.thehindu.com/news/national/feeder/default.rss',
        'name': 'The Hindu - National'
    },
    {
        'type': 'RSS',
        'url': 'https://zeenews.india.com/rss/india-news.xml',
        'name': 'Zee News - India'
    }
]

