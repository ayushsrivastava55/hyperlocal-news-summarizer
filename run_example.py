"""
Example script to demonstrate the workflow
Run this to test the system without the web interface
"""

from workflow import HyperlocalNewsWorkflow
from report_generator import ReportGenerator
from feed_collector import NAGPUR_FEED_CONFIGS
import json

def main():
    print("🚀 Starting Hyperlocal News Summarizer Workflow\n")
    
    # Initialize workflow
    workflow = HyperlocalNewsWorkflow(target_languages=['en', 'mr', 'hi'])
    report_generator = ReportGenerator()
    
    # Process feeds
    print("📡 Collecting news feeds...")
    articles = workflow.process_feeds(NAGPUR_FEED_CONFIGS)
    
    if not articles:
        print("⚠️  No articles collected. This might be due to:")
        print("   - Network connectivity issues")
        print("   - RSS feed URLs not accessible")
        print("   - Rate limiting")
        print("\n💡 Try using the web interface or check feed URLs")
        return
    
    print(f"✅ Collected {len(articles)} articles\n")
    
    # Enrich articles
    print("🔍 Enriching articles with sentiment and categories...")
    enriched_articles = []
    for i, article in enumerate(articles, 1):
        enriched = workflow.enrich_article(article)
        enriched['publishing_status'] = 'Published to Community Portal'
        enriched_articles.append(enriched)
        print(f"   Processed article {i}/{len(articles)}")
    
    print(f"\n✅ Enriched {len(enriched_articles)} articles\n")
    
    # Display sample article
    if enriched_articles:
        print("=" * 80)
        print("📰 SAMPLE ARTICLE")
        print("=" * 80)
        sample = enriched_articles[0]
        
        print(f"\nTitle: {sample.get('title', 'N/A')}")
        print(f"Source: {sample.get('source', 'N/A')}")
        print(f"Language: {sample.get('detected_language', 'N/A')}")
        print(f"\nSummary: {sample.get('ai_summary', 'N/A')}")
        
        entities = sample.get('named_entities', {})
        print(f"\nEntities:")
        if entities.get('PERSON'):
            print(f"  Persons: {', '.join(entities['PERSON'][:3])}")
        if entities.get('ORG'):
            print(f"  Organizations: {', '.join(entities['ORG'][:3])}")
        if entities.get('GPE') or entities.get('LOC'):
            locations = (entities.get('GPE', []) + entities.get('LOC', []))[:3]
            print(f"  Locations: {', '.join(locations)}")
        
        if sample.get('primary_location'):
            loc = sample['primary_location']
            print(f"\n📍 Location: {loc['name']}")
            print(f"   Coordinates: {loc['latitude']:.4f}°N, {loc['longitude']:.4f}°E")
        
        sentiment = sample.get('sentiment', {})
        print(f"\nSentiment: {sentiment.get('tone', 'N/A')}")
        
        categories = sample.get('suggested_categories', [])
        print(f"Categories: {', '.join(categories)}")
        
        print(f"\nRecommendations: {sample.get('recommendations', 'N/A')}")
        print("=" * 80)
    
    # Generate report
    print("\n📊 Generating report...")
    report = report_generator.generate_batch_report(enriched_articles, location="Nagpur")
    
    # Save report
    report_file = "report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"✅ Report saved to {report_file}")
    
    # Generate HTML report
    html_report = report_generator.format_report_html(report)
    html_file = "report.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"✅ HTML report saved to {html_file}")
    
    # Generate Markdown report
    md_report = report_generator.format_report_table(report)
    md_file = "report.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_report)
    print(f"✅ Markdown report saved to {md_file}")
    
    print("\n🎉 Workflow complete!")
    print(f"\n📈 Statistics:")
    print(f"   Total articles: {len(enriched_articles)}")
    
    # Count languages
    languages = {}
    for article in enriched_articles:
        lang = article.get('detected_language', 'unknown')
        languages[lang] = languages.get(lang, 0) + 1
    print(f"   Languages: {', '.join(languages.keys())}")
    
    # Count locations
    locations = set()
    for article in enriched_articles:
        if article.get('primary_location'):
            locations.add(article['primary_location']['name'])
    print(f"   Unique locations: {len(locations)}")

if __name__ == '__main__':
    main()

