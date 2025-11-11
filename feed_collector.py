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

    def __init__(self, scrape_full_content: bool = True):
        """
        Initialize feed collector

        Args:
            scrape_full_content: Whether to scrape full article content from URLs (default: True)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.scrape_full_content = scrape_full_content
    
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

                # Scrape full article content if enabled
                full_content = ""
                if hasattr(self, 'scrape_full_content') and self.scrape_full_content and entry.get('link'):
                    logger.info(f"Scraping full content from: {entry.get('link')}")
                    full_content = self.scrape_article_content(entry.get('link'))
                    if full_content:
                        import time
                        time.sleep(0.5)  # Be polite, don't hammer servers
                        
                        # Validate scraped content: if it contains too much navigation text, use RSS description instead
                        nav_indicators = ['subscribe', 'login', 'newsletter', 'e-paper', 'back to the page', 'use the weekly']
                        nav_count = sum(1 for phrase in nav_indicators if phrase in full_content.lower())
                        if nav_count >= 2 or len(full_content) < 200:
                            logger.warning(f"Scraped content appears to be mostly navigation, using RSS description instead")
                            full_content = ""  # Fall back to RSS description

                # Use full content if available and good, otherwise use description
                content_text = full_content if full_content and len(full_content) > 200 else desc_text

                article = {
                    'title': entry.get('title', ''),
                    'description': content_text,  # Now contains full article if scraped
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'source': source_name,
                    'feed_type': 'RSS',
                    'raw_content': f"{entry.get('title', '')} {content_text}",
                    'scraped': bool(full_content)
                }
                articles.append(article)
            
            logger.info(f"Collected {len(articles)} articles from {source_name}")
            
        except Exception as e:
            logger.error(f"Error collecting RSS feed {feed_url}: {str(e)}")
        
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

            # Remove script, style, nav, footer, ads, menus, headers
            for tag in soup(['script', 'style', 'nav', 'footer', 'iframe', 'aside', 'header', 'menu', 'form', 'button', 'noscript']):
                tag.decompose()

            # Remove common ad/navigation classes and IDs
            unwanted_selectors = [
                '[class*="advertisement"]', '[class*="ad-"]', '[class*="sidebar"]',
                '[class*="menu"]', '[class*="nav"]', '[class*="footer"]',
                '[class*="header"]', '[class*="social"]', '[class*="share"]',
                '[class*="related"]', '[class*="trending"]', '[class*="subscribe"]',
                '[class*="newsletter"]', '[class*="login"]', '[class*="sign"]',
                '[id*="ad"]', '[id*="sidebar"]', '[id*="menu"]', '[id*="nav"]',
                '[id*="footer"]', '[id*="header"]'
            ]
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # Site-specific selectors (The Hindu, TOI, etc.)
            content_selectors = [
                # The Hindu specific
                'div[data-template="article"]',
                '.article-body',
                '.article-content',
                '[itemprop="articleBody"]',
                # Generic article selectors
                'article',
                '.story-content',
                '.post-content',
                '.entry-content',
                '#article-body',
                '.content-body',
                'main article',
                '.article-text'
            ]

            article_text = ""

            # Try each selector
            for selector in content_selectors:
                try:
                    content = soup.select_one(selector)
                    if content:
                        # Get all paragraphs within the content area
                        paragraphs = content.find_all('p')
                        if paragraphs:
                            # Filter paragraphs: must be substantial (>30 chars) and not navigation
                            filtered_paras = []
                            nav_phrases = ['subscribe', 'login', 'sign in', 'newsletter', 'e-paper', 'edition', 
                                         'back to', 'use the', 'click here', 'read more', 'related articles']
                            
                            for p in paragraphs:
                                text = p.get_text(strip=True)
                                # Skip if too short or contains navigation phrases
                                if len(text) > 30 and not any(phrase in text.lower() for phrase in nav_phrases):
                                    # Skip if it's mostly uppercase (likely navigation)
                                    if not (text.isupper() and len(text) < 100):
                                        filtered_paras.append(text)
                            
                            if filtered_paras:
                                article_text = ' '.join(filtered_paras)
                                if len(article_text) > 200:  # Found substantial content
                                    break
                except:
                    continue

            # Fallback: get paragraphs from body, but filter aggressively
            if not article_text or len(article_text) < 200:
                body = soup.find('body')
                if body:
                    paragraphs = body.find_all('p')
                    filtered_paras = []
                    nav_phrases = ['subscribe', 'login', 'sign in', 'newsletter', 'e-paper', 'edition',
                                 'back to', 'use the', 'click here', 'read more', 'related', 'trending',
                                 'the hindu', 'november', 'daily mail', 'account', 'ebooks']
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # More aggressive filtering for fallback
                        if (len(text) > 50 and 
                            not any(phrase in text.lower() for phrase in nav_phrases) and
                            not text.isupper() and
                            not text.startswith('LOGIN') and
                            not text.startswith('Subscribe')):
                            filtered_paras.append(text)
                    
                    article_text = ' '.join(filtered_paras[:20])  # Limit to first 20 paragraphs

            # Clean up extra whitespace
            article_text = ' '.join(article_text.split())

            # Remove navigation text patterns at the start
            nav_patterns = [
                r'^.*?The Hindu.*?e-Paper.*?',
                r'^.*?LOGIN.*?Account.*?',
                r'^.*?Subscribe.*?GIFT.*?',
                r'^.*?Back to the page.*?',
                r'^.*?Use the.*?',
            ]
            import re
            for pattern in nav_patterns:
                article_text = re.sub(pattern, '', article_text, flags=re.IGNORECASE | re.DOTALL)

            # Find the first substantial sentence (skip navigation)
            sentences = article_text.split('.')
            clean_sentences = []
            for sent in sentences:
                sent = sent.strip()
                if (len(sent) > 50 and 
                    not any(phrase in sent.lower() for phrase in ['subscribe', 'login', 'newsletter', 'e-paper', 'back to', 'use the']) and
                    not sent.isupper()):
                    clean_sentences.append(sent)
            
            article_text = '. '.join(clean_sentences)

            # Final cleanup: remove if starts with navigation
            if article_text:
                first_100 = article_text[:100].lower()
                if any(phrase in first_100 for phrase in ['subscribe', 'login', 'newsletter', 'e-paper', 'the hindu november']):
                    # Find first real sentence
                    for i, sent in enumerate(clean_sentences):
                        if len(sent) > 100 and not any(phrase in sent.lower()[:50] for phrase in ['subscribe', 'login', 'newsletter']):
                            article_text = '. '.join(clean_sentences[i:])
                            break

            return article_text[:5000] if article_text else ""  # Limit to 5000 chars

        except Exception as e:
            logger.warning(f"Failed to scrape content from {url}: {e}")
            return ""

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


# Default feed configurations (All URLs Verified)
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

