"""
Flask Web Application
Community Portal for Hyperlocal News Summarizer
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from pathlib import Path
from workflow import HyperlocalNewsWorkflow
from report_generator import ReportGenerator
from feed_collector import NAGPUR_FEED_CONFIGS
from feed_discovery import discover_feeds_by_city, fetch_city_news_via_serpapi
from config import SERPAPI_API_KEY, TARGET_LANGUAGES
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Initialize components (lazy loading for faster startup)
print("🚀 Starting Hyperlocal News Summarizer...")
print("📦 Initializing components (models will load on first use)...")
workflow = HyperlocalNewsWorkflow(target_languages=TARGET_LANGUAGES, fast_mode=False)
report_generator = ReportGenerator()
print("✅ Application ready! Models will load when processing articles.")

# Storage for processed articles (in production, use a database)
processed_articles = []
seen_links = set()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Get all processed articles"""
    return jsonify({
        'articles': processed_articles,
        'count': len(processed_articles)
    })


@app.route('/api/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """Get a specific article by ID"""
    if 0 <= article_id < len(processed_articles):
        return jsonify(processed_articles[article_id])
    return jsonify({'error': 'Article not found'}), 404


@app.route('/api/process', methods=['POST'])
def process_feeds():
    """Process news feeds"""
    try:
        body = request.json or {}
        feed_configs = body.get('feed_configs', NAGPUR_FEED_CONFIGS)
        limit_per_feed = int(body.get('limit_per_feed', 5))
        max_total = body.get('max_total')
        max_total = int(max_total) if max_total is not None else None
        fast = bool(body.get('fast', False))
        offset = int(body.get('offset', 0))
        reset_seen = bool(body.get('reset_seen', False))
        global seen_links
        if reset_seen:
            seen_links = set()
        
        if fast and not workflow.fast_mode:
            # enable fast mode for this run
            globals()['workflow'] = HyperlocalNewsWorkflow(target_languages=['en', 'mr', 'hi'], fast_mode=True)
        
        # Process feeds
        articles = workflow.process_feeds(feed_configs, limit_per_feed=limit_per_feed, max_total=max_total, seen_links=seen_links, offset=offset)
        
        # Enrich articles
        enriched_articles = []
        for article in articles:
            enriched = workflow.enrich_article(article)
            enriched['publishing_status'] = 'Published to Community Portal'
            enriched_articles.append(enriched)
            # Track link as seen to avoid repetition on subsequent runs
            link = (enriched.get('link') or '').strip()
            key = link or f"{enriched.get('title','')}-{enriched.get('published','')}"
            if key:
                seen_links.add(key)
        
        # Update storage
        processed_articles.clear()
        processed_articles.extend(enriched_articles)
        
        return jsonify({
            'success': True,
            'articles_processed': len(enriched_articles),
            'articles': enriched_articles
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collect', methods=['POST'])
def collect_only():
    """Collect raw articles from feeds without NLP processing"""
    try:
        body = request.json or {}
        feed_configs = body.get('feed_configs', NAGPUR_FEED_CONFIGS)
        limit_per_feed = int(body.get('limit_per_feed', 5))
        raw_articles = workflow.feed_collector.collect_multiple_feeds(feed_configs, per_feed_limit=limit_per_feed)
        return jsonify({'count': len(raw_articles), 'articles': raw_articles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Basic health check"""
    return jsonify({
        'status': 'ok',
        'articles_cached': len(processed_articles),
        'nlp_lazy_loaded': True,
        'serpapi_configured': bool(SERPAPI_API_KEY)
    })


@app.route('/api/report', methods=['GET'])
def get_report():
    """Generate and return report"""
    try:
        location = request.args.get('location', 'Nagpur')
        report = report_generator.generate_batch_report(processed_articles, location)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/html', methods=['GET'])
def get_report_html():
    """Generate and return HTML report"""
    try:
        location = request.args.get('location', 'Nagpur')
        report = report_generator.generate_batch_report(processed_articles, location)
        html = report_generator.format_report_html(report)
        return html
    except Exception as e:
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", 500


@app.route('/api/report/markdown', methods=['GET'])
def get_report_markdown():
    """Generate and return Markdown report"""
    try:
        location = request.args.get('location', 'Nagpur')
        report = report_generator.generate_batch_report(processed_articles, location)
        markdown = report_generator.format_report_table(report)
        return markdown, 200, {'Content-Type': 'text/markdown; charset=utf-8'}
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/api/discover-feeds', methods=['POST'])
def api_discover_feeds():
    """Discover RSS/feed URLs for a given city using SerpAPI Google Search."""
    try:
        if not SERPAPI_API_KEY:
            return jsonify({'success': False, 'error': 'SERPAPI_API_KEY not configured'}), 400
        payload = request.json or {}
        city = (payload.get('city') or '').strip()
        max_results = int(payload.get('max_results', 8))
        if not city:
            return jsonify({'success': False, 'error': 'City is required'}), 400
        feeds = discover_feeds_by_city(city, max_results=max_results)
        return jsonify({'success': True, 'feeds': feeds})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/serp-news', methods=['POST'])
def api_serp_news():
    """Fetch recent city news via SerpAPI Google News (fallback when RSS is not available)."""
    try:
        if not SERPAPI_API_KEY:
            return jsonify({'success': False, 'error': 'SERPAPI_API_KEY not configured'}), 400
        payload = request.json or {}
        city = (payload.get('city') or '').strip()
        max_results = int(payload.get('max_results', 10))
        process_flag = bool(payload.get('process', False))
        fast = bool(payload.get('fast', False))
        if not city:
            return jsonify({'success': False, 'error': 'City is required'}), 400

        # Optionally toggle fast mode for processing
        if process_flag and fast and not workflow.fast_mode:
            globals()['workflow'] = HyperlocalNewsWorkflow(target_languages=['en', 'mr', 'hi'], fast_mode=True)

        articles = fetch_city_news_via_serpapi(city, max_results=max_results)

        if not process_flag:
            # Return raw articles (no NLP processing)
            return jsonify({'success': True, 'articles': articles, 'count': len(articles)})

        # Process and enrich articles through the full pipeline
        enriched_articles = []
        for article in articles:
            processed = workflow.process_single_article(article)
            enriched = workflow.enrich_article(processed)
            enriched['publishing_status'] = f'Processed via SerpAPI for {city}'
            enriched_articles.append(enriched)

        # Update cache
        processed_articles.clear()
        processed_articles.extend(enriched_articles)

        return jsonify({
            'success': True,
            'articles': enriched_articles,
            'articles_processed': len(enriched_articles),
            'city': city,
            'fast_mode': workflow.fast_mode
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files"""
    audio_dir = Path('audio_output')
    if audio_dir.exists():
        return send_from_directory(str(audio_dir), filename)
    return "Audio file not found", 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about processed articles"""
    if not processed_articles:
        return jsonify({
            'total_articles': 0,
            'languages': {},
            'locations': [],
            'categories': {}
        })
    
    # Count languages
    languages = {}
    for article in processed_articles:
        detected = article.get('detected_language', 'unknown')
        languages[detected] = languages.get(detected, 0) + 1
    
    # Extract locations
    locations = []
    for article in processed_articles:
        if article.get('primary_location'):
            loc_name = article['primary_location']['name']
            if loc_name not in locations:
                locations.append(loc_name)
    
    # Count categories
    categories = {}
    for article in processed_articles:
        cats = article.get('suggested_categories', ['General News'])
        for cat in cats:
            categories[cat] = categories.get(cat, 0) + 1
    
    return jsonify({
        'total_articles': len(processed_articles),
        'languages': languages,
        'locations': locations,
        'categories': categories
    })


if __name__ == '__main__':
    # Create necessary directories
    Path('audio_output').mkdir(exist_ok=True)
    Path('templates').mkdir(exist_ok=True)
    Path('static').mkdir(exist_ok=True)
    
    # Use port 5001 to avoid conflict with AirPlay Receiver on macOS
    port = 5001
    print(f"🌐 Starting server on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

