# 📰 Hyperlocal News Summarizer

A comprehensive system for collecting, processing, and summarizing hyperlocal news articles with multi-language support, NLP processing, geo-tagging, and voice synthesis.

## Features

- **Multi-language News Ingestion**: Collects news from RSS feeds and APIs
- **Text Summarization**: Uses HuggingFace models (BART) for automatic summarization
- **Named Entity Recognition (NER)**: Extracts persons, organizations, locations, dates, and events
- **Indic Language Support**: Supports Hindi, Marathi, Tamil, Telugu, Kannada, Gujarati, Bengali, Punjabi, Malayalam, and Odia
- **Geo-tagging**: Automatically extracts and geocodes location information
- **Voice Summary Output**: Generates audio summaries in multiple languages for accessibility
- **Community Portal**: Modern web dashboard for viewing and managing news articles
- **Report Generation**: Generates formatted reports in HTML and Markdown formats

## Project Structure

```
ml-cp/
├── app.py                 # Flask web application
├── feed_collector.py      # RSS/API feed collection
├── translator.py          # Translation module
├── nlp_processor.py       # Summarization and NER
├── geo_tagger.py          # Location extraction and geocoding
├── voice_synthesizer.py   # Audio generation
├── workflow.py            # Main workflow orchestrator
├── report_generator.py    # Report generation
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Web dashboard
└── README.md             # This file
```

## Installation

### 1. Clone the repository

```bash
cd /Users/ayush/Documents/clg-sem5/ml-cp
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install spaCy English model

```bash
python -m spacy download en_core_web_sm
```

## Usage

### Web Portal (Recommended)

1. Start the Flask application:

```bash
python app.py
```

2. Open your browser and navigate to:

```
http://localhost:5000
```

3. Click "Process News Feeds" to start collecting and processing articles

4. View articles, generate reports, and download summaries

### Command Line Usage

You can also use the modules programmatically:

```python
from workflow import HyperlocalNewsWorkflow
from feed_collector import NAGPUR_FEED_CONFIGS

# Initialize workflow
workflow = HyperlocalNewsWorkflow(target_languages=['en', 'mr', 'hi'])

# Process feeds
articles = workflow.process_feeds(NAGPUR_FEED_CONFIGS)

# Process individual article
for article in articles:
    enriched = workflow.enrich_article(article)
    print(f"Title: {enriched['title']}")
    print(f"Summary: {enriched['ai_summary']}")
    print(f"Entities: {enriched['named_entities']}")
```

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/articles` - Get all processed articles
- `GET /api/articles/<id>` - Get specific article
- `POST /api/process` - Process news feeds
- `GET /api/report` - Generate JSON report
- `GET /api/report/html` - Generate HTML report
- `GET /api/report/markdown` - Generate Markdown report
- `GET /api/stats` - Get statistics
- `GET /audio/<filename>` - Serve audio files

## Report Format

The system generates reports in the following format:

| Section | Data Captured | Example Output |
|---------|---------------|----------------|
| Topic Analyzed | Input feed/source | RSS: Lokmat Nagpur |
| Languages Ingested | Source languages detected | Marathi, Hindi, English |
| Translation (if required) | Standardized output language | Translated into Marathi & English |
| Raw Article Example | Title & snippet | "Nagpur Municipal Corporation launches..." |
| AI Summary (short) | Auto-generated concise version | "Nagpur civic body begins waste segregation..." |
| Named Entity Recognition (NER) | Persons, Orgs, Places, Dates | Entities: Nagpur Municipal Corporation(ORG), Nagpur (LOC) |
| Geo-tagging | Location coordinates | Nagpur, Maharashtra – Lat: 21.1458°N, Long: 79.0882°E |
| Emotion / Tone | Sentiment / tone | Tone: Neutral–Positive |
| Voice Summary Output | Accessibility feature | Generated audio in Marathi & Hindi |
| Portal/App Publishing Status | Final action | Published to Community Portal |
| Recommendations / Next Action | System suggestion | Highlight in "Environment & Civic" category |

## Configuration

### Feed Configuration

Edit `feed_collector.py` to add your RSS feeds or API endpoints:

```python
FEED_CONFIGS = [
    {
        'type': 'RSS',
        'url': 'https://example.com/rss',
        'name': 'Example News'
    },
    {
        'type': 'API',
        'url': 'https://api.example.com/news',
        'api_key': 'your-api-key',
        'name': 'Example API'
    }
]
```

### Target Languages

Modify target languages in `app.py`:

```python
workflow = HyperlocalNewsWorkflow(target_languages=['en', 'mr', 'hi', 'ta'])
```

## Dependencies

- **Flask**: Web framework
- **transformers**: HuggingFace models for summarization
- **spacy**: Named Entity Recognition
- **googletrans**: Translation services
- **geopy**: Geocoding
- **gTTS**: Text-to-speech
- **feedparser**: RSS feed parsing
- **beautifulsoup4**: HTML parsing

## Troubleshooting

### spaCy model not found

```bash
python -m spacy download en_core_web_sm
```

### Translation errors

The `googletrans` library may have rate limits. If you encounter errors, wait a few seconds and retry.

### Audio generation fails

Ensure you have an internet connection for gTTS to work. Audio files are saved in the `audio_output/` directory.

### Memory issues with large models

If you encounter memory issues, consider:
- Using a smaller summarization model
- Processing fewer articles at a time
- Using CPU instead of GPU

## Future Enhancements

- [ ] Database integration for persistent storage
- [ ] Real-time feed updates
- [ ] Advanced sentiment analysis with ML models
- [ ] Interactive map visualization
- [ ] User authentication and personalization
- [ ] Mobile app integration
- [ ] Push notifications
- [ ] Advanced analytics dashboard

## License

This project is part of a college assignment (ML-CP).

## Contributors

- Developed as part of ML-CP coursework

## Notes

- The system uses free APIs and services which may have rate limits
- For production use, consider using paid APIs for better reliability
- Some features require internet connectivity (translation, geocoding, TTS)

