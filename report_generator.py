"""
Report Generator Module
Generates formatted reports in table format
"""

import logging
from datetime import datetime
from typing import List, Dict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates formatted reports for processed articles"""
    
    def __init__(self):
        self.report_date = datetime.now().strftime("%d %b %Y")
    
    def generate_article_report(self, article: Dict) -> Dict:
        """
        Generate report for a single article
        
        Args:
            article: Processed article dictionary
            
        Returns:
            Formatted report dictionary
        """
        # Get source languages
        detected_lang = article.get('detected_language', 'unknown')
        lang_name = self._get_language_name(detected_lang)
        
        # Get translations info
        translations = article.get('translations', {})
        target_languages = list(translations.keys())
        target_lang_names = [self._get_language_name(lang) for lang in target_languages]
        
        # Get entities formatted
        entities = article.get('named_entities', {})
        entities_formatted = self._format_entities_for_report(entities)
        
        # Get geo-tagging
        geo_display = article.get('geo_display', 'Location not identified')
        primary_loc = article.get('primary_location', {})
        
        # Get sentiment
        sentiment = article.get('sentiment', {})
        tone = sentiment.get('tone', 'Neutral')
        
        # Get audio files
        audio_files = article.get('audio_files', {})
        audio_summary = self._format_audio_summary(audio_files)
        
        # Get recommendations
        recommendations = article.get('recommendations', 'Standard publishing')
        
        report = {
            'Topic Analyzed': {
                'Input feed/source': f"{article.get('feed_type', 'Unknown')}: {article.get('source', 'Unknown')}"
            },
            'Languages Ingested': {
                'Source languages detected': lang_name
            },
            'Translation (if required)': {
                'Standardized output language': ', '.join(target_lang_names)
            },
            'Raw Article Example': {
                'Title & snippet before summarization': f"{article.get('title', 'N/A')[:100]}..."
            },
            'AI Summary (short)': {
                'Auto-generated concise version': article.get('ai_summary', 'N/A')
            },
            'Named Entity Recognition (NER)': {
                'Persons, Orgs, Places, Dates': entities_formatted
            },
            'Geo-tagging': {
                'Location coordinates for map display': geo_display
            },
            'Emotion / Tone': {
                'Sentiment / tone of the article': f"Tone: {tone}"
            },
            'Voice Summary Output': {
                'Accessibility feature': audio_summary
            },
            'Portal/App Publishing Status': {
                'Final action': article.get('publishing_status', 'Ready for publishing')
            },
            'Recommendations / Next Action': {
                'System suggestion': recommendations
            }
        }
        
        return report
    
    def generate_batch_report(self, articles: List[Dict], location: str = "Nagpur") -> Dict:
        """
        Generate batch report for multiple articles
        
        Args:
            articles: List of processed articles
            location: Location name for report header
            
        Returns:
            Complete batch report
        """
        batch_report = {
            'report_metadata': {
                'location': location,
                'date': self.report_date,
                'total_articles': len(articles),
                'generated_at': datetime.now().isoformat()
            },
            'articles': []
        }
        
        for i, article in enumerate(articles, 1):
            article_report = self.generate_article_report(article)
            article_report['article_number'] = i
            article_report['article_id'] = article.get('link', f'article_{i}')
            batch_report['articles'].append(article_report)
        
        return batch_report
    
    def format_report_table(self, report: Dict) -> str:
        """
        Format report as markdown table

        Args:
            report: Report dictionary

        Returns:
            Formatted markdown string
        """
        lines = []
        lines.append("## Hyperlocal News Summarizer – Sample Report\n")
        lines.append(f"**Location:** {report.get('report_metadata', {}).get('location', 'Unknown')}")
        lines.append(f"**Date:** {report.get('report_metadata', {}).get('date', 'Unknown')}")
        lines.append(f"**Total Articles:** {report.get('report_metadata', {}).get('total_articles', 0)}\n")
        
        for article_data in report.get('articles', []):
            article_num = article_data.get('article_number', 0)
            lines.append(f"\n### Article {article_num}\n")
            lines.append("| Section | Data Captured | Example Output |")
            lines.append("|---------|---------------|----------------|")
            
            for section, data in article_data.items():
                if section in ['article_number', 'article_id']:
                    continue
                if isinstance(data, dict):
                    for key, value in data.items():
                        # Truncate long values
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        lines.append(f"| {section} | {key} | {value} |")
        
        return "\n".join(lines)
    
    def format_report_html(self, report: Dict) -> str:
        """
        Format report as HTML table
        
        Args:
            report: Report dictionary
            
        Returns:
            Formatted HTML string
        """
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html><head>")
        html.append("<meta charset='UTF-8'>")
        html.append("<title>Hyperlocal News Summarizer Report</title>")
        html.append("<style>")
        html.append("""
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .header { background-color: #2196F3; color: white; padding: 15px; }
        """)
        html.append("</style></head><body>")
        
        metadata = report.get('report_metadata', {})
        html.append(f"<div class='header'>")
        html.append(f"<h1>Hyperlocal News Summarizer Report</h1>")
        html.append(f"<p><strong>Location:</strong> {metadata.get('location', 'Unknown')}</p>")
        html.append(f"<p><strong>Date:</strong> {metadata.get('date', 'Unknown')}</p>")
        html.append(f"<p><strong>Total Articles:</strong> {metadata.get('total_articles', 0)}</p>")
        html.append("</div>")
        
        for article_data in report.get('articles', []):
            article_num = article_data.get('article_number', 0)
            html.append(f"<h2>Article {article_num}</h2>")
            html.append("<table>")
            html.append("<tr><th>Section</th><th>Data Captured</th><th>Example Output</th></tr>")
            
            for section, data in article_data.items():
                if section in ['article_number', 'article_id']:
                    continue
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        html.append(f"<tr><td>{section}</td><td>{key}</td><td>{value}</td></tr>")
            
            html.append("</table>")
        
        html.append("</body></html>")
        return "\n".join(html)
    
    def _get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name"""
        lang_names = {
            'en': 'English',
            'hi': 'Hindi',
            'mr': 'Marathi',
            'ta': 'Tamil',
            'te': 'Telugu',
            'kn': 'Kannada',
            'gu': 'Gujarati',
            'bn': 'Bengali',
            'pa': 'Punjabi',
            'ml': 'Malayalam',
            'or': 'Odia'
        }
        return lang_names.get(lang_code.lower(), lang_code.upper())
    
    def _format_entities_for_report(self, entities: Dict) -> str:
        """Format entities for report display"""
        parts = []
        
        if entities.get('PERSON'):
            persons = ', '.join(entities['PERSON'][:3])
            parts.append(f"Persons: {persons}")
        
        if entities.get('ORG'):
            orgs = ', '.join(entities['ORG'][:3])
            parts.append(f"Organizations: {orgs}")
        
        if entities.get('GPE') or entities.get('LOC'):
            locations = (entities.get('GPE', []) + entities.get('LOC', []))[:3]
            locs = ', '.join(locations)
            parts.append(f"Locations: {locs}")
        
        if entities.get('DATE'):
            dates = ', '.join(entities['DATE'][:2])
            parts.append(f"Dates: {dates}")
        
        return '; '.join(parts) if parts else "No entities detected"
    
    def _format_audio_summary(self, audio_files: Dict) -> str:
        """Format audio file information"""
        if not audio_files:
            return "No audio generated"
        
        lang_names = {
            'en': 'English',
            'hi': 'Hindi',
            'mr': 'Marathi'
        }
        
        parts = []
        for lang, filepath in audio_files.items():
            lang_name = lang_names.get(lang, lang.upper())
            filename = filepath.split('/')[-1] if '/' in filepath else filepath
            parts.append(f"{lang_name}: {filename}")
        
        return '; '.join(parts)

