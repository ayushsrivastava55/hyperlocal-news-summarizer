"""
Main Workflow Orchestrator
Coordinates all modules for hyperlocal news processing
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from dateutil import parser as date_parser
from feed_collector import FeedCollector, NAGPUR_FEED_CONFIGS
from translator import NewsTranslator
from nlp_processor import NLPProcessor
from geo_tagger import GeoTagger
from voice_synthesizer import VoiceSynthesizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HyperlocalNewsWorkflow:
    """Main workflow for processing hyperlocal news"""
    
    def __init__(self, target_languages: List[str] = ['en', 'mr', 'hi'], fast_mode: bool = False):
        """
        Initialize workflow components
        
        Args:
            target_languages: List of target languages for translation
            fast_mode: Use faster light-weight processing (no HF model, limited geocoding, skip audio)
        """
        self.feed_collector = FeedCollector()
        self.translator = NewsTranslator()
        self.fast_mode = fast_mode
        self.nlp_processor = NLPProcessor(fast_mode=self.fast_mode)
        self.geo_tagger = GeoTagger()
        self.voice_synthesizer = VoiceSynthesizer()
        self.target_languages = target_languages
    
    def process_single_article(self, article: Dict) -> Dict:
        """
        Process a single article through the complete pipeline
        
        Args:
            article: Raw article dictionary
            
        Returns:
            Fully processed article with all features
        """
        logger.info(f"Processing article: {article.get('title', 'Unknown')[:50]}...")
        
        # Step 1: Translate to target languages
        translated_article = self.translator.translate_article(
            article, 
            self.target_languages
        )
        
        # Step 2: Generate summary and extract entities
        processed_article = self.nlp_processor.process_article(
            translated_article,
            target_language='en'  # Process in English for better NLP results
        )
        # Translate summary to target languages for multi-language display
        try:
            ai_summary_en = processed_article.get('ai_summary', '')
            if ai_summary_en:
                # Ensure translations dict exists
                if 'translations' not in processed_article:
                    processed_article['translations'] = {}
                # English summary
                processed_article['translations'].setdefault('en', {})
                processed_article['translations']['en']['summary'] = ai_summary_en
                # Other languages
                for lang in self.target_languages:
                    if lang == 'en':
                        continue
                    try:
                        trans = self.translator.translate_text(ai_summary_en, target_lang=lang, source_lang='en')
                        processed_article['translations'].setdefault(lang, {})
                        processed_article['translations'][lang]['summary'] = trans.get('translated_text', ai_summary_en)
                    except Exception:
                        # Skip on per-language failure
                        continue
        except Exception:
            pass
        
        # Step 3: Geo-tag the article
        geo_tagged = self.geo_tagger.tag_article(
            processed_article,
            entities=processed_article,
            fast=self.fast_mode
        )
        
        # Step 4: Generate voice summaries
        final_article = self.voice_synthesizer.generate_multilingual_audio(
            geo_tagged,
            languages=self.target_languages,
            skip=self.fast_mode
        )
        
        # Add metadata
        final_article['processed_at'] = datetime.now().isoformat()
        final_article['workflow_version'] = '1.0'
        
        return final_article
    
    def process_feeds(self, feed_configs: List[Dict] = None, limit_per_feed: int = 5, max_total: int = None, seen_links: Optional[Set[str]] = None, offset: int = 0) -> List[Dict]:
        """
        Process multiple feeds through the complete pipeline
        
        Args:
            feed_configs: List of feed configurations (uses default if None)
            
        Returns:
            List of fully processed articles
        """
        if feed_configs is None:
            feed_configs = NAGPUR_FEED_CONFIGS
        
        logger.info(f"Starting workflow with {len(feed_configs)} feeds")
        
        # Step 1: Collect articles
        raw_articles = self.feed_collector.collect_multiple_feeds(feed_configs, per_feed_limit=limit_per_feed)
        logger.info(f"Collected {len(raw_articles)} raw articles")

        # Step 1b: Normalize, sort (newest first), dedupe, and drop already-seen links
        def _parse_dt(s: str):
            try:
                return date_parser.parse(s)
            except Exception:
                return None

        # sort by published desc when available
        raw_articles.sort(key=lambda a: (_parse_dt(a.get('published', '')) or 0), reverse=True)

        deduped = []
        seen_local: Set[str] = set()
        external_seen = seen_links or set()
        for item in raw_articles:
            link = (item.get('link') or '').strip()
            key = link or f"{item.get('title','')}-{item.get('published','')}"
            if not key or key in seen_local or key in external_seen:
                continue
            seen_local.add(key)
            deduped.append(item)

        # apply offset and max_total window
        if offset > 0:
            deduped = deduped[offset:]
        if max_total:
            deduped = deduped[:max_total]
        logger.info(f"After dedupe/filter: {len(deduped)} articles remaining")
        
        # Step 2: Process each article
        processed_articles = []
        for i, article in enumerate(raw_articles, 1):
            try:
                processed = self.process_single_article(article)
                processed_articles.append(processed)
                logger.info(f"Processed article {i}/{len(raw_articles)}")
            except Exception as e:
                logger.error(f"Error processing article {i}: {str(e)}")
                continue
        
        logger.info(f"Workflow complete: {len(processed_articles)} articles processed")
        return processed_articles
    
    def analyze_sentiment_tone(self, text: str) -> Dict:
        """
        Analyze sentiment and tone of article
        
        Args:
            text: Article text
            
        Returns:
            Dictionary with sentiment analysis
        """
        # Simple keyword-based sentiment (can be enhanced with ML models)
        positive_keywords = ['launch', 'success', 'improve', 'new', 'initiative', 'progress', 'achieve']
        negative_keywords = ['problem', 'issue', 'fail', 'crisis', 'accident', 'protest', 'delay']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        
        if positive_count > negative_count:
            tone = "Positive"
        elif negative_count > positive_count:
            tone = "Negative"
        else:
            tone = "Neutral"
        
        return {
            'tone': tone,
            'sentiment_score': positive_count - negative_count,
            'confidence': 'medium'
        }
    
    def enrich_article(self, article: Dict) -> Dict:
        """
        Add additional metadata to article
        
        Args:
            article: Processed article
            
        Returns:
            Enriched article
        """
        enriched = article.copy()
        
        # Add sentiment analysis
        text = article.get('ai_summary', '') or article.get('description', '')
        sentiment = self.analyze_sentiment_tone(text)
        enriched['sentiment'] = sentiment
        
        # Add category suggestions
        categories = self._suggest_categories(article)
        enriched['suggested_categories'] = categories
        
        # Add recommendations
        recommendations = self._generate_recommendations(article)
        enriched['recommendations'] = recommendations
        
        return enriched
    
    def _suggest_categories(self, article: Dict) -> List[str]:
        """Suggest categories based on content"""
        categories = []
        text = (article.get('ai_summary', '') + ' ' + article.get('title', '')).lower()
        
        category_keywords = {
            'Civic Updates': ['municipal', 'corporation', 'ward', 'civic', 'infrastructure'],
            'Environment': ['waste', 'pollution', 'green', 'environment', 'recycle'],
            'Transport': ['traffic', 'road', 'metro', 'bus', 'transport'],
            'Education': ['school', 'college', 'education', 'student', 'exam'],
            'Health': ['hospital', 'health', 'medical', 'doctor', 'clinic'],
            'Politics': ['minister', 'election', 'party', 'government', 'political'],
            'Business': ['business', 'market', 'economy', 'trade', 'industry']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)
        
        return categories if categories else ['General News']
    
    def _generate_recommendations(self, article: Dict) -> str:
        """Generate recommendations for article visibility"""
        recommendations = []
        
        # Location-based recommendation
        if article.get('primary_location'):
            loc_name = article['primary_location']['name']
            recommendations.append(f"Push notification to residents in {loc_name}")
        
        # Category-based recommendation
        if article.get('suggested_categories'):
            categories = ', '.join(article['suggested_categories'])
            recommendations.append(f"Highlight in '{categories}' category")
        
        # Entity-based recommendation
        entities = article.get('named_entities', {})
        if entities.get('ORG'):
            orgs = ', '.join(entities['ORG'][:2])
            recommendations.append(f"Tag organizations: {orgs}")
        
        return '; '.join(recommendations) if recommendations else "Standard publishing"

